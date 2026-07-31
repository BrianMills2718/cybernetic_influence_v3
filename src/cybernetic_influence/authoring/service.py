"""Structured conversation, validation, approval, and execution for Slice 17B."""

from __future__ import annotations

import json
from collections.abc import Callable
from hashlib import sha256
from importlib import resources
from typing import Annotated, Any, Literal, TypedDict, cast

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field

from cybernetic_influence.authoring.compiler import (
    AuthoringCompilationError,
    CompiledScenario,
    compile_scenario,
)
from cybernetic_influence.authoring.component_composition import (
    apply_component_configuration,
)
from cybernetic_influence.authoring.coordination_review import (
    coordination_proposal_from_review,
    coordination_review_from_proposal,
)
from cybernetic_influence.authoring.examples import (
    reviewed_component_composition_proposal,
    reviewed_coordination_proposal,
)
from cybernetic_influence.authoring.models import (
    ComponentCompositionConfigurationReview,
    ComponentCompositionWorkflowDraft,
    CoordinationScenarioReview,
    PersonDraft,
    ProfileStatement,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.store import AuthoringDraftStore, DraftConflictError
from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_TERRA_MODEL,
    structured_backend_options,
)
from cybernetic_influence.run_store import now_iso

StructuredCall = Callable[..., tuple[Any, Any]]
AUTHORING_TASK = "cybernetic_influence_v3_scenario_draft"
AUTHORING_MAX_BUDGET = 0.10
AuthoringModel = Literal[
    "codex/gpt-5.6-terra",
    "codex/gpt-5.6-luna",
    "openrouter/openai/gpt-5.6-terra",
    "openrouter/openai/gpt-5.6-sol",
]
AuthoringReasoningEffort = Literal["none", "low", "medium", "high", "xhigh", "max"]
AUTHORING_MODEL: AuthoringModel = OPENROUTER_TERRA_MODEL
AUTHORING_REASONING_EFFORT: AuthoringReasoningEffort = "medium"
AUTHORING_MAX_ATTEMPTS = 3
AUTHORING_MAX_TOKENS = 8000
AUTHORING_PROMPT_VERSION = "scenario_draft.v4"


class AuthoringModelOption(TypedDict):
    model: AuthoringModel
    label: str
    provider: str
    billing_mode: Literal["subscription_included", "usage_based"]
    reasoning_efforts: tuple[AuthoringReasoningEffort, ...]
    default_reasoning_effort: AuthoringReasoningEffort


AUTHORING_MODEL_OPTIONS: tuple[AuthoringModelOption, ...] = (
    {
        "model": CODEX_TERRA_MODEL,
        "label": "Terra · subscription",
        "provider": "ChatGPT Codex subscription",
        "billing_mode": "subscription_included",
        "reasoning_efforts": ("medium",),
        "default_reasoning_effort": "medium",
    },
    {
        "model": CODEX_LUNA_MODEL,
        "label": "Luna · subscription",
        "provider": "ChatGPT Codex subscription",
        "billing_mode": "subscription_included",
        "reasoning_efforts": ("low", "medium", "high"),
        "default_reasoning_effort": "medium",
    },
    {
        "model": OPENROUTER_TERRA_MODEL,
        "label": "Terra · OpenRouter",
        "provider": "OpenRouter",
        "billing_mode": "usage_based",
        "reasoning_efforts": ("none", "low", "medium", "high", "xhigh", "max"),
        "default_reasoning_effort": "medium",
    },
    {
        "model": "openrouter/openai/gpt-5.6-sol",
        "label": "Sol",
        "provider": "OpenRouter",
        "billing_mode": "usage_based",
        "reasoning_efforts": ("none", "low", "medium", "high", "xhigh", "max"),
        "default_reasoning_effort": "medium",
    },
)
AUTHORING_REASONING_EFFORTS: tuple[AuthoringReasoningEffort, ...] = (
    "none", "low", "medium", "high", "xhigh", "max",
)


