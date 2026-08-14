"""Theory-neutral public projection of one retained general simulation."""

from __future__ import annotations

import json
from typing import Any

from .compiler import CompiledGeneralSimulationV1
from .analysis_projection import project_waltzman_analysis
from .models import GeneralGroupSimulationResult


def project_general_run(
    compiled: CompiledGeneralSimulationV1,
    result: GeneralGroupSimulationResult,
    *,
    run_id: str,
    created_at: str,
    execution: str,
) -> dict[str, object]:
    proposal = compiled.proposal
    state = result.final_state
    person_labels = {person.entity_id: person.label for person in proposal.people}
    nodes: list[dict[str, object]] = []
    for record in state.records.values():
        nodes.append(
            {
                "id": record.record_id,
                "type": "person" if record.record_id in person_labels else "thing",
                "kind": "person" if record.record_id in person_labels else record.kind,
                "label": person_labels.get(record.record_id, record.label),
                "description": json.dumps(record.state, sort_keys=True),
                "state": record.state,
            }
        )
    for place in state.places.values():
        nodes.append({"id": place.place_id, "type": "place", "kind": "place", "label": place.label})
    for representation in state.representations.values():
        nodes.append(
            {
                "id": representation.representation_id,
                "type": "representation",
                "kind": "information",
                "label": representation.apparent_source,
                "content": representation.content,
            }
        )
    for resource in state.resources.values():
        nodes.append(
            {
                "id": resource.resource_id,
                "type": "resource",
                "kind": "resource",
                "label": resource.resource_id.replace("_", " ").title(),
                "quantity": resource.quantity,
            }
        )
    edges: list[dict[str, object]] = []
    for route in state.routes.values():
        edges.append(
            {
                "id": route.route_id,
                "type": "route",
                "kind": "route",
                "source": route.origin_id,
                "target": route.destination_id,
                "label": "operational route" if route.operational else "unavailable route",
                "operational": route.operational,
            }
        )
    for placement in state.placements.values():
        edges.append(
            {
                "id": f"placement:{placement.record_id}",
                "type": "placement",
                "kind": "placement",
                "source": placement.record_id,
                "target": placement.place_id,
                "label": "located at",
            }
        )
    for representation in state.representations.values():
        for recipient in representation.recipient_ids:
            edges.append(
                {
                    "id": f"delivery:{representation.representation_id}:{recipient}",
                    "type": "information_delivery",
                    "kind": "information_delivery",
                    "source": representation.representation_id,
                    "target": recipient,
                    "label": "delivered to",
                }
            )
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
                            "collective_question": proposal.question,
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
        "scenario": proposal.simulation_id,
        "profile": "general_world_v1",
        "arm": "approved_draft",
        "execution": execution,
        "model_calls": len(result.model_calls),
        "cost": 0.0,
        "headline": proposal.title,
        "summary": (
            f"{len(proposal.people)} people acted across {len(result.moments)} "
            f"scheduled moments; {accepted} joint transactions committed and {rejected} were rejected."
        ),
        "story": {
            "question": proposal.question,
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
            "proposal_kind": proposal.proposal_kind,
            "proposal_digest": result.proposal_digest,
            "registry_digest": result.registry_digest,
            "title": proposal.title,
            "description": proposal.description,
            "question": proposal.question,
            "people": [
                {
                    "entity_id": person.entity_id,
                    "label": person.label,
                    "position": person.position,
                }
                for person in proposal.people
            ],
            "coverage": compiled.coverage.model_dump(mode="json"),
        },
        "nodes": nodes,
        "edges": edges,
        "timeline": events,
        "events": events,
        "moments": events,
        "traces": traces,
        "general_simulation": result.model_dump(mode="json"),
        "theory_analysis": project_waltzman_analysis(compiled, result),
    }
