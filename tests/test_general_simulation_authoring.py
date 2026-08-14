from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest

from cybernetic_influence.authoring.store import AuthoringDraftStore, DraftConflictError
from cybernetic_influence.general_simulation.authoring import GeneralDraftAuthoringService
from cybernetic_influence.general_simulation.authoring_models import (
    ComponentRequestV1,
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)


FIXTURES = Path("tests/fixtures/general_simulation")


def proposal(name: str = "port_coordination.json") -> GeneralSimulationProposalV1:
    return GeneralSimulationProposalV1.model_validate_json(
        (FIXTURES / name).read_text(encoding="utf-8")
    )


def provider_for(
    value: GeneralSimulationProposalV1,
) -> Callable[..., tuple[object, object]]:
    def call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        del args, kwargs
        return GeneralProposalEnvelopeV1(proposal=value), SimpleNamespace(
            provider="test", cost=0.0
        )

    return call


def test_conversation_retains_general_proposal_coverage_and_trace(tmp_path: Path) -> None:
    store = AuthoringDraftStore(tmp_path)
    created = store.create(now="2026-08-13T12:00:00Z", target_kind="general_world_v1")
    service = GeneralDraftAuthoringService(store, call=provider_for(proposal()))

    drafted = service.advance(
        str(created["draft_id"]),
        expected_revision=0,
        message_id="port_prompt",
        message="Model relief cargo coordination after a bridge failure.",
    )

    assert drafted["target_kind"] == "general_world_v1"
    assert drafted["status"] == "ready_for_review"
    assert drafted["proposal"]["proposal_kind"] == "general_world_v1"  # type: ignore[index]
    assert drafted["coverage"]["blocking_request_ids"] == []  # type: ignore[index]
    assert drafted["messages"][0]["trace_ids"] == [  # type: ignore[index]
        f"{created['draft_id']}/general/revision/1/attempt/1"
    ]


def test_unknown_material_behavior_is_retained_but_cannot_be_approved(
    tmp_path: Path,
) -> None:
    unsupported = proposal("service_incident.json")
    unsupported.component_requests.append(
        ComponentRequestV1(
            request_id="unsupported_oracle",
            subject_refs=["api_service"],
            behavior_description="Foretell an exact unknowable future.",
            required_reads=["api_service"],
            desired_effects=["Predict a future market price."],
            fidelity_need="exact",
            material_to_question=True,
        )
    )
    store = AuthoringDraftStore(tmp_path)
    created = store.create(now="2026-08-13T12:00:00Z", target_kind="general_world_v1")
    service = GeneralDraftAuthoringService(store, call=provider_for(unsupported))

    drafted = service.advance(
        str(created["draft_id"]),
        expected_revision=0,
        message_id="unsupported_prompt",
        message="Include exact future prediction.",
    )

    assert drafted["status"] == "needs_input"
    assert drafted["proposal"] is not None
    assert drafted["coverage"]["blocking_request_ids"] == ["unsupported_oracle"]  # type: ignore[index]
    with pytest.raises(ValueError, match="blocking"):
        service.approve(str(created["draft_id"]), expected_revision=1)


def test_direct_general_edit_is_revisioned_idempotent_and_approvable(
    tmp_path: Path,
) -> None:
    store = AuthoringDraftStore(tmp_path)
    created = store.create(now="2026-08-13T12:00:00Z", target_kind="general_world_v1")
    service = GeneralDraftAuthoringService(store, call=provider_for(proposal()))
    drafted = service.advance(
        str(created["draft_id"]),
        expected_revision=0,
        message_id="first",
        message="Draft the port simulation.",
    )
    edited_proposal = GeneralSimulationProposalV1.model_validate(drafted["proposal"])
    edited_proposal.question = "Can the four parties execute a safe dispatch before sunset?"

    edited = service.edit_proposal(
        str(created["draft_id"]),
        expected_revision=1,
        edit_id="question_edit",
        proposal=edited_proposal,
    )
    repeated = service.edit_proposal(
        str(created["draft_id"]),
        expected_revision=1,
        edit_id="question_edit",
        proposal=edited_proposal,
    )

    assert edited["revision"] == 2
    assert repeated == edited
    assert edited["messages"][-1]["trace_ids"] == []  # type: ignore[index]
    with pytest.raises(DraftConflictError, match="revision"):
        service.edit_proposal(
            str(created["draft_id"]),
            expected_revision=1,
            edit_id="stale_edit",
            proposal=edited_proposal,
        )
    approved = service.approve(str(created["draft_id"]), expected_revision=2)
    assert approved["status"] == "approved"
    assert approved["approval"]["proposal_kind"] == "general_world_v1"  # type: ignore[index]


def test_general_proposal_schema_contains_no_executable_reference_field() -> None:
    schema = json.dumps(GeneralSimulationProposalV1.model_json_schema())

    assert "implementation_ref" not in schema
    assert "template_id" not in schema
    assert "python" not in schema.lower()


def test_general_authoring_prompt_defaults_to_a_short_editable_run() -> None:
    prompt = Path(
        "src/cybernetic_influence/general_simulation/prompts/general_world_draft.yaml"
    ).read_text(encoding="utf-8")

    assert "use exactly three scheduled moments" in prompt
    assert "Use a fourth moment when sensing or verification" in prompt
    assert "preserve an explicitly requested schedule length" in prompt
    assert "Initial state is already present before the schedule begins" in prompt
    assert "never spend a scheduled moment merely restating" in prompt
    assert "include a moment in which someone can attempt to sense" in prompt
    assert "do not pre-author success" in prompt
    assert "every moment advances the causal path" in prompt
    assert "Each request must name one transition responsibility" in prompt
    assert "Do not combine a person's interpretation" in prompt
