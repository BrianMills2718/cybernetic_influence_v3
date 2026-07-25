"""Structured conversation, validation, approval, and execution for Slice 17B."""

from __future__ import annotations

from collections.abc import Callable
from importlib import resources
import json
from typing import Any, cast

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

    proposal_version: int = 1
    scenario_id: str
    title: str
    description: str
    people: list[dict[str, object]]
    objects: list[dict[str, object]]
    information: list[dict[str, object]]
    places: list[dict[str, object]]
    spatial_links: list[dict[str, object]]
    placements: dict[str, str]
    timing_assumptions: list[dict[str, object]]
    workflow: dict[str, object]
    analytical_boundaries: list[dict[str, object]]
    fidelity_questions: list[str]
    unresolved_questions: list[str] = []


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
            diagnostics = [{"severity": "error", "code": "schema", "message": str(error)}]
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
