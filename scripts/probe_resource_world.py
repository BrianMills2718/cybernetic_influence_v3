"""Compare partial, complete, and contradicted packages from one exact checkpoint.

This is a deliberately narrow live probe. It does not claim that one pair of
LLM calls estimates a general effect; it proves that an allocation authority
changes retained world objects, and that an agent can then reassess from those
changed facts.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue
from cybernetic_influence.active_runtime import ActiveRuntimeSession
from cybernetic_influence.causal_core.models import ActionAttempt
from cybernetic_influence.scenarios.regional_outbreak import (
    outbreak_bindings,
    outbreak_fixture,
    outbreak_runtime_config,
    outbreak_resource_commitments,
)


TARGET = "regional_logistics_coordinator"
FULL = [
    "alba_mobile_lab",
    "borin_clinician_roster",
    "cyrenia_diagnostic_kits",
    "cyrenia_protective_equipment",
    "darsia_cold_chain_route",
    "darsia_fuel_lot",
]
PARTIAL = ["alba_mobile_lab", "borin_clinician_roster"]


def _branch(
    *, fixture: Any, shared: Any, commitment_ids: list[str], model: str,
    reasoning_effort: str, trace_prefix: str,
    contradicted_ids: frozenset[str] = frozenset(),
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
    action: dict[str, JsonValue] = {
        "commitments": cast(
            JsonValue,
            outbreak_resource_commitments(
                commitment_ids, contradicted_ids=contradicted_ids
            ),
        ),
        "verification_status": "contradicted" if contradicted_ids else "verified",
        "manifest_ref": (
            f"allocation-{len(commitment_ids)}-contradicted"
            if contradicted_ids
            else f"allocation-{len(commitment_ids)}-verified-48h"
        ),
    }
    session.apply_external_action(
        ActionAttempt(
            action_id=f"allocate_{len(commitment_ids)}_resources",
            actor_entity_id="regional_allocation_authority",
            output_port_id="resource_allocation_out",
            payload=action,
            logical_time=session.core_state.logical_time,
            public_summary="Applied a retained resource-allocation branch.",
        )
    )
    due = session.next_due_activation()
    if due is None or TARGET not in due.active_system_ids:
        raise RuntimeError("resource branch did not wake the target participant")
    session.activate(
        [TARGET], logical_time=due.logical_time, activation_causes={TARGET: due.causes[TARGET]}
    )
    checkpoint = session.checkpoint()
    participant = checkpoint.attempts[-1].participants[0]
    if participant.proposal is None:
        raise RuntimeError("target produced no proposal")
    return {
        "allocation": action,
        "checkpoint_digest": checkpoint.record_digest,
        "exact_work": [
            item.model_dump(mode="json") for item in checkpoint.exact_work[len(shared.exact_work):]
        ],
        "target_input": participant.input.model_dump(mode="json"),
        "target_output": participant.proposal.actions[0].model_dump(mode="json"),
        "call_evidence": [item.model_dump(mode="json") for item in participant.call_evidence],
        "incremental_observed_cost": checkpoint.total_observed_cost - shared.total_observed_cost,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="openrouter/openai/gpt-5.6-luna")
    parser.add_argument("--reasoning-effort", default="medium")
    args = parser.parse_args()

    probe_id = f"resource_world_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    fixture = outbreak_fixture(
        "baseline", model=args.model, reasoning_effort=args.reasoning_effort,
        world_resource_probe=True,
    )
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        outbreak_bindings(
            fixture, model=args.model, reasoning_effort=args.reasoning_effort,
            trace_id_prefix=f"{probe_id}/shared",
        ),
        run_id=probe_id,
        config=outbreak_runtime_config(per_call_budget=0.05, per_run_budget=0.16),
        participant_concurrency=1,
    )
    shared = session.checkpoint()
    partial = _branch(
        fixture=fixture, shared=shared, commitment_ids=PARTIAL, model=args.model,
        reasoning_effort=args.reasoning_effort, trace_prefix=f"{probe_id}/partial",
    )
    full = _branch(
        fixture=fixture, shared=shared, commitment_ids=FULL, model=args.model,
        reasoning_effort=args.reasoning_effort, trace_prefix=f"{probe_id}/full",
    )
    false_claim = _branch(
        fixture=fixture, shared=shared, commitment_ids=FULL, model=args.model,
        reasoning_effort=args.reasoning_effort, trace_prefix=f"{probe_id}/false-claim",
        contradicted_ids=frozenset(FULL),
    )
    artifact = {
        "contract": "resource-world-checkpoint-probe.v2",
        "probe_id": probe_id,
        "model": args.model,
        "target": TARGET,
        "shared_checkpoint_digest": shared.record_digest,
        "claim": "One recipient reassesses three operationally distinct resource packages from one exact shared checkpoint.",
        "nonclaims": [
            "Three stochastic continuations do not estimate a general causal effect.",
            "The allocation authority is exogenous scenario control, not a coalition participant.",
            "This vertical does not yet model travel, consumption, or implementation failure.",
        ],
        "branches": {"partial": partial, "complete": full, "false_claim": false_claim},
        "observed_decisions": {
            name: branch["target_output"]["payload"]["decision"]
            for name, branch in {"partial": partial, "complete": full, "false_claim": false_claim}.items()
        },
        "unique_provider_cost": sum(
            branch["incremental_observed_cost"] for branch in (partial, full, false_claim)
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "artifact": str(args.output), "target": TARGET,
        "observed_decisions": artifact["observed_decisions"],
        "unique_provider_cost": artifact["unique_provider_cost"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
