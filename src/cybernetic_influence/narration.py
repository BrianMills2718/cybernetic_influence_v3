"""Sequential, evidence-bound LLM narration for completed live runs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from hashlib import sha256
from importlib import resources
import json
from typing import Any, cast

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field
import yaml


NARRATOR_TASK = "cybernetic_causal_moment_narration"
NARRATOR_MAX_BUDGET = 0.025
# The analyst card needs one compact account; a bounded completion prevents a
# provider-accepted but locally overlong response from breaking the sequence.
# One response now contains a compact timeline account and the readable
# evidence-bound passage. Provider cost is retained as evidence but does not
# terminate a valid account after a response has been returned.
NARRATOR_MAX_TOKENS = 640
NARRATOR_TIMEOUT_SECONDS = 180
NARRATOR_REASONING_EFFORT = "low"
NARRATOR_PROMPT_VERSION = "causal_moment_narrator/v4"
_LEGACY_V3_PROMPT_VERSION = "causal_moment_narrator/v3"
NARRATIVE_VERSION = 3

StructuredCall = Callable[..., tuple[Any, Any]]
_FORBID = ConfigDict(extra="forbid", strict=True)


class NarrativeParagraph(BaseModel):
    """One detailed prose paragraph; provenance is assigned by the simulator."""

    model_config = _FORBID

    text: str = Field(min_length=1, max_length=900)


class CausalMomentNarration(BaseModel):
    """Dual-level natural-language account; the simulator retains provenance."""

    model_config = _FORBID

    concise_narrative: str = Field(min_length=1, max_length=360)
    detailed_paragraphs: list[NarrativeParagraph] = Field(min_length=1, max_length=3)


def narrate_live_moments(
    document: Mapping[str, object],
    *,
    model: str,
    trace_id_prefix: str,
    max_total_cost: float = 0.74,
    max_calls: int | None = None,
    reasoning_effort: str = NARRATOR_REASONING_EFFORT,
    structured_call: StructuredCall | None = None,
) -> dict[str, object]:
    """Narrate each retained causal moment without giving the narrator authority.

    The narrator sees only analyst-visible fields and returns prose only. The
    simulator records the exact context supplied to each call, so provenance is
    not delegated to a model reproducing arbitrary identifiers.
    """
    moments = _moment_inputs(document)
    if not moments:
        return {
            "status": "unavailable",
            "reason": "the completed run retained no causal moments to narrate",
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        }

    required_calls = len(moments)
    if max_calls is not None and required_calls > max_calls:
        return {
            "status": "unavailable",
            "reason": (
                "narration was not started because the retained run requires "
                f"{required_calls} narrator calls but its configured limit is "
                f"{max_calls}"
            ),
            "failure_boundary": {
                "kind": "call_limit_preflight",
                "required_calls": required_calls,
                "configured_max_calls": max_calls,
            },
            "model_calls": 0,
            "cost": 0.0,
            "moments": [],
            "calls": [],
        }
    call = structured_call or _resolve_structured_call()
    run_id = _required_run_id(document)
    prior: list[dict[str, object]] = []
    narrated: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    total_cost = 0.0
    for index, moment in enumerate(moments, start=1):
        context = _evidence_context(
            run_id=run_id,
            moment=moment,
            moment_number=index,
            prior=prior,
        )
        system, user = _render_prompt(
            moment=moment,
            prior_summaries=_prior_summaries(prior),
        )
        trace_id = (
            f"{trace_id_prefix}/narrator/moment/{moment['activation']}"
        )
        meta: object | None = None
        cost = 0.0
        cost_source = "unavailable"
        cost_covers_all_attempts = False
        try:
            parsed, meta = call(
                model,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                model_justification=(
                    "Use the run-configured narration model to generate the "
                    "bounded analyst-facing causal-moment account."
                ),
                response_model=CausalMomentNarration,
                task=NARRATOR_TASK,
                trace_id=trace_id,
                max_budget=NARRATOR_MAX_BUDGET,
                max_tokens=NARRATOR_MAX_TOKENS,
                timeout=NARRATOR_TIMEOUT_SECONDS,
                reasoning_effort=reasoning_effort,
            )
            cost = _observed_cost(meta)
            cost_source = str(getattr(meta, "cost_source", "unavailable"))
            cost_covers_all_attempts = _cost_covers_all_attempts(meta)
            total_cost += cost
            narration = CausalMomentNarration.model_validate(
                parsed.model_dump(mode="json")
                if isinstance(parsed, BaseModel)
                else parsed
            )
            record = {
                "narrative_version": NARRATIVE_VERSION,
                "narrative_record_id": context["narrative_record_id"],
                "moment": index,
                "activation": moment["activation"],
                "participants": moment["participants"],
                "causal_time": moment["causal_time"],
                "causal_timestamp": moment["causal_timestamp"],
                "logical_time": moment["logical_time"],
                "narrative": narration.concise_narrative,
                "concise_narrative": narration.concise_narrative,
                "evidence_context": context,
                "concise_evidence_context_id": context["context_id"],
                "detailed_paragraphs": [
                    {
                        "text": paragraph.text,
                        "evidence_context_id": context["context_id"],
                    }
                    for paragraph in narration.detailed_paragraphs
                ],
            }
            narrated.append(record)
            prior.append(record)
            calls.append(
                {
                    "status": "completed",
                    "trace_id": trace_id,
                    "model": model,
                    "task": NARRATOR_TASK,
                    "reasoning_effort": reasoning_effort,
                    "cost": cost,
                    "cost_source": cost_source,
                    "cost_covers_all_attempts": cost_covers_all_attempts,
                }
            )
        except Exception as error:
            calls.append(
                {
                    "status": "failed",
                    "trace_id": trace_id,
                    "model": model,
                    "task": NARRATOR_TASK,
                    "reasoning_effort": reasoning_effort,
                    "cost": cost if meta is not None else None,
                    "cost_source": cost_source,
                    "cost_covers_all_attempts": cost_covers_all_attempts,
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            return {
                "status": "unavailable",
                "reason": "live causal-moment narration stopped before the run could be fully narrated",
                "model_calls": len(calls),
                "cost": total_cost,
                "cost_fully_observable": all(
                    item.get("cost_covers_all_attempts") is True
                    for item in calls
                ),
                "moments": narrated,
                "calls": calls,
            }
    return {
        "status": "completed",
        "model_calls": len(calls),
        "cost": total_cost,
        "cost_fully_observable": all(
            item.get("cost_covers_all_attempts") is True for item in calls
        ),
        "moments": narrated,
        "calls": calls,
    }


def reference_narration() -> dict[str, object]:
    """Truthful marker for a zero-cost run that intentionally called no narrator."""
    return {
        "status": "not_requested",
        "reason": "causal-moment narration is created only for live LLM runs",
        "model_calls": 0,
        "cost": 0.0,
        "cost_fully_observable": True,
        "moments": [],
        "calls": [],
    }


def _moment_inputs(document: Mapping[str, object]) -> list[dict[str, object]]:
    timeline = _list_of_mappings(document.get("timeline"))
    timeline_by_id = {
        str(event["event_id"]): event
        for event in timeline
        if isinstance(event.get("event_id"), str)
    }
    traces = _list_of_mappings(document.get("traces"))
    projected_moments = _list_of_mappings(document.get("moments"))
    events_by_activation: dict[str, list[dict[str, object]]] = {}
    for event in timeline:
        activation = event.get("activation")
        if isinstance(activation, str):
            events_by_activation.setdefault(activation, []).append(
                {
                    key: event[key]
                    for key in (
                        "event_id",
                        "kind",
                        "summary",
                        "logical_time",
                        "state_revision",
                        "mechanism_id",
                        "mechanism_kind",
                        "mechanism_description",
                        "transition_contract",
                        "representation_abstraction",
                        "representation_known_omissions",
                    )
                    if key in event
                }
            )
    traces_by_activation: dict[str, list[dict[str, object]]] = {}
    for trace in traces:
        activation = trace.get("activation")
        person = trace.get("person")
        logical_time = trace.get("logical_time")
        if not isinstance(activation, str) or not isinstance(person, str) or not isinstance(logical_time, int):
            continue
        traces_by_activation.setdefault(activation, []).append(trace)
    moments: list[dict[str, object]] = []
    for projected_moment in projected_moments:
        activation = projected_moment.get("activation")
        logical_time = projected_moment.get("logical_time")
        causal_time = projected_moment.get("causal_time")
        causal_timestamp = projected_moment.get("causal_timestamp")
        participants = projected_moment.get("participants")
        if (
            not isinstance(activation, str)
            or not isinstance(logical_time, int)
            or not isinstance(causal_time, int)
            or not isinstance(causal_timestamp, str)
            or not isinstance(participants, list)
            or not all(isinstance(item, str) for item in participants)
        ):
            raise ValueError(
                "projected causal moment lacks a valid activation/time contract"
            )
        activation_traces = traces_by_activation.get(activation, [])
        projected_event_ids = projected_moment.get("event_ids")
        selected_events = (
            [
                timeline_by_id[event_id]
                for event_id in projected_event_ids
                if isinstance(event_id, str) and event_id in timeline_by_id
            ]
            if isinstance(projected_event_ids, list)
            else []
        )
        events: list[dict[str, object]] = [
            {
                key: event[key]
                for key in (
                    "event_id",
                    "kind",
                    "summary",
                    "logical_time",
                    "state_revision",
                    "mechanism_id",
                    "mechanism_kind",
                    "mechanism_description",
                    "transition_contract",
                    "representation_abstraction",
                    "representation_known_omissions",
                )
                if key in event
            }
            for event in selected_events
        ]
        if not events:
            events = list(events_by_activation.get(activation, []))
        if not events:
            private_updates = [
                str(trace["person"])
                for trace in activation_traces
                if trace.get("private_state_updated") is True
            ]
            private_summary = (
                "Protected private state changed for "
                f"{', '.join(private_updates)}."
                if private_updates
                else "Protected private state did not change."
            )
            events = [{
                "event_id": f"{activation}:silence",
                "kind": "no_external_action",
                "summary": (
                    "No participant committed an external action or world-state "
                    f"effect during this causal moment. {private_summary}"
                ),
                "logical_time": logical_time,
                "state_revision": None,
            }]
        moments.append(
            {
                "activation": activation,
                "participants": participants,
                "causal_time": causal_time,
                "causal_timestamp": causal_timestamp,
                "logical_time": logical_time,
                "events": events,
                "participant_traces": [
                    {
                        key: trace[key]
                        for key in (
                            "person",
                            "participant_kind",
                            "activation_causes",
                            "scheduled_update_before",
                            "update_schedule",
                            "model_call_count",
                            "private_state_updated",
                            "orientation",
                            "actions",
                            "observations",
                            "status",
                        )
                        if key in trace
                    }
                    for trace in activation_traces
                ],
            }
        )
    return sorted(
        moments,
        key=lambda item: cast(int, item["causal_time"]),
    )


def _list_of_mappings(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def validate_retained_narration(document: Mapping[str, object]) -> None:
    """Fail loudly if a v3 retained narrative no longer matches its context.

    v1/v2 records remain readable because they predate simulator-owned context.
    A completed v3 sequence must be wholly reconstructable from this run's
    retained analyst-visible trace and its earlier retained narrative records.
    """
    narration = document.get("narration")
    if not isinstance(narration, Mapping) or narration.get("status") != "completed":
        return
    records = narration.get("moments")
    if not isinstance(records, list):
        raise ValueError("completed narration lacks retained moments")
    v3_records = [
        record for record in records
        if isinstance(record, Mapping) and record.get("narrative_version") == NARRATIVE_VERSION
    ]
    if not v3_records:
        return
    if len(v3_records) != len(records):
        raise ValueError("retained narration mixes v3 and legacy moment records")
    moments = _moment_inputs(document)
    if len(records) != len(moments):
        raise ValueError("retained v3 narration does not cover every causal moment")
    run_id = _required_run_id(document)
    prior: list[dict[str, object]] = []
    for index, (raw_record, moment) in enumerate(zip(records, moments, strict=True), start=1):
        if not isinstance(raw_record, Mapping):
            raise ValueError("retained v3 narration has a malformed moment record")
        record = dict(raw_record)
        _validate_v3_record(
            record=record,
            run_id=run_id,
            moment=moment,
            moment_number=index,
            prior=prior,
        )
        prior.append(record)


def _required_run_id(document: Mapping[str, object]) -> str:
    run_id = document.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("narration requires a retained run ID")
    return run_id


def _evidence_context(
    *,
    run_id: str,
    moment: Mapping[str, object],
    moment_number: int,
    prior: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    record_id = _narrative_record_id(run_id, moment_number)
    material = _context_material(run_id=run_id, moment=moment, prior=prior)
    events = cast(list[dict[str, object]], moment["events"])
    return {
        "context_version": 2,
        "context_id": _context_id(run_id, moment_number),
        "run_id": run_id,
        "narrative_record_id": record_id,
        "current_event_ids": [str(event["event_id"]) for event in events],
        "prior_narrative_record_ids": [
            _required_narrative_record_id(record) for record in prior
        ],
        "prompt_version": NARRATOR_PROMPT_VERSION,
        "context_digest": _context_digest(material),
    }


def _validate_v3_record(
    *,
    record: Mapping[str, object],
    run_id: str,
    moment: Mapping[str, object],
    moment_number: int,
    prior: Sequence[Mapping[str, object]],
) -> None:
    if record.get("moment") != moment_number or record.get("activation") != moment["activation"]:
        raise ValueError("retained v3 narration moment does not match the causal trace")
    paragraphs = record.get("detailed_paragraphs")
    if not isinstance(paragraphs, list):
        raise ValueError("retained v3 narration paragraphs are malformed")
    try:
        CausalMomentNarration.model_validate({
            "concise_narrative": record.get("concise_narrative"),
            "detailed_paragraphs": [
                {"text": paragraph.get("text")}
                for paragraph in paragraphs
                if isinstance(paragraph, Mapping)
            ],
        })
    except Exception as error:
        raise ValueError("retained v3 narration prose is malformed") from error
    context = record.get("evidence_context")
    if not isinstance(context, Mapping):
        raise ValueError("retained v3 narration lacks an evidence context")
    expected = (
        _legacy_v3_evidence_context(
            run_id=run_id,
            moment=moment,
            moment_number=moment_number,
            prior=prior,
        )
        if context.get("context_version") == 1
        else _evidence_context(
            run_id=run_id,
            moment=moment,
            moment_number=moment_number,
            prior=prior,
        )
    )
    if dict(context) != expected:
        raise ValueError("retained v3 narration evidence context is corrupt")
    context_id = expected["context_id"]
    if record.get("narrative_record_id") != expected["narrative_record_id"]:
        raise ValueError("retained v3 narration record ID is corrupt")
    if record.get("concise_evidence_context_id") != context_id:
        raise ValueError("retained v3 concise context reference is corrupt")
    if any(
        not isinstance(paragraph, Mapping)
        or paragraph.get("evidence_context_id") != context_id
        for paragraph in paragraphs
    ):
        raise ValueError("retained v3 detailed context reference is corrupt")


def _context_material(
    *, run_id: str, moment: Mapping[str, object], prior: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "prompt_version": NARRATOR_PROMPT_VERSION,
        "current_moment": dict(moment),
        "prior_narrative_summaries": _prior_summaries(prior),
    }


def _legacy_v3_evidence_context(
    *,
    run_id: str,
    moment: Mapping[str, object],
    moment_number: int,
    prior: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Reconstruct pre-compaction V3 evidence without changing its meaning."""
    material = {
        "run_id": run_id,
        "prompt_version": _LEGACY_V3_PROMPT_VERSION,
        "current_moment": dict(moment),
        "prior_narratives": [dict(record) for record in prior],
    }
    events = cast(list[dict[str, object]], moment["events"])
    return {
        "context_version": 1,
        "context_id": _context_id(run_id, moment_number),
        "run_id": run_id,
        "narrative_record_id": _narrative_record_id(run_id, moment_number),
        "current_event_ids": [str(event["event_id"]) for event in events],
        "prior_narrative_record_ids": [
            _required_narrative_record_id(record) for record in prior
        ],
        "prompt_version": _LEGACY_V3_PROMPT_VERSION,
        "context_digest": _context_digest(material),
    }


