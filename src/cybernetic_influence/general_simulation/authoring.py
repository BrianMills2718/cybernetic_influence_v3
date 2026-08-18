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
    DependencyCompletenessReviewV1,
    GeneralAuthoringDiscussionV1,
    GeneralProposalEnvelopeV1,
    GeneralSimulationProposalV1,
)
from .compiler import (
    CompiledGeneralSimulationV1,
    CompiledGeneralSimulationV2,
    GeneralCompilationError,
    compile_general_simulation,
    compile_general_simulation_v2,
    materialize_dependency_guard_repairs,
    materialize_unambiguous_contract_references,
)
from .study_models import (
    AuthoredSimulationBundleV2,
    AuthoredSimulationProposalEnvelopeV2,
    AuthoredSimulationProposalV2,
    materialize_authored_bundle_v2,
)


StructuredCall = Callable[..., tuple[Any, Any]]
AuthoringProgress = Callable[[str, str, int | None], None]
GENERAL_AUTHORING_TASK = "cybernetic_influence_v3_general_world_draft"
GENERAL_AUTHORING_PROMPT_VERSION = "general_world_draft.v2"
GENERAL_AUTHORING_MAX_ATTEMPTS = 5
GENERAL_AUTHORING_MAX_BUDGET = 0.10
GENERAL_AUTHORING_MAX_TOKENS = 8000
GENERAL_AUTHORING_CALL_TIMEOUT_S = 300
GENERAL_AUTHORING_MODELS = {
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_TERRA_MODEL,
    "openrouter/openai/gpt-5.6-sol",
}


def _report_progress(
    progress: AuthoringProgress | None,
    phase: str,
    detail: str,
    attempt: int | None = None,
) -> None:
    if progress is not None:
        progress(phase, detail, attempt)


def _is_terminal_provider_error(error: Exception) -> bool:
    """Return whether retrying the same provider route cannot reasonably help."""

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


def _dependency_review_prompt_source() -> str:
    return (
        resources.files("cybernetic_influence.general_simulation")
        .joinpath("prompts/dependency_completeness_review.yaml")
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


def _dependency_review_prompt(
    *,
    message: str,
    proposal: AuthoredSimulationProposalV2,
    compiled: CompiledGeneralSimulationV2,
) -> tuple[str, str]:
    template = yaml.safe_load(_dependency_review_prompt_source())
    if not isinstance(template, dict):
        raise ValueError("dependency completeness prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(value, sort_keys=True)
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(
            message=message,
            proposal=proposal.model_dump(mode="json"),
            coverage=compiled.coverage.model_dump(mode="json"),
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


def _suppress_redundant_custody_findings(
    proposal: AuthoredSimulationProposalV2,
    review: DependencyCompletenessReviewV1,
) -> tuple[DependencyCompletenessReviewV1, list[str]]:
    """Suppress only review findings already enforced by exact resource custody."""

    if review.status == "complete":
        return review, []
    scenario = proposal.scenario
    requests = {item.request_id: item for item in scenario.component_requests}
    transformations = {
        item.transformation_id: item for item in scenario.resource_transformations
    }
    transports = {item.transport_id: item for item in scenario.resource_transports}
    stocks = (
        {item.resource_id: item for item in scenario.resource_extension.stocks}
        if scenario.resource_extension
        else {}
    )
    contract_moments: dict[str, int] = {}
    for index, moment in enumerate(proposal.default_run.scheduled_moments):
        for contract_id in moment.active_transition_contract_ids:
            contract_moments.setdefault(contract_id, index)

    retained = []
    suppressions: list[str] = []
    for finding in review.missing_dependencies:
        request = requests.get(finding.exact_action_request_id)
        suppressed_by: tuple[str, str] | None = None
        if (
            request is not None
            and finding.existing_ref is not None
            and finding.required_resolution in {"exact_guard", "required_read"}
        ):
            for contract_id in request.transition_contract_ids:
                transformation = transformations.get(contract_id)
                transformation_moment = contract_moments.get(contract_id)
                if transformation is None or transformation_moment is None:
                    continue
                for requirement in transformation.input_resource_quantities:
                    stock = stocks.get(requirement.resource_id)
                    if (
                        stock is None
                        or stock.quantity != 0
                        or requirement.resource_id not in request.required_reads
                    ):
                        continue
                    for transport in transports.values():
                        transport_moment = contract_moments.get(transport.transport_id)
                        if (
                            transport.destination_resource_id == requirement.resource_id
                            and transport.arrival_record_id == finding.existing_ref
                            and transport_moment is not None
                            and transport_moment < transformation_moment
                        ):
                            suppressed_by = (
                                transport.transport_id,
                                requirement.resource_id,
                            )
                            break
                    if suppressed_by is not None:
                        break
                if suppressed_by is not None:
                    break
        if suppressed_by is None:
            retained.append(finding)
            continue
        suppressions.append(
            f"{finding.exact_action_request_id}: {finding.existing_ref} is redundant "
            f"because exact transport {suppressed_by[0]} supplies initially empty "
            f"canonical resource {suppressed_by[1]} before the transformation"
        )

    if len(retained) == len(review.missing_dependencies):
        return review, []
    return (
        DependencyCompletenessReviewV1(
            status="complete" if not retained else "repair_required",
            summary=(
                "All remaining exact action prerequisites are covered after recognizing "
                "canonical resource custody produced by earlier exact transport."
                if not retained
                else review.summary
            ),
            missing_dependencies=retained,
        ),
        suppressions,
    )


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
                    f"Material behavior {request_id!r} has {item.causal_closure} "
                    f"causal closure ({item.classification} authority); "
                    + "; ".join(item.compiler_evidence)
                ),
            }
        )
    graph_diagnostics = compiled.configuration_graph.get("diagnostics", [])
    assert isinstance(graph_diagnostics, list)
    for item in graph_diagnostics:
        assert isinstance(item, dict)
        if item["severity"] == "error":
            diagnostics.append(
                {
                    "severity": "error",
                    "code": str(item["code"]),
                    "message": str(item["message"]),
                }
            )
    return diagnostics


