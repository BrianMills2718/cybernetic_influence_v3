#!/usr/bin/env python3
"""Project the adaptive-CSO stabilization run into bounded public case evidence.

This is the run that exercises Waltzman's framework end to end rather than
adjacent to it. Its arc is the paper's own: a stable coalition, heterogeneous
and individually plausible pressure from four differentiated sources, a
measurable shift from implicit to conditional trust, a Cognitive Security
Operations chain that detects and diagnoses the shift, one stabilization action,
and recovery -- with no false claim anywhere in the run.

Emits only what the public case study needs: per-round stance distributions so
direction is visible rather than a single end-state, the risk and request mixes
that carry the paper's observable indicators, the CSO detect/diagnose/stabilize
records, the source injects, and provenance. Retains no prompts.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any


def _tally(stances: dict[str, Any], field: str) -> dict[str, int]:
    return dict(sorted(Counter(v.get(field) for v in stances.values()).items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="run summary JSON")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    run = json.loads(args.input.read_text(encoding="utf-8"))
    outcome = run["outcome"]
    if outcome.get("condition") != "adaptive_cso_stabilization":
        raise ValueError(f"expected adaptive_cso_stabilization, got {outcome.get('condition')}")
    if run.get("status") != "completed":
        raise ValueError("run is not completed")

    rounds = []
    for index, entry in enumerate(outcome.get("round_history") or [], start=1):
        stances = entry.get("stances") or {}
        rounds.append({
            "round": index,
            "decisions": _tally(stances, "decision"),
            "risks": _tally(stances, "risk"),
            "requests": _tally(stances, "request"),
        })

    # The CSO chain in the order the paper names it: detect, diagnose, stabilize.
    order = {
        "cso_decision_environment_monitor": 0,
        "cso_coordination_diagnostician": 1,
        "cso_stabilization_planner": 2,
    }
    cso = sorted(
        (
            {"actor_id": r["actor_id"], "payload": r["payload"]}
            for r in (outcome.get("cso_records") or [])
            if r.get("actor_id") in order
        ),
        key=lambda r: order[r["actor_id"]],
    )

    # The paired rationales are the case's evidentiary core: the same named
    # official, in its own words, before and after the stabilization action.
    # Chosen to span countries and roles rather than to flatter the result.
    history = outcome.get("round_history") or []
    pressured = (history[1].get("stances") or {}) if len(history) > 1 else {}
    recovered = (history[2].get("stances") or {}) if len(history) > 2 else {}
    wanted = [
        "alba_community_liaison",
        "borin_community_liaison",
        "cyrenia_policy_delegate",
        "darsia_supply_lead",
        "regional_legal_oversight_lead",
        "regional_scientific_advisor",
    ]
    paired = []
    for actor in wanted:
        before, after = pressured.get(actor), recovered.get(actor)
        if not before or not after:
            continue
        paired.append({
            "actor_id": actor,
            "under_pressure": {
                "decision": before.get("decision"),
                "risk": before.get("risk"),
                "request": before.get("request"),
                "rationale": before.get("rationale"),
            },
            "after_stabilization": {
                "decision": after.get("decision"),
                "risk": after.get("risk"),
                "request": after.get("request"),
                "rationale": after.get("rationale"),
            },
        })

    public = {
        "schema_version": 1,
        "source_run_id": run.get("run_id"),
        "condition": outcome.get("condition"),
        "agent_count": outcome.get("agent_count"),
        "model_calls": outcome.get("model_calls"),
        "rounds_completed": outcome.get("rounds_completed"),
        "outcome": outcome.get("outcome"),
        "rounds": rounds,
        "final_decisions": outcome.get("final_decisions"),
        "final_risks": outcome.get("final_risks"),
        "final_requests": outcome.get("final_requests"),
        "source_injects": outcome.get("exercise_injects"),
        "cso_chain": cso,
        "paired_rationales": paired,
        "stabilization_events": outcome.get("stabilization_events"),
        "nonclaims": [
            "One retained execution is not a statistical sample or an effect estimate.",
            "The pressure sources and the stabilization action are scenario-authored "
            "controls, not discovered behaviour.",
            "Model sampling is not seeded, so a rerun would not reproduce these exact "
            "stances.",
            "Derived trust, risk and readiness readings are analyst views over retained "
            "evidence. They are not calibrated measures of real trust, risk or readiness, "
            "and they never governed the simulated people.",
        ],
    }
    args.output.write_text(json.dumps(public, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    for r in rounds:
        print(f"  round {r['round']}: {r['decisions']}")
    print(f"  outcome: {public['outcome']}  ·  CSO chain: {len(cso)} records  ·  paired rationales: {len(paired)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
