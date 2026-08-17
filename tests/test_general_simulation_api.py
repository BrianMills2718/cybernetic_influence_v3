from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import time
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

import cybernetic_influence.api as api_module
from cybernetic_influence.api import create_app
from cybernetic_influence.api import _general_world_node_overrides
from cybernetic_influence.api import _attach_transitions_to_causal_moments
from cybernetic_influence.api import _simulation_replay
from cybernetic_influence.analysis.theory_analysis import AnalysisSpecV2
from cybernetic_influence.general_simulation.authoring_models import (
    AnalysisSpecV1,
    DependencyCompletenessReviewV1,
    GeneralSimulationProposalV1,
    MissingDependencyFindingV1,
)
from cybernetic_influence.general_simulation.authoring import (
    _suppress_redundant_custody_findings,
)
from cybernetic_influence.general_simulation.compiler import (
    materialize_unambiguous_contract_references,
)
from cybernetic_influence.general_simulation.study_models import (
    AuthoredSimulationProposalEnvelopeV2,
    AuthoredSimulationProposalV2,
    AuthoringRunProposalV2,
    adapt_authored_bundle_v1,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    SemanticActionIntent,
    WorldTransactionProposal,
)
from cybernetic_influence.run_configuration import EffectiveRunLlmConfiguration


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


def _native_v2_proposal() -> AuthoredSimulationProposalV2:
    legacy = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    bundle = adapt_authored_bundle_v1(legacy, run_id="draft_fixture_run")
    return AuthoredSimulationProposalV2(
        authored_study_id=bundle.authored_study_id,
        scenario=bundle.scenario,
        default_run=AuthoringRunProposalV2(
            horizon_minutes=bundle.default_run.horizon_minutes,
            scheduled_moments=bundle.default_run.scheduled_moments,
            termination_conditions=bundle.default_run.termination_conditions,
        ),
        analyses=bundle.analyses,
        unresolved_questions=bundle.unresolved_questions,
        analyst_question=bundle.analyst_question,
    )


def test_materializes_only_unambiguous_contract_references() -> None:
    scenario_payload = _native_v2_proposal().scenario.model_dump(mode="json")
    scenario_payload["world_records"].extend(
        [
            {
                "record_id": "outage_truth",
                "kind": "infrastructure_condition",
                "label": "Outage truth",
                "public_state": [],
                "hidden_state": [{"key": "restoration_minutes", "value": 180}],
                "visible_to_actor_ids": ["trucking_dispatcher"],
            },
            {
                "record_id": "restoration_finding",
                "kind": "inspection_finding",
                "label": "Restoration finding",
                "public_state": [],
                "hidden_state": [],
                "visible_to_actor_ids": ["trucking_dispatcher"],
            },
            {
                "record_id": "backup_inventory",
                "kind": "public_inventory",
                "label": "Backup inventory",
                "public_state": [{"key": "available_power", "value": 0}],
                "hidden_state": [],
                "visible_to_actor_ids": ["trucking_dispatcher"],
            },
        ]
    )
    scenario_payload["resource_extension"]["stocks"].append(
        {
            "resource_id": "backup_power",
            "quantity": 0,
            "custodian_id": "trucking_dispatcher",
            "conserved": True,
        }
    )
    scenario_payload["sensing_rules"] = [
        {
            "rule_id": "sense_restoration",
            "subject_ref": "outage_truth",
            "observer_ids": ["trucking_dispatcher"],
            "reveal_hidden_keys": ["restoration_minutes"],
            "output_record_id": "restoration_finding",
            "result_recipient_ids": ["trucking_dispatcher"],
        }
    ]
    scenario_payload["resource_transformations"] = [
        {
            "transformation_id": "convert_fuel",
            "operator_ids": ["trucking_dispatcher"],
            "input_resource_quantities": [
                {"resource_id": "dispatch_fuel", "quantity": 20}
            ],
            "output_resource_id": "backup_power",
            "output_quantity": 80,
            "maximum_batches": 1,
            "public_inventory_record_id": "backup_inventory",
            "public_inventory_input_fields": [
                {"resource_id": "misnamed_fuel", "field": "fuel_received"}
            ],
            "public_inventory_output_field": "available_power",
        }
    ]

    scenario = _native_v2_proposal().scenario.model_validate(scenario_payload)
    normalized, corrections = materialize_unambiguous_contract_references(scenario)

    records = {item.record_id: item for item in normalized.world_records}
    finding_state = {item.key: item.value for item in records["restoration_finding"].public_state}
    inventory_state = {item.key: item.value for item in records["backup_inventory"].public_state}
    transformation = normalized.resource_transformations[0]
    assert finding_state == {"restoration_minutes": None}
    assert inventory_state == {"available_power": 0, "fuel_received": 100.0}
    assert transformation.public_inventory_input_fields[0].resource_id == "dispatch_fuel"
    assert len(corrections) == 3


