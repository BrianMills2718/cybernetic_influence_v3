#!/usr/bin/env python3
"""Run every automated check that protects the public demo, and report once.

Each check here exists because a real defect got past everything else. They are
run together, nightly, so that keeping the demo correct does not depend on
someone remembering to look:

  claims        the page states something the retained runs do not support
                (a chapter once described an experiment the run was not running)
  assets        the shared URL serves a page whose own asset references 404
                (the link was broken for anyone omitting the trailing slash)
  controls      a primary control sits outside the viewport at some width
                (Next was off-screen between 1280 and 1600)
  case-ux       the flagship case is unreadable or obscures/clips its evidence
                (mobile labels, navigation, overlays, and comparison all escaped earlier checks)
  route         the authoring certification is close to lapsing
                (Create went dark with no warning, twice)

Every check is offline or read-only against the running service; none makes a
model call, so this costs nothing to run as often as you like.

Exit non-zero if any check fails, so a scheduler surfaces it rather than
recording a quiet success.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PYTHON = REPO / ".venv" / "bin" / "python"
DEFAULT_PAGE_URL = "https://brian-mac-mini.tail9c321e.ts.net/waltzman/"


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{stamp}] {message}", flush=True)



# The deck is the page Brian actually opens. A verdict that lives only in a log
# on the deployment host is a verdict nobody reads, and an audit nobody reads is
# not a control. This rewrites exactly the text between two sentinels inside the
# demo's existing card -- never the surrounding file, which carries every other
# project's card too.
STATUS_START = "<!--demo-audit-status-->"
STATUS_END = "<!--/demo-audit-status-->"


def write_status(target: Path, ok: bool, failures: list[str], checked: int) -> None:
    if not target.exists():
        log(f"status target not found, leaving it alone: {target}")
        return
    markup = target.read_text(encoding="utf-8")
    if STATUS_START not in markup or STATUS_END not in markup:
        log(f"status sentinels absent in {target.name}; not modifying a shared page")
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if ok:
        text = f"Audited {stamp}Z &middot; {checked} checks passed"
    else:
        text = (
            f"NEEDS ATTENTION {stamp}Z &middot; "
            f"{', '.join(failures)} failing &mdash; do not share until fixed"
        )
    updated = re.sub(
        re.escape(STATUS_START) + ".*?" + re.escape(STATUS_END),
        STATUS_START + text + STATUS_END,
        markup,
        count=1,
        flags=re.DOTALL,
    )
    if updated != markup:
        target.write_text(updated, encoding="utf-8")
        log(f"wrote verdict to {target.name}")


def run(name: str, argv: list[str], env: dict[str, str] | None = None) -> tuple[str, bool, str]:
    try:
        completed = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True, timeout=900,
            env={**os.environ, **(env or {})},
        )
    except Exception as error:  # noqa: BLE001 - a check that cannot run is a failure
        return name, False, f"could not run: {error}"
    output = (completed.stderr or completed.stdout).strip().splitlines()
    tail = output[-1] if output else ""
    return name, completed.returncode == 0, tail


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-url", default=DEFAULT_PAGE_URL)
    parser.add_argument(
        "--chromium",
        default=None,
        help="explicit Chromium executable for browser checks; omit on the deployment host",
    )
    parser.add_argument(
        "--status-target",
        type=Path,
        default=None,
        help="page carrying demo-audit-status sentinels; its verdict line is rewritten",
    )
    parser.add_argument(
        "--skip-route",
        action="store_true",
        help="skip the certification check when the service environment is unavailable",
    )
    args = parser.parse_args()

    python = str(PYTHON) if PYTHON.exists() else sys.executable
    checks = [
        ("claims", [python, str(REPO / "scripts" / "check_page_claims_match_evidence.py")], None),
        ("assets", [python, str(REPO / "scripts" / "check_public_assets.py"), args.page_url], None),
        (
            "controls",
            [
                python,
                str(REPO / "scripts" / "check_primary_controls_visible.py"),
                "--base-url",
                args.page_url,
                *(["--chromium", args.chromium] if args.chromium else []),
            ],
            None,
        ),
        (
            "case-ux",
            [
                python,
                str(REPO / "scripts" / "check_case_study_ux.py"),
                "--base-url",
                args.page_url,
                *(["--chromium", args.chromium] if args.chromium else []),
            ],
            None,
        ),
    ]
    if not args.skip_route:
        service_env: dict[str, str] = {}
        try:
            sys.path.insert(0, str(REPO / "scripts"))
            from service_env import service_env as read_service_env  # type: ignore

            service_env = read_service_env()
        except Exception as error:  # noqa: BLE001
            log(f"service environment unavailable, skipping route check: {error}")
            service_env = {}
        if service_env:
            checks.append(
                (
                    "route",
                    [python, str(REPO / "scripts" / "check_authoring_route_health.py")],
                    service_env,
                )
            )

    log(f"auditing {args.page_url}")
    failures = []
    for name, argv, env in checks:
        check_name, ok, tail = run(name, argv, env)
        log(f"  {check_name:9s} {'ok  ' if ok else 'FAIL'}  {tail[:150]}")
        if not ok:
            failures.append(check_name)

    if args.status_target:
        write_status(args.status_target, not failures, failures, len(checks))

    if failures:
        print(
            f"\n{len(failures)} check(s) failed: {', '.join(failures)}. "
            "The public demo needs attention before it is shared.",
            file=sys.stderr,
        )
        return 1
    log(f"all {len(checks)} checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
