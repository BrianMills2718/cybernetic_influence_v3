from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cybernetic_influence.general_simulation.authoring_models import (
    AnalysisSpecV1,
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.compiler import compile_general_simulation
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    Consequence,
    PatchOperation,
    Precondition,
    ResourceTransportContract,
    SemanticActionIntent,
    SensingTransitionContract,
    TypedTarget,
    WorldRecord,
    WorldTransaction,
    WorldTransactionProposal,
)
from cybernetic_influence.general_simulation.runner import (
    _drop_unauthorized_representation_deliveries,
    _inject_selected_contract_preconditions,
    _memory_reference_is_grounded,
    _normalize_transaction_targets,
    _normalized_memory,
    run_general_simulation,
)
from cybernetic_influence.general_simulation.world import CanonicalWorld
from cybernetic_influence.general_simulation.analysis_projection import (
    project_waltzman_analysis,
)
from cybernetic_influence.general_simulation.projection import project_general_run


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")
SERVICE_FIXTURE = Path("tests/fixtures/general_simulation/service_incident.json")


def test_memory_provenance_accepts_only_unambiguous_sentence_prefixes() -> None:
    first = (
        "At minute 105, the outage remains active across multiple regions. "
        "The external dependency remains unknown."
    )
    second = "At minute 75, the outage remains active across one region."
    memories = {_normalized_memory(first), _normalized_memory(second)}

    assert _memory_reference_is_grounded(first, memories)
    assert _memory_reference_is_grounded(
        "At minute 105, the outage remains active across multiple regions.", memories
    )
    assert not _memory_reference_is_grounded(
        "The outage remains active across multiple regions.", memories
    )
    assert not _memory_reference_is_grounded("At minute 105", memories)

    ambiguous = memories | {
        _normalized_memory(
            "At minute 105, the outage remains active across multiple regions. "
            "A different dependency remains unknown."
        )
    }
    assert not _memory_reference_is_grounded(
        "At minute 105, the outage remains active across multiple regions.", ambiguous
    )


def test_existing_record_state_fields_are_normalized_before_validation() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    world = CanonicalWorld(compile_general_simulation(proposal).world_spec)
    transaction = WorldTransaction(
        transaction_id="normalize_record_state",
        base_revision=0,
        authority_id="general_semantic_adjudicator",
        intent_ids=["intent_1"],
        operations=[
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="record",
                    record_id="relief_cargo",
                    field="status",
                ),
                value="dispatched",
            )
        ],
        preconditions=[
            Precondition(
                target=TypedTarget(
                    record_type="record",
                    record_id="relief_cargo",
                    field="status",
                ),
                expected="awaiting_dispatch",
            )
        ],
        consequences=[],
        evidence_refs=["relief_cargo"],
        stated_rationale="Exercise typed record-state normalization.",
    )
    corrections: list[str] = []

    normalized = _normalize_transaction_targets(transaction, world, corrections)

    assert normalized.operations[0].target.field == "state.status"
    assert normalized.preconditions[0].target.field == "state.status"
    assert corrections == [
        "operation target relief_cargo field normalized from status to state.status",
        "precondition target relief_cargo field normalized from status to state.status",
    ]


def test_whole_record_targets_do_not_require_state_field_normalization() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    world = CanonicalWorld(compile_general_simulation(proposal).world_spec)
    transaction = WorldTransaction(
        transaction_id="whole_record_target",
        base_revision=0,
        authority_id="general_semantic_adjudicator",
        intent_ids=["intent_1"],
        operations=[
            PatchOperation(
                operation="remove",
                target=TypedTarget(
                    record_type="record", record_id="relief_cargo", field=None
                ),
            )
        ],
        preconditions=[],
        consequences=[],
        evidence_refs=["relief_cargo"],
        stated_rationale="Exercise a whole-record target.",
    )
    corrections: list[str] = []

    normalized = _normalize_transaction_targets(transaction, world, corrections)

    assert normalized.operations[0].target.field is None
    assert corrections == []


