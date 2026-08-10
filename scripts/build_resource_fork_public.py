#!/usr/bin/env python3
"""Project the full checkpoint-fork artifact into bounded public evidence."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, cast


LABELS = {
    "no_intervention": "No package",
    "partial": "Partial resources",
    "complete": "Complete resources",
    "false_claim": "False claims",
}


def counts(stances: dict[str, dict[str, str]]) -> dict[str, int]:
    return dict(sorted(Counter(item["decision"] for item in stances.values()).items()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    if source.get("status") != "complete":
        raise ValueError("resource fork artifact is not complete")
    branches = []
    for branch_id in ("no_intervention", "partial", "complete", "false_claim"):
        branch = source["branches"][branch_id]
        manifest = json.loads(branch["manifest_observation"]["apparent_content"])
        traces = [
            call["trace_id"]
            for attempt in branch["incremental_attempts"]
            for participant in attempt["participants"]
            for call in participant["call_evidence"]
        ]
        branches.append(
            {
                "id": branch_id,
                "label": LABELS[branch_id],
                "manifest": manifest["manifest"],
                "resource_commitments": manifest["resource_commitments"],
                "outcome": branch["outcome"],
                "final_decisions": branch["final_decisions"],
                "final_stances": branch["final_stances"],
                "trace_ids": traces,
                "checkpoint_digest": branch["checkpoint_digest"],
            }
        )
    shared_stances = cast(
        dict[str, dict[str, str]], source["shared_round_history"][-1]["stances"]
    )
    public = {
        "schema_version": 1,
        "experiment_id": source["probe_id"],
        "model": source["model"],
        "reasoning_effort": source["reasoning_effort"],
        "shared_checkpoint_digest": source["shared_checkpoint_digest"],
        "shared_prefix_model_calls": source["shared_prefix_model_calls"],
        "shared_round_two_decisions": counts(shared_stances),
        "agent_count": len(shared_stances),
        "total_model_calls": source["shared_prefix_model_calls"]
        + sum(item["incremental_model_calls"] for item in source["branches"].values()),
        "observed_cost": source["unique_provider_cost"],
        "gate": {
            "minimum_support": 13,
            "minimum_support_or_conditional": 20,
            "maximum_oppose": 2,
        },
        "branches": branches,
        "nonclaims": source["nonclaims"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(public, indent=2, sort_keys=True), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