def _proposal_with_exact_transport_then_transformation() -> AuthoredSimulationProposalV2:
    proposal_payload = _native_v2_proposal().model_dump(mode="json")
    scenario = proposal_payload["scenario"]
    scenario["world_records"].extend(
        [
            {
                "record_id": "fuel_delivery_record",
                "kind": "delivery_record",
                "label": "Fuel delivery record",
                "public_state": [
                    {"key": "arrived_quantity", "value": 0},
                    {"key": "usable_quantity", "value": 0},
                    {"key": "arrival_minute", "value": None},
                ],
                "hidden_state": [],
                "visible_to_actor_ids": ["trucking_dispatcher"],
            },
            {
                "record_id": "hospital_inventory",
                "kind": "public_inventory",
                "label": "Hospital inventory",
                "public_state": [
                    {"key": "fuel_liters", "value": 0},
                    {"key": "available_power", "value": 0},
                ],
                "hidden_state": [],
                "visible_to_actor_ids": ["trucking_dispatcher"],
            },
        ]
    )
    scenario["resource_extension"]["stocks"].extend(
        [
            {
                "resource_id": "fuel_hospital",
                "quantity": 0,
                "custodian_id": "trucking_dispatcher",
                "conserved": True,
            },
            {
                "resource_id": "backup_power",
                "quantity": 0,
                "custodian_id": "trucking_dispatcher",
                "conserved": True,
            },
        ]
    )
    scenario["resource_transports"] = [
        {
            "transport_id": "deliver_fuel",
            "operator_ids": ["trucking_dispatcher"],
            "source_resource_id": "dispatch_fuel",
            "destination_resource_id": "fuel_hospital",
            "source_custodian_id": "trucking_dispatcher",
            "destination_custodian_id": "trucking_dispatcher",
            "quantity": 40,
            "origin_place_id": "outside_port",
            "destination_place_id": "port",
            "allowed_route_ids": ["temporary_route"],
            "arrival_record_id": "fuel_delivery_record",
            "arrival_quantity_key": "arrived_quantity",
            "usable_quantity_key": "usable_quantity",
            "arrival_minute_key": "arrival_minute",
            "required_preconditions": [],
        }
    ]
    temporary_route = next(
        item
        for item in scenario["spatial_extension"]["links"]
        if item["link_id"] == "temporary_route"
    )
    temporary_route["public_state"].append(
        {"key": "travel_time_minutes", "value": 30}
    )
    scenario["resource_transformations"] = [
        {
            "transformation_id": "convert_fuel",
            "operator_ids": ["trucking_dispatcher"],
            "input_resource_quantities": [
                {"resource_id": "fuel_hospital", "quantity": 20}
            ],
            "output_resource_id": "backup_power",
            "output_quantity": 80,
            "maximum_batches": 1,
            "public_inventory_record_id": "hospital_inventory",
            "public_inventory_input_fields": [
                {"resource_id": "fuel_hospital", "field": "fuel_liters"}
            ],
            "public_inventory_output_field": "available_power",
        }
    ]
    scenario["component_requests"].extend(
        [
            {
                "request_id": "deliver_fuel",
                "subject_refs": [
                    "trucking_dispatcher",
                    "dispatch_fuel",
                    "fuel_hospital",
                    "temporary_route",
                ],
                "behavior_description": "Move fuel to hospital custody.",
                "required_reads": ["dispatch_fuel", "temporary_route"],
                "desired_effects": ["transfer bounded fuel custody"],
                "fidelity_need": "exact",
                "causally_material": True,
                "fidelity_material": True,
                "transition_contract_ids": ["deliver_fuel"],
            },
            {
            "request_id": "convert_after_delivery",
            "subject_refs": [
                "trucking_dispatcher",
                "fuel_hospital",
                "backup_power",
            ],
            "behavior_description": "Convert available hospital fuel after delivery.",
            "required_reads": ["fuel_hospital"],
            "desired_effects": ["produce bounded backup power"],
            "fidelity_need": "exact",
            "causally_material": True,
            "fidelity_material": True,
            "transition_contract_ids": ["convert_fuel"],
            },
        ]
    )
    moments = proposal_payload["default_run"]["scheduled_moments"]
    moments[1]["active_component_request_ids"].append("deliver_fuel")
    moments[1]["active_transition_contract_ids"].append("deliver_fuel")
    moments[2]["active_component_request_ids"].append("convert_after_delivery")
    moments[2]["active_transition_contract_ids"].append("convert_fuel")
    return AuthoredSimulationProposalV2.model_validate(proposal_payload)


def test_dependency_review_accepts_prior_exact_transport_as_custody_evidence() -> None:
    proposal = _proposal_with_exact_transport_then_transformation()
    review = DependencyCompletenessReviewV1(
        status="repair_required",
        summary="Delivery record should guard conversion.",
        missing_dependencies=[
            MissingDependencyFindingV1(
                exact_action_request_id="convert_after_delivery",
                prerequisite_description="Fuel delivery must precede conversion.",
                existing_ref="fuel_delivery_record",
                evidence="The proposal says after delivery.",
                required_resolution="exact_guard",
            )
        ],
    )

    filtered, suppressions = _suppress_redundant_custody_findings(proposal, review)

    assert filtered.status == "complete"
    assert filtered.missing_dependencies == []
    assert suppressions and "deliver_fuel" in suppressions[0]

    payload = proposal.model_dump(mode="json")
    fuel = next(
        item
        for item in payload["scenario"]["resource_extension"]["stocks"]
        if item["resource_id"] == "fuel_hospital"
    )
    fuel["quantity"] = 5
    prepositioned = AuthoredSimulationProposalV2.model_validate(payload)
    retained, suppressions = _suppress_redundant_custody_findings(
        prepositioned, review
    )
    assert retained.status == "repair_required"
    assert len(retained.missing_dependencies) == 1
    assert suppressions == []