def test_field_scoped_create_on_existing_record_normalizes_to_replace() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    world = CanonicalWorld(compile_general_simulation(proposal).world_spec)
    transaction = WorldTransaction(
        transaction_id="add_record_state_field",
        base_revision=0,
        authority_id="general_semantic_adjudicator",
        intent_ids=["intent_1"],
        operations=[
            PatchOperation(
                operation="create",
                target=TypedTarget(
                    record_type="record",
                    record_id="relief_cargo",
                    field="decision",
                ),
                value="withheld pending review",
            )
        ],
        preconditions=[],
        consequences=[],
        evidence_refs=["relief_cargo"],
        stated_rationale="Add one field without recreating the record.",
    )
    corrections: list[str] = []

    normalized = _normalize_transaction_targets(transaction, world, corrections)

    assert normalized.operations[0].operation == "replace"
    assert normalized.operations[0].target.field == "state.decision"
    assert corrections == [
        "operation target relief_cargo field normalized from decision to state.decision",
        "field-scoped create normalized to replace for existing record relief_cargo",
    ]


def test_selected_exact_transport_receives_compiled_guards() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    spec = compile_general_simulation(proposal).world_spec
    guard = Precondition(
        target=TypedTarget(
            record_type="record",
            record_id="relief_cargo",
            field="state.status",
        ),
        expected="cleared",
    )
    spec.resource_transport_contracts = [
        ResourceTransportContract(
            contract_id="move_relief_cargo",
            operator_ids=["trucking_dispatcher"],
            source_resource_id="dispatch_fuel",
            destination_resource_id="dispatch_fuel",
            quantity=1,
            origin_place_id="outside_port",
            destination_place_id="port",
            allowed_route_ids=["temporary_route"],
            arrival_record_id="relief_cargo",
            arrival_quantity_key="quantity",
            usable_quantity_key="usable_quantity",
            arrival_minute_key="arrival_minute",
            required_preconditions=[guard],
        )
    ]
    world = CanonicalWorld(spec)
    intent = SemanticActionIntent(
        intent_id="move_intent",
        actor_id="trucking_dispatcher",
        base_revision=0,
        action="Move relief cargo.",
        target_refs=["relief_cargo"],
        purpose="Deliver aid.",
        expected_effect="Cargo reaches the port.",
        stated_rationale="Attempt the configured transport.",
        transition_contract_ids=["move_relief_cargo"],
    )
    transaction = WorldTransaction(
        transaction_id="transport_without_restated_guard",
        base_revision=0,
        authority_id="general_semantic_adjudicator",
        intent_ids=[intent.intent_id],
        operations=[],
        preconditions=[],
        consequences=[],
        evidence_refs=[intent.intent_id],
        stated_rationale="The adjudicator omitted the compiled guard.",
    )
    corrections: list[str] = []

    guarded = _inject_selected_contract_preconditions(
        transaction,
        intents=[intent],
        world=world,
        corrections=corrections,
    )

    assert guarded.preconditions == [guard]
    assert corrections == [
        "trusted exact contract preconditions injected: "
        "record:relief_cargo:state.status"
    ]


def test_whole_sensing_state_is_expanded_and_unauthorized_delivery_is_omitted() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    spec = compile_general_simulation(proposal).world_spec
    spec.initial_state.records["relief_cargo"].hidden_state["inspection"] = "ready"
    spec.initial_state.records["cargo_finding"] = WorldRecord(
        record_id="cargo_finding", kind="finding", label="Cargo finding"
    )
    spec.sensing_contracts = [
        SensingTransitionContract(
            contract_id="inspect_cargo",
            subject_type="record",
            subject_id="relief_cargo",
            observer_ids=["customs_officer"],
            hidden_to_output_fields={"inspection": "inspection"},
            output_record_id="cargo_finding",
            result_recipient_ids=["customs_officer"],
        )
    ]
    world = CanonicalWorld(spec)
    sensing_contract = world.spec.sensing_contracts[0]
    output_record = world.state.records[sensing_contract.output_record_id]
    values = {
        output_field: (
            world.state.records[sensing_contract.subject_id].hidden_state[hidden_key]
            if sensing_contract.subject_type == "record"
            else world.state.routes[sensing_contract.subject_id].hidden_state[hidden_key]
        )
        for hidden_key, output_field in sensing_contract.hidden_to_output_fields.items()
    }
    representation = next(
        item
        for item in world.state.representations.values()
        if len(item.recipient_ids) < 4
    )
    unauthorized_actor = next(
        actor_id
        for actor_id in world.state.records
        if world.state.records[actor_id].kind == "person"
        and actor_id not in representation.recipient_ids
    )
    transaction = WorldTransaction(
        transaction_id="normalize_sensing_state",
        base_revision=0,
        authority_id="general_semantic_adjudicator",
        intent_ids=["intent_1"],
        operations=[
            PatchOperation(
                operation="replace",
                target=TypedTarget(
                    record_type="record",
                    record_id=output_record.record_id,
                    field="state",
                ),
                value=values,
            )
        ],
        preconditions=[],
        consequences=[
            Consequence(
                consequence_id="bad_delivery",
                recipient_id=unauthorized_actor,
                content="Do not deliver this representation here.",
                apparent_source="fixture",
                representation_id=representation.representation_id,
            )
        ],
        evidence_refs=[output_record.record_id],
        stated_rationale="Exercise bounded envelope normalization.",
    )
    corrections: list[str] = []

    normalized = _normalize_transaction_targets(transaction, world, corrections)
    normalized = _drop_unauthorized_representation_deliveries(
        normalized, world, corrections
    )

    assert {item.target.field for item in normalized.operations} == {
        f"state.{field}" for field in values
    }
    assert normalized.consequences == []
    assert any("expanded into typed fields" in item for item in corrections)
    assert any("unauthorized representation delivery omitted" in item for item in corrections)


