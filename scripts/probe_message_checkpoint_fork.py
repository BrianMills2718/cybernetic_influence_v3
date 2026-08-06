#!/usr/bin/env python3
"""Run one disposable exact-checkpoint direct-message fork."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any, cast

from pydantic import JsonValue

from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeCheckpoint,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ScriptedActiveSystem,
    UpdateScheduleDirective,
)
from cybernetic_influence.causal_core.models import ActionAttempt
from cybernetic_influence.scenarios.regional_outbreak import (
    AGENT_IDS,
    SOURCE_IDS,
    OutbreakFixture,
    outbreak_bindings,
    outbreak_fixture,
    outbreak_runtime_config,
)


def _static_source_bindings(
    fixture: OutbreakFixture,
    native: Mapping[str, ActiveSystemBinding],
) -> dict[str, ActiveSystemBinding]:
    bindings = dict(native)
    specs = {item.active_system_id: item for item in fixture.active_specs}
    for source_id in SOURCE_IDS:
        implementation_id = specs[source_id].implementation_id

        def step(
            active_input: ActiveSystemInput,
            *,
            expected_source_id: str = source_id,
            expected_implementation_id: str = implementation_id,
        ) -> ActiveStepResult:
            return ActiveStepResult(
                proposal=ActiveProposal(
                    active_system_id=expected_source_id,
                    implementation_id=expected_implementation_id,
                    private_state=active_input.private_state,
                    actions=[
                        ActionIntent(
                            output_port_id=f"{expected_source_id}_out",
                            payload={
                                "signal_id": "verify",
                                "rationale": (
                                    "Fixed identical verification source used in both "
                                    "checkpoint branches."
                                ),
                            },
                            public_summary="Emitted the fixed paired-probe source signal.",
                        )
                    ],
                    update_schedule=UpdateScheduleDirective(mode="dormant"),
                )
            )

        bindings[source_id] = ActiveSystemBinding(
            implementation_id,
            ScriptedActiveSystem(implementation_id, step),
        )
    return bindings


def _native_bindings(
    fixture: OutbreakFixture,
    *,
    model: str,
    reasoning_effort: str,
    trace_prefix: str,
) -> dict[str, ActiveSystemBinding]:
    return _static_source_bindings(
        fixture,
        outbreak_bindings(
            fixture,
            trace_id_prefix=trace_prefix,
            model=model,
            reasoning_effort=reasoning_effort,
        ),
    )


def _choose_target(
    checkpoint: ActiveRuntimeCheckpoint, requested: str | None
) -> tuple[str, list[dict[str, Any]]]:
    raw_messages = checkpoint.core_checkpoint.state.fact(
        "outbreak_decision.coordination_messages"
    ).value
    messages = [
        cast(dict[str, Any], item)
        for item in cast(list[object], raw_messages)
        if cast(dict[str, Any], item)["outcome"] == "queued_for_next_round"
    ]
    counts = Counter(str(item["target_ref"]) for item in messages)
    if requested is not None:
        if requested not in AGENT_IDS:
            raise ValueError(f"unknown target participant: {requested}")
        if counts[requested] == 0:
            raise RuntimeError(f"round one produced no queued message for {requested}")
        target = requested
    elif 0 < counts["regional_scientific_advisor"] <= 3:
        target = "regional_scientific_advisor"
    else:
        candidates = sorted(
            ((count, target_ref) for target_ref, count in counts.items() if count > 0)
        )
        if not candidates:
            raise RuntimeError("round one produced no queued direct message")
        target = candidates[0][1]
    return target, [item for item in messages if item["target_ref"] == target]


def _direct_messages(active_input: ActiveSystemInput) -> list[dict[str, Any]]:
    delivered: list[dict[str, Any]] = []
    for observation in active_input.observations:
        try:
            content = json.loads(observation.apparent_content)
        except json.JSONDecodeError:
            continue
        if isinstance(content, dict) and isinstance(content.get("direct_messages"), list):
            delivered.extend(cast(list[dict[str, Any]], content["direct_messages"]))
    return delivered


def _run_branch(
    *,
    fixture: OutbreakFixture,
    shared: ActiveRuntimeCheckpoint,
    mode: str,
    target: str,
    model: str,
    reasoning_effort: str,
    trace_prefix: str,
) -> dict[str, Any]:
    bindings = _native_bindings(
        fixture,
        model=model,
        reasoning_effort=reasoning_effort,
        trace_prefix=trace_prefix,
    )
    session = ActiveRuntimeSession.restore(
        fixture.scenario, fixture.exact_bindings, bindings, shared
    )
    control_payload: dict[str, JsonValue] = {
        "mode": mode,
        "target_ref": target,
        "round": 1,
    }
    session.apply_external_action(
        ActionAttempt(
            action_id=f"message_fork_{mode}",
            actor_entity_id="message_fork_controller",
            output_port_id="message_fork_control_out",
            payload=control_payload,
            logical_time=session.core_state.logical_time,
            public_summary=f"Applied the explicit {mode} branch at the shared checkpoint.",
        )
    )
    sources = session.next_due_activation()
    if sources is None or set(sources.active_system_ids) != set(SOURCE_IDS):
        raise RuntimeError("fork did not resume at the fixed source phase")
    session.activate(
        sources.active_system_ids,
        logical_time=sources.logical_time,
        activation_causes=sources.causes,
    )
    participants = session.next_due_activation()
    if participants is None or target not in participants.active_system_ids:
        raise RuntimeError("fork did not deliver the round-two recipient input")
    session.activate(
        [target],
        logical_time=participants.logical_time,
        activation_causes={target: participants.causes[target]},
    )
    checkpoint = session.checkpoint()
    attempt = checkpoint.attempts[-1]
    participant = attempt.participants[0]
    if participant.proposal is None:
        raise RuntimeError("recipient branch produced no proposal")
    return {
        "mode": mode,
        "control_action": control_payload,
        "checkpoint_digest": checkpoint.record_digest,
        "new_exact_work": [
            item.model_dump(mode="json")
            for item in checkpoint.exact_work[len(shared.exact_work) :]
        ],
        "source_attempt": checkpoint.attempts[-2].model_dump(mode="json"),
        "recipient_attempt": attempt.model_dump(mode="json"),
        "recipient_direct_messages": _direct_messages(participant.input),
        "recipient_output": participant.proposal.actions[0].model_dump(mode="json"),
        "recipient_private_state": participant.proposal.private_state,
        "incremental_observed_cost": (
            checkpoint.total_observed_cost - shared.total_observed_cost
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target")
    parser.add_argument("--model", default="openrouter/openai/gpt-5.6-terra")
    parser.add_argument("--reasoning-effort", default="medium")
    args = parser.parse_args()

    probe_id = f"message_fork_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    fixture = outbreak_fixture(
        "responsive_exercise_injects",
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        message_fork_probe=True,
    )
    prefix_bindings = _native_bindings(
        fixture,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        trace_prefix=f"{probe_id}/shared-prefix",
    )
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        prefix_bindings,
        run_id=probe_id,
        config=outbreak_runtime_config(per_call_budget=0.05, per_run_budget=0.74),
        participant_concurrency=3,
    )
    first = session.next_due_activation()
    if first is None or set(first.active_system_ids) != set(AGENT_IDS):
        raise RuntimeError("probe did not start with the complete coalition")
    session.activate(
        first.active_system_ids,
        logical_time=first.logical_time,
        activation_causes=first.causes,
    )
    sources = session.next_due_activation()
    if sources is None or set(sources.active_system_ids) != set(SOURCE_IDS):
        raise RuntimeError("probe did not reach the post-round-one fork boundary")
    shared = session.checkpoint()
    target, queued_messages = _choose_target(shared, args.target)

    delivery = _run_branch(
        fixture=fixture,
        shared=shared,
        mode="deliver",
        target=target,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        trace_prefix=f"{probe_id}/delivery",
    )
    withheld = _run_branch(
        fixture=fixture,
        shared=shared,
        mode="withhold_target",
        target=target,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        trace_prefix=f"{probe_id}/withheld",
    )
    artifact = {
        "contract": "message-checkpoint-fork-probe.v1",
        "probe_id": probe_id,
        "created_at": datetime.now(UTC).isoformat(),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "claim": (
            "One recipient can be reassessed from an exact shared prefix with queued "
            "direct messages delivered versus explicitly withheld."
        ),
        "nonclaims": [
            "This one stochastic pair does not estimate a general causal effect.",
            "Output differences are not attributable solely to delivery without replication or provider seed control.",
            "The withhold action is experiment control, not a modeled real-world failure mechanism.",
        ],
        "target": target,
        "shared_checkpoint_digest": shared.record_digest,
        "shared_core_checkpoint_digest": shared.core_checkpoint.record_digest,
        "shared_prefix_model_calls": sum(
            len(participant.call_evidence)
            for attempt in shared.attempts
            for participant in attempt.participants
        ),
        "shared_prefix_observed_cost": shared.total_observed_cost,
        "queued_messages_to_target": queued_messages,
        "shared_checkpoint": shared.model_dump(mode="json"),
        "branches": {"delivery": delivery, "withheld": withheld},
        "observed_differences": {
            "decision_changed": (
                delivery["recipient_output"]["payload"]["decision"]
                != withheld["recipient_output"]["payload"]["decision"]
            ),
            "risk_changed": (
                delivery["recipient_output"]["payload"]["risk"]
                != withheld["recipient_output"]["payload"]["risk"]
            ),
            "request_changed": (
                delivery["recipient_output"]["payload"]["request"]
                != withheld["recipient_output"]["payload"]["request"]
            ),
            "rationale_changed": (
                delivery["recipient_output"]["payload"]["rationale"]
                != withheld["recipient_output"]["payload"]["rationale"]
            ),
            "action_changed": (
                delivery["recipient_output"]["payload"]["coordination_content"]
                != withheld["recipient_output"]["payload"]["coordination_content"]
            ),
        },
        "unique_provider_cost": (
            shared.total_observed_cost
            + delivery["incremental_observed_cost"]
            + withheld["incremental_observed_cost"]
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(args.output),
                "probe_id": probe_id,
                "target": target,
                "queued_message_count": len(queued_messages),
                "delivery_message_count": len(delivery["recipient_direct_messages"]),
                "withheld_message_count": len(withheld["recipient_direct_messages"]),
                "observed_differences": artifact["observed_differences"],
                "unique_provider_cost": artifact["unique_provider_cost"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