def test_authoring_uses_materialization_and_custody_evidence_without_regeneration(
    tmp_path: Path,
) -> None:
    payload = _proposal_with_exact_transport_then_transformation().model_dump(
        mode="json"
    )
    inventory = next(
        item
        for item in payload["scenario"]["world_records"]
        if item["record_id"] == "hospital_inventory"
    )
    inventory["public_state"] = [
        item for item in inventory["public_state"] if item["key"] != "fuel_liters"
    ]
    transformation = payload["scenario"]["resource_transformations"][0]
    transformation["public_inventory_input_fields"][0]["resource_id"] = (
        "misnamed_hospital_fuel"
    )
    proposal = AuthoredSimulationProposalV2.model_validate(payload)
    generation_calls = 0
    review_calls = 0

    def provider(*_args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal generation_calls, review_calls
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            review_calls += 1
            return DependencyCompletenessReviewV1(
                status="repair_required",
                summary="Delivery record should guard conversion.",
                missing_dependencies=[
                    MissingDependencyFindingV1(
                        exact_action_request_id="convert_after_delivery",
                        prerequisite_description="Fuel delivery must precede conversion.",
                        existing_ref="fuel_delivery_record",
                        evidence="The proposal says after delivery.",
                        required_resolution="exact_guard",
                    )
                ],
            ), SimpleNamespace(provider="test", cost=0.0)
        generation_calls += 1
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    response = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "deterministic_materialization",
            "message": "Model exact fuel delivery followed by bounded conversion.",
        },
    )

    assert response.status_code == 200
    document = response.json()
    assert document["status"] == "ready_for_review"
    assert generation_calls == 1
    assert review_calls == 1
    assert [item["status"] for item in document["attempts"]] == [
        "accepted",
        "accepted",
    ]
    assert "rebound sole public inventory input mapping" in document["attempts"][0][
        "message"
    ]
    assert "Retained dependency equivalences" in document["attempts"][1]["message"]
    retained_inventory = next(
        item
        for item in document["proposal"]["scenario"]["world_records"]
        if item["record_id"] == "hospital_inventory"
    )
    assert {item["key"]: item["value"] for item in retained_inventory["public_state"]}[
        "fuel_liters"
    ] == 0


def test_general_world_replay_retains_state_by_revision() -> None:
    def state(revision: int, quantity: int) -> dict[str, object]:
        return {
            "revision": revision,
            "records": {
                "inventory": {"state": {"quantity": quantity}},
            },
            "resources": {
                "cargo": {"quantity": quantity, "custodian_id": "operator"},
            },
        }

    def checkpoint(revision: int, quantity: int) -> dict[str, object]:
        return {
            "game_masters": {
                "general_world_game_master": {
                    "components": {
                        "context_components": {
                            "canonical_world": {
                                "spec": {"initial_state": state(0, 0)},
                                "state": state(revision, quantity),
                            }
                        }
                    }
                }
            }
        }

    revisions = _general_world_node_overrides(
        {"checkpoints": [checkpoint(1, 0), checkpoint(2, 500)]}
    )

    initial = {item["node_id"]: item["description"] for item in revisions[0]}
    final = {item["node_id"]: item["description"] for item in revisions[2]}
    assert initial["inventory"] == '{"quantity": 0}'
    assert final["inventory"] == '{"quantity": 500}'
    assert initial["cargo"] == "quantity: 0; custodian: operator"
    assert final["cargo"] == "quantity: 500; custodian: operator"


def test_general_replay_focuses_changed_nodes_and_edges() -> None:
    replay = _simulation_replay(
        title="Route test",
        headline="Route test",
        summary="One retained transition.",
        outcome={"accepted_transactions": 1, "final_revision": 1},
        rounds=[],
        network_nodes=[
            {"id": "operator", "kind": "person", "label": "Operator"},
            {"id": "floor", "kind": "thing", "label": "Floor"},
            {"id": "storage", "kind": "place", "label": "Storage"},
            {"id": "loading", "kind": "place", "label": "Loading"},
        ],
        network_edges=[
            {
                "id": "storage_route",
                "kind": "route",
                "source": "storage",
                "target": "loading",
            }
        ],
        raw_moments=[
            {
                "event_id": "inspect_and_open",
                "narrative": "Inspect the floor and open the route.",
                "participants": ["operator"],
                "execution_parent": "revision:0",
                "resulting_revision": 1,
                "transition": {
                    "transaction": {
                        "operations": [
                            {
                                "operation": "replace",
                                "target": {
                                    "record_type": "record",
                                    "record_id": "floor",
                                    "field": "state.safety_status",
                                },
                                "value": "safe",
                            },
                            {
                                "operation": "replace",
                                "target": {
                                    "record_type": "route",
                                    "record_id": "storage_route",
                                    "field": "operational",
                                },
                                "value": True,
                            },
                        ],
                        "consequences": [],
                        "stated_rationale": "Inspection established a usable route.",
                    }
                },
            }
        ],
        general_world=True,
    )

    assert replay["scenes"][0]["title"] == "Who and what begin in the system"
    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    assert event["focus_node_ids"] == ["floor"]
    assert event["focus_edge_ids"] == ["storage_route"]
    assert "storage_route" in event["visible_edge_ids"]