def test_actor_output_gets_one_bounded_validation_repair() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    injected_invalid_output = False

    def repairing_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal injected_invalid_output
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user.get("actor_context") or user["original_input"]["actor_context"]
            observations = [item["observation_id"] for item in context["observations"]]
            if not injected_invalid_output:
                injected_invalid_output = True
                observations.append("consequence:invented-observation")
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=observations,
                    memory_additions=[],
                    memory_revisions=[],
                    provenance_links=[],
                    interpretation="Retain only authorized evidence.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{context['actor_id']}_{context['base_revision']}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a reversible check.",
                    target_refs=[],
                    purpose="Preserve evidence.",
                    expected_effect="A bounded proposal.",
                    stated_rationale="The cause remains uncertain.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=[
                *user["requirements"]["intent_ids"],
                user["moment"]["moment_id"],
            ],
            stated_rationale="Retain the current world.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_actor_repair_fixture",
        call=repairing_call,
    )

    assert len(result.moments) == 2
    assert len(result.model_calls) == 7
    assert any(item.trace_id.endswith("/repair/1") for item in result.model_calls)
    projected = project_general_run(
        compiled,
        result,
        run_id="run_actor_repair_fixture",
        created_at="2026-08-13T00:00:00Z",
        execution="live",
    )
    assert len(projected["traces"]) == len(proposal.schedule) * len(proposal.people)
    assert all("/repair/1" in trace["trace_id"] or "/repair/" not in trace["trace_id"] for trace in projected["traces"])
    assert projected["theory_analysis"] is None

    proposal.analysis_spec = AnalysisSpecV1(
        analysis_id="coordination_lens",
        profile="waltzman_coordination_v1",
        purpose="Inspect influence-to-coordination signals in this retained run.",
    )
    analyzed = project_general_run(
        compile_general_simulation(proposal),
        result,
        run_id="run_actor_repair_fixture",
        created_at="2026-08-13T00:00:00Z",
        execution="live",
    )
    assert analyzed["theory_analysis"]["framework"] == (
        "Waltzman-informed diagnostic projection"
    )
    assert analyzed["authoring"]["analysis_spec"]["profile"] == (
        "waltzman_coordination_v1"
    )


def test_authored_person_memories_are_adopted_as_mutable_runtime_memory() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    seen_initial_memories: dict[str, list[str]] = {}

    def memory_revision_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user["actor_context"]
            actor_id = context["actor_id"]
            memories = context["private_memory"]
            seen_initial_memories.setdefault(actor_id, list(memories))
            prior = memories[0]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[],
                    memory_additions=[],
                    memory_revisions=[
                        {
                            "prior_memory": prior,
                            "revised_memory": f"Reassessed: {prior}",
                        }
                    ],
                    provenance_links=[],
                    interpretation="Reassess one retained memory.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{actor_id}_{context['base_revision']}",
                    actor_id=actor_id,
                    base_revision=context["base_revision"],
                    action="Propose a bounded review.",
                    target_refs=[],
                    purpose="Exercise retained cognition.",
                    expected_effect="One reviewable intent.",
                    stated_rationale="The configured memory is part of actor state.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the current world.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_person_memory_adoption_fixture",
        call=memory_revision_call,
        max_additional_moments=1,
    )

    assert seen_initial_memories == {
        person.entity_id: person.memories for person in proposal.people
    }
    assert not any("/repair/" in item.trace_id for item in result.model_calls)