def _prior_summaries(
    prior: Sequence[Mapping[str, object]],
) -> list[dict[str, str]]:
    """Keep continuity bounded while retaining full records outside the prompt."""
    return [
        {
            "narrative_record_id": _required_narrative_record_id(record),
            "concise_narrative": _required_concise_narrative(record),
        }
        for record in prior
    ]


def _context_digest(material: Mapping[str, object]) -> str:
    encoded = json.dumps(
        material,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _context_id(run_id: str, moment_number: int) -> str:
    return f"narration_context:{run_id}:{moment_number:04d}"


def _narrative_record_id(run_id: str, moment_number: int) -> str:
    return f"narrative_moment:{run_id}:{moment_number:04d}"


def _required_narrative_record_id(record: Mapping[str, object]) -> str:
    value = record.get("narrative_record_id")
    if not isinstance(value, str) or not value:
        raise ValueError("prior v3 narration record lacks a record ID")
    return value


def _required_concise_narrative(record: Mapping[str, object]) -> str:
    value = record.get("concise_narrative")
    if not isinstance(value, str) or not value:
        raise ValueError("prior narration record lacks a concise account")
    return value


def _render_prompt(
    *, moment: Mapping[str, object], prior_summaries: Sequence[Mapping[str, str]],
) -> tuple[str, str]:
    raw = resources.files("cybernetic_influence.active_runtime").joinpath(
        "prompts/causal_moment_narrator.yaml"
    ).read_text(encoding="utf-8")
    template = yaml.safe_load(raw)
    if not isinstance(template, dict):
        raise ValueError("turn narrator prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(
        value, ensure_ascii=False, sort_keys=True
    )
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(
            moment=moment,
            prior_summaries=list(prior_summaries),
        ),
    )


def _resolve_structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as error:
        raise RuntimeError("live turn narration requires the shared llm_client") from error
    return cast(StructuredCall, call_llm_structured)


def _observed_cost(meta: object) -> float:
    raw = getattr(meta, "cost", 0.0)
    if isinstance(raw, (int, float)) and not isinstance(raw, bool) and raw >= 0:
        return float(raw)
    return 0.0


def _cost_covers_all_attempts(meta: object) -> bool:
    """Keep retry/fallback price uncertainty visible without stopping narration."""
    coverage_hint = getattr(meta, "cost_covers_all_attempts", None)
    if isinstance(coverage_hint, bool):
        return coverage_hint
    warning_records = getattr(meta, "warning_records", None)
    if not isinstance(warning_records, list):
        return getattr(meta, "cost", None) is not None
    recovered = any(
        isinstance(record, dict)
        and record.get("code") in {"LLMC_WARN_RETRY", "LLMC_WARN_FALLBACK"}
        for record in warning_records
    )
    return not recovered