def test_general_replay_prioritizes_exact_resource_chain_after_earlier_changes() -> None:
    network_nodes: list[dict[str, object]] = [
        {"id": "operator", "kind": "person", "label": "Operator"},
        *[
            {
                "id": f"finding_{index}",
                "kind": "information",
                "label": f"Finding {index}",
            }
            for index in range(5)
        ],
        {"id": "graphite", "kind": "resource", "label": "Graphite cores"},
        {"id": "cedar", "kind": "resource", "label": "Cedar slats"},
        {"id": "pencils", "kind": "resource", "label": "Finished pencils"},
        {"id": "inventory", "kind": "information", "label": "Finished inventory"},
        {
            "id": "make_pencils",
            "kind": "mechanism",
            "label": "Make pencils",
            "mechanism_kind": "resource_transformation",
        },
    ]
    network_edges: list[dict[str, object]] = [
        {
            "id": "make:graphite",
            "kind": "resource_input",
            "source": "graphite",
            "target": "make_pencils",
        },
        {
            "id": "make:cedar",
            "kind": "resource_input",
            "source": "cedar",
            "target": "make_pencils",
        },
        {
            "id": "make:pencils",
            "kind": "resource_output",
            "source": "make_pencils",
            "target": "pencils",
        },
        {
            "id": "make:inventory",
            "kind": "mechanism_write",
            "source": "make_pencils",
            "target": "inventory",
        },
        {
            "id": "make:operator",
            "kind": "capability",
            "source": "operator",
            "target": "make_pencils",
        },
    ]
    operations: list[dict[str, object]] = [
        *[
            {
                "operation": "replace",
                "target": {
                    "record_type": "record",
                    "record_id": f"finding_{index}",
                    "field": "state.status",
                },
                "value": "confirmed",
            }
            for index in range(5)
        ],
        {
            "operation": "replace",
            "target": {
                "record_type": "resource",
                "record_id": "graphite",
                "field": "quantity",
            },
            "value": 100,
        },
        {
            "operation": "replace",
            "target": {
                "record_type": "resource",
                "record_id": "cedar",
                "field": "quantity",
            },
            "value": 100,
        },
        {
            "operation": "replace",
            "target": {
                "record_type": "resource",
                "record_id": "pencils",
                "field": "quantity",
            },
            "value": 500,
        },
        {
            "operation": "replace",
            "target": {
                "record_type": "record",
                "record_id": "inventory",
                "field": "state.quantity",
            },
            "value": 500,
        },
    ]
    replay = _simulation_replay(
        title="Pencil production",
        headline="Pencil production",
        summary="One retained transformation.",
        outcome={"accepted_transactions": 1, "final_revision": 1},
        rounds=[],
        network_nodes=network_nodes,
        network_edges=network_edges,
        raw_moments=[
            {
                "event_id": "produce_pencils",
                "narrative": "Produce a bounded batch of pencils.",
                "participants": ["operator"],
                "execution_parent": "revision:0",
                "resulting_revision": 1,
                "transition": {
                    "transaction": {
                        "operations": operations,
                        "consequences": [],
                        "stated_rationale": "Converted verified inputs into pencils.",
                    },
                    "operation_attributions": [
                        {
                            "operation_index": operation_index,
                            "authority_id": "production_authority",
                            "classification": "exact_contract",
                            "contract_id": "make_pencils",
                        }
                        for operation_index in range(5, 9)
                    ],
                },
            }
        ],
        general_world=True,
    )

    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    assert event["visible_node_ids"][:4] == [
        "make_pencils",
        "graphite",
        "cedar",
        "pencils",
    ]
    assert event["focus_node_ids"][:4] == [
        "make_pencils",
        "graphite",
        "cedar",
        "pencils",
    ]
    assert {
        "make:graphite",
        "make:cedar",
        "make:pencils",
        "make:inventory",
    } <= set(event["visible_edge_ids"])
    fact_values = [item["value"] for item in event["facts"]]
    assert "Graphite cores · quantity: 100" in fact_values
    assert "Cedar slats · quantity: 100" in fact_values
    assert "Finished pencils · quantity: 500" in fact_values
    assert "Finished inventory · state.quantity: 500" in fact_values


def test_general_replay_groups_repairs_with_their_causal_moment() -> None:
    moments = [
        {
            "event_id": "moment_0_inspection",
            "intent_ids": ["inspect"],
            "narrative": "Inspect.",
        },
        {
            "event_id": "moment_30_reservation",
            "intent_ids": ["reserve"],
            "narrative": "Reserve.",
        },
        {
            "event_id": "moment_75_movement",
            "intent_ids": ["move"],
            "narrative": "Move.",
        },
        {
            "event_id": "moment_150_update",
            "intent_ids": ["update"],
            "narrative": "Update.",
        },
    ]

    def transition(moment_id: str, intent_id: str) -> dict[str, object]:
        return {
            "transaction": {
                "evidence_refs": [moment_id],
                "intent_ids": [intent_id],
            },
            "validation": {"accepted": True, "errors": []},
        }

    grouped = _attach_transitions_to_causal_moments(
        moments,
        [
            transition("moment_0_inspection", "inspect"),
            transition("moment_30_reservation", "reserve"),
            transition("moment_30_reservation", "reserve"),
            transition("moment_75_movement", "move"),
            transition("moment_150_update", "update"),
        ],
    )

    assert [len(item["transitions"]) for item in grouped] == [1, 2, 1, 1]


