#!/usr/bin/env python3
"""Fork one authentic round-two coalition state into four resource packages."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from cybernetic_influence.active_runtime import ActiveRuntimeCheckpoint, ActiveRuntimeSession
from cybernetic_influence.causal_core.models import ActionAttempt
from cybernetic_influence.scenarios.regional_outbreak import (
    AGENT_IDS,
    SOURCE_IDS,
    outbreak_bindings,
    outbreak_fixture,
    outbreak_resource_commitments,
    outbreak_runtime_config,
)


RESOURCE_IDS = [
    "alba_mobile_lab",
    "borin_clinician_roster",
    "cyrenia_diagnostic_kits",
    "cyrenia_protective_equipment",
    "darsia_cold_chain_route",
    "darsia_fuel_lot",
]
PARTIAL_IDS = RESOURCE_IDS[:2]


def _activate_expected(
    session: ActiveRuntimeSession, expected: set[str], label: str
) -> None:
    due = session.next_due_activation()
    if due is None or set(due.active_system_ids) != expected:
        actual = [] if due is None else due.active_system_ids
        raise RuntimeError(f"expected {label} {sorted(expected)}, found {actual}")
    session.activate(
        due.active_system_ids,
        logical_time=due.logical_time,
        activation_causes=due.causes,
    )


def _package(branch: str) -> dict[str, JsonValue]:
    if branch == "no_intervention":
        return {
            "commitments": [],
            "manifest_claim_status": "no_package",
            "manifest_ref": "no-package-after-round-two",
        }
    resource_ids = PARTIAL_IDS if branch == "partial" else RESOURCE_IDS
    falsified_ids = frozenset(RESOURCE_IDS) if branch == "false_claim" else frozenset()
    return {
        "commitments": cast(
            JsonValue,
            outbreak_resource_commitments(resource_ids, falsified_ids=falsified_ids),
        ),
        "manifest_claim_status": "claimed_verified",
        "manifest_ref": f"round-two-{branch}-package",
    }


def _branch(
    *,
    fixture: Any,
    shared: ActiveRuntimeCheckpoint,
    branch: str,
    model: str,
    reasoning_effort: str,
    trace_prefix: str,
) -> dict[str, Any]:
    session = ActiveRuntimeSession.restore(
        fixture.scenario,
        fixture.exact_bindings,
        outbreak_bindings(
            fixture,
            model=model,
            reasoning_effort=reasoning_effort,
            trace_id_prefix=trace_prefix,
        ),
        shared,
    )
    package = _package(branch)
    session.apply_external_action(
        ActionAttempt(
            action_id=f"round_two_resource_fork_{branch}",
            actor_entity_id="regional_allocation_authority",
            output_port_id="resource_allocation_out",
            payload=package,
            logical_time=session.core_state.logical_time,
            public_summary=f"Applied the retained {branch} package after round two.",
        )
    )
    due = session.next_due_activation()
    if due is None:
        raise RuntimeError(f"{branch} package did not wake the coalition")
    active_agents = [item for item in due.active_system_ids if item in AGENT_IDS]
    if set(active_agents) != set(AGENT_IDS):
        raise RuntimeError(
            f"{branch} package woke {len(active_agents)} of {len(AGENT_IDS)} coalition agents"
        )
    session.activate(
        active_agents,
        logical_time=due.logical_time,
        activation_causes={agent_id: due.causes[agent_id] for agent_id in active_agents},
    )
    checkpoint = session.checkpoint()
    history = cast(
        list[dict[str, Any]],
        checkpoint.core_checkpoint.state.fact("outbreak_decision.history").value,
    )
    if len(history) != 3:
        raise RuntimeError(f"{branch} ended with {len(history)} coalition rounds")
    final_stances = cast(dict[str, dict[str, str]], history[-1]["stances"])
    decisions = Counter(item["decision"] for item in final_stances.values())
    manifest_observation = next(
        observation.model_dump(mode="json")
        for observation in checkpoint.core_checkpoint.state.observations.values()
        if observation.apparent_source_ref == "regional_allocation_authority"
    )
    return {
        "branch": branch,
        "package_action": package,
        "checkpoint_digest": checkpoint.record_digest,
        "core_checkpoint_digest": checkpoint.core_checkpoint.record_digest,
        "outcome": checkpoint.core_checkpoint.state.fact("outbreak_decision.outcome").value,
        "final_decisions": dict(sorted(decisions.items())),
        "final_stances": final_stances,
        "manifest_observation": manifest_observation,
        "incremental_attempts": [
            item.model_dump(mode="json") for item in checkpoint.attempts[len(shared.attempts) :]
        ],
        "incremental_exact_work": [
            item.model_dump(mode="json")
            for item in checkpoint.exact_work[len(shared.exact_work) :]
        ],
        "incremental_model_calls": sum(
            len(participant.call_evidence)
            for attempt in checkpoint.attempts[len(shared.attempts) :]
            for participant in attempt.participants
        ),
        "incremental_observed_cost": checkpoint.total_observed_cost - shared.total_observed_cost,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="openrouter/openai/gpt-5.6-luna")
    parser.add_argument("--reasoning-effort", default="medium")
    args = parser.parse_args()

    probe_id = f"outbreak_resource_forks_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    fixture = outbreak_fixture(
        "responsive_exercise_injects",
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        world_resource_probe=True,
    )
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        outbreak_bindings(
            fixture,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            trace_id_prefix=f"{probe_id}/shared-prefix",
        ),
        run_id=probe_id,
        config=outbreak_runtime_config(per_call_budget=0.05, per_run_budget=1.0),
        participant_concurrency=8,
    )
    _activate_expected(session, set(AGENT_IDS), "round-one coalition")
    _activate_expected(session, set(SOURCE_IDS), "post-round-one sources")
    _activate_expected(session, set(AGENT_IDS), "round-two coalition")
    shared = session.checkpoint()
    history = cast(
        list[dict[str, Any]],
        shared.core_checkpoint.state.fact("outbreak_decision.history").value,
    )
    if len(history) != 2:
        raise RuntimeError("shared prefix did not end immediately after round two")

    branches = {
        branch: _branch(
            fixture=fixture,
            shared=shared,
            branch=branch,
            model=args.model,
            reasoning_effort=args.reasoning_effort,
            trace_prefix=f"{probe_id}/{branch}",
        )
        for branch in ("no_intervention", "partial", "complete", "false_claim")
    }
    shared_calls = sum(
        len(participant.call_evidence)
        for attempt in shared.attempts
        for participant in attempt.participants
    )
    artifact = {
        "contract": "outbreak-resource-checkpoint-forks.v1",
        "probe_id": probe_id,
        "created_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "claim": (
            "Four final-round coalition continuations share one exact authentic prefix "
            "through every round-two coalition output."
        ),
        "nonclaims": [
            "One retained execution is not a statistical sample or human-behavior estimate.",
            "The packages and resource mechanics are scenario-authored experiment controls.",
            "Only the final-round continuations are checkpoint-paired; model sampling is not seeded.",
        ],
        "shared_checkpoint_digest": shared.record_digest,
        "shared_core_checkpoint_digest": shared.core_checkpoint.record_digest,
        "shared_prefix_model_calls": shared_calls,
        "shared_prefix_observed_cost": shared.total_observed_cost,
        "shared_round_history": history,
        "shared_checkpoint": shared.model_dump(mode="json"),
        "branches": branches,
        "observed_outcomes": {
            branch: {
                "outcome": result["outcome"],
                "final_decisions": result["final_decisions"],
            }
            for branch, result in branches.items()
        },
        "unique_provider_cost": shared.total_observed_cost
        + sum(result["incremental_observed_cost"] for result in branches.values()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "probe_id": probe_id,
                "shared_prefix_model_calls": shared_calls,
                "shared_checkpoint_digest": shared.record_digest,
                "observed_outcomes": artifact["observed_outcomes"],
                "unique_provider_cost": artifact["unique_provider_cost"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
