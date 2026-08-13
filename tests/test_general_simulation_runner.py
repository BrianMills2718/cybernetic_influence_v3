from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cybernetic_influence.general_simulation.authoring_models import (
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.compiler import compile_general_simulation
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    SemanticActionIntent,
    WorldTransaction,
)
from cybernetic_influence.general_simulation.runner import run_general_simulation


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


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