def _diagnostics_v2(
    bundle: AuthoredSimulationBundleV2,
    compiled: CompiledGeneralSimulationV2,
) -> list[dict[str, str]]:
    diagnostics = [
        {"severity": "question", "code": "unresolved", "message": question}
        for question in bundle.unresolved_questions
    ]
    for request_id in compiled.coverage.blocking_request_ids:
        item = next(item for item in compiled.coverage.items if item.request_id == request_id)
        diagnostics.append(
            {
                "severity": "error",
                "code": "unsupported_behavior",
                "message": (
                    f"Material behavior {request_id!r} has {item.causal_closure} "
                    f"causal closure ({item.classification} authority); "
                    + "; ".join(item.compiler_evidence)
                ),
            }
        )
    graph_diagnostics = compiled.configuration_graph.get("diagnostics", [])
    assert isinstance(graph_diagnostics, list)
    for item in graph_diagnostics:
        assert isinstance(item, dict)
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

    def compile(
        self, document: dict[str, object]
    ) -> CompiledGeneralSimulationV1 | CompiledGeneralSimulationV2:
        target_kind = document.get("target_kind")
        if target_kind not in {"general_world_v1", "general_world_v2"}:
            raise GeneralCompilationError("draft is not a general-world proposal")
        raw = document.get("proposal")
        if not isinstance(raw, dict):
            raise GeneralCompilationError("draft has no valid general proposal")
        if target_kind == "general_world_v2":
            bundle = AuthoredSimulationBundleV2.model_validate(raw)
            return compile_general_simulation_v2(bundle.scenario, bundle.default_run)
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
        progress: AuthoringProgress | None = None,
    ) -> dict[str, object]:
        if model not in GENERAL_AUTHORING_MODELS:
            raise ValueError("unsupported general authoring model")
        current = self.store.get(draft_id)
        if current.get("target_kind") not in {"general_world_v1", "general_world_v2"}:
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
        _report_progress(
            progress,
            "discussion",
            "The model is identifying the few choices that materially change this simulation.",
            1,
        )
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
        _report_progress(
            progress,
            "retaining",
            "Saving the discussion and unresolved choices to this draft.",
            1,
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
        progress: AuthoringProgress | None = None,
    ) -> dict[str, object]:
        current = self.store.get(draft_id)
        if current.get("target_kind") == "general_world_v2":
            return self._advance_v2(
                draft_id,
                current=current,
                expected_revision=expected_revision,
                message_id=message_id,
                message=message,
                model=model,
                reasoning_effort=reasoning_effort,
                progress=progress,
            )
        if model not in GENERAL_AUTHORING_MODELS:
            raise ValueError("unsupported general authoring model")
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
                if _is_terminal_provider_error(exc):
                    break
                repair_feedback = (
                    "The provider response could not be parsed. Return one complete, "
                    "concise proposal envelope that validates against the supplied schema."
                )
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

    def _advance_v2(
        self,
        draft_id: str,
        *,
        current: dict[str, object],
        expected_revision: int,
        message_id: str,
        message: str,
        model: str,
        reasoning_effort: str,
        progress: AuthoringProgress | None,
    ) -> dict[str, object]:
        """Generate a native separated proposal and retain only its trusted bundle."""
        if model not in GENERAL_AUTHORING_MODELS:
            raise ValueError("unsupported general authoring model")
        messages = cast(list[dict[str, object]], current["messages"])
        existing = next((item for item in messages if item.get("message_id") == message_id), None)
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

        proposal: AuthoredSimulationProposalV2 | None = None
        bundle: AuthoredSimulationBundleV2 | None = None
        compiled: CompiledGeneralSimulationV2 | None = None
        candidate: object | None = None
        repair_feedback: str | None = None
        attempts: list[dict[str, object]] = []
        diagnostics: list[dict[str, str]] = []
        for attempt_number in range(1, GENERAL_AUTHORING_MAX_ATTEMPTS + 1):
            trace_id = (
                f"{draft_id}/general-v2/revision/{expected_revision + 1}/attempt/"
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
                _report_progress(
                    progress,
                    "proposal_generation",
                    "The model is composing the people, world, information paths, and run conditions.",
                    attempt_number,
                )
                with structured_backend_options(model) as backend_options:
                    parsed, meta = _call_with_deadline(
                        self.call,
                        model,
                        [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                        response_model=AuthoredSimulationProposalEnvelopeV2,
                        task="cybernetic_influence_v3_general_world_v2_draft",
                        trace_id=trace_id,
                        max_budget=GENERAL_AUTHORING_MAX_BUDGET,
                        max_tokens=GENERAL_AUTHORING_MAX_TOKENS,
                        model_justification=(
                            "Translate an analyst's situation into separated world, run, "
                            "and optional analysis semantics."
                        ),
                        reasoning_effort=reasoning_effort,
                        timeout=270,
                        **backend_options,
                    )
                raw = parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
                proposal = AuthoredSimulationProposalEnvelopeV2.model_validate(raw).proposal
                _report_progress(
                    progress,
                    "contract_materialization",
                    "Linking uniquely determined fields and references without another model call.",
                    attempt_number,
                )
                scenario, attempt_corrections = materialize_unambiguous_contract_references(
                    proposal.scenario
                )
                proposal = proposal.model_copy(update={"scenario": scenario})
                candidate = proposal.model_dump(mode="json")
                bundle = materialize_authored_bundle_v2(
                    proposal, run_id=f"{draft_id}_run"
                )
                _report_progress(
                    progress,
                    "compiling",
                    "Checking references, execution coverage, and registered transition contracts.",
                    attempt_number,
                )
                compiled = compile_general_simulation_v2(
                    bundle.scenario, bundle.default_run
                )
                diagnostics = _diagnostics_v2(bundle, compiled)
                if not diagnostics:
                    attempts.append(
                        _attempt(
                            attempt_number,
                            trace_id,
                            "accepted",
                            (
                                "The separated semantic proposal compiled after "
                                f"{len(attempt_corrections)} retained deterministic "
                                "correction(s); dependency completeness review follows."
                                + (
                                    " Corrections: " + "; ".join(attempt_corrections)
                                    if attempt_corrections
                                    else ""
                                )
                            ),
                            meta,
                        )
                    )
                    review_trace_id = f"{trace_id}/dependency-review"
                    review_system, review_user = _dependency_review_prompt(
                        message=message,
                        proposal=proposal,
                        compiled=compiled,
                    )
                    _report_progress(
                        progress,
                        "dependency_review",
                        "The model is checking whether consequential prerequisites were omitted.",
                        attempt_number,
                    )
                    with structured_backend_options(model) as review_backend_options:
                        reviewed, review_meta = _call_with_deadline(
                            self.call,
                            model,
                            [
                                {"role": "system", "content": review_system},
                                {"role": "user", "content": review_user},
                            ],
                            response_model=DependencyCompletenessReviewV1,
                            task="cybernetic_influence_v3_dependency_completeness_review",
                            trace_id=review_trace_id,
                            max_budget=GENERAL_AUTHORING_MAX_BUDGET,
                            max_tokens=2400,
                            model_justification=(
                                "Adversarially compare the analyst request with the generated "
                                "exact transition dependencies before approval."
                            ),
                            reasoning_effort=reasoning_effort,
                            timeout=180,
                            **review_backend_options,
                        )
                    review = DependencyCompletenessReviewV1.model_validate(
                        reviewed.model_dump(mode="json")
                        if isinstance(reviewed, BaseModel)
                        else reviewed
                    )
                    review, review_suppressions = _suppress_redundant_custody_findings(
                        proposal, review
                    )
                    if review.status == "repair_required":
                        repaired_scenario, guard_corrections = (
                            materialize_dependency_guard_repairs(proposal.scenario, review)
                        )
                        if guard_corrections:
                            repaired_proposal = proposal.model_copy(
                                update={"scenario": repaired_scenario}
                            )
                            repaired_bundle = materialize_authored_bundle_v2(
                                repaired_proposal, run_id=f"{draft_id}_run"
                            )
                            repaired_compiled = compile_general_simulation_v2(
                                repaired_bundle.scenario, repaired_bundle.default_run
                            )
                            repaired_diagnostics = _diagnostics_v2(
                                repaired_bundle, repaired_compiled
                            )
                            if not repaired_diagnostics:
                                recheck_trace_id = f"{review_trace_id}/guard-recheck"
                                recheck_system, recheck_user = _dependency_review_prompt(
                                    message=message,
                                    proposal=repaired_proposal,
                                    compiled=repaired_compiled,
                                )
                                _report_progress(
                                    progress,
                                    "dependency_review",
                                    "Rechecking the narrowly repaired causal guards.",
                                    attempt_number,
                                )
                                with structured_backend_options(model) as recheck_backend_options:
                                    rechecked, recheck_meta = _call_with_deadline(
                                        self.call,
                                        model,
                                        [
                                            {"role": "system", "content": recheck_system},
                                            {"role": "user", "content": recheck_user},
                                        ],
                                        response_model=DependencyCompletenessReviewV1,
                                        task="cybernetic_influence_v3_dependency_guard_recheck",
                                        trace_id=recheck_trace_id,
                                        max_budget=GENERAL_AUTHORING_MAX_BUDGET,
                                        max_tokens=2400,
                                        model_justification=(
                                            "Verify reviewer-proposed exact guards before retaining "
                                            "the compiled scenario."
                                        ),
                                        reasoning_effort=reasoning_effort,
                                        timeout=180,
                                        **recheck_backend_options,
                                    )
                                recheck = DependencyCompletenessReviewV1.model_validate(
                                    rechecked.model_dump(mode="json")
                                    if isinstance(rechecked, BaseModel)
                                    else rechecked
                                )
                                recheck, recheck_suppressions = (
                                    _suppress_redundant_custody_findings(
                                        repaired_proposal, recheck
                                    )
                                )
                                attempts.append(
                                    _attempt(
                                        attempt_number,
                                        review_trace_id,
                                        "repair",
                                        "; ".join(guard_corrections),
                                        review_meta,
                                    )
                                )
                                if recheck.status == "complete":
                                    attempts.append(
                                        _attempt(
                                            attempt_number,
                                            recheck_trace_id,
                                            "accepted",
                                            recheck.summary
                                            + (
                                                " Retained dependency equivalences: "
                                                + "; ".join(recheck_suppressions)
                                                if recheck_suppressions
                                                else ""
                                            ),
                                            recheck_meta,
                                        )
                                    )
                                    proposal = repaired_proposal
                                    bundle = repaired_bundle
                                    compiled = repaired_compiled
                                    diagnostics = []
                                    break
                                review = recheck
                                review_suppressions = recheck_suppressions
                        repair_feedback = "Dependency completeness review requires repair: " + "; ".join(
                            (
                                f"{item.exact_action_request_id}: "
                                f"{item.prerequisite_description} "
                                f"(evidence: {item.evidence}; existing_ref: "
                                f"{item.existing_ref or 'none'}; resolution: "
                                f"{item.required_resolution})"
                            )
                            for item in review.missing_dependencies
                        )
                        attempts.append(
                            _attempt(
                                attempt_number,
                                review_trace_id,
                                "repair",
                                repair_feedback,
                                review_meta,
                            )
                        )
                        proposal = None
                        bundle = None
                        compiled = None
                        _report_progress(
                            progress,
                            "repairing",
                            "The dependency review found a material omission; the model will revise the proposal.",
                            attempt_number,
                        )
                        continue
                    attempts.append(
                        _attempt(
                            attempt_number,
                            review_trace_id,
                            "accepted",
                            review.summary
                            + (
                                " Retained dependency equivalences: "
                                + "; ".join(review_suppressions)
                                if review_suppressions
                                else ""
                            ),
                            review_meta,
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
                attempts.append(_attempt(attempt_number, trace_id, "repair", repair_feedback, meta))
                proposal = None
                bundle = None
                compiled = None
                _report_progress(
                    progress,
                    "repairing",
                    "The compiler found an invalid or unsupported reference; the model will revise the proposal.",
                    attempt_number,
                )
            except (ValueError, GeneralCompilationError) as exc:
                repair_feedback = str(exc)
                diagnostics = [{"severity": "error", "code": "validation", "message": str(exc)}]
                attempts.append(_attempt(attempt_number, trace_id, "repair", str(exc), meta))
                proposal = None
                bundle = None
                compiled = None
                _report_progress(
                    progress,
                    "repairing",
                    "The typed proposal did not validate; the model will revise it from the retained error.",
                    attempt_number,
                )
            except Exception as exc:
                concise_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                diagnostics = [
                    {
                        "severity": "error",
                        "code": "provider",
                        "message": f"General authoring provider failed: {concise_error}",
                    }
                ]
                attempts.append(_attempt(attempt_number, trace_id, "provider_error", diagnostics[0]["message"], meta))
                if _is_terminal_provider_error(exc):
                    break
                repair_feedback = (
                    "Return one complete native V2 proposal envelope matching the supplied schema."
                )
                _report_progress(
                    progress,
                    "repairing",
                    "The response was incomplete; the model will return one complete typed proposal.",
                    attempt_number,
                )

        if (
            bundle is None
            and compiled is None
            and repair_feedback
            and not diagnostics
        ):
            diagnostics = [
                {
                    "severity": "error",
                    "code": "repair_exhausted",
                    "message": repair_feedback,
                }
            ]

        if bundle is not None and compiled is not None:
            status = "needs_input" if diagnostics else "ready_for_review"
            summary = (
                f"Generated {bundle.scenario.title}. Coverage resolved "
                f"{len(compiled.coverage.items)} requested behaviors; "
                f"{len(compiled.coverage.blocking_request_ids)} block approval."
            )
            proposal_payload: dict[str, object] | None = bundle.model_dump(mode="json")
            coverage_payload: dict[str, object] | None = compiled.coverage.model_dump(mode="json")
            graph_payload: dict[str, object] | None = compiled.configuration_graph
        elif isinstance(current.get("proposal"), dict) and attempts and all(
            item["status"] == "provider_error" for item in attempts
        ):
            status = str(current["status"])
            summary = "The provider failed, so the prior retained proposal was preserved."
            proposal_payload = cast(dict[str, object], current["proposal"])
            coverage_payload = cast(dict[str, object] | None, current.get("coverage"))
            graph_payload = cast(dict[str, object] | None, current.get("configuration_graph"))
            diagnostics = cast(list[dict[str, str]], current.get("diagnostics", []))
        else:
            status = "needs_input"
            summary = "No valid separated proposal was produced; revise the request using the diagnostics."
            proposal_payload = None
            coverage_payload = None
            graph_payload = None
        assistant_summary = " ".join([summary, *[item["message"] for item in diagnostics]])
        _report_progress(
            progress,
            "retaining",
            "Saving the retained result, diagnostics, and any editable typed configuration.",
            None,
        )
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
                "configuration_graph": graph_payload,
                "diagnostics": diagnostics,
                "approval": None,
                "updated_at": now_iso(),
            },
        )

    def edit_proposal(
        self,
        draft_id: str,
        *,
        expected_revision: int,
        edit_id: str,
        proposal: (
            GeneralSimulationProposalV1
            | AuthoredSimulationProposalV2
            | AuthoredSimulationBundleV2
        ),
    ) -> dict[str, object]:
        current = self.store.get(draft_id)
        target_kind = current.get("target_kind")
        materialization_corrections: list[str] = []
        if isinstance(proposal, AuthoredSimulationProposalV2):
            scenario, materialization_corrections = (
                materialize_unambiguous_contract_references(proposal.scenario)
            )
            proposal = proposal.model_copy(update={"scenario": scenario})
            proposal = materialize_authored_bundle_v2(
                proposal, run_id=f"{draft_id}_run"
            )
        elif isinstance(proposal, AuthoredSimulationBundleV2):
            scenario, materialization_corrections = (
                materialize_unambiguous_contract_references(proposal.scenario)
            )
            if materialization_corrections:
                proposal = proposal.model_copy(
                    update={
                        "scenario": scenario,
                        "default_run": proposal.default_run.model_copy(
                            update={"scenario_digest": scenario.digest}
                        ),
                    }
                )
        if target_kind == "general_world_v2" and not isinstance(
            proposal, AuthoredSimulationBundleV2
        ):
            raise ValueError("V2 drafts require a separated authored bundle")
        if target_kind == "general_world_v1" and not isinstance(
            proposal, GeneralSimulationProposalV1
        ):
            raise ValueError("historical V1 drafts require a V1 proposal")
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
        if isinstance(proposal, AuthoredSimulationBundleV2):
            compiled_v2 = compile_general_simulation_v2(
                proposal.scenario, proposal.default_run
            )
            diagnostics = _diagnostics_v2(proposal, compiled_v2)
            coverage = compiled_v2.coverage
            configuration_graph = compiled_v2.configuration_graph
        else:
            compiled_v1 = compile_general_simulation(proposal)
            diagnostics = _diagnostics(proposal, compiled_v1)
            coverage = compiled_v1.coverage
            configuration_graph = compiled_v1.configuration_graph
        status = "needs_input" if diagnostics else "ready_for_review"
        summary = "Saved the typed general-world proposal without a model call."
        if materialization_corrections:
            summary += " Trusted compiler materializations: " + "; ".join(
                materialization_corrections
            )
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
                "coverage": coverage.model_dump(mode="json"),
                "configuration_graph": configuration_graph,
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
        if isinstance(compiled, CompiledGeneralSimulationV2):
            bundle = AuthoredSimulationBundleV2.model_validate(current["proposal"])
            diagnostics = _diagnostics_v2(bundle, compiled)
        else:
            diagnostics = _diagnostics(compiled.proposal, compiled)
        if diagnostics or not compiled.coverage.approvable:
            raise GeneralCompilationError("general proposal has blocking diagnostics or coverage")
        if isinstance(compiled, CompiledGeneralSimulationV2):
            approval = {
                "approved_from_revision": expected_revision,
                "proposal_kind": "general_world_v2",
                "bundle_digest": bundle.digest,
                "scenario_digest": compiled.scenario_digest,
                "run_spec_digest": compiled.run_spec_digest,
                "registry_digest": compiled.registry_digest,
                "world_spec_digest": sha256(
                    compiled.world_spec.model_dump_json().encode()
                ).hexdigest(),
                "approved_at": now_iso(),
            }
        else:
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

    def approved_compile(
        self, draft_id: str
    ) -> CompiledGeneralSimulationV1 | CompiledGeneralSimulationV2:
        current = self.store.get(draft_id)
        approval = current.get("approval")
        if current.get("status") != "approved" or not isinstance(approval, dict):
            raise GeneralCompilationError("draft must be approved before execution")
        compiled = self.compile(current)
        if not compiled.coverage.approvable:
            raise GeneralCompilationError(
                "approved draft no longer has complete required execution coverage"
            )
        if isinstance(compiled, CompiledGeneralSimulationV2):
            bundle = AuthoredSimulationBundleV2.model_validate(current["proposal"])
            if approval.get("bundle_digest") != bundle.digest:
                raise GeneralCompilationError("approval no longer matches authored bundle")
            if approval.get("scenario_digest") != compiled.scenario_digest:
                raise GeneralCompilationError("approval no longer matches scenario")
            if approval.get("run_spec_digest") != compiled.run_spec_digest:
                raise GeneralCompilationError("approval no longer matches run")
        elif approval.get("proposal_digest") != compiled.proposal_digest:
            raise GeneralCompilationError("approval no longer matches proposal")
        if approval.get("registry_digest") != compiled.registry_digest:
            raise GeneralCompilationError("approval no longer matches installed registry")
        return compiled