def test_general_replay_exposes_rejected_attempt_before_no_op_repair() -> None:
    false_consequence = {
        "consequence_id": "false_success",
        "recipient_id": "operator",
        "content": "The conversion succeeded and produced 180 power units.",
        "apparent_source": "adjudicator",
        "representation_id": None,
    }
    replay = _simulation_replay(
        title="Conversion attempt",
        headline="Conversion attempt",
        summary="One retained causal moment.",
        outcome={"accepted_transactions": 1, "final_revision": 1},
        rounds=[],
        network_nodes=[
            {"id": "operator", "kind": "person", "label": "Operator"},
            {"id": "fuel", "kind": "resource", "label": "Fuel"},
            {"id": "power", "kind": "resource", "label": "Power"},
        ],
        network_edges=[],
        raw_moments=[
            {
                "event_id": "attempt_conversion",
                "narrative": "Attempt one bounded conversion.",
                "participants": ["operator"],
                "execution_parent": "revision:0",
                "resulting_revision": 1,
                "transitions": [
                    {
                        "transaction": {
                            "operations": [
                                {
                                    "operation": "replace",
                                    "target": {
                                        "record_type": "resource",
                                        "record_id": "fuel",
                                        "field": "quantity",
                                    },
                                    "value": 0,
                                },
                                {
                                    "operation": "replace",
                                    "target": {
                                        "record_type": "resource",
                                        "record_id": "power",
                                        "field": "quantity",
                                    },
                                    "value": 180,
                                },
                            ],
                            "consequences": [false_consequence],
                            "evidence_refs": ["fuel", "power"],
                            "stated_rationale": "The conversion succeeded.",
                        },
                        "validation": {
                            "accepted": False,
                            "errors": [
                                "operation 0 was not licensed",
                                "operation 1 was not licensed",
                            ],
                        },
                    },
                    {
                        "transaction": {
                            "operations": [],
                            "consequences": [false_consequence],
                            "evidence_refs": ["fuel", "power"],
                            "stated_rationale": "The conversion succeeded.",
                        },
                        "envelope_corrections": [
                            "trusted runtime removed only the explicitly unlicensed operations"
                        ],
                        "validation": {"accepted": True, "errors": []},
                    },
                ],
            }
        ],
        general_world=True,
    )

    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    facts = {item["label"]: item["value"] for item in event["facts"]}
    assert facts["Transaction attempts"] == "2"
    assert facts["Rejected attempts"] == (
        "1 · 2 proposed world changes did not commit"
    )
    assert facts["World change"] == (
        "No canonical fields changed in this committed moment."
    )
    assert "conversion succeeded" not in event["summary"].lower()
    assert all(
        "conversion succeeded" not in item["value"].lower()
        for item in event["facts"]
    )
    assert event["focus_node_ids"] == ["operator"]


def test_general_replay_does_not_present_rejected_operations_as_world_changes() -> None:
    replay = _simulation_replay(
        title="Blocked dispatch",
        headline="Blocked dispatch",
        summary="One rejected transition.",
        outcome={"accepted_transactions": 0, "final_revision": 0},
        rounds=[],
        network_nodes=[
            {"id": "operator", "kind": "person", "label": "Operator"},
            {"id": "cargo", "kind": "resource", "label": "Cargo"},
        ],
        network_edges=[],
        raw_moments=[
            {
                "event_id": "attempt_dispatch",
                "narrative": "Attempt cargo dispatch.",
                "participants": ["operator"],
                "execution_parent": "revision:0",
                "resulting_revision": 0,
                "transition": {
                    "transaction": {
                        "operations": [
                            {
                                "operation": "replace",
                                "target": {
                                    "record_type": "resource",
                                    "record_id": "cargo",
                                    "field": "quantity",
                                },
                                "value": 0,
                            }
                        ],
                        "consequences": [],
                        "stated_rationale": "Cargo moved successfully.",
                    },
                    "validation": {
                        "accepted": False,
                        "errors": [
                            "precondition failed for dispatch authorization",
                            "precondition failed for route clearance",
                        ],
                    },
                },
            }
        ],
        general_world=True,
    )

    event = next(scene for scene in replay["scenes"] if scene["kind"] == "event")
    assert event["summary"] == (
        "Canonical validation rejected the joint attempt, so none of its 1 "
        "proposed world change committed. 2 required preconditions were not met."
    )
    assert event["focus_node_ids"] == ["operator"]
    assert {item["label"]: item["value"] for item in event["facts"]} == {
        "Moment": "1",
        "People acting": "1",
        "Attempt": "Rejected · 1 proposed world change",
        "World change": "No change committed.",
        "Why": "2 required preconditions were not met.",
    }


class _GeneralRuntimeFake:
    def __init__(self) -> None:
        self.actor_counter = 0
        self.supplied_inputs: list[dict[str, object]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[object, object]:
        response_model = kwargs["response_model"]
        user = json.loads(args[1][1]["content"])
        self.supplied_inputs.append(user)
        if response_model is ActorDecision:
            self.actor_counter += 1
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    memory_additions=[f"memory {self.actor_counter}"],
                    memory_revisions=[],
                    provenance_links=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    interpretation="Bounded fixture interpretation.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{self.actor_counter}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a bounded joint check.",
                    target_refs=["relief_cargo"],
                    purpose="Explore the configured question.",
                    expected_effect="A joint proposal.",
                    stated_rationale="Available evidence supports a bounded attempt.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransactionProposal(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the world while recording joint review.",
        ), SimpleNamespace(provider="fixture")