def test_adjudicator_output_gets_one_authority_grammar_repair() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    injected_invalid_output = False

    def repairing_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal injected_invalid_output
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[],
                    memory_additions=[],
                    memory_revisions=[],
                    provenance_links=[],
                    interpretation="Retain only authorized evidence.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{context['actor_id']}_{context['base_revision']}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a reversible check.",
                    target_refs=[],
                    purpose="Preserve evidence.",
                    expected_effect="A bounded proposal.",
                    stated_rationale="The cause remains uncertain.",
                ),
            ), SimpleNamespace(provider="fixture")
        source = user.get("original_input", user)
        operations: list[PatchOperation] = []
        if not injected_invalid_output:
            injected_invalid_output = True
            operations = [
                PatchOperation(
                    operation="replace",
                    target=TypedTarget(
                        record_type="representation",
                        record_id="service_status_update",
                        field="content",
                    ),
                    value="An impermissible direct representation edit.",
                )
            ]
        return WorldTransaction(
            transaction_id=f"transaction_{source['moment']['moment_id']}",
            base_revision=source["requirements"]["base_revision"],
            authority_id=source["requirements"]["authority_id"],
            intent_ids=source["requirements"]["intent_ids"],
            operations=operations,
            preconditions=[],
            consequences=[],
            evidence_refs=source["requirements"]["intent_ids"],
            stated_rationale="Retain the current world after bounded validation.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_adjudicator_repair_fixture",
        call=repairing_call,
    )

    planned_calls = len(proposal.schedule) * (len(proposal.people) + 1)
    assert len(result.model_calls) == planned_calls + 1
    assert any(
        item.trace_id.endswith("/adjudicator/repair/1")
        for item in result.model_calls
    )
    assert result.transition_evidence[0].validation.accepted is False
    assert result.transition_evidence[1].validation.accepted is True


def test_general_group_runner_uses_frozen_revisions_and_stock_concordia() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    actor_counter = 0

    def fake_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal actor_counter
        response_model = kwargs["response_model"]
        user = json.loads(args[1][1]["content"])
        if response_model is ActorDecision:
            actor_counter += 1
            context = user["actor_context"]
            actor_id = context["actor_id"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    memory_additions=[f"memory {actor_counter}"],
                    memory_revisions=[],
                    provenance_links=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    interpretation="A bounded synthetic interpretation.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"intent_{actor_counter}",
                    actor_id=actor_id,
                    base_revision=context["base_revision"],
                    action="Propose a joint dispatch check.",
                    target_refs=["relief_cargo"],
                    purpose="Address the configured phase responsibilities.",
                    expected_effect="A reviewable joint proposal.",
                    stated_rationale="The available evidence warrants a bounded attempt.",
                ),
            ), SimpleNamespace(provider="fixture")
        assert response_model is WorldTransactionProposal
        return WorldTransactionProposal(
            transaction_id=f"transaction_{len(user['intents'])}_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[
                Precondition(
                    target=TypedTarget(
                        record_type="record",
                        record_id="temporary_route",
                        field="public_state",
                    ),
                    expected={"capacity": "limited"},
                )
            ],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the current world while recording joint review.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_general_fixture",
        call=fake_call,
    )

    assert len(result.moments) == 3
    assert len(result.model_calls) == 15
    assert [item.frozen_revision for item in result.moments] == [0, 1, 2]
    assert all(len(item.intent_ids) == 4 for item in result.moments)
    assert result.transition_evidence[0].transaction.preconditions[0].target.record_type == "route"
    assert result.transition_evidence[0].envelope_corrections == [
        "precondition target temporary_route normalized from record to route"
    ]
    assert result.adoption.engine_class.endswith("simultaneous.Simultaneous")
    assert result.adoption.actor_selection_component.endswith(
        "next_acting.NextActingAllEntities"
    )
    assert result.adoption.actor_names == [
        "port_coordinator",
        "customs_officer",
        "union_representative",
        "trucking_dispatcher",
    ]
    assert result.adoption.forbidden_runtime_imports == []
    actor_inputs = [
        json.loads(item.input_context)["actor_context"]
        for item in result.model_calls
        if item.role == "actor"
    ]
    first_moment = [item for item in actor_inputs if item["base_revision"] == 0]
    public_claim_recipients = {
        item["actor_id"]
        for item in first_moment
        if any(
            observation["representation_id"] == "public_fuel_claim"
            for observation in item["observations"]
        )
    }
    assert public_claim_recipients == set(result.adoption.actor_names)
    technical_recipients = {
        item["actor_id"]
        for item in first_moment
        if any(
            observation["representation_id"] == "technical_fuel_message"
            for observation in item["observations"]
        )
    }
    assert technical_recipients == {"port_coordinator", "customs_officer"}
    assert all(item.checkpoint_hash != "pending" for item in result.moments)
    analysis = project_waltzman_analysis(compiled, result)
    assert len(analysis["findings"]) == 5
    for finding in analysis["findings"]:
        assert finding["method"]
        assert finding["evidence_refs"]
        assert finding["uncertainty"]
        assert finding["limitation"]


