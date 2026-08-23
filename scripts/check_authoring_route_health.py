#!/usr/bin/env python3
"""Warn before the authoring route expires, instead of after it has gone dark.

Route certifications last 7 days by design (CERTIFICATION_MAX_AGE). When the
last one lapses, authoring_model_ids() returns an empty list, the public Create
surface renders "Simulation builder unavailable" with both actions disabled,
and nothing anywhere says why. That happened on 2026-08-19 and took hours to
trace, because an empty list is indistinguishable from a route that never
existed.

Expiry is a date, so it is knowable in advance. This reports days remaining and
exits non-zero once the margin is short enough that a demo could land inside the
dark window.

Run it where the service env is available -- the certification store and the
CERT_* variables are read from the environment, exactly as the app reads them.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

AUTHORING_ENV = {
    "codex/gpt-5.6-luna": "CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA",
    "openrouter/openai/gpt-5.6-terra": "CYBERNETIC_INFLUENCE_CERT_AUTHORING_TERRA",
    "openrouter/openai/gpt-5.6-sol": "CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL",
}
CERTIFICATION_MAX_AGE = timedelta(days=7)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warn-days", type=float, default=3.0,
        help="exit non-zero when the longest-lived route has less than this many days left",
    )
    args = parser.parse_args()

    root_raw = os.environ.get("LLM_ROUTE_CERTIFICATION_ROOT")
    if not root_raw:
        print("LLM_ROUTE_CERTIFICATION_ROOT is unset; run this with the service environment", file=sys.stderr)
        return 2
    try:
        from llm_client.route_certification import RouteCertificationStore
    except ImportError:
        print("llm_client is not importable here", file=sys.stderr)
        return 2

    store = RouteCertificationStore(Path(root_raw).expanduser() / "observations")
    observations = {item.observation_id: item for item in store.observations()}
    now = datetime.now(timezone.utc)

    best_remaining: timedelta | None = None
    any_configured = False

    for model, env_name in sorted(AUTHORING_ENV.items()):
        configured = os.environ.get(env_name, "").strip()
        if not configured:
            print(f"  {model:34s} not configured")
            continue
        any_configured = True
        expiries = []
        missing = []
        for oid in (item.strip() for item in configured.split(",") if item.strip()):
            item = observations.get(oid)
            if item is None:
                missing.append(oid)
                continue
            expiries.append(item.observed_at + CERTIFICATION_MAX_AGE)
        if missing or not expiries:
            print(f"  {model:34s} observation(s) missing from the store: {', '.join(missing) or 'none recorded'}")
            continue
        soonest = min(expiries)
        remaining = soonest - now
        if best_remaining is None or remaining > best_remaining:
            best_remaining = remaining
        state = "EXPIRED" if remaining.total_seconds() <= 0 else f"{remaining.days}d {remaining.seconds // 3600}h left"
        print(f"  {model:34s} expires {soonest:%Y-%m-%d %H:%M}Z  ({state})")

    if not any_configured:
        print("\nNo authoring route is configured at all: Create is already dark.", file=sys.stderr)
        return 1
    if best_remaining is None:
        print("\nEvery configured route has unusable observations: Create is already dark.", file=sys.stderr)
        return 1

    days_left = best_remaining.total_seconds() / 86400
    print(f"\nlongest-lived authoring route: {days_left:.1f} days remaining")
    if days_left <= 0:
        print("Create is dark now. Re-certify before demoing.", file=sys.stderr)
        return 1
    if days_left < args.warn_days:
        print(
            f"Under the {args.warn_days:g}-day margin. Re-certify now rather than "
            "discovering it as a disabled button:\n"
            "  .venv/bin/python scripts/certify_codex_luna.py sol-authoring",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
