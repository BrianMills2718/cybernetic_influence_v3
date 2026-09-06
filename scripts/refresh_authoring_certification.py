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

from check_authoring_route_health import CERTIFICATION_MAX_AGE, ROUTE_FAMILIES
from host_busy_check import DEFAULT_STORE, busy_reasons
from service_env import SERVICE_LABEL, plist_path, service_env

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
# Authoring and execution are certified separately and BOTH are required for
# the public Create path: authoring composes the draft, execution runs it. Only
# authoring was automated here, so on 2026-08-25 the builder produced a draft,
# accepted an approval, and then refused to run it with "model is not currently
# advertised for simulator execution", while this job reported a healthy margin
# every night. Refreshing one family and calling the route healthy is the bug.
FREE_ROUTES = ("luna-authoring", "luna")
# Two distinct metered models, not one. A paid fallback that certifies a single
# model leaves that model the sole live route in both families, which is exactly
# what check_authoring_route_health.py refuses to call healthy -- and its printed
# remedy is this flag, so a one-model PAID_ROUTES made the gate unclearable. On
# 2026-09-02 the Codex token was revoked, Luna went dark, the fallback certified
# Sol alone, and the nightly demo audit stamped "do not share" on the published
# Deck card for four days with no reachable fix.
PAID_ROUTES = (
    "sol-authoring",
    "sol",
    "openrouter-terra-authoring",
    "openrouter-terra",
)
PLIST_BACKUPS_KEPT = 5
BOOTOUT_SETTLE_SECONDS = 3
CERT_LINE = re.compile(r"^(?P<key>CYBERNETIC_INFLUENCE_CERT_[A-Z0-9_]+)=(?P<ids>[\w,]+)$")


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)


def margin_days(env: dict[str, str]) -> float | None:
    """Days until the weakest route family expires, or None if either is dark.

    The weakest family governs. A healthy authoring margin says nothing about
    whether an authored simulation can actually be run, and reporting the
    stronger of the two is what let execution go dark unnoticed for days.
    """
    from llm_client.route_certification import RouteCertificationStore

    root = env.get("LLM_ROUTE_CERTIFICATION_ROOT")
    if not root:
        raise ValueError("LLM_ROUTE_CERTIFICATION_ROOT missing from the service environment")
    store = RouteCertificationStore(Path(root).expanduser() / "observations")
    observations = {item.observation_id: item for item in store.observations()}
    now = datetime.now(timezone.utc)

    family_best: dict[str, timedelta] = {}
    for label, env_map in ROUTE_FAMILIES.items():
        for env_name in env_map.values():
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
            if remaining.total_seconds() <= 0:
                continue
            current = family_best.get(label)
            if current is None or remaining > current:
                family_best[label] = remaining
    if set(family_best) != set(ROUTE_FAMILIES):
        return None
    return min(item.total_seconds() for item in family_best.values()) / 86400


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


def finish(assignments: dict[str, str], before: float | None, args) -> int:
    """Install what was certified, restart, and prove the route came back live."""
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
    log(f"weakest route family now has {after:.2f} days remaining")
    # A deliberate paid refresh adds a second route to a family that already has
    # one; the family margin it reports is the LONGEST-lived route, so it can
    # legitimately not move. Only a margin-driven refresh has to extend it.
    if not args.paid and before is not None and after <= before:
        print(f"refresh did not extend the margin ({before:.2f} -> {after:.2f} days)", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warn-days", type=float, default=3.0,
                        help="refresh once the longest-lived route drops below this")
    parser.add_argument("--paid-fallback-days", type=float, default=2.0,
                        help="allow the metered route only inside this margin")
    parser.add_argument("--no-paid-fallback", action="store_true",
                        help="never spend; fail loudly if the free route cannot certify")
    parser.add_argument("--force", action="store_true", help="refresh regardless of margin")
    # Spend was reachable only by falling out of a failure: the paid route ran
    # when the free one raised, and never because someone decided to pay. That
    # left no way to execute the one decision the margin cannot make for you --
    # adding a SECOND route so the free one is not carrying a family alone --
    # and the check that detects it recommends exactly this flag.
    parser.add_argument("--paid", action="store_true",
                        help="certify the metered route deliberately (costs money); implies --force")
    parser.add_argument("--force-restart", action="store_true",
                        help="restart even with work in flight, losing it")
    args = parser.parse_args()

    env = service_env()
    before = margin_days(env)
    if before is None:
        log("a route family has no usable certification: Create is dark right now")
    else:
        log(f"weakest route family: {before:.2f} days remaining")

    if not (args.force or args.paid) and before is not None and before >= args.warn_days:
        log(f"above the {args.warn_days:g}-day margin; nothing to do")
        return 0

    def certify_all(routes: tuple[str, ...]) -> dict[str, str]:
        """Certify every family's route; a partial refresh is not a refresh."""
        produced: dict[str, str] = {}
        for route in routes:
            produced.update(certify(route, env))
        return produced

    if args.paid:
        if args.no_paid_fallback:
            print("--paid and --no-paid-fallback contradict each other", file=sys.stderr)
            return 2
        log("--paid given; certifying over the metered route (this costs money)")
        assignments = certify_all(PAID_ROUTES)
        return finish(assignments, before, args)

    try:
        assignments = certify_all(FREE_ROUTES)
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
        assignments = certify_all(PAID_ROUTES)

    return finish(assignments, before, args)


if __name__ == "__main__":
    raise SystemExit(main())