def test_second_domain_uses_the_same_compiler_runner_and_receipt() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    actor_counter = 0

    def fake_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal actor_counter
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            actor_counter += 1
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    memory_additions=["Retain the observed incident evidence."],
                    memory_revisions=[],
                    provenance_links=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    interpretation="The cause remains uncertain.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"service_intent_{actor_counter}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a reversible recovery check.",
                    target_refs=["api_service", "forensic_log"],
                    purpose="Restore service without erasing evidence.",
                    expected_effect="A bounded recovery proposal.",
                    stated_rationale="Recovery and evidence preservation must be reconciled.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id=f"service_transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the world pending a reversible recovery action.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_service_fixture",
        call=fake_call,
    )

    assert len(result.moments) == 2
    assert len(result.model_calls) == 6
    assert result.adoption.engine_class.endswith("simultaneous.Simultaneous")
    assert result.adoption.game_master_names == ["general_world_game_master"]
    actor_inputs = [
        item.input_context for item in result.model_calls if item.role == "actor"
    ]
    adjudicator_inputs = [
        item.input_context for item in result.model_calls if item.role == "adjudicator"
    ]
    assert all("expired_replication_credential" not in item for item in actor_inputs)
    assert any("expired_replication_credential" in item for item in adjudicator_inputs)


def test_general_runner_uses_the_operator_selected_model_and_effort() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    observed_calls: list[tuple[str, str]] = []

    def selected_model_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        observed_calls.append((str(args[0]), str(kwargs["reasoning_effort"])))
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[],
                    memory_additions=[],
                    memory_revisions=[],
                    provenance_links=[],
                    interpretation="Retain the authorized context.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"selected_model_{context['actor_id']}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a bounded review.",
                    target_refs=[],
                    purpose="Exercise runtime model routing.",
                    expected_effect="One reviewable intent.",
                    stated_rationale="The context is bounded.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id="selected_model_transaction",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Retain the world.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation(
        compiled,
        run_id="run_selected_model_fixture",
        call=selected_model_call,
        max_additional_moments=1,
        model="openrouter/openai/gpt-5.6-terra",
        reasoning_effort="low",
    )

    assert len(result.moments) == 1
    assert observed_calls == [
        ("openrouter/openai/gpt-5.6-terra", "low")
    ] * (len(proposal.people) + 1)


def test_actor_activation_failures_are_not_silently_recast_as_missing_intents() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    failing_actor = proposal.people[0].entity_id

    def actor_failure_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user["actor_context"]
            if context["actor_id"] == failing_actor:
                raise RuntimeError("provider rejected this actor activation")
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[],
                    memory_additions=[],
                    memory_revisions=[],
                    provenance_links=[],
                    interpretation="Retain the authorized context.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"actor_failure_{context['actor_id']}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a bounded review.",
                    target_refs=[],
                    purpose="Exercise failure reporting.",
                    expected_effect="One reviewable intent.",
                    stated_rationale="The context is bounded.",
                ),
            ), SimpleNamespace(provider="fixture")
        raise AssertionError("joint adjudication must not run after an actor failure")

    with pytest.raises(
        RuntimeError,
        match=(
            "one or more same-moment actors failed before joint resolution: "
            f"{failing_actor}: RuntimeError: provider rejected this actor activation"
        ),
    ):
        run_general_simulation(
            compiled,
            run_id="run_actor_failure_fixture",
            call=actor_failure_call,
            max_additional_moments=1,
        )