class _BehavioralProfileConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    values: list[ProfileStatement] = Field(
        description="Principles or outcomes the person regards as important."
    )
    goals: list[ProfileStatement] = Field(
        description="Outcomes the person currently wants to bring about."
    )
    beliefs: list[ProfileStatement] = Field(
        description="Claims the person currently takes to be true and may be wrong about."
    )
    decision_tendencies: list[ProfileStatement] = Field(
        description="Scenario-relevant habits, biases, or ways the person tends to decide."
    )
    social_perceptions: list[ProfileStatement] = Field(
        description="What the person thinks others do, value, or expect."
    )
    current_state: list[ProfileStatement] = Field(
        description="Current affect, attention, confidence, fatigue, or intent."
    )
    capabilities: list[ProfileStatement] = Field(
        description="Relevant real-world skills or knowledge attributed to the person."
    )
    limitations: list[ProfileStatement] = Field(
        description="Relevant real-world skill, knowledge, physical, or practical limits."
    )


class _PersonConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entity_id: str
    label: str
    position: str
    disposition: str
    memories: list[str]
    behavioral_profile: _BehavioralProfileConsumer


class _ObjectConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entity_id: str
    entity_kind: str
    label: str
    description: str


class _InformationConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    information_id: str
    label: str
    content: str


class _PlaceConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    place_id: str
    label: str
    description: str


class _SpatialLinkConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    spatial_link_id: str
    endpoint_a_place_id: str
    endpoint_b_place_id: str
    description: str


class _TimingConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    minutes: int
    basis: str


class _PlacementConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entity_id: str
    place_id: str


class _WorkflowConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    template_id: Literal["resource_request_v1"]
    requester_id: str
    reviewer_id: str
    request_id: str
    resource_id: str
    policy_information_id: str
    eligible_requester_ids: list[str]
    resource_available: bool
    request_delivery_minutes: int
    decision_delivery_minutes: int
    result_delivery_minutes: int


class _InformationCampaignWorkflowConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    template_id: Literal["information_campaign_v1"]
    source_id: str
    recipient_id: str
    campaign_id: str
    claim_information_id: str
    channel_object_id: str
    publication_enabled: bool
    publication_delivery_minutes: int
    assessment_recording_minutes: int


class _ComponentSelectionConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    component_id: str
    component_kind: str
    version: int


class _ComponentCompositionWorkflowConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    template_id: Literal["component_composition_v1"]
    components: list[_ComponentSelectionConsumer]
    source_id: str
    recipient_id: str
    record_id: str
    information_id: str
    channel_object_id: str
    delivery_enabled: bool
    delivery_minutes: int
    recording_minutes: int


class _BoundaryConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    boundary_id: str
    label: str
    description: str
    member_refs: list[str]


class _LegacyProposalConsumer(BaseModel):
    """Permissive read boundary for the two earlier provider schemas."""

    model_config = ConfigDict(extra="ignore")

    proposal_version: Literal[1]
    scenario_id: str
    title: str
    description: str
    people: list[_PersonConsumer]
    objects: list[_ObjectConsumer]
    information: list[_InformationConsumer]
    places: list[_PlaceConsumer]
    spatial_links: list[_SpatialLinkConsumer]
    placements: list[_PlacementConsumer]
    timing_assumptions: list[_TimingConsumer]
    workflow: Annotated[
        _WorkflowConsumer
        | _InformationCampaignWorkflowConsumer
        | _ComponentCompositionWorkflowConsumer,
        Field(discriminator="template_id"),
    ]
    analytical_boundaries: list[_BoundaryConsumer]
    fidelity_questions: list[str]
    unresolved_questions: list[str]


class _ProposalConsumer(BaseModel):
    """Strict LLM output envelope with one ID-free coordination branch."""

    model_config = ConfigDict(extra="forbid")

    proposal: _LegacyProposalConsumer | CoordinationScenarioReview = Field(
        description=(
            "One complete reviewed-template proposal. Coordination proposals use "
            "semantic fields and never supply compiler-owned runtime identities."
        )
    )


