"""Sign-in-free spend controls for the public Waltzman deployment (ADR-016).

The public demo stays open to anyone: no login, password, or access code. Spend on
the metered LLM route is bounded instead by two controls applied only to requests
that start provider-backed work:

* a per-visitor rate limit keyed by the client address Cloudflare reports in
  ``CF-Connecting-IP``, and
* a global daily cap on new live runs and on authoring attempts, persisted on the
  durable data disk so a container restart does not reset it.

Read, replay, progress, and scripted (provider-free) requests are never counted.
A refused request gets HTTP 429 with a plain-language ``detail`` string, which the
public page already renders verbatim in its run/authoring status line. A request
the application itself rejects (status >= 400) gives its reserved slot back, so a
validation error never consumes the day's capacity.

Per-call ``max_budget`` ceilings and call-count limits in ``run_configuration`` still
bound each run; these controls bound how many runs there can be.
"""

from __future__ import annotations

import json
import os
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal

SpendKind = Literal["run", "authoring"]

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

DEFAULT_DAILY_RUN_CAP = 10
DEFAULT_DAILY_AUTHORING_CAP = 30
DEFAULT_PER_IP_RUNS_PER_HOUR = 3
DEFAULT_PER_IP_AUTHORING_PER_HOUR = 12
_RATE_WINDOW_SECONDS = 3600.0
_MAX_BUFFERED_BODY_BYTES = 2 * 1024 * 1024

_DRAFT_RUNS = re.compile(r"^/api/authoring/drafts/[^/]+/runs$")
_DRAFT_EXPERIMENTS = re.compile(r"^/api/authoring/drafts/[^/]+/experiments$")
_DRAFT_MESSAGES = re.compile(r"^/api/authoring/drafts/[^/]+/messages$")
_RUN_RESUME = re.compile(r"^/api/runs/[^/]+/resume$")
_PUBLIC_UNDELETABLE = re.compile(
    r"^/api/(runs|composite-assays|coordination-experiments)/[^/]+/?$"
)


@dataclass(frozen=True)
class SpendControlSettings:
    """Operator-configured limits; every value is overridable by environment."""

    state_path: Path
    daily_run_cap: int = DEFAULT_DAILY_RUN_CAP
    daily_authoring_cap: int = DEFAULT_DAILY_AUTHORING_CAP
    per_ip_runs_per_hour: int = DEFAULT_PER_IP_RUNS_PER_HOUR
    per_ip_authoring_per_hour: int = DEFAULT_PER_IP_AUTHORING_PER_HOUR

    @classmethod
    def from_env(cls, default_state_path: Path) -> SpendControlSettings:
        return cls(
            state_path=Path(
                os.getenv("CYBERNETIC_INFLUENCE_SPEND_STATE", str(default_state_path))
            ),
            daily_run_cap=_env_int(
                "CYBERNETIC_INFLUENCE_DAILY_RUN_CAP", DEFAULT_DAILY_RUN_CAP
            ),
            daily_authoring_cap=_env_int(
                "CYBERNETIC_INFLUENCE_DAILY_AUTHORING_CAP",
                DEFAULT_DAILY_AUTHORING_CAP,
            ),
            per_ip_runs_per_hour=_env_int(
                "CYBERNETIC_INFLUENCE_PER_IP_RUNS_PER_HOUR",
                DEFAULT_PER_IP_RUNS_PER_HOUR,
            ),
            per_ip_authoring_per_hour=_env_int(
                "CYBERNETIC_INFLUENCE_PER_IP_AUTHORING_PER_HOUR",
                DEFAULT_PER_IP_AUTHORING_PER_HOUR,
            ),
        )


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    value = int(raw)  # a malformed operator value must fail loudly at startup
    if value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {raw!r}")
    return value


def _noun(kind: SpendKind, count: int) -> str:
    singular = "live simulation" if kind == "run" else "authoring request"
    return singular if count == 1 else f"{singular}s"


@dataclass(frozen=True)
class Refusal:
    """A plain-language refusal returned to the visitor."""

    error: str
    detail: str
    retry_after_seconds: int


@dataclass
class _Reservation:
    kind: SpendKind
    weight: int
    day: str