def test_general_authoring_api_create_generate_preview_edit_and_approve(
    tmp_path: Path,
) -> None:
    proposal = _native_v2_proposal()

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="No stated exact-action prerequisite is omitted.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        assert "state.<key>" in args[1][0]["content"]
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    created = api.post("/api/authoring/drafts")
    assert created.status_code == 200
    draft = created.json()
    assert draft["target_kind"] == "general_world_v2"

    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "port_prompt",
            "message": "Model relief cargo coordination after a bridge failure.",
        },
    )
    assert generated.status_code == 200
    assert [item["status"] for item in generated.json()["attempts"]] == [
        "accepted",
        "accepted",
    ]
    assert generated.json()["messages"][-1]["trace_ids"][-1].endswith(
        "/dependency-review"
    )
    assert generated.json()["configuration_graph"]["isolated_node_ids"] == []
    assert generated.json()["configuration_graph"]["edges"]
    document = generated.json()
    assert document["status"] == "ready_for_review"
    assert document["coverage"]["blocking_request_ids"] == []
    assert all(
        item["causal_closure"] in {"exact", "coarse"}
        for item in document["coverage"]["items"]
    )


    retained_path = tmp_path / "drafts" / f"{draft['draft_id']}.json"
    retained = json.loads(retained_path.read_text(encoding="utf-8"))
    retained["coverage"] = {
        "registry_digest": "stale_snapshot",
        "items": [],
        "blocking_request_ids": [],
    }
    retained_path.write_text(json.dumps(retained), encoding="utf-8")
    reopened = api.get(f"/api/authoring/drafts/{draft['draft_id']}")
    assert reopened.status_code == 200
    assert reopened.json()["coverage"]["registry_digest"] != "stale_snapshot"
    assert reopened.json()["coverage"]["items"]

    preview = api.get(f"/api/authoring/drafts/{draft['draft_id']}/preview")
    assert preview.status_code == 200
    preview_payload = preview.json()
    assert preview_payload["profile"] == "general_world_v2"
    assert preview_payload["world_spec"]["spec_id"] == "relief_port_coordination"
    assert preview_payload["composition_receipt"]["resolved_component_refs"]

    edited = deepcopy(document["proposal"])
    edited["analyst_question"] = "Can the parties dispatch safely before sunset?"
    response = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 1, "edit_id": "question_edit", "proposal": edited},
    )
    assert response.status_code == 200
    assert response.json()["revision"] == 2

    stale = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 1, "edit_id": "stale_edit", "proposal": edited},
    )
    assert stale.status_code == 409

    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": 2},
    )
    assert approved.status_code == 200
    assert approved.json()["approval"]["registry_digest"]


def test_dependency_review_repairs_an_omitted_exact_action_prerequisite(
    tmp_path: Path,
) -> None:
    proposal = _native_v2_proposal()
    review_calls = 0
    generation_inputs: list[str] = []

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal review_calls
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            review_calls += 1
            if review_calls == 1:
                return DependencyCompletenessReviewV1(
                    status="repair_required",
                    summary="Cargo movement omitted one stated prerequisite.",
                    missing_dependencies=[
                        MissingDependencyFindingV1(
                            exact_action_request_id="cargo_movement",
                            prerequisite_description="Customs clearance must gate movement.",
                            existing_ref="customs_release_status",
                            evidence="The analyst called customs clearance a genuine prerequisite.",
                            required_resolution="exact_guard",
                        )
                    ],
                ), SimpleNamespace(provider="test", cost=0.0)
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="The repaired candidate covers every stated prerequisite.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        generation_inputs.append(str(args[1][1]["content"]))
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "review_repair",
            "message": "Model cargo movement where customs clearance is a genuine prerequisite.",
        },
    )

    assert generated.status_code == 200
    assert generated.json()["status"] == "ready_for_review"
    assert review_calls == 2
    assert len(generation_inputs) == 2
    assert "Dependency completeness review requires repair" in generation_inputs[1]
    assert [item["status"] for item in generated.json()["attempts"]] == [
        "accepted",
        "repair",
        "accepted",
        "accepted",
    ]


def test_dependency_review_can_repair_after_two_compiler_retries(
    tmp_path: Path,
) -> None:
    proposal = _native_v2_proposal()
    generation_calls = 0
    review_calls = 0

    def provider(*_args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal generation_calls, review_calls
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            review_calls += 1
            if review_calls == 1:
                return DependencyCompletenessReviewV1(
                    status="repair_required",
                    summary="The compiled candidate omitted one communication prerequisite.",
                    missing_dependencies=[
                        MissingDependencyFindingV1(
                            exact_action_request_id="cargo_movement",
                            prerequisite_description=(
                                "The bridge finding must reach the transport coordinator."
                            ),
                            existing_ref="bridge_finding_delivery",
                            evidence="The analyst required the finding to be communicated.",
                            required_resolution="declare_world_state",
                        )
                    ],
                ), SimpleNamespace(provider="test", cost=0.0)
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="The repaired candidate covers the communication prerequisite.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        generation_calls += 1
        if generation_calls <= 2:
            raise ValueError(f"bounded compiler repair {generation_calls}")
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    generated = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "late_review_repair",
            "message": "Model a bridge-dependent cargo transfer.",
        },
    )

    assert generated.status_code == 200
    assert generated.json()["status"] == "ready_for_review"
    assert generation_calls == 4
    assert review_calls == 2
    assert [item["status"] for item in generated.json()["attempts"]] == [
        "repair",
        "repair",
        "accepted",
        "repair",
        "accepted",
        "accepted",
    ]