def _structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as error:
        raise RuntimeError("scenario authoring requires the shared llm_client") from error
    return cast(StructuredCall, call_llm_structured)


def _prompt_source() -> str:
    return resources.files("cybernetic_influence.authoring").joinpath(
        "prompts/scenario_draft.yaml"
    ).read_text(encoding="utf-8")


def _prompt(
    *, message: str, prior: dict[str, object], repair_feedback: str | None,
    candidate: object | None,
) -> tuple[str, str]:
    raw = _prompt_source()
    template = yaml.safe_load(raw)
    if not isinstance(template, dict):
        raise ValueError("authoring prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(value, sort_keys=True)
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(
            message=message, prior=prior, repair_feedback=repair_feedback,
            candidate=candidate,
        ),
    )


def authoring_contract() -> dict[str, object]:
    """Expose the exact structured-call contract without invoking a provider."""

    schema = _ProposalConsumer.model_json_schema()
    schema_digest = sha256(
        json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "task": AUTHORING_TASK,
        "prompt_version": AUTHORING_PROMPT_VERSION,
        "prompt_digest": sha256(_prompt_source().encode("utf-8")).hexdigest(),
        "schema_name": _ProposalConsumer.__name__,
        "schema_digest": schema_digest,
        "maximum_attempts_per_message": AUTHORING_MAX_ATTEMPTS,
        "maximum_output_tokens_per_attempt": AUTHORING_MAX_TOKENS,
        "maximum_cost_per_attempt": AUTHORING_MAX_BUDGET,
        "maximum_usage_based_cost_per_message": round(
            AUTHORING_MAX_ATTEMPTS * AUTHORING_MAX_BUDGET,
            2,
        ),
        "model_options": list(AUTHORING_MODEL_OPTIONS),
        "repair_behavior": (
            "A rejected typed candidate may be repaired within the same bounded "
            "message sequence; the prior accepted revision remains retained."
        ),
    }