@dataclass
class SpendLedger:
    """Thread-safe daily counters (durable) and per-address windows (in memory)."""

    settings: SpendControlSettings
    clock: Callable[[], float] = time.time
    _lock: Lock = field(default_factory=Lock)
    _recent: dict[tuple[str, SpendKind], deque[float]] = field(default_factory=dict)

    def _today(self) -> str:
        return datetime.fromtimestamp(self.clock(), tz=timezone.utc).strftime("%Y-%m-%d")

    def _seconds_until_utc_midnight(self) -> int:
        now = datetime.fromtimestamp(self.clock(), tz=timezone.utc)
        midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max(1, int((midnight - now).total_seconds()))

    def _load(self) -> dict[str, Any]:
        path = self.settings.state_path
        if not path.exists():
            return {}
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError(f"spend state {path} is not a JSON object")
        return document

    def _save(self, document: dict[str, Any]) -> None:
        path = self.settings.state_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        temporary.replace(path)

    def _cap(self, kind: SpendKind) -> int:
        return (
            self.settings.daily_run_cap
            if kind == "run"
            else self.settings.daily_authoring_cap
        )

    def _per_ip_limit(self, kind: SpendKind) -> int:
        return (
            self.settings.per_ip_runs_per_hour
            if kind == "run"
            else self.settings.per_ip_authoring_per_hour
        )

    def status(self) -> dict[str, object]:
        """UI-safe snapshot of today's usage and the configured limits."""
        with self._lock:
            document = self._load()
            today = self._today()
            used = document.get("counts", {}) if document.get("day") == today else {}
            return {
                "day_utc": today,
                "live_runs": {
                    "used": int(used.get("run", 0)),
                    "daily_cap": self.settings.daily_run_cap,
                    "per_visitor_per_hour": self.settings.per_ip_runs_per_hour,
                },
                "authoring": {
                    "used": int(used.get("authoring", 0)),
                    "daily_cap": self.settings.daily_authoring_cap,
                    "per_visitor_per_hour": self.settings.per_ip_authoring_per_hour,
                },
            }

    def reserve(
        self, kind: SpendKind, weight: int, client: str
    ) -> _Reservation | Refusal:
        now = self.clock()
        with self._lock:
            window = self._recent.setdefault((client, kind), deque())
            while window and now - window[0] >= _RATE_WINDOW_SECONDS:
                window.popleft()
            limit = self._per_ip_limit(kind)
            if len(window) + weight > limit:
                noun = _noun(kind, limit)
                retry = (
                    int(_RATE_WINDOW_SECONDS - (now - window[0])) + 1
                    if window
                    else int(_RATE_WINDOW_SECONDS)
                )
                return Refusal(
                    error="per_visitor_rate_limited",
                    detail=(
                        f"This public demo allows {limit} {noun} per visitor per hour, "
                        f"and that limit has been reached from your connection. "
                        f"Try again in about {max(1, retry // 60)} minutes. "
                        "Retained runs and replays remain available."
                    ),
                    retry_after_seconds=retry,
                )
            document = self._load()
            today = self._today()
            if document.get("day") != today:
                document = {"day": today, "counts": {}}
            counts = document.setdefault("counts", {})
            used = int(counts.get(kind, 0))
            cap = self._cap(kind)
            if used + weight > cap:
                noun = _noun(kind, cap)
                return Refusal(
                    error=(
                        "daily_run_cap_reached"
                        if kind == "run"
                        else "daily_authoring_cap_reached"
                    ),
                    detail=(
                        f"Today's public limit of {cap} {noun} has been reached "
                        f"({used} used). It resets at 00:00 UTC. Retained runs and "
                        "replays remain available."
                    ),
                    retry_after_seconds=self._seconds_until_utc_midnight(),
                )
            counts[kind] = used + weight
            self._save(document)
            for _ in range(weight):
                window.append(now)
            return _Reservation(kind=kind, weight=weight, day=today)

    def release(self, reservation: _Reservation, client: str) -> None:
        """Return a slot for a request the application rejected."""
        with self._lock:
            document = self._load()
            if document.get("day") == reservation.day:
                counts = document.setdefault("counts", {})
                counts[reservation.kind] = max(
                    0, int(counts.get(reservation.kind, 0)) - reservation.weight
                )
                self._save(document)
            window = self._recent.get((client, reservation.kind))
            for _ in range(reservation.weight):
                if window:
                    window.pop()


