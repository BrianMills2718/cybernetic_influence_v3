#!/usr/bin/env python3
"""Re-certify the authoring route before it lapses, and install the result.

Route certifications last 7 days (CERTIFICATION_MAX_AGE). Producing a new one
was already automated -- `certify_codex_luna.py` does that -- but *installing*
it never was: the observation ids it prints had to be pasted into the service
plist by hand and the service restarted by hand. That manual step is the reason
the public Create surface has gone dark repeatedly; nothing fails until the
button is already disabled, and by then the fix needs a human at a keyboard.

This closes that loop. It checks the margin, certifies over the free Codex
subscription route when it can, writes the ids into the plist the service
actually reads, restarts the service, and then re-runs the health check to
prove the route is live. Every step that cannot be completed exits non-zero
with the reason on stderr -- a silently-skipped refresh would recreate exactly
the failure this exists to prevent.

Paid fallback: if the free route cannot certify and the margin is inside
--paid-fallback-days, it certifies over the metered OpenRouter route instead
and says so. A demo going dark in front of a reviewer costs more than the
fraction of a dollar that one certification call costs. Pass
--no-paid-fallback to forbid spend entirely.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_authoring_route_health import AUTHORING_ENV, CERTIFICATION_MAX_AGE
from host_busy_check import DEFAULT_STORE, busy_reasons
from service_env import SERVICE_LABEL, plist_path, service_env

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
FREE_ROUTE = "luna-authoring"
PAID_ROUTE = "sol-authoring"
PLIST_BACKUPS_KEPT = 5
BOOTOUT_SETTLE_SECONDS = 3
CERT_LINE = re.compile(r"^(?P<key>CYBERNETIC_INFLUENCE_CERT_[A-Z0-9_]+)=(?P<ids>[\w,]+)$")


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def margin_days(env: dict[str, str]) -> float | None:
    """Days until the longest-lived authoring route expires, or None if dark."""
    from llm_client.route_certification import RouteCertificationStore

    root = env.get("LLM_ROUTE_CERTIFICATION_ROOT")
    if not root:
        raise ValueError("LLM_ROUTE_CERTIFICATION_ROOT missing from the service environment")
    store = RouteCertificationStore(Path(root).expanduser() / "observations")
    observations = {item.observation_id: item for item in store.observations()}
    now = datetime.now(timezone.utc)

    best: timedelta | None = None
    for env_name in AUTHORING_ENV.values():
        configured = env.get(env_name, "").strip()
        if not configured:
            continue
        expiries = []
        for oid in (part.strip() for part in configured.split(",") if part.strip()):
            item = observations.get(oid)
            if item is None:
                expiries = []
                break
            expiries.append(item.observed_at + CERTIFICATION_MAX_AGE)
        if not expiries:
            continue
        remaining = min(expiries) - now
        if best is None or remaining > best:
            best = remaining
    return None if best is None else best.total_seconds() / 86400


def certify(route: str, env: dict[str, str]) -> dict[str, str]:
    """Run one certification route; return the CERT_* assignments it produced."""
    log(f"certifying over {route}")
    merged = {**os.environ, **env}
    merged["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{merged.get('PATH', '')}"
    completed = subprocess.run(
        [str(VENV_PYTHON), str(REPO_ROOT / "scripts" / "certify_codex_luna.py"), route],
        cwd=REPO_ROOT, env=merged, capture_output=True, text=True, timeout=1800,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-6:]
        raise RuntimeError(f"{route} certification failed:\n  " + "\n  ".join(tail))
    produced = {}
    for line in completed.stdout.splitlines():
        match = CERT_LINE.match(line.strip())
        if match:
            produced[match.group("key")] = match.group("ids")
    if not produced:
        raise RuntimeError(f"{route} certification printed no certification ids")
    return produced


def install(assignments: dict[str, str]) -> None:
    """Write the new ids into the service plist, keeping a rotated backup."""
    path = plist_path()
    backup = path.with_suffix(f".plist.autocert-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    shutil.copy2(path, backup)
    log(f"backed up plist to {backup.name}")

    with path.open("rb") as handle:
        document = plistlib.load(handle)
    env = document.setdefault("EnvironmentVariables", {})
    for key, value in assignments.items():
        log(f"  {key} -> {value}")
        env[key] = value
    with path.open("wb") as handle:
        plistlib.dump(document, handle)

    stale = sorted(path.parent.glob(f"{SERVICE_LABEL}.plist.autocert-*"))[:-PLIST_BACKUPS_KEPT]
    for item in stale:
        item.unlink()
    if stale:
        log(f"pruned {len(stale)} old certification backup(s)")


def service_port() -> int:
    """The port the service is configured to serve on, from its own plist."""
    with plist_path().open("rb") as handle:
        document = plistlib.load(handle)
    args = [str(item) for item in document.get("ProgramArguments", [])]
    if "--port" in args:
        return int(args[args.index("--port") + 1])
    raise ValueError("no --port in the service plist ProgramArguments")


def wait_until_serving(port: int, timeout_seconds: int = 60) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                if response.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def restart() -> None:
    """Reload the service and prove it came back.

    A changed plist needs bootout+bootstrap; kickstart keeps the loaded plist,
    so it would restart the service with the old certification ids. The settle
    time between the two is not optional: bootstrapping while launchd is still
    tearing the job down fails with "Input/output error", which on 2026-08-23
    left the public surface down for four minutes because nothing checked.

    Bootstrap returning non-zero is therefore not trusted either way -- the only
    evidence that counts is the service answering on its port.
    """
    uid = os.getuid()
    target = f"gui/{uid}"
    port = service_port()
    log("restarting the service (bootout, settle, bootstrap)")
    subprocess.run(["launchctl", "bootout", f"{target}/{SERVICE_LABEL}"], capture_output=True)
    time.sleep(BOOTOUT_SETTLE_SECONDS)
    completed = subprocess.run(
        ["launchctl", "bootstrap", target, str(plist_path())], capture_output=True, text=True
    )
    if completed.returncode != 0:
        # Can mean "already loaded", which is fine, or a real failure, which is
        # not. The port check below is what distinguishes them.
        log(f"bootstrap reported: {(completed.stderr or completed.stdout).strip() or completed.returncode}")

    if not wait_until_serving(port):
        raise RuntimeError(
            f"the service is not answering on port {port} after the restart; "
            "the public surface is DOWN and needs attention now"
        )
    log(f"service is answering on port {port}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-days", type=float, default=3.0,
                        help="refresh once the longest-lived route drops below this")
    parser.add_argument("--paid-fallback-days", type=float, default=2.0,
                        help="allow the metered route only inside this margin")
    parser.add_argument("--no-paid-fallback", action="store_true",
                        help="never spend; fail loudly if the free route cannot certify")
    parser.add_argument("--force", action="store_true", help="refresh regardless of margin")
    parser.add_argument("--force-restart", action="store_true",
                        help="restart even with work in flight, losing it")
    args = parser.parse_args()

    env = service_env()
    before = margin_days(env)
    if before is None:
        log("no usable authoring certification: Create is dark right now")
    else:
        log(f"longest-lived authoring route: {before:.2f} days remaining")

    if not args.force and before is not None and before >= args.warn_days:
        log(f"above the {args.warn_days:g}-day margin; nothing to do")
        return 0

    try:
        assignments = certify(FREE_ROUTE, env)
    except Exception as free_error:  # noqa: BLE001 - the fallback decision needs the reason
        log(f"free route unavailable: {free_error}")
        if args.no_paid_fallback:
            print("free route failed and paid fallback is disabled", file=sys.stderr)
            return 1
        inside_margin = before is None or before <= args.paid_fallback_days
        if not inside_margin:
            print(
                f"free route failed with {before:.2f} days still in hand; not spending yet. "
                "It will retry, and fall back to the metered route inside "
                f"{args.paid_fallback_days:g} days.",
                file=sys.stderr,
            )
            return 1
        log("inside the paid-fallback margin; certifying over the metered route (this costs money)")
        assignments = certify(PAID_ROUTE, env)

    in_flight = busy_reasons(os.path.expanduser(DEFAULT_STORE))
    if in_flight and not args.force_restart:
        # The certification itself is already recorded in the store, so nothing
        # is lost by stopping here -- the next run installs it. Killing a live
        # simulation to save a few hours of margin is the wrong trade.
        for reason in in_flight:
            log(f"work in flight: {reason}")
        print(
            "certified, but not installing yet: a restart would kill the above. "
            "It will install on the next run once the host is idle.",
            file=sys.stderr,
        )
        return 4

    install(assignments)
    restart()

    after = margin_days(service_env())
    if after is None:
        print("refresh installed but no usable certification is visible afterwards", file=sys.stderr)
        return 1
    log(f"authoring route now has {after:.2f} days remaining")
    if before is not None and after <= before:
        print(f"refresh did not extend the margin ({before:.2f} -> {after:.2f} days)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
