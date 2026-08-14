"""Revisioned conversational authoring for ``general_world_v1`` proposals."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from hashlib import sha256
from importlib import resources
from typing import Any, cast

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from cybernetic_influence.authoring.store import (
    AuthoringDraftStore,
    DraftConflictError,
)
from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_TERRA_MODEL,
    structured_backend_options,
)
from cybernetic_influence.run_store import now_iso

from .authoring_models import (
    GeneralAuthoringDiscussionV1,
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)
from .compiler import (
    CompiledGeneralSimulationV1,
    GeneralCompilationError,
    compile_general_simulation,
)


StructuredCall = Callable[..., tuple[Any, Any]]
GENERAL_AUTHORING_TASK = "cybernetic_influence_v3_general_world_draft"
GENERAL_AUTHORING_PROMPT_VERSION = "general_world_draft.v1"
GENERAL_AUTHORING_MAX_ATTEMPTS = 3
GENERAL_AUTHORING_MAX_BUDGET = 0.10
GENERAL_AUTHORING_MAX_TOKENS = 8000
GENERAL_AUTHORING_CALL_TIMEOUT_S = 300
GENERAL_AUTHORING_MODELS = {
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_TERRA_MODEL,
    "openrouter/openai/gpt-5.6-sol",
}


def _structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as exc:
        raise RuntimeError("general authoring requires the shared llm_client") from exc
    return cast(StructuredCall, call_llm_structured)


def _call_with_deadline(
    call: StructuredCall, *args: Any, **kwargs: Any
) -> tuple[Any, Any]:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(call, *args, **kwargs)
    try:
        return future.result(timeout=GENERAL_AUTHORING_CALL_TIMEOUT_S)
    except FutureTimeoutError as exc:
        raise TimeoutError(
            f"general authoring call exceeded {GENERAL_AUTHORING_CALL_TIMEOUT_S}s"
        ) from exc
    finally:
        pool.shutdown(wait=False)


def _prompt_source() -> str:
    return (
        resources.files("cybernetic_influence.general_simulation")
        .joinpath("prompts/general_world_draft.yaml")
        .read_text(encoding="utf-8")
    )


def _discussion_prompt_source() -> str:
    return (
        resources.files("cybernetic_influence.general_simulation")
        .joinpath("prompts/general_world_discussion.yaml")
        .read_text(encoding="utf-8")
    )


def _discussion_prompt(*, message: str, prior: dict[str, object]) -> tuple[str, str]:
    template = yaml.safe_load(_discussion_prompt_source())
    if not isinstance(template, dict):
        raise ValueError("general discussion prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(value, sort_keys=True)
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(message=message, prior=prior),
    )


def _prompt(
    *,
    message: str,
    prior: dict[str, object],
    repair_feedback: str | None,
    candidate: object | None,
) -> tuple[str, str]:
    template = yaml.safe_load(_prompt_source())
    if not isinstance(template, dict):
        raise ValueError("general authoring prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(value, sort_keys=True)
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(
            message=message,
            prior=prior,
            repair_feedback=repair_feedback,
            candidate=candidate,
        ),
    )


def _attempt(
    attempt: int,
    trace_id: str,
    status: str,
    message: str,
    meta: object | None,
) -> dict[str, object]:
    raw_cost = getattr(meta, "cost", None)
    cost = float(raw_cost) if isinstance(raw_cost, (int, float)) and raw_cost >= 0 else None
    return {
        "attempt": attempt,
        "trace_id": trace_id,
        "status": status,
        "message": message,
        "observed_cost": cost,
    }


def _prior(document: dict[str, object]) -> dict[str, object]:
    messages = document.get("messages")
    result: dict[str, object] = {
        "revision": document.get("revision"),
        "messages": [
            {
                "content": item.get("content"),
                "assistant_summary": item.get("assistant_summary"),
            }
            for item in messages
            if isinstance(item, dict)
        ]
        if isinstance(messages, list)
        else [],
    }
    if isinstance(document.get("proposal"), dict):
        result["proposal"] = document["proposal"]
    return result


def _diagnostics(
    proposal: GeneralSimulationProposalV1,
    compiled: CompiledGeneralSimulationV1,
) -> list[dict[str, str]]:
    diagnostics = [
        {"severity": "question", "code": "unresolved", "message": question}
        for question in proposal.unresolved_questions
    ]
    for request_id in compiled.coverage.blocking_request_ids:
        item = next(item for item in compiled.coverage.items if item.request_id == request_id)
        diagnostics.append(
            {
                "severity": "error",
                "code": "unsupported_behavior",
                "message": (
                    f"Material behavior {request_id!r} is {item.classification}; "
                    + "; ".join(item.compiler_evidence)
                ),
            }
        )
    for item in compiled.configuration_graph["diagnostics"]:
        if item["severity"] == "error":
            diagnostics.append(
                {
                    "severity": "error",
                    "code": str(item["code"]),
                    "message": str(item["message"]),
                }
            )
    return diagnostics


class GeneralDraftAuthoringService:
    def __init__(
        self, store: AuthoringDraftStore, *, call: StructuredCall | None = None
    ) -> None:
        self.store = store
        self.call = call or _structured_call()

    def compile(self, document: dict[str, object]) -> CompiledGeneralSimulationV1:
        if document.get("target_kind") != "general_world_v1":
            raise GeneralCompilationError("draft is not a general-world proposal")
        raw = document.get("proposal")
        if not isinstance(raw, dict):
            raise GeneralCompilationError("draft has no valid general proposal")
        return compile_general_simulation(GeneralSimulationProposalV1.model_validate(raw))

    def discuss(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        message_id: str,
        message: str,
        model: str = CODEX_LUNA_MODEL,
        reasoning_effort: str = "medium",
    ) -> dict[str, object]:
        if model not in GENERAL_AUTHORING_MODELS:
            raise ValueError("unsupported general authoring model")
        current = self.store.get(draft_id)
        if current.get("target_kind") != "general_world_v1":
            raise ValueError("draft is not a general-world draft")
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        messages = cast(list[dict[str, object]], current["messages"])
        existing = next((item for item in messages if item.get("message_id") == message_id), None)
        if existing is not None:
            if existing.get("content") != message:
                raise DraftConflictError("message ID was reused with different content")
            return current
        trace_id = f"{draft_id}/general/discussion/{expected_revision + 1}"
        system, user = _discussion_prompt(message=message, prior=_prior(current))
        with structured_backend_options(model) as backend_options:
            parsed, meta = _call_with_deadline(
                self.call,
                model,
                [{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_model=GeneralAuthoringDiscussionV1,
                task="cybernetic_influence_v3_general_world_discussion",
                trace_id=trace_id,
                max_budget=GENERAL_AUTHORING_MAX_BUDGET,
                max_tokens=1800,
                model_justification="Clarify a simulation request before typed configuration.",
                reasoning_effort=reasoning_effort,
                timeout=120,
                **backend_options,
            )
        discussion = GeneralAuthoringDiscussionV1.model_validate(
            parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
        )
        assistant_text = discussion.reply
        if discussion.material_questions:
            assistant_text += "\n\n" + "\n".join(
                f"{index}. {question}"
                for index, question in enumerate(discussion.material_questions, start=1)
            )
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document={
                **current,
                "revision": expected_revision + 1,
                "status": "draft",
                "messages": [
                    *messages,
                    {
                        "message_id": message_id,
                        "content": message,
                        "source": "conversation",
                        "model": model,
                        "reasoning_effort": reasoning_effort,
                        "assistant_summary": assistant_text,
                        "result_status": "discussion",
                        "trace_ids": [trace_id],
                    },
                ],
                "attempts": [
                    *cast(list[dict[str, object]], current["attempts"]),
                    _attempt(1, trace_id, "accepted", discussion.understood_summary, meta),
                ],
                "authoring_summary": assistant_text,
                "diagnostics": [
                    {"severity": "question", "code": "discussion", "message": item}
                    for item in discussion.material_questions
                ],
                "approval": None,
                "updated_at": now_iso(),
            },
        )

    def advance(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        message_id: str,
        message: str,
        model: str = CODEX_LUNA_MODEL,
        reasoning_effort: str = "medium",
    ) -> dict[str, object]:
        if model not in GENERAL_AUTHORING_MODELS:
            raise ValueError("unsupported general authoring model")
        current = self.store.get(draft_id)
        if current.get("target_kind") != "general_world_v1":
            raise ValueError("draft is not a general-world draft")
        messages = current["messages"]
        assert isinstance(messages, list)
        existing = next(
            (item for item in messages if item.get("message_id") == message_id), None
        )
        if existing is not None:
            if (
                existing.get("content") != message
                or existing.get("model") not in (None, model)
                or existing.get("reasoning_effort") not in (None, reasoning_effort)
            ):
                raise DraftConflictError("message ID was reused with different content")
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        proposal: GeneralSimulationProposalV1 | None = None
        compiled: CompiledGeneralSimulationV1 | None = None
        candidate: object | None = None
        repair_feedback: str | None = None
        attempts: list[dict[str, object]] = []
        diagnostics: list[dict[str, str]] = []
        for attempt_number in range(1, GENERAL_AUTHORING_MAX_ATTEMPTS + 1):
            trace_id = (
                f"{draft_id}/general/revision/{expected_revision + 1}/attempt/"
                f"{attempt_number}"
            )
            system, user = _prompt(
                message=message,
                prior=_prior(current),
                repair_feedback=repair_feedback,
                candidate=candidate,
            )
            meta: object | None = None
            try:
                with structured_backend_options(model) as backend_options:
                    parsed, meta = _call_with_deadline(
                        self.call,
                        model,
                        [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_model=GeneralProposalEnvelopeV1,
                        task=GENERAL_AUTHORING_TASK,
                        trace_id=trace_id,
                        max_budget=GENERAL_AUTHORING_MAX_BUDGET,
                        max_tokens=GENERAL_AUTHORING_MAX_TOKENS,
                        model_justification=(
                            "Translate an analyst's ordinary-language situation into a "
                            "semantic general-world proposal without executable references."
                        ),
                        reasoning_effort=reasoning_effort,
                        timeout=270,
                        **backend_options,
                    )
                raw = parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
                if isinstance(parsed, GeneralSimulationProposalV1):
                    proposal = parsed
                else:
                    proposal = GeneralProposalEnvelopeV1.model_validate(raw).proposal
                candidate = proposal.model_dump(mode="json")
                compiled = compile_general_simulation(proposal)
                diagnostics = _diagnostics(proposal, compiled)
                if not diagnostics:
                    attempts.append(
                        _attempt(
                            attempt_number,
                            trace_id,
                            "accepted",
                            "The semantic proposal compiled with complete material coverage.",
                            meta,
                        )
                    )
                    break
                if all(item["severity"] == "question" for item in diagnostics):
                    attempts.append(
                        _attempt(
                            attempt_number,
                            trace_id,
                            "needs_input",
                            "; ".join(item["message"] for item in diagnostics),
                            meta,
                        )
                    )
                    break
                repair_feedback = "; ".join(item["message"] for item in diagnostics[:5])
                attempts.append(
                    _attempt(attempt_number, trace_id, "repair", repair_feedback, meta)
                )
                proposal = None
                compiled = None
            except (ValueError, GeneralCompilationError) as exc:
                repair_feedback = str(exc)
                diagnostics = [
                    {"severity": "error", "code": "validation", "message": str(exc)}
                ]
                attempts.append(
                    _attempt(attempt_number, trace_id, "repair", str(exc), meta)
                )
                proposal = None
                compiled = None
            except Exception as exc:
                concise_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                diagnostics = [
                    {
                        "severity": "error",
                        "code": "provider",
                        "message": f"General authoring provider failed: {concise_error}",
                    }
                ]
                attempts.append(
                    _attempt(attempt_number, trace_id, "provider_error", diagnostics[0]["message"], meta)
                )
                break
        if proposal is None and isinstance(candidate, dict):
            proposal = GeneralSimulationProposalV1.model_validate(candidate)
            compiled = compile_general_simulation(proposal)
            diagnostics = _diagnostics(proposal, compiled)
        if proposal is not None and compiled is not None:
            status = "needs_input" if diagnostics else "ready_for_review"
            summary = (
                f"Generated {proposal.title}. Coverage resolved "
                f"{len(compiled.coverage.items)} requested behaviors; "
                f"{len(compiled.coverage.blocking_request_ids)} block approval."
            )
            proposal_payload: dict[str, object] | None = proposal.model_dump(mode="json")
            coverage_payload: dict[str, object] | None = compiled.coverage.model_dump(
                mode="json"
            )
            configuration_graph_payload: dict[str, object] | None = (
                compiled.configuration_graph
            )
        elif isinstance(current.get("proposal"), dict) and attempts and all(
            item["status"] == "provider_error" for item in attempts
        ):
            status = str(current["status"])
            summary = "The provider failed, so the prior retained proposal was preserved."
            proposal_payload = cast(dict[str, object], current["proposal"])
            coverage_payload = cast(
                dict[str, object] | None, current.get("coverage")
            )
            configuration_graph_payload = cast(
                dict[str, object] | None, current.get("configuration_graph")
            )
            diagnostics = cast(list[dict[str, str]], current.get("diagnostics", []))
        else:
            status = "needs_input"
            summary = "No valid general-world proposal was produced; revise the request using the diagnostics."
            proposal_payload = None
            coverage_payload = None
            configuration_graph_payload = None
        assistant_summary = " ".join(
            [summary, *[item["message"] for item in diagnostics]]
        )
        document = {
            **current,
            "revision": expected_revision + 1,
            "status": status,
            "messages": [
                *messages,
                {
                    "message_id": message_id,
                    "content": message,
                    "source": "conversation",
                    "model": model,
                    "reasoning_effort": reasoning_effort,
                    "assistant_summary": assistant_summary,
                    "result_status": status,
                    "trace_ids": [str(item["trace_id"]) for item in attempts],
                },
            ],
            "attempts": attempts,
            "authoring_summary": summary,
            "proposal": proposal_payload,
            "coverage": coverage_payload,
            "configuration_graph": configuration_graph_payload,
            "diagnostics": diagnostics,
            "approval": None,
            "updated_at": now_iso(),
        }
        return self.store.replace(
            draft_id, expected_revision=expected_revision, document=document
        )

    def edit_proposal(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        edit_id: str,
        proposal: GeneralSimulationProposalV1,
    ) -> dict[str, object]:
        current = self.store.get(draft_id)
        messages = current["messages"]
        assert isinstance(messages, list)
        digest = sha256(proposal.model_dump_json().encode()).hexdigest()
        existing = next(
            (item for item in messages if item.get("message_id") == edit_id), None
        )
        if existing is not None:
            if (
                existing.get("source") != "direct_general_proposal_edit"
                or existing.get("edit_digest") != digest
            ):
                raise DraftConflictError("edit ID was reused with different content")
            return current
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        compiled = compile_general_simulation(proposal)
        diagnostics = _diagnostics(proposal, compiled)
        status = "needs_input" if diagnostics else "ready_for_review"
        summary = "Saved the typed general-world proposal without a model call."
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document={
                **current,
                "revision": expected_revision + 1,
                "status": status,
                "messages": [
                    *messages,
                    {
                        "message_id": edit_id,
                        "content": "Edited the general-world proposal directly.",
                        "source": "direct_general_proposal_edit",
                        "edit_digest": digest,
                        "assistant_summary": summary,
                        "result_status": status,
                        "trace_ids": [],
                    },
                ],
                "authoring_summary": summary,
                "proposal": proposal.model_dump(mode="json"),
                "coverage": compiled.coverage.model_dump(mode="json"),
                "configuration_graph": compiled.configuration_graph,
                "diagnostics": diagnostics,
                "approval": None,
                "updated_at": now_iso(),
            },
        )

    def approve(self, draft_id: str, *, expected_revision: int) -> dict[str, object]:
        current = self.store.get(draft_id)
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before approving")
        compiled = self.compile(current)
        diagnostics = _diagnostics(compiled.proposal, compiled)
        if diagnostics or not compiled.coverage.approvable:
            raise GeneralCompilationError("general proposal has blocking diagnostics or coverage")
        approval = {
            "approved_from_revision": expected_revision,
            "proposal_kind": "general_world_v1",
            "proposal_digest": compiled.proposal_digest,
            "registry_digest": compiled.registry_digest,
            "world_spec_digest": sha256(
                compiled.world_spec.model_dump_json().encode()
            ).hexdigest(),
            "approved_at": now_iso(),
        }
        return self.store.replace(
            draft_id,
            expected_revision=expected_revision,
            document={
                **current,
                "revision": expected_revision + 1,
                "status": "approved",
                "diagnostics": [],
                "approval": approval,
                "updated_at": now_iso(),
            },
        )

    def approved_compile(self, draft_id: str) -> CompiledGeneralSimulationV1:
        current = self.store.get(draft_id)
        approval = current.get("approval")
        if current.get("status") != "approved" or not isinstance(approval, dict):
            raise GeneralCompilationError("draft must be approved before execution")
        compiled = self.compile(current)
        if approval.get("proposal_digest") != compiled.proposal_digest:
            raise GeneralCompilationError("approval no longer matches proposal")
        if approval.get("registry_digest") != compiled.registry_digest:
            raise GeneralCompilationError("approval no longer matches installed registry")
        return compiled