def classify_request(
    method: str, path: str, body: bytes
) -> tuple[SpendKind, int] | None:
    """Return the spend class and weight of a request, or None if it is free."""
    if method != "POST":
        return None
    if path == "/api/runs" or _DRAFT_RUNS.match(path):
        return ("run", 1) if _json_field(body, "execution") == "live" else None
    if _DRAFT_EXPERIMENTS.match(path):
        conditions = _json_field(body, "conditions")
        weight = len(conditions) if isinstance(conditions, list) and conditions else 1
        return ("run", weight)
    if _RUN_RESUME.match(path):
        return ("run", 1)
    if _DRAFT_MESSAGES.match(path):
        return ("authoring", 1)
    return None


def _json_field(body: bytes, name: str) -> object:
    try:
        document = json.loads(body or b"null")
    except ValueError:
        return None
    return document.get(name) if isinstance(document, dict) else None


def client_address(scope: Scope) -> str:
    """Cloudflare's reported visitor address, else the socket peer."""
    for key, value in scope.get("headers", []):
        if key == b"cf-connecting-ip":
            text = bytes(value).decode("latin-1").strip()
            if text:
                return text
    peer = scope.get("client")
    return str(peer[0]) if peer else "unknown"


class SpendControlMiddleware:
    """Pure ASGI middleware so the request body can be inspected and replayed."""

    def __init__(self, app: ASGIApp, ledger: SpendLedger) -> None:
        self.app = app
        self.ledger = ledger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("method") == "DELETE"
            and _PUBLIC_UNDELETABLE.match(str(scope.get("path", "")))
        ):
            # The store is durable and public; one anonymous request must not be able
            # to erase retained evidence. Operators delete on the host (ADR-016).
            await _json_response(
                send,
                403,
                {
                    "error": "public_delete_disabled",
                    "detail": (
                        "Deleting retained runs, assays, or experiments is disabled "
                        "on the public demo."
                    ),
                },
            )
            return
        if scope.get("type") != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        path = str(scope.get("path", ""))
        if not (
            path == "/api/runs"
            or _DRAFT_RUNS.match(path)
            or _DRAFT_EXPERIMENTS.match(path)
            or _RUN_RESUME.match(path)
            or _DRAFT_MESSAGES.match(path)
        ):
            await self.app(scope, receive, send)
            return

        chunks: list[bytes] = []
        size = 0
        more = True
        while more:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > _MAX_BUFFERED_BODY_BYTES:
                await _json_response(
                    send,
                    413,
                    {"error": "request_too_large", "detail": "Request body is too large."},
                )
                return
            chunks.append(chunk)
            more = bool(message.get("more_body", False))
        body = b"".join(chunks)

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        classification = classify_request("POST", path, body)
        if classification is None:
            await self.app(scope, replay, send)
            return
        kind, weight = classification
        client = client_address(scope)
        outcome = self.ledger.reserve(kind, weight, client)
        if isinstance(outcome, Refusal):
            await _json_response(
                send,
                429,
                {
                    "error": outcome.error,
                    "detail": outcome.detail,
                    "retry_after_seconds": outcome.retry_after_seconds,
                },
                extra_headers=[(b"retry-after", str(outcome.retry_after_seconds).encode())],
            )
            return

        status_holder: dict[str, int] = {}

        async def observe(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = int(message["status"])
            await send(message)

        try:
            await self.app(scope, replay, observe)
        except BaseException:
            self.ledger.release(outcome, client)
            raise
        if status_holder.get("status", 500) >= 400:
            self.ledger.release(outcome, client)


async def _json_response(
    send: Send,
    status: int,
    payload: dict[str, object],
    *,
    extra_headers: list[tuple[bytes, bytes]] | None = None,
) -> None:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode()),
        (b"cache-control", b"no-store"),
        *(extra_headers or []),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})
