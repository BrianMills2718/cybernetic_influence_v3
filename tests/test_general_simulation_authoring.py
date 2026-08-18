from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest

from cybernetic_influence.authoring.store import AuthoringDraftStore, DraftConflictError
from cybernetic_influence.general_simulation.authoring import GeneralDraftAuthoringService
from cybernetic_influence.general_simulation.authoring_models import (
    ComponentRequestV1,
    GeneralAuthoringDiscussionV1,
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


def test_transient_provider_failure_retries_general_authoring(tmp_path: Path) -> None:
    store = AuthoringDraftStore(tmp_path)
    created = store.create(now="2026-08-13T12:00:00Z", target_kind="general_world_v1")
    calls = 0

    def flaky_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        nonlocal calls
        del args, kwargs
        calls += 1
        if calls == 1:
            raise RuntimeError("Provider response was not valid JSON")
        return GeneralProposalEnvelopeV1(proposal=proposal()), SimpleNamespace(
            provider="test", cost=0.0
        )

    service = GeneralDraftAuthoringService(store, call=flaky_call)
    drafted = service.advance(
        str(created["draft_id"]),
        expected_revision=0,
        message_id="retry_prompt",
        message="Model relief cargo coordination after a bridge failure.",
    )

    assert calls == 2
    assert drafted["status"] == "ready_for_review"
    assert [cast(dict[str, object], attempt)["status"] for attempt in cast(list[object], drafted["attempts"])] == [
        "provider_error",
        "accepted",
    ]


def test_discussion_retains_chat_without_configuring(tmp_path: Path) -> None:
    store = AuthoringDraftStore(tmp_path)
    created = store.create(now="2026-08-13T12:00:00Z", target_kind="general_world_v1")

    def discuss_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        del args, kwargs
        return GeneralAuthoringDiscussionV1(
            reply="Should transport disruption be endogenous or scheduled?",
            understood_summary="A pencil production and delivery chain.",
            material_questions=["Should disruption occur during every run?"],
        ), SimpleNamespace(provider="test", cost=0.0)

    service = GeneralDraftAuthoringService(store, call=discuss_call)
    discussed = service.discuss(
        str(created["draft_id"]),
        expected_revision=0,
        message_id="first_chat",
        message="Simulate a pencil supply chain.",
    )

    assert discussed["status"] == "draft"
    assert discussed["proposal"] is None
    assert discussed["messages"][0]["assistant_summary"].startswith("Should transport")  # type: ignore[index]
    assert discussed["diagnostics"] == [
        {
            "severity": "question",
            "code": "discussion",
            "message": "Should disruption occur during every run?",
        }
    ]

    reloaded = store.get(str(created["draft_id"]))
    assert reloaded["revision"] == 1
    assert reloaded["proposal"] is None
    assert reloaded["messages"] == discussed["messages"]


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
    unsupported.schedule[-1] = unsupported.schedule[-1].model_copy(
        update={
            "active_component_request_ids": [
                *unsupported.schedule[-1].active_component_request_ids,
                "unsupported_oracle",
            ]
        }
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
    raw_schema = GeneralSimulationProposalV1.model_json_schema()
    schema = json.dumps(raw_schema)

    assert "implementation_ref" not in schema
    assert "template_id" not in schema
    assert "python" not in schema.lower()
    assert "sensing_rules" in raw_schema["required"]
    assert "resource_transformations" in raw_schema["required"]
    assert "resource_transports" in raw_schema["required"]


def test_pre_transition_contract_proposal_migrates_to_empty_contract_lists() -> None:
    raw = json.loads((FIXTURES / "port_coordination.json").read_text(encoding="utf-8"))
    raw.pop("sensing_rules", None)
    raw.pop("resource_transformations", None)
    raw.pop("resource_transports", None)

    parsed = GeneralSimulationProposalV1.model_validate(raw)

    assert parsed.sensing_rules == []
    assert parsed.resource_transformations == []
    assert parsed.resource_transports == []


def test_general_proposal_schema_has_no_open_object_maps() -> None:
    schema = GeneralProposalEnvelopeV1.model_json_schema()

    def open_objects(value: object, path: str = "$") -> list[str]:
        if isinstance(value, list):
            return [
                item
                for index, child in enumerate(value)
                for item in open_objects(child, f"{path}/{index}")
            ]
        if not isinstance(value, dict):
            return []
        found = []
        if value.get("type") == "object" and value.get("additionalProperties") is not False:
            found.append(path)
        return found + [
            item
            for key, child in value.items()
            for item in open_objects(child, f"{path}/{key}")
        ]

    assert open_objects(schema) == []


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
    assert "Make the configured world causally contestable" in prompt
    assert "one plausible but non-guaranteed path to the objective" in prompt
    assert "denying every actor and active system any means" in prompt
    assert "sensing, permission, and action success must remain separate" in prompt
    assert "Each request must name one transition responsibility" in prompt
    assert "Do not combine a person's interpretation" in prompt
    assert "perform one final reference and execution-coverage check" in prompt
    assert "Every transition_contract_id used by a component request" in prompt
    assert "Every sensing rule subject_ref and output_record_id" in prompt
    assert "A spatial placement may place only a declared world record" in prompt
    assert "Do not list a transport destination, output record, or public mirror" in prompt
    assert "Omit decorative or orphan places" in prompt