class DraftAuthoringService:
    def __init__(self, store: AuthoringDraftStore, *, call: StructuredCall | None = None) -> None:
        self.store = store
        self.call = call or _structured_call()

    def create_reviewed_coordination_draft(self) -> dict[str, object]:
        """Create one saved review draft without making a provider call."""

        proposal = reviewed_coordination_proposal()
        compile_scenario(proposal)
        current = self.store.create(now=now_iso())
        return self.store.replace(
            str(current["draft_id"]),
            expected_revision=0,
            document={
                **current,
                "revision": 1,
                "status": "ready_for_review",
                "authoring_summary": (
                    "Ready to review: Multinational bio-surveillance deployment "
                    "review. This example is already typed and made no model call."
                ),
                "proposal": proposal.model_dump(mode="json"),
                "diagnostics": [],
                "approval": None,
                "updated_at": now_iso(),
            },
        )

    def create_reviewed_component_composition_draft(self) -> dict[str, object]:
        """Create the first mixed reviewed-component example without a model call."""

        proposal = reviewed_component_composition_proposal()
        compile_scenario(proposal)
        current = self.store.create(now=now_iso())
        return self.store.replace(
            str(current["draft_id"]),
            expected_revision=0,
            document={
                **current,
                "revision": 1,
                "status": "ready_for_review",
                "authoring_summary": (
                    "Ready to review: a field report moves through selected "
                    "delivery, recording, route, and person components. This "
                    "example is already typed and made no model call."
                ),
                "proposal": proposal.model_dump(mode="json"),
                "diagnostics": [],
                "approval": None,
                "updated_at": now_iso(),
            },
        )

    def advance(
        self, draft_id: str, *, expected_revision: int, message_id: str, message: str,
        model: AuthoringModel = AUTHORING_MODEL,
        reasoning_effort: AuthoringReasoningEffort = AUTHORING_REASONING_EFFORT,
    ) -> dict[str, object]:
        selected_model = next(
            (item for item in AUTHORING_MODEL_OPTIONS if item["model"] == model),
            None,
        )
        if selected_model is None:
            raise ValueError("unsupported authoring model")
        supported_efforts = selected_model["reasoning_efforts"]
        if reasoning_effort not in supported_efforts:
            raise ValueError(
                f"{model} does not support authoring reasoning effort "
                f"{reasoning_effort!r}; choose one of {', '.join(supported_efforts)}"
            )
        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        existing = next((item for item in messages if item.get("message_id") == message_id), None)
        if existing is not None:
            if (
                existing.get("content") != message
                or existing.get("model") not in (None, model)
                or existing.get("reasoning_effort") not in (None, reasoning_effort)
            ):
                raise DraftConflictError(
                    "message ID was already used with different content or model settings"
                )
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        proposal: ScenarioDraftProposal | None = None
        diagnostics: list[dict[str, str]] = []
        attempts: list[dict[str, object]] = []
        repair_feedback: str | None = None
        candidate: object | None = None
        for attempt_number in range(1, AUTHORING_MAX_ATTEMPTS + 1):
            meta: object | None = None
            trace_id = f"{draft_id}/revision/{expected_revision + 1}/attempt/{attempt_number}"
            system, user = _prompt(
                message=message,
                prior=_provider_prior(current),
                repair_feedback=repair_feedback,
                candidate=candidate,
            )
            try:
                with structured_backend_options(model) as backend_options:
                    parsed, meta = self.call(
                        model,
                        [{"role": "system", "content": system}, {"role": "user", "content": user}],
                        response_model=_ProposalConsumer,
                        task=AUTHORING_TASK,
                        trace_id=trace_id,
                        max_budget=AUTHORING_MAX_BUDGET,
                        max_tokens=AUTHORING_MAX_TOKENS,
                        model_justification=(
                            "Select and populate one reviewed executable scenario template "
                            "from a bounded natural-language situation."
                        ),
                        reasoning_effort=reasoning_effort,
                        **backend_options,
                    )
                if isinstance(parsed, ScenarioDraftProposal):
                    proposal = parsed
                    candidate = _provider_candidate_from_proposal(parsed)
                else:
                    raw_parsed = (
                        parsed.model_dump(mode="json")
                        if isinstance(parsed, BaseModel)
                        else parsed
                    )
                    try:
                        consumer = _ProposalConsumer.model_validate(raw_parsed)
                    except ValueError:
                        # Fake calls and pre-v3 retained candidates may still
                        # return the proposal without the new envelope. The
                        # actual provider schema always requires the envelope.
                        consumer = _ProposalConsumer.model_validate(
                            {"proposal": raw_parsed}
                        )
                    candidate = consumer.proposal.model_dump(mode="json")
                    proposal = _proposal_from_consumer(consumer)
                diagnostics = _diagnostics(proposal)
                if not diagnostics:
                    attempts.append(_attempt(trace_id, attempt_number, "accepted", "The typed draft compiled successfully.", meta))
                    break
                if all(item["severity"] == "question" for item in diagnostics):
                    repair_feedback = _diagnostic_feedback(diagnostics)
                    attempts.append(
                        _attempt(trace_id, attempt_number, "needs_input", repair_feedback, meta)
                    )
                    break
                repair_feedback = _diagnostic_feedback(diagnostics)
                attempts.append(_attempt(trace_id, attempt_number, "repair", repair_feedback, meta))
                proposal = None
            except ValueError as error:
                repair_feedback = _concise_validation_error(error)
                diagnostics = [{"severity": "error", "code": "validation", "message": repair_feedback}]
                attempts.append(_attempt(trace_id, attempt_number, "repair", repair_feedback, meta))
                proposal = None
            except Exception as error:
                terminal_provider_error = _is_terminal_provider_error(error)
                repair_feedback = _concise_provider_error(error)
                diagnostics = [{"severity": "error", "code": "drafting", "message": repair_feedback}]
                attempts.append(_attempt(trace_id, attempt_number, "provider_error", repair_feedback, meta))
                if terminal_provider_error:
                    break
        successful = proposal is not None and not diagnostics
        if successful:
            assert proposal is not None
            status = "ready_for_review"
            summary = (
                f"Ready to review: {proposal.title}. "
                f"{proposal.description}"
            )
            approval: dict[str, object] | None = None
        elif (
            attempts
            and all(item["status"] == "provider_error" for item in attempts)
            and isinstance(current.get("proposal"), dict)
        ):
            proposal = ScenarioDraftProposal.model_validate(current["proposal"])
            retained_diagnostics = current.get("diagnostics")
            diagnostics = (
                [
                    {"severity": str(item["severity"]), "code": str(item["code"]), "message": str(item["message"])}
                    for item in retained_diagnostics
                    if isinstance(item, dict)
                    and {"severity", "code", "message"} <= set(item)
                ]
                if isinstance(retained_diagnostics, list)
                else []
            )
            status = str(current["status"])
            summary = (
                f"The authoring provider failed {len(attempts)} time(s), so the prior "
                "reviewable draft was preserved and this requested change was not applied."
            )
            raw_approval = current.get("approval")
            approval = raw_approval if isinstance(raw_approval, dict) else None
        else:
            status = "needs_input"
            summary = (
                f"I drafted {proposal.title}, but I need your answer before approval."
                if proposal is not None and diagnostics
                else (
                    f"The authoring assistant tried {len(attempts)} time(s) without producing "
                    "a valid bounded scenario. Review the concise issue below, then clarify the "
                    "people, information or resource, configured pathway, and desired trace boundary."
                )
            )
            approval = None
        assistant_details = [
            str(item["message"])
            for item in diagnostics
            if isinstance(item.get("message"), str)
        ]
        if (
            attempts
            and all(item["status"] == "provider_error" for item in attempts)
            and isinstance(attempts[-1].get("message"), str)
            and attempts[-1]["message"] not in assistant_details
        ):
            assistant_details.append(str(attempts[-1]["message"]))
        assistant_summary = " ".join([summary, *assistant_details])
        updated = {
            **current,
            "revision": expected_revision + 1,
            "status": status,
            "messages": [
                *messages,
                {
                    "message_id": message_id,
                    "content": message,
                    "model": model,
                    "reasoning_effort": reasoning_effort,
                    "assistant_summary": assistant_summary,
                    "result_status": status,
                    "trace_ids": [
                        str(item["trace_id"])
                        for item in attempts
                        if isinstance(item.get("trace_id"), str)
                    ],
                },
            ],
            "attempts": attempts,
            "authoring_summary": summary,
            "proposal": proposal.model_dump(mode="json") if proposal else None,
            "diagnostics": diagnostics,
            "approval": approval,
            "updated_at": now_iso(),
        }
        return self.store.replace(draft_id, expected_revision=expected_revision, document=updated)

    def edit_person(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        edit_id: str,
        person_id: str,
        person: PersonDraft,
    ) -> dict[str, object]:
        """Persist one direct, typed person edit without making a model call."""
        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        edit_digest = sha256(
            person.model_dump_json(exclude_none=False).encode("utf-8")
        ).hexdigest()
        existing = next(
            (item for item in messages if item.get("message_id") == edit_id),
            None,
        )
        if existing is not None:
            if (
                existing.get("source") != "direct_person_edit"
                or existing.get("edit_digest") != edit_digest
            ):
                raise DraftConflictError(
                    "edit ID was already used with different person content"
                )
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        if person.entity_id != person_id:
            raise ValueError("edited person ID must match the requested person")
        raw_proposal = current.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AuthoringCompilationError("draft has no valid proposal")
        proposal = ScenarioDraftProposal.model_validate(raw_proposal)
        person_index = next(
            (
                index
                for index, existing_person in enumerate(proposal.people)
                if existing_person.entity_id == person_id
            ),
            None,
        )
        if person_index is None:
            raise ValueError("draft does not contain the requested person")
        proposal.people[person_index] = person
        diagnostics = _diagnostics(proposal)
        if any(item["severity"] == "error" for item in diagnostics):
            raise AuthoringCompilationError(
                "edited person would make the scenario unpreviewable"
            )
        status = "needs_input" if diagnostics else "ready_for_review"
        summary = (
            f"Saved direct edits to {person.label}. "
            "No authoring model call was made."
        )
        updated = {
            **current,
            "revision": expected_revision + 1,
            "status": status,
            "messages": [
                *messages,
                {
                    "message_id": edit_id,
                    "content": f"Edited {person.label}'s person model directly.",
                    "source": "direct_person_edit",
                    "edit_digest": edit_digest,
                    "assistant_summary": summary,
                    "result_status": status,
                    "trace_ids": [],
                },
            ],
            "authoring_summary": summary,
            "proposal": proposal.model_dump(mode="json"),
            "diagnostics": diagnostics,
            "approval": None,
            "updated_at": now_iso(),
        }
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document=updated,
        )

    def edit_coordination_configuration(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        edit_id: str,
        configuration: CoordinationScenarioReview,
    ) -> dict[str, object]:
        """Persist semantic coordination edits without a model call."""

        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        edit_digest = sha256(
            configuration.model_dump_json(exclude_none=False).encode("utf-8")
        ).hexdigest()
        existing = next(
            (item for item in messages if item.get("message_id") == edit_id),
            None,
        )
        if existing is not None:
            if (
                existing.get("source") != "direct_coordination_edit"
                or existing.get("edit_digest") != edit_digest
            ):
                raise DraftConflictError(
                    "edit ID was already used with different coordination content"
                )
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        raw_proposal = current.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AuthoringCompilationError("draft has no valid proposal")
        previous = ScenarioDraftProposal.model_validate(raw_proposal)
        if previous.workflow.template_id != "coordination_decision_v1":
            raise ValueError(
                "direct coordination editing requires a coordination decision draft"
            )
        proposal = coordination_proposal_from_review(configuration)
        diagnostics = _diagnostics(proposal)
        if any(item["severity"] == "error" for item in diagnostics):
            raise AuthoringCompilationError(_diagnostic_feedback(diagnostics))
        status = "needs_input" if diagnostics else "ready_for_review"
        summary = (
            f"Saved direct edits to {proposal.title}. "
            "No authoring model call was made."
        )
        updated = {
            **current,
            "revision": expected_revision + 1,
            "status": status,
            "messages": [
                *messages,
                {
                    "message_id": edit_id,
                    "content": "Edited the coordination scenario directly.",
                    "source": "direct_coordination_edit",
                    "edit_digest": edit_digest,
                    "assistant_summary": summary,
                    "result_status": status,
                    "trace_ids": [],
                },
            ],
            "authoring_summary": summary,
            "proposal": proposal.model_dump(mode="json"),
            "diagnostics": diagnostics,
            "approval": None,
            "updated_at": now_iso(),
        }
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document=updated,
        )

    def edit_component_composition_configuration(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        edit_id: str,
        configuration: ComponentCompositionConfigurationReview,
    ) -> dict[str, object]:
        """Persist component bindings and timing without exposing implementations."""

        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        edit_digest = sha256(
            configuration.model_dump_json(exclude_none=False).encode("utf-8")
        ).hexdigest()
        existing = next(
            (item for item in messages if item.get("message_id") == edit_id),
            None,
        )
        if existing is not None:
            if (
                existing.get("source") != "direct_component_composition_edit"
                or existing.get("edit_digest") != edit_digest
            ):
                raise DraftConflictError("edit ID was already used with different content")
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        raw_proposal = current.get("proposal")
        if not isinstance(raw_proposal, dict):
            raise AuthoringCompilationError("draft has no valid proposal")
        previous = ScenarioDraftProposal.model_validate(raw_proposal)
        proposal = apply_component_configuration(previous, configuration)
        diagnostics = _diagnostics(proposal)
        if any(item["severity"] == "error" for item in diagnostics):
            raise AuthoringCompilationError(
                "edited component configuration would make the scenario unpreviewable"
            )
        status = "needs_input" if diagnostics else "ready_for_review"
        summary = (
            "Saved component bindings and timing. The compiler rebuilt the reviewed "
            "routes and exact mechanisms; no authoring model call was made."
        )
        updated = {
            **current,
            "revision": expected_revision + 1,
            "status": status,
            "messages": [
                *messages,
                {
                    "message_id": edit_id,
                    "content": "Edited the component composition directly.",
                    "source": "direct_component_composition_edit",
                    "edit_digest": edit_digest,
                    "assistant_summary": summary,
                    "result_status": status,
                    "trace_ids": [],
                },
            ],
            "authoring_summary": summary,
            "proposal": proposal.model_dump(mode="json"),
            "diagnostics": diagnostics,
            "approval": None,
            "updated_at": now_iso(),
        }
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document=updated,
        )

    def compile(self, document: dict[str, object]) -> CompiledScenario:
        raw = document.get("proposal")
        if not isinstance(raw, dict):
            raise AuthoringCompilationError("draft has no valid proposal")
        return compile_scenario(ScenarioDraftProposal.model_validate(raw))

    def approve(self, draft_id: str, *, expected_revision: int) -> dict[str, object]:
        document = self.store.get(draft_id)
        if document["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before approving")
        compiled = self.compile(document)
        diagnostics = _diagnostics(compiled.proposal)
        if diagnostics:
            raise AuthoringCompilationError("draft has unresolved validation diagnostics")
        updated = {
            **document,
            "revision": expected_revision + 1,
            "status": "approved",
            "diagnostics": [],
            "approval": {
                "approved_from_revision": expected_revision,
                "proposal_digest": compiled.proposal_digest,
                "template_id": compiled.proposal.workflow.template_id,
                "composition_receipt_digest": compiled.composition_receipt.digest,
                "approved_at": now_iso(),
            },
            "updated_at": now_iso(),
        }
        return self.store.replace(draft_id, expected_revision=expected_revision, document=updated)

    def approved_compile(self, draft_id: str) -> CompiledScenario:
        document = self.store.get(draft_id)
        approval = document.get("approval")
        if document.get("status") != "approved" or not isinstance(approval, dict):
            raise AuthoringCompilationError("draft must be explicitly approved before it can run")
        compiled = self.compile(document)
        if approval.get("proposal_digest") != compiled.proposal_digest:
            raise AuthoringCompilationError("approval no longer matches compiled proposal")
        receipt_digest = approval.get("composition_receipt_digest")
        if receipt_digest is not None and receipt_digest != compiled.composition_receipt.digest:
            raise AuthoringCompilationError("approval no longer matches compiled composition")
        return compiled


