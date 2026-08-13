from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from cybernetic_influence.general_simulation.authoring_models import (
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.compiler import compile_general_simulation
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    PatchOperation,
    SemanticActionIntent,
    TypedTarget,
    WorldTransaction,
)
from cybernetic_influence.general_simulation.runner import (
    _memory_reference_is_grounded,
    _normalized_memory,
    run_general_simulation,
)
from cybernetic_influence.general_simulation.analysis_projection import (
    project_waltzman_analysis,
)


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
            evidence_refs=user["requirements"]["intent_ids"],
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
                    purpose="Answer the configured research question.",
                    expected_effect="A reviewable joint proposal.",
                    stated_rationale="The available evidence warrants a bounded attempt.",
                ),
            ), SimpleNamespace(provider="fixture")
        assert response_model is WorldTransaction
        return WorldTransaction(
            transaction_id=f"transaction_{len(user['intents'])}_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
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
