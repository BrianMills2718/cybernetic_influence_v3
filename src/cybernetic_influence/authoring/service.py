"""Structured conversation, validation, approval, and execution for Slice 17B."""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
import json
from typing import Any, Literal, cast

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict

from cybernetic_influence.authoring.compiler import (
    AuthoringCompilationError,
    CompiledScenario,
    compile_resource_request,
)
from cybernetic_influence.authoring.models import ScenarioDraftProposal
from cybernetic_influence.authoring.store import AuthoringDraftStore, DraftConflictError
from cybernetic_influence.run_store import now_iso

StructuredCall = Callable[..., tuple[Any, Any]]
AUTHORING_TASK = "cybernetic_influence_v3_scenario_draft"
AUTHORING_MAX_BUDGET = 0.10
AUTHORING_MODEL = "openrouter/deepseek/deepseek-v4-flash"


class _ProposalConsumer(BaseModel):
    """Permissive at the provider boundary; strict proposal validation follows."""

    model_config = ConfigDict(extra="ignore")

    proposal_version: Literal[1] = 1
    scenario_id: str
    title: str
    description: str
    people: list["_PersonConsumer"]
    objects: list["_ObjectConsumer"]
    information: list["_InformationConsumer"]
    places: list["_PlaceConsumer"]
    spatial_links: list["_SpatialLinkConsumer"]
    placements: dict[str, str]
    timing_assumptions: list["_TimingConsumer"]
    workflow: "_WorkflowConsumer"
    analytical_boundaries: list["_BoundaryConsumer"]
    fidelity_questions: list[str]
    unresolved_questions: list[str] = []


class _PersonConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entity_id: str
    label: str
    position: str
    disposition: str
    memories: list[str]


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


class _WorkflowConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    template_id: Literal["resource_request_v1"] = "resource_request_v1"
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


class _BoundaryConsumer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    boundary_id: str
    label: str
    description: str
    member_refs: list[str]


def _structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as error:
        raise RuntimeError("scenario authoring requires the shared llm_client") from error
    return cast(StructuredCall, call_llm_structured)


def _prompt(*, message: str, prior: dict[str, object]) -> tuple[str, str]:
    raw = resources.files("cybernetic_influence.authoring").joinpath(
        "prompts/scenario_draft.yaml"
    ).read_text(encoding="utf-8")
    template = yaml.safe_load(raw)
    if not isinstance(template, dict):
        raise ValueError("authoring prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(value, sort_keys=True)
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(message=message, prior=prior),
    )


class DraftAuthoringService:
    def __init__(self, store: AuthoringDraftStore, *, call: StructuredCall | None = None) -> None:
        self.store = store
        self.call = call or _structured_call()

    def advance(
        self, draft_id: str, *, expected_revision: int, message_id: str, message: str
    ) -> dict[str, object]:
        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        existing = next((item for item in messages if item.get("message_id") == message_id), None)
        if existing is not None:
            if existing.get("content") != message:
                raise DraftConflictError("message ID was already used with different content")
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        system, user = _prompt(message=message, prior=current)
        parsed, _meta = self.call(
            AUTHORING_MODEL,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_model=_ProposalConsumer,
            task=AUTHORING_TASK,
            trace_id=f"{draft_id}/revision/{expected_revision + 1}",
            max_budget=AUTHORING_MAX_BUDGET,
            max_tokens=4000,
            model_justification="Produce a bounded, reviewable resource-request scenario draft.",
            reasoning_effort="none",
        )
        consumer = _ProposalConsumer.model_validate(
            parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
        )
        proposal: ScenarioDraftProposal | None = None
        diagnostics: list[dict[str, str]]
        try:
            proposal = ScenarioDraftProposal.model_validate(consumer.model_dump(mode="json"))
            diagnostics = _diagnostics(proposal)
        except ValueError as error:
            diagnostics = [{
                "severity": "error", "code": "schema",
                "message": _concise_validation_error(error),
            }]
        updated = {
            **current,
            "revision": expected_revision + 1,
            "status": "draft",
            "messages": [*messages, {"message_id": message_id, "content": message}],
            "proposal": proposal.model_dump(mode="json") if proposal else None,
            "diagnostics": diagnostics,
            "approval": None,
            "updated_at": now_iso(),
        }
        return self.store.replace(draft_id, expected_revision=expected_revision, document=updated)

    def compile(self, document: dict[str, object]) -> CompiledScenario:
        raw = document.get("proposal")
        if not isinstance(raw, dict):
            raise AuthoringCompilationError("draft has no valid proposal")
        return compile_resource_request(ScenarioDraftProposal.model_validate(raw))

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
        return compiled


def _diagnostics(proposal: ScenarioDraftProposal) -> list[dict[str, str]]:
    diagnostics = [
        {"severity": "question", "code": "unresolved", "message": question}
        for question in proposal.unresolved_questions
    ]
    try:
        compile_resource_request(proposal)
    except AuthoringCompilationError as error:
        diagnostics.append({"severity": "error", "code": "compile", "message": str(error)})
    return diagnostics


def _concise_validation_error(error: ValueError) -> str:
    """Expose the first actionable schema mismatch, not a provider-sized dump."""
    errors = getattr(error, "errors", None)
    if callable(errors):
        details = errors()
        if isinstance(details, list) and details:
            first = details[0]
            if isinstance(first, dict):
                location = ".".join(str(part) for part in first.get("loc", ()))
                message = str(first.get("msg", "invalid value"))
                return f"The draft does not match the required scenario fields at {location}: {message}."
    return "The draft does not match the required bounded scenario schema."
