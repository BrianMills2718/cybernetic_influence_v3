"""Sequential, evidence-bound LLM narration for completed live runs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from importlib import resources
import json
from typing import Any, cast

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field
import yaml


NARRATOR_TASK = "cybernetic_causal_moment_narration"
NARRATOR_MAX_BUDGET = 0.02
NARRATOR_MAX_TOKENS = 384
NARRATOR_REASONING_EFFORT = "low"

StructuredCall = Callable[..., tuple[Any, Any]]
_FORBID = ConfigDict(extra="forbid", strict=True)


class CausalMomentNarration(BaseModel):
    """One bounded natural-language account with explicit causal provenance."""

    model_config = _FORBID

    narrative: str = Field(min_length=1, max_length=360)
    source_event_ids: list[str] = Field(min_length=1, max_length=4)


def narrate_live_moments(
    document: Mapping[str, object],
    *,
    model: str,
    trace_id_prefix: str,
    max_total_cost: float = 0.74,
    reasoning_effort: str = NARRATOR_REASONING_EFFORT,
    structured_call: StructuredCall | None = None,
) -> dict[str, object]:
    """Narrate each retained causal moment without giving the narrator authority.

    The narrator sees only analyst-visible fields.  It returns evidence IDs that
    must be drawn from that moment, making a fluent account step down to exact
    retained events rather than become another world model.
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

    call = structured_call or _resolve_structured_call()
    prior: list[dict[str, object]] = []
    narrated: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    total_cost = 0.0
    for index, moment in enumerate(moments, start=1):
        remaining = max_total_cost - total_cost
        if remaining + 1e-12 < NARRATOR_MAX_BUDGET:
            return {
                "status": "unavailable",
                "reason": (
                    f"narration stopped before moment {index}: remaining "
                    f"authorization ${remaining:.8f} cannot fit the "
                    f"${NARRATOR_MAX_BUDGET:.8f} narrator call ceiling"
                ),
                "failure_boundary": {
                    "kind": "budget_exhausted",
                    "next_moment": index,
                    "remaining_authorization": max(0.0, remaining),
                    "required_call_ceiling": NARRATOR_MAX_BUDGET,
                },
                "model_calls": len(calls),
                "cost": total_cost,
                "moments": narrated,
                "calls": calls,
            }
        system, user = _render_prompt(moment=moment, prior=prior)
        trace_id = (
            f"{trace_id_prefix}/narrator/moment/{moment['activation']}"
        )
        meta: object | None = None
        cost = 0.0
        cost_source = "unavailable"
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
                reasoning_effort=reasoning_effort,
            )
            cost = _observed_cost(meta)
            cost_source = str(getattr(meta, "cost_source", "unavailable"))
            total_cost += cost
            if cost > NARRATOR_MAX_BUDGET:
                raise ValueError(
                    f"narrator call cost {cost:.8f} exceeds per-call ceiling "
                    f"{NARRATOR_MAX_BUDGET:.8f}"
                )
            if total_cost > max_total_cost:
                raise ValueError(
                    f"observed narration cost {total_cost:.8f} exceeds remaining "
                    f"authorization {max_total_cost:.8f}"
                )
            narration = CausalMomentNarration.model_validate(
                parsed.model_dump(mode="json")
                if isinstance(parsed, BaseModel)
                else parsed
            )
            events = cast(list[dict[str, object]], moment["events"])
            allowed_ids = {str(event["event_id"]) for event in events}
            if not set(narration.source_event_ids) <= allowed_ids:
                raise ValueError(
                    "narrator cited an event outside its current causal moment"
                )
            record = {
                "moment": index,
                "activation": moment["activation"],
                "participants": moment["participants"],
                "causal_time": moment["causal_time"],
                "causal_timestamp": moment["causal_timestamp"],
                "logical_time": moment["logical_time"],
                "narrative": narration.narrative,
                "source_event_ids": narration.source_event_ids,
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
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            return {
                "status": "unavailable",
                "reason": "live causal-moment narration stopped before the run could be fully narrated",
                "model_calls": len(calls),
                "cost": total_cost,
                "moments": narrated,
                "calls": calls,
            }
    return {
        "status": "completed",
        "model_calls": len(calls),
        "cost": total_cost,
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
        "moments": [],
        "calls": [],
    }


def _moment_inputs(document: Mapping[str, object]) -> list[dict[str, object]]:
    timeline = _list_of_mappings(document.get("timeline"))
    traces = _list_of_mappings(document.get("traces"))
    projected_moments = _list_of_mappings(document.get("moments"))
    moment_by_activation = {
        str(moment["activation"]): moment
        for moment in projected_moments
        if isinstance(moment.get("activation"), str)
    }
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
    for activation, activation_traces in traces_by_activation.items():
        logical_time = activation_traces[0]["logical_time"]
        projected_moment = moment_by_activation.get(activation)
        causal_time = (
            projected_moment.get("causal_time")
            if projected_moment is not None
            else activation_traces[0].get("causal_time")
        )
        causal_timestamp = (
            projected_moment.get("causal_timestamp")
            if projected_moment is not None
            else activation_traces[0].get("causal_timestamp")
        )
        if not isinstance(causal_time, int) or not isinstance(
            causal_timestamp, str
        ):
            raise ValueError(
                f"causal moment {activation!r} lacks a valid causal timestamp"
            )
        events = events_by_activation.get(activation, [])
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
                "participants": [trace["person"] for trace in activation_traces],
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


def _render_prompt(
    *, moment: Mapping[str, object], prior: Sequence[Mapping[str, object]],
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
            prior=list(prior),
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