def _diagnostics(proposal: ScenarioDraftProposal) -> list[dict[str, str]]:
    diagnostics = [
        {"severity": "question", "code": "unresolved", "message": question}
        for question in proposal.unresolved_questions
    ]
    try:
        compile_scenario(proposal)
    except AuthoringCompilationError as error:
        diagnostics.append({"severity": "error", "code": "compile", "message": str(error)})
    return diagnostics


def _proposal_from_consumer(consumer: _ProposalConsumer) -> ScenarioDraftProposal:
    if isinstance(consumer.proposal, CoordinationScenarioReview):
        return coordination_proposal_from_review(consumer.proposal)
    payload = consumer.proposal.model_dump(mode="json")
    raw_placements = payload["placements"]
    assert isinstance(raw_placements, list)
    placements = {
        str(item["entity_id"]): str(item["place_id"])
        for item in raw_placements
        if isinstance(item, dict)
    }
    if len(placements) != len(raw_placements):
        raise ValueError("placements must name each entity at most once")
    payload["placements"] = placements
    return ScenarioDraftProposal.model_validate(payload)


def _provider_candidate_from_proposal(proposal: ScenarioDraftProposal) -> dict[str, object]:
    if proposal.workflow.template_id == "coordination_decision_v1":
        return coordination_review_from_proposal(proposal).model_dump(mode="json")
    payload = proposal.model_dump(mode="json")
    placements = payload["placements"]
    assert isinstance(placements, dict)
    payload["placements"] = [
        {"entity_id": entity_id, "place_id": place_id}
        for entity_id, place_id in placements.items()
    ]
    return payload