def test_live_general_authoring_runs_as_pollable_background_job(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    monkeypatch.setattr(
        api_module,
        "model_catalog",
        lambda: [{"model": "codex/gpt-5.6-luna"}],
    )
    proposal = _native_v2_proposal()

    def provider(*args: Any, **kwargs: Any) -> tuple[object, object]:
        del args
        if kwargs["response_model"] is DependencyCompletenessReviewV1:
            return DependencyCompletenessReviewV1(
                status="complete",
                summary="No stated exact-action prerequisite is omitted.",
                missing_dependencies=[],
            ), SimpleNamespace(provider="test", cost=0.0)
        return AuthoredSimulationProposalEnvelopeV2(proposal=proposal), SimpleNamespace(
            provider="test", cost=0.0
        )

    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            authoring_call=provider,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    started = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/messages",
        json={
            "expected_revision": 0,
            "message_id": "background_generation",
            "message": "Model relief cargo coordination after a bridge failure.",
        },
    )

    assert started.status_code == 202
    job = started.json()
    assert job["status"] == "generating"
    for _ in range(100):
        polled = api.get(f"/api/authoring/jobs/{job['job_id']}")
        assert polled.status_code == 200
        job = polled.json()
        if job["status"] != "generating":
            break
        time.sleep(0.01)
    assert job["status"] == "completed"
    assert job["draft"]["status"] == "ready_for_review"
    assert job["draft"]["revision"] == 1


def test_general_proposal_endpoint_rejects_invented_implementation_reference(
    tmp_path: Path,
) -> None:
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload["component_requests"][0]["implementation_ref"] = "invented.module:run"

    response = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 0, "edit_id": "bad", "proposal": payload},
    )

    assert response.status_code == 422
    assert "implementation_ref" in response.text


