#!/usr/bin/env python3
"""Project the overt and threshold-managed runs into one public comparison.

The source paper's section 7 argues that pressure can preserve a directional
effect while changing how that effect appears. A synthetic world lets the source
expression policy be authored while the coalition and monitoring system stay
fixed. In this retained pair the shaped arm was not missed: the monitor recorded
`degrading`. The inspectable result is a different severity and mechanism
classification under the changed expression policy.

The designed manipulation changes the source expression policy. The source roles,
coalition, decision gate, and entire detection cell -- monitor, diagnostician,
planner, their categories, and their trigger -- are shared. Model sampling is not
seeded, so the realized trajectories are not otherwise token-level-identical
counterfactuals and the two policies are not independently calibrated to an equal
pressure dose.

Emits per-round stance distributions for both arms, each arm's retained detector
reading, and the nonclaims. Retains no prompts.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any


def _tally(stances: dict[str, Any], field: str) -> dict[str, int]:
    return dict(sorted(Counter(v.get(field) for v in stances.values()).items()))


def _detector_reading(run: dict[str, Any]) -> dict[str, str]:
    """The typed values the detection cell recorded, read from the run itself.

    Taken from the retained document rather than recomputed, so the projection
    cannot disagree with the run it describes.
    """
    blob = json.dumps(run)
    reading: dict[str, str] = {}
    for key in (
        "trust_structure",
        "perceived_risk",
        "coordination_readiness",
        "mechanism",
        "primary_dimension",
        "affected_scope",
        "action_id",
    ):
        found = re.findall(r'\\?"%s\\?":\s*\\?"([a-z_]+)\\?"' % key, blob)
        if found:
            reading[key] = found[0]
    return reading


def _arm(path: Path, expected_condition: str) -> dict[str, Any]:
    run = json.loads(path.read_text(encoding="utf-8"))
    outcome = run["outcome"]
    if outcome.get("condition") != expected_condition:
        raise ValueError(
            f"{path.name}: expected condition {expected_condition}, "
            f"got {outcome.get('condition')}"
        )
    if run.get("status") != "completed":
        raise ValueError(f"{path.name}: run is not completed")
    rounds = [
        {
            "round": index,
            "decisions": _tally(entry.get("stances") or {}, "decision"),
            "risks": _tally(entry.get("stances") or {}, "risk"),
        }
        for index, entry in enumerate(outcome.get("round_history") or [], start=1)
    ]
    if not rounds:
        raise ValueError(f"{path.name}: no round history")
    return {
        "run_id": run.get("run_id") or path.stem,
        "condition": outcome.get("condition"),
        "rounds": rounds,
        "final_decisions": rounds[-1]["decisions"],
        "outcome": outcome.get("outcome"),
        "detector": _detector_reading(run),
        "model_calls": run.get("model_calls"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overt", type=Path, required=True)
    parser.add_argument("--evasion", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    overt = _arm(args.overt, "adaptive_cso_stabilization")
    evasion = _arm(args.evasion, "threshold_managed_evasion")

    payload = {
        "schema_version": 1,
        "overt": overt,
        "evasion": evasion,
        "shared": {
            "detection_cell": [
                "cso_decision_environment_monitor",
                "cso_coordination_diagnostician",
                "cso_stabilization_planner",
            ],
            "held_identical": (
                "The source roles, coalition, decision gate, and whole detection cell "
                "-- monitor, diagnostician, planner, their categories and trigger -- "
                "are shared. The designed manipulation changes the source expression "
                "policy; unseeded sampling means the realized agent text is not "
                "otherwise identical."
            ),
        },
        "nonclaims": [
            "Two retained executions are not a sample, and one pair cannot establish "
            "how often this monitor would under-classify or misdiagnose such a pattern.",
            "The evasion is authored, not discovered: the source expression policy was "
            "constrained to narrow verification requests, and the two policies are not "
            "independently calibrated to an equal pressure dose.",
            "The shaped arm was detected as degrading, so this is not a detector miss. "
            "A more sensitive decision boundary might also raise false alarms on benign "
            "variation; that tradeoff is not answered here.",
            "Model sampling is not seeded, so a rerun would not reproduce these exact "
            "stances.",
        ],
    }
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    print(f"  overt   : {overt['detector']}")
    print(f"  evasion : {evasion['detector']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