def _provider_prior(current: dict[str, object]) -> dict[str, object]:
    """Retain conversation without exposing coordination runtime identities."""

    raw_messages = current.get("messages")
    messages = (
        [
            {
                "content": item.get("content"),
                "assistant_summary": item.get("assistant_summary"),
            }
            for item in raw_messages
            if isinstance(item, dict)
        ]
        if isinstance(raw_messages, list)
        else []
    )
    result: dict[str, object] = {
        "revision": current.get("revision"),
        "status": current.get("status"),
        "messages": messages,
    }
    raw_proposal = current.get("proposal")
    if isinstance(raw_proposal, dict):
        proposal = ScenarioDraftProposal.model_validate(raw_proposal)
        result["proposal"] = _provider_candidate_from_proposal(proposal)
    return result


def _diagnostic_feedback(diagnostics: list[dict[str, str]]) -> str:
    return "; ".join(item["message"] for item in diagnostics[:3])


def _attempt(
    trace_id: str, attempt: int,
    status: Literal["accepted", "repair", "needs_input", "provider_error"],
    message: str, meta: object | None,
) -> dict[str, object]:
    raw_cost = getattr(meta, "cost", None)
    cost = float(raw_cost) if isinstance(raw_cost, (int, float)) and raw_cost >= 0 else None
    return {
        "attempt": attempt, "trace_id": trace_id, "status": status,
        "message": message, "observed_cost": cost,
    }


