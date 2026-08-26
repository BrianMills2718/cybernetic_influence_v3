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
# Execution is certified separately from authoring, and only authoring was ever
# automated. On 2026-08-25 every execution certification had lapsed -- Terra 110
# hours earlier, Luna 52, Sol 6 -- while this check reported 5.6 healthy days and
# the nightly audit wrote a green verdict onto the page. Authoring still worked,
# so the builder composed a draft, accepted an approval, and then refused to run
# it. A check that covers one of two required families cannot go red for the
# other, which is the whole failure.
EXECUTION_ENV = {
    "codex/gpt-5.6-luna": "CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA",
    "codex/gpt-5.6-terra": "CYBERNETIC_INFLUENCE_CERT_CODEX_TERRA",
    "openrouter/openai/gpt-5.6-terra": "CYBERNETIC_INFLUENCE_CERT_TERRA",
    "openrouter/openai/gpt-5.6-sol": "CYBERNETIC_INFLUENCE_CERT_SOL",
}
ROUTE_FAMILIES = {"authoring": AUTHORING_ENV, "execution": EXECUTION_ENV}
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

    def family_margin(label: str, env_map: dict[str, str]) -> dict[str, timedelta]:
        """Every live certification in one family, by model. Empty means dark."""
        print(f"\n{label} routes:")
        live: dict[str, timedelta] = {}
        for model, env_name in sorted(env_map.items()):
            configured = os.environ.get(env_name, "").strip()
            if not configured:
                print(f"  {model:34s} not configured")
                continue
            expiries = []
            missing = []
            for oid in (item.strip() for item in configured.split(",") if item.strip()):
                item = observations.get(oid)
                if item is None:
                    missing.append(oid)
                    continue
                expiries.append(item.observed_at + CERTIFICATION_MAX_AGE)
            if missing or not expiries:
                print(
                    f"  {model:34s} observation(s) missing from the store: "
                    f"{', '.join(missing) or 'none recorded'}"
                )
                continue
            soonest = min(expiries)
            remaining = soonest - now
            state = (
                "EXPIRED"
                if remaining.total_seconds() <= 0
                else f"{remaining.days}d {remaining.seconds // 3600}h left"
            )
            print(f"  {model:34s} expires {soonest:%Y-%m-%d %H:%M}Z  ({state})")
            if remaining.total_seconds() > 0:
                live[model] = remaining
        print(f"  -> {len(live)} of {len(env_map)} routes live")
        return live

    live_routes = {
        label: family_margin(label, env_map)
        for label, env_map in ROUTE_FAMILIES.items()
    }
    margins = {
        label: (max(live.values()) if live else None)
        for label, live in live_routes.items()
    }
    dark = [label for label, margin in margins.items() if margin is None]
    if dark:
        print(
            "\nNo usable certification for: " + ", ".join(sorted(dark))
            + ". That half of Create is dark now -- authoring and execution are "
            "certified separately and both are required to author and then run "
            "a simulation. Re-certify before demoing:\n"
            "  .venv/bin/python scripts/refresh_authoring_certification.py --force",
            file=sys.stderr,
        )
        return 1

    # A family reports its longest-lived route, so a family down to one survivor
    # reads exactly like a healthy one. On 2026-08-26 that summary said "6.5 days
    # remaining" over three expired execution routes, and Luna was hours away from
    # being the only live route in BOTH families -- one Codex login failure would
    # have taken authoring and execution dark together, with seven days of
    # apparent margin on the board. Two families sharing their last route are not
    # two families.
    sole = {
        label: next(iter(live))
        for label, live in live_routes.items()
        if len(live) == 1
    }
    shared: dict[str, list[str]] = {}
    for label, model in sole.items():
        shared.setdefault(model, []).append(label)
    doubled = {model: labels for model, labels in shared.items() if len(labels) > 1}
    if doubled:
        for model, labels in sorted(doubled.items()):
            print(
                f"\n{model} is the only live route in {' and '.join(sorted(labels))}. "
                "Those families are not independent: one failure on that route takes "
                "all of them dark at once, however many days it has left. Certify a "
                "second route:\n"
                "  .venv/bin/python scripts/refresh_authoring_certification.py --paid",
                file=sys.stderr,
            )
        return 1

    # The weakest family governs: a healthy authoring margin says nothing about
    # whether an authored simulation can actually be run.
    weakest_label = min(margins, key=lambda label: margins[label].total_seconds())
    days_left = margins[weakest_label].total_seconds() / 86400
    for label in sorted(margins):
        print(f"\nlongest-lived {label} route: {margins[label].total_seconds() / 86400:.1f} days remaining")
    if days_left < args.warn_days:
        print(
            f"\nThe {weakest_label} family is under the {args.warn_days:g}-day margin "
            f"({days_left:.1f} days). Re-certify now rather than discovering it as a "
            "disabled button or a run that will not start:\n"
            "  .venv/bin/python scripts/refresh_authoring_certification.py",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
