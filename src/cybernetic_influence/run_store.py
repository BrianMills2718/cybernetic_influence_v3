"""Small crash-resistant repository for authoritative simulator run documents."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import cast
from uuid import uuid4


RUN_ID_PATTERN = re.compile(r"run_[0-9a-f]{12}")


class InvalidRunIdError(ValueError):
    """Raised when an external run ID is not in the simulator's closed format."""


class RunNotFoundError(FileNotFoundError):
    """Raised when a valid run ID has no retained document."""


class RunCorruptError(ValueError):
    """Raised when retained bytes disagree with the requested evidence identity."""


class RunStore:
    """Persist one complete JSON document per run using atomic replacement."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.trash_root = root / ".trash"
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        for path in self.root.glob("run_*.json"):
            path.chmod(0o600)
        if self.trash_root.exists():
            self.trash_root.chmod(0o700)
            for path in self.trash_root.glob("*.json"):
                path.chmod(0o600)

    def save(self, document: Mapping[str, object]) -> dict[str, object]:
        """Atomically retain a run document and return the stored form."""
        run_id = document.get("run_id")
        if not isinstance(run_id, str):
            raise InvalidRunIdError("run document requires a string run_id")
        self._validate(run_id)
        stored = dict(document)
        stored["storage_schema_version"] = 1
        stored["updated_at"] = now_iso()
        destination = self._path(run_id)
        temporary = self.root / f".{run_id}.{uuid4().hex}.tmp"
        encoded = json.dumps(stored, ensure_ascii=False, indent=2, sort_keys=True)
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                temporary.chmod(0o600)
                handle.write(encoded)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            self._sync_directory(self.root)
        finally:
            temporary.unlink(missing_ok=True)
        return stored

    def get(self, run_id: str) -> dict[str, object]:
        """Load one retained run without allowing path-shaped identifiers."""
        path = self._path(run_id)
        if not path.is_file():
            raise RunNotFoundError(run_id)
        try:
            return self._read(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as error:
            raise RunCorruptError(run_id) from error

    def list_runs(self) -> tuple[list[dict[str, object]], list[str]]:
        """Return newest-first summaries and names of unreadable documents."""
        summaries: list[dict[str, object]] = []
        corrupt: list[str] = []
        for path in self.root.glob("run_*.json"):
            try:
                document = self._read(path)
                summaries.append(self._summary(document))
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                corrupt.append(path.name)
        summaries.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return summaries, sorted(corrupt)

    def cost_baselines(self) -> list[dict[str, object]]:
        """Summarize comparable, fully observed completed live-run costs.

        These are descriptive history, not provider pricing or a promise about
        a future call.  Keeping the calculation beside the retained evidence
        lets the UI distinguish an expected spend from its hard authorization.
        """
        buckets: dict[tuple[str, str, str, str, str], list[float]] = {}
        for path in self.root.glob("run_*.json"):
            try:
                document = self._read(path)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                continue
            if (
                document.get("status") != "completed"
                or document.get("execution") != "live"
                or document.get("cost_fully_observable") is not True
            ):
                continue
            configuration = document.get("llm_configuration")
            cost = document.get("cost")
            if not isinstance(configuration, Mapping) or isinstance(cost, bool):
                continue
            if not isinstance(cost, (int, float)) or cost < 0:
                continue
            fields = (
                document.get("scenario"),
                document.get("arm"),
                configuration.get("model"),
                configuration.get("agent_reasoning_effort"),
                configuration.get("narrator_reasoning_effort"),
            )
            if not all(isinstance(value, str) and value for value in fields):
                continue
            key = cast(tuple[str, str, str, str, str], fields)
            buckets.setdefault(key, []).append(float(cost))
        return [
            {
                "scenario": key[0],
                "arm": key[1],
                "model": key[2],
                "agent_reasoning_effort": key[3],
                "narrator_reasoning_effort": key[4],
                "sample_count": len(costs),
                "median_cost": median(costs),
                "minimum_cost": min(costs),
                "maximum_cost": max(costs),
            }
            for key, costs in sorted(buckets.items())
        ]

    def trash(self, run_id: str) -> Path:
        """Move a retained run to recoverable private trash."""
        source = self._path(run_id)
        if not source.is_file():
            raise RunNotFoundError(run_id)
        self.trash_root.mkdir(parents=True, exist_ok=True)
        self.trash_root.chmod(0o700)
        destination = self.trash_root / f"{run_id}.{uuid4().hex}.json"
        os.replace(source, destination)
        destination.chmod(0o600)
        self._sync_directory(self.root)
        self._sync_directory(self.trash_root)
        return destination

    def mark_incomplete_interrupted(self) -> int:
        """Classify run records left in progress by an earlier app instance."""
        changed = 0
        for path in self.root.glob("run_*.json"):
            try:
                document = self._read(path)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
                continue
            if document.get("status") != "running":
                continue
            document["status"] = "interrupted"
            document["error"] = "The server stopped before this run produced a final record."
            self.save(document)
            changed += 1
        return changed

    def _path(self, run_id: str) -> Path:
        self._validate(run_id)
        return self.root / f"{run_id}.json"

    @staticmethod
    def _validate(run_id: str) -> None:
        if RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise InvalidRunIdError("invalid run ID")

    @staticmethod
    def _read(path: Path) -> dict[str, object]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("run document must be a JSON object")
        document = cast(dict[str, object], value)
        run_id = document.get("run_id")
        if not isinstance(run_id, str) or RUN_ID_PATTERN.fullmatch(run_id) is None:
            raise ValueError("run document has an invalid run ID")
        if path.stem != run_id:
            raise ValueError("run document identity does not match its filename")
        return document

    @staticmethod
    def _summary(document: Mapping[str, object]) -> dict[str, object]:
        story = document.get("story")
        headline = story.get("headline") if isinstance(story, dict) else None
        return {
            "run_id": document.get("run_id"),
            "created_at": document.get("created_at"),
            "updated_at": document.get("updated_at"),
            "status": document.get("status"),
            "scenario": document.get("scenario"),
            "profile": document.get("profile"),
            "arm": document.get("arm"),
            "execution": document.get("execution"),
            "model_calls": document.get("model_calls", 0),
            "cost": document.get("cost", 0.0),
            "headline": headline,
        }

    @staticmethod
    def _sync_directory(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def now_iso() -> str:
    """Return a stable, sortable UTC timestamp."""
    return datetime.now(UTC).isoformat()