def _concise_validation_error(error: ValueError) -> str:
    """Expose every bounded actionable mismatch without a provider-sized dump."""
    errors = getattr(error, "errors", None)
    if callable(errors):
        details = errors()
        if isinstance(details, list) and details:
            issues = []
            for item in details[:8]:
                if not isinstance(item, dict):
                    continue
                location = ".".join(str(part) for part in item.get("loc", ())) or "proposal"
                message = str(item.get("msg", "invalid value"))
                issues.append(f"{location}: {message}")
            if issues:
                remaining = len(details) - len(issues)
                suffix = f" ({remaining} more issue(s) omitted.)" if remaining > 0 else ""
                return "The draft does not match the required scenario fields: " + "; ".join(issues) + suffix
    return "The draft does not match the required bounded scenario schema."


def _is_capability_error(error: Exception) -> bool:
    try:
        from llm_client import LLMCapabilityError
    except ImportError:
        return False
    return isinstance(error, LLMCapabilityError)


def _is_terminal_provider_error(error: Exception) -> bool:
    try:
        from llm_client import (
            LLMAuthError,
            LLMBudgetExceededError,
            LLMCapabilityError,
            LLMConfigurationError,
            LLMContentFilterError,
            LLMModelNotFoundError,
            LLMQuotaExhaustedError,
        )
    except ImportError:
        return False
    return isinstance(
        error,
        (
            LLMAuthError,
            LLMBudgetExceededError,
            LLMCapabilityError,
            LLMConfigurationError,
            LLMContentFilterError,
            LLMModelNotFoundError,
            LLMQuotaExhaustedError,
        ),
    )


def _is_quota_error(error: Exception) -> bool:
    try:
        from llm_client import LLMQuotaExhaustedError
    except ImportError:
        return False
    return isinstance(error, LLMQuotaExhaustedError)


def _concise_provider_error(error: Exception) -> str:
    if _is_quota_error(error):
        return (
            "Sol could not run because the selected OpenRouter route has no usable quota. "
            "The prior draft was preserved; choose Terra or restore OpenRouter credits."
        )
    if _is_capability_error(error):
        return f"The selected authoring route cannot accept this structured schema: {error}"
    return f"The provider did not produce a usable typed draft: {type(error).__name__}."