def test_approved_general_draft_runs_and_reopens_without_more_calls(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CYBERNETIC_INFLUENCE_LIVE", "1")
    effective = EffectiveRunLlmConfiguration(
        model="codex/gpt-5.6-luna",
        agent_reasoning_effort="medium",
        narrator_reasoning_effort="none",
        max_total_cost=0.74,
        selection_basis="operator_selected",
        llm_client_revision="fixture",
        billing_mode="subscription_included",
    )
    monkeypatch.setattr(api_module, "resolve_live_configuration", lambda _options: effective)
    runtime_call = _GeneralRuntimeFake()
    api = TestClient(
        create_app(
            Path(__file__).resolve().parents[1] / "web",
            tmp_path / "runs",
            authoring_root=tmp_path / "drafts",
            general_simulation_call=runtime_call,
        )
    )
    draft = api.post("/api/authoring/drafts").json()
    legacy = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    legacy.analysis_spec = legacy.analysis_spec or AnalysisSpecV1(
        analysis_id="waltzman_port_diagnostic",
        profile="waltzman_coordination_v1",
        purpose="Inspect influence-to-coordination signals in the retained run.",
    )
    proposal = adapt_authored_bundle_v1(
        legacy, run_id=f"{draft['draft_id']}_run"
    ).model_dump(mode="json")
    edited = api.put(
        f"/api/authoring/drafts/{draft['draft_id']}/general-proposal",
        json={"expected_revision": 0, "edit_id": "fixture", "proposal": proposal},
    ).json()
    approved = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/approve",
        json={"expected_revision": edited["revision"]},
    )
    assert approved.status_code == 200
    started = api.post(
        f"/api/authoring/drafts/{draft['draft_id']}/runs",
        json={
            "execution": "live",
            "narration": "deterministic",
            "llm_options": {
                "model": "codex/gpt-5.6-luna",
                "agent_reasoning_effort": "medium",
                "max_total_cost": 0.74,
            },
        },
    )
    assert started.status_code == 202, started.text
    run_id = started.json()["run_id"]
    for _ in range(200):
        reopened = api.get(f"/api/runs/{run_id}").json()
        if reopened["status"] != "running":
            break
        time.sleep(0.01)
    assert reopened["status"] == "completed", reopened
    assert reopened["profile"] == "general_world_v2"
    assert reopened["execution_contract"] == "general_world_v2"
    assert reopened["authoring"]["proposal_kind"] == "general_world_v2"
    assert reopened["authoring"]["scenario_digest"]
    assert reopened["authoring"]["run_spec_digest"]
    assert reopened["model_calls"] == 15
    assert reopened["general_simulation"]["run_id"] == run_id
    assert "question" not in reopened["general_simulation"]
    assert reopened["run_evidence_bundle"]["run_id"] == run_id
    assert len(reopened["analysis_results"]) == 1
    assert reopened["analysis_results"][0]["coverage_status"] == "supported"
    assert all(
        "research_question" not in supplied
        for supplied in runtime_call.supplied_inputs
    )
    assert all("analysis_spec" not in supplied for supplied in runtime_call.supplied_inputs)
    assert reopened["general_simulation"]["adoption"]["engine_class"].endswith(
        "simultaneous.Simultaneous"
    )
    assert len(reopened["general_simulation"]["moments"]) == 3
    call_count = runtime_call.actor_counter
    summary = api.get(f"/api/runs/{run_id}/summary")
    assert summary.status_code == 200, summary.text
    summary_payload = summary.json()
    assert summary_payload["profile"] == "general_world_v2"
    assert summary_payload["execution_contract"] == "general_world_v2"
    assert summary_payload["authoring"]["question"]
    assert summary_payload["evidence_bundle"]["record_digest"]
    assert summary_payload["evidence_bundle"]["evidence_record_count"] > 0
    assert len(summary_payload["analysis_results"]) == 1
    assert summary_payload["causal_moments"] == 3
    assert summary_payload["participant_model_calls"] == 15
    assert summary_payload["simulation_replay"]["scenes"]
    assert not any(
        node["id"] == "collective_decision"
        for node in summary_payload["influence_network"]["nodes"]
    )
    assert summary_payload["simulation_replay"]["scenes"][0]["visible_node_ids"] == []
    assert summary_payload["simulation_replay"]["scenes"][0]["title"] == "Your review question"
    replay_scenes = summary_payload["simulation_replay"]["scenes"]
    assert len([scene for scene in replay_scenes if scene["kind"] == "event"]) == 3
    assert not any(scene["kind"] == "decisions" for scene in replay_scenes)
    assert not any(
        fact["label"] == "Positions"
        for scene in replay_scenes
        for fact in scene["facts"]
    )
    event_scenes = [scene for scene in replay_scenes if scene["kind"] == "event"]
    assert all(len(scene["visible_node_ids"]) <= 12 for scene in event_scenes)
    assert all(len(scene["visible_edge_ids"]) <= 18 for scene in event_scenes)
    assert all(
        any(fact["label"] == "World change" for fact in scene["facts"])
        for scene in event_scenes
    )
    assert not any(
        fact["label"] == "World transition"
        for scene in event_scenes
        for fact in scene["facts"]
    )

    before_revision = reopened["general_simulation"]["final_state"]["revision"]
    before_evidence = reopened["run_evidence_bundle"]["record_digest"]
    before_calls = reopened["model_calls"]
    exact_spec = AnalysisSpecV2(
        analysis_id="exact_terminal_review",
        profile="exact_outcome_v1",
        purpose="Read the retained terminal outcome without changing the run.",
        construct_definitions=["Terminal state is read from retained evidence."],
        required_evidence_kinds=["configuration", "terminal_state"],
        method_classes=["exact"],
        aggregation="Report the retained terminal evidence.",
        uncertainty="No inference beyond retained state.",
        limitations=["This does not establish a counterfactual."],
    )
    attached = api.post(
        f"/api/runs/{run_id}/analyses",
        json={"analysis_spec": exact_spec.model_dump(mode="json")},
    )
    assert attached.status_code == 200, attached.text
    assert len(attached.json()["analysis_results"]) == 2
    assert attached.json()["analysis_isolation_receipts"][-1][
        "simulation_unchanged"
    ]
    after_attachment = api.get(f"/api/runs/{run_id}").json()
    assert after_attachment["model_calls"] == before_calls
    assert after_attachment["general_simulation"]["final_state"]["revision"] == before_revision
    assert after_attachment["run_evidence_bundle"]["record_digest"] == before_evidence

    mutation_attempt = exact_spec.model_dump(mode="json")
    mutation_attempt["world_patch"] = {"operations": [{"op": "remove", "target": "port"}]}
    rejected = api.post(
        f"/api/runs/{run_id}/analyses",
        json={"analysis_spec": mutation_attempt},
    )
    assert rejected.status_code == 422
    after_rejection = api.get(f"/api/runs/{run_id}").json()
    assert after_rejection["model_calls"] == before_calls
    assert after_rejection["general_simulation"]["final_state"]["revision"] == before_revision
    assert after_rejection["run_evidence_bundle"]["record_digest"] == before_evidence

    removed = api.delete(f"/api/runs/{run_id}/analyses/exact_terminal_review")
    assert removed.status_code == 200, removed.text
    assert len(removed.json()["analysis_results"]) == 1
    assert removed.json()["analysis_isolation_receipts"][-1][
        "simulation_unchanged"
    ]
    assert replay_scenes[1]["facts"] == [
        {"label": "People", "value": "4"},
        {"label": "Other world components", "value": "17"},
    ]
    assert len(replay_scenes[1]["visible_node_ids"]) < len(
        summary_payload["influence_network"]["nodes"]
    )
    assert len(replay_scenes[-1]["visible_node_ids"]) < len(
        summary_payload["influence_network"]["nodes"]
    )
    outcome_scene = replay_scenes[-1]
    assert len(outcome_scene["visible_node_ids"]) <= 12
    assert len(outcome_scene["visible_edge_ids"]) <= 18
    assert outcome_scene["summary"] == (
        "The simulation completed 3 scheduled moments. 3 committed a validated "
        "transition; the retained final world is revision 3."
    )
    assert outcome_scene["facts"] == [
        {"label": "Committed transitions", "value": "3"},
        {"label": "Final world revision", "value": "3"},
    ]
    assert summary_payload["theory_analysis"] is None
    assert runtime_call.actor_counter == call_count