def test_general_run_restores_checkpoint_into_fresh_simulation() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    call = _CheckpointRuntimeFake()

    prefix = run_general_simulation(
        compiled,
        run_id="run_general_checkpoint",
        call=call,
        max_additional_moments=1,
    )
    assert len(prefix.moments) == 1
    assert len(prefix.checkpoints) == 1

    resumed = run_general_simulation(
        compiled,
        run_id="run_general_checkpoint",
        call=call,
        checkpoint=prefix.checkpoints[-1],
    )

    assert len(resumed.moments) == 3
    assert [item.frozen_revision for item in resumed.moments] == [0, 1, 2]
    assert len(resumed.model_calls) == 15
    assert resumed.moments[0].checkpoint_hash != "pending"
    assert resumed.final_state.revision == 3


def test_general_run_rejects_lossy_checkpoint() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    prefix = run_general_simulation(
        compiled,
        run_id="run_service_checkpoint",
        call=_CheckpointRuntimeFake(),
        max_additional_moments=1,
    )
    corrupt = json.loads(json.dumps(prefix.checkpoints[-1]))
    del corrupt["entities"][proposal.people[0].entity_id]

    with pytest.raises(ValueError, match="invalid or incomplete"):
        run_general_simulation(
            compiled,
            run_id="run_service_checkpoint",
            call=_CheckpointRuntimeFake(),
            checkpoint=corrupt,
        )


def test_trusted_runtime_owns_transaction_envelope_identity() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        SERVICE_FIXTURE.read_text(encoding="utf-8")
    )
    compiled = compile_general_simulation(proposal)
    result = run_general_simulation(
        compiled,
        run_id="run_service_envelope",
        call=_CheckpointRuntimeFake(mutate_envelope=True),
        max_additional_moments=1,
    )

    evidence = result.transition_evidence[0]
    assert evidence.transaction.authority_id == "general_semantic_adjudicator"
    assert evidence.transaction.base_revision == 0
    assert set(evidence.transaction.intent_ids) == set(result.moments[0].intent_ids)
    assert evidence.envelope_corrections == [
        "authority_id restored from trusted runtime",
        "base_revision restored from trusted runtime",
        "intent_ids restored from collected Concordia actions",
    ]


class _CheckpointRuntimeFake:
    def __init__(self, *, mutate_envelope: bool = False) -> None:
        self.actor_counter = 0
        self.mutate_envelope = mutate_envelope

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[object, object]:
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            self.actor_counter += 1
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    memory_additions=[f"checkpoint memory {self.actor_counter}"],
                    memory_revisions=[],
                    provenance_links=[
                        item["observation_id"] for item in context["observations"]
                    ],
                    interpretation="Retain the bounded checkpoint evidence.",
                ),
                intent=SemanticActionIntent(
                    intent_id=f"checkpoint_intent_{self.actor_counter}",
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Propose a joint checkpoint-safe review.",
                    target_refs=[],
                    purpose="Continue from the exact retained prefix.",
                    expected_effect="A reviewable no-op transaction.",
                    stated_rationale="The same frozen revision remains authoritative.",
                ),
            ), SimpleNamespace(provider="fixture")
        return WorldTransaction(
            transaction_id=f"checkpoint_transaction_{user['moment']['moment_id']}",
            base_revision=(
                999 if self.mutate_envelope else user["requirements"]["base_revision"]
            ),
            authority_id=(
                "invented_authority"
                if self.mutate_envelope
                else user["requirements"]["authority_id"]
            ),
            intent_ids=(
                ["invented_intent"]
                if self.mutate_envelope
                else user["requirements"]["intent_ids"]
            ),
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="Commit the checkpoint-safe no-op transaction.",
        ), SimpleNamespace(provider="fixture")
