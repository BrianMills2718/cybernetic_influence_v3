#!/usr/bin/env python3
"""Project the overt and threshold-managed runs into one public comparison.

The source paper's section 7 argues that influence can keep its directional
pressure while changing how that pressure appears, so that it resembles ordinary
variation. Evasion is unobservable in the field by construction; the claim that
a detector missed something is only checkable where the pressure is authored.

These two runs differ in exactly one respect: how each source expresses its
signal. The four sources, the coalition, the decision gate, and the entire
detection cell -- monitor, diagnostician, planner, their thresholds and their
trigger -- are shared. So a difference in what the cell reported is a fact about
the shape of the pressure, not about a changed detector.

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
                "The four sources, the coalition, the decision gate, and the whole "
                "detection cell -- personas, thresholds and trigger -- are the same "
                "in both runs. Only how each source expresses its signal differs."
            ),
        },
        "nonclaims": [
            "Two retained executions are not a sample, and one pair cannot establish "
            "how often a detector would miss this.",
            "The evasion is authored, not discovered: the sources were instructed to "
            "keep each signal inside ordinary variation.",
            "A detector missing an authored pattern is evidence about that detector at "
            "that threshold, and nothing more. A threshold that caught this one might "
            "produce false alarms elsewhere; that is not answered here.",
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
