"""Theory-neutral public projection of one retained general simulation."""

from __future__ import annotations

import json
from typing import Any, cast

from .analysis_projection import project_waltzman_analysis
from .authoring_models import GeneralSimulationProposalV1
from .compiler import CompiledGeneralSimulationV1, CompiledGeneralSimulationV2
from .contracts_v2 import ScenarioSpecV2
from .models import GeneralGroupSimulationResult, GeneralGroupSimulationResultV2


def project_general_run(
    compiled: CompiledGeneralSimulationV1 | CompiledGeneralSimulationV2,
    result: GeneralGroupSimulationResult | GeneralGroupSimulationResultV2,
    *,
    run_id: str,
    created_at: str,
    execution: str,
    presentation_question: str | None = None,
) -> dict[str, object]:
    proposal: GeneralSimulationProposalV1 | ScenarioSpecV2
    if isinstance(compiled, CompiledGeneralSimulationV2):
        if not isinstance(result, GeneralGroupSimulationResultV2):
            raise TypeError("V2 compilation requires a V2 run result")
        v2 = True
        proposal = compiled.scenario
        analyst_question = presentation_question
        question = analyst_question or compiled.scenario.description
        scenario_id = compiled.scenario.scenario_id
        proposal_kind = "general_world_v2"
        analysis_spec: dict[str, object] | None = None
        theory_analysis: dict[str, object] | None = None
    else:
        if not isinstance(result, GeneralGroupSimulationResult):
            raise TypeError("V1 compilation requires a V1 run result")
        v2 = False
        proposal = compiled.proposal
        question = compiled.proposal.question
        analyst_question = question
        scenario_id = compiled.proposal.simulation_id
        proposal_kind = compiled.proposal.proposal_kind
        analysis_spec = (
            compiled.proposal.analysis_spec.model_dump(mode="json")
            if compiled.proposal.analysis_spec is not None
            else None
        )
        theory_analysis = (
            project_waltzman_analysis(compiled, result)
            if compiled.proposal.analysis_spec is not None
            and compiled.proposal.analysis_spec.profile == "waltzman_coordination_v1"
            else None
        )
    state = result.final_state
    nodes = [
        dict(item)
        for item in cast(list[dict[str, object]], compiled.configuration_graph["nodes"])
    ]
    for item in nodes:
        node_id = str(item["id"])
        if node_id in state.records:
            item["state"] = state.records[node_id].state
            item["description"] = json.dumps(state.records[node_id].state, sort_keys=True)
        elif node_id in state.resources:
            item["quantity"] = state.resources[node_id].quantity
        elif node_id in state.routes:
            item["operational"] = state.routes[node_id].operational
    edges = [
        dict(item)
        for item in cast(list[dict[str, object]], compiled.configuration_graph["edges"])
    ]
    traces: list[dict[str, object]] = []
    repaired_actor_trace_ids = {
        receipt.trace_id.removesuffix("/repair/1")
        for receipt in result.model_calls
        if receipt.role == "actor" and receipt.trace_id.endswith("/repair/1")
    }
    for receipt in result.model_calls:
        if receipt.role == "actor":
            if receipt.trace_id in repaired_actor_trace_ids:
                continue
            supplied = json.loads(receipt.input_context)
            if receipt.trace_id.endswith("/repair/1"):
                supplied = supplied["original_input"]
            context = supplied["actor_context"]
            output = receipt.structured_output
            observations = [
                {
                    "apparent_source_ref": item["apparent_source"],
                    "apparent_content": json.dumps(
                        {
                            "document_kind": "influence_message",
                            "delivery_id": item.get("representation_id") or item["observation_id"],
                            "topic": item["apparent_source"],
                            "content": item["content"],
                        }
                    ),
                }
                for item in context["observations"]
            ]
            observations.append(
                {
                    "apparent_source_ref": "canonical_world",
                    "apparent_content": json.dumps(
                        {
                            "document_kind": "decision_round_snapshot",
                            "round_index": context["base_revision"] + 1,
                            "collective_question": question,
                            "round_feedback": "retained semantic intents and committed world evidence",
                        }
                    ),
                }
            )
            traces.append(
                {
                    "trace_id": receipt.trace_id,
                    "participant_kind": "person",
                    "person": context["actor_id"],
                    "activation": context["base_revision"] + 1,
                    "causal_time": context["current_minute"],
                    "logical_time": context["base_revision"] + 1,
                    "moment": context["current_minute"],
                    "base_revision": context["base_revision"],
                    "observations": observations,
                    "assimilation": output.get("assimilation"),
                    "intent": output.get("intent"),
                    "orientation": output.get("intent", {}).get("action"),
                    "actions": [
                        {
                            "public_summary": output.get("intent", {}).get("action"),
                            "output_port_id": "semantic_action_intent",
                            "payload": output.get("intent"),
                        }
                    ],
                    "model_call_count": 1,
                    "model": receipt.model,
                    "provider": receipt.provider,
                }
            )
    events = [
        {
            "event_id": moment.moment_id,
            "kind": "joint_transition",
            "minute": moment.minute,
            "narrative": moment.description,
            "participants": moment.actor_ids,
            "intent_ids": moment.intent_ids,
            "execution_parent": f"revision:{moment.frozen_revision}",
            "resulting_revision": moment.resulting_revision,
            "checkpoint_hash": moment.checkpoint_hash,
        }
        for moment in result.moments
    ]
    accepted = sum(
        1 for item in result.transition_evidence if item.validation.accepted
    )
    rejected = len(result.transition_evidence) - accepted
    observed_costs = [
        receipt.observed_cost
        for receipt in result.model_calls
        if receipt.observed_cost is not None
    ]
    objective_assessment = next(
        (
            item.transaction.objective_assessment
            for item in reversed(result.transition_evidence)
            if item.validation.accepted
            and item.transaction.objective_assessment is not None
        ),
        None,
    )
    return {
        "run_id": run_id,
        "created_at": created_at,
        "status": "completed",
        "scenario": scenario_id,
        "profile": "general_world_v2" if v2 else "general_world_v1",
        "execution_contract": "general_world_v2" if v2 else "general_world_v1",
        "arm": "approved_draft",
        "execution": execution,
        "model_calls": len(result.model_calls),
        "cost": round(sum(observed_costs), 8) if observed_costs else None,
        "cost_coverage": (
            "complete"
            if len(observed_costs) == len(result.model_calls)
            else "partial"
            if observed_costs
            else "unavailable"
        ),
        "execution_providers": sorted({item.provider for item in result.model_calls}),
        "headline": proposal.title,
        "summary": (
            f"{len(proposal.people)} people acted across {len(result.moments)} "
            f"scheduled moments; {accepted} joint transactions committed and {rejected} were rejected."
        ),
        "story": {
            "question": analyst_question,
            "presentation_brief": question,
            "headline": proposal.title,
            "summary": proposal.description,
        },
        "outcome": {
            "final_status": "completed",
            "accepted_transactions": accepted,
            "rejected_transactions": rejected,
            "final_revision": state.revision,
            "objective_assessment": (
                objective_assessment.model_dump(mode="json")
                if objective_assessment is not None
                else None
            ),
        },
        "authoring": {
            "proposal_kind": proposal_kind,
            "proposal_digest": (
                result.scenario_digest
                if isinstance(result, GeneralGroupSimulationResultV2)
                else result.proposal_digest
            ),
            "scenario_digest": (
                result.scenario_digest
                if isinstance(result, GeneralGroupSimulationResultV2)
                else result.proposal_digest
            ),
            "run_spec_digest": (
                result.run_spec_digest
                if isinstance(result, GeneralGroupSimulationResultV2)
                else None
            ),
            "registry_digest": result.registry_digest,
            "title": proposal.title,
            "description": proposal.description,
            "question": question,
            "people": [
                {
                    "entity_id": person.entity_id,
                    "label": person.label,
                    "position": person.position,
                }
                for person in proposal.people
            ],
            "coverage": compiled.coverage.model_dump(mode="json"),
            "analysis_spec": analysis_spec,
        },
        "nodes": nodes,
        "edges": edges,
        "configuration_graph": compiled.configuration_graph,
        "timeline": events,
        "events": events,
        "moments": events,
        "traces": traces,
        "general_simulation": result.model_dump(mode="json"),
        "theory_analysis": theory_analysis,
    }
