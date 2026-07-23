"""Sequential, evidence-bound LLM narration for completed live runs."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from importlib import resources
import json
from typing import Any, cast

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field
import yaml


NARRATOR_TASK = "cybernetic_turn_narration"
NARRATOR_MAX_BUDGET = 0.02
NARRATOR_MAX_TOKENS = 256
NARRATOR_REASONING_EFFORT = "low"

StructuredCall = Callable[..., tuple[Any, Any]]
_FORBID = ConfigDict(extra="forbid", strict=True)


class TurnNarration(BaseModel):
    """One bounded natural-language account with explicit causal provenance."""

    model_config = _FORBID

    narrative: str = Field(min_length=1, max_length=600)
    source_event_ids: list[str] = Field(min_length=1)


def narrate_live_turns(
    document: Mapping[str, object],
    *,
    model: str,
    trace_id_prefix: str,
    structured_call: StructuredCall | None = None,
) -> dict[str, object]:
    """Narrate each retained activation in order without giving the narrator authority.

    The narrator sees only analyst-visible fields.  It returns evidence IDs that
    must be drawn from that turn, making a fluent account step down to exact
    retained events rather than become another world model.
    """
    turns = _turn_inputs(document)
    if not turns:
        return {
            "status": "unavailable",
            "reason": "the completed run retained no activations to narrate",
            "model_calls": 0,
            "cost": 0.0,
            "turns": [],
            "calls": [],
        }

    call = structured_call or _resolve_structured_call()
    prior: list[dict[str, object]] = []
    narrated: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    total_cost = 0.0
    for index, turn in enumerate(turns, start=1):
        system, user = _render_prompt(turn=turn, prior=prior)
        trace_id = f"{trace_id_prefix}/narrator/turn/{turn['activation']}"
        try:
            parsed, meta = call(
                model,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_model=TurnNarration,
                task=NARRATOR_TASK,
                trace_id=trace_id,
                max_budget=NARRATOR_MAX_BUDGET,
                max_tokens=NARRATOR_MAX_TOKENS,
                reasoning_effort=NARRATOR_REASONING_EFFORT,
            )
            narration = TurnNarration.model_validate(
                parsed.model_dump(mode="json")
                if isinstance(parsed, BaseModel)
                else parsed
            )
            events = cast(list[dict[str, object]], turn["events"])
            allowed_ids = {str(event["event_id"]) for event in events}
            if not set(narration.source_event_ids) <= allowed_ids:
                raise ValueError("narrator cited an event outside its current turn")
            cost = _observed_cost(meta)
            total_cost += cost
            record = {
                "turn": index,
                "activation": turn["activation"],
                "person": turn["person"],
                "logical_time": turn["logical_time"],
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
                    "cost": cost,
                    "cost_source": str(getattr(meta, "cost_source", "unavailable")),
                }
            )
        except Exception as error:
            calls.append(
                {
                    "status": "failed",
                    "trace_id": trace_id,
                    "model": model,
                    "task": NARRATOR_TASK,
                    "cost": 0.0,
                    "cost_source": "unavailable",
                    "error_type": type(error).__name__,
                    "error_message": str(error),
                }
            )
            return {
                "status": "unavailable",
                "reason": "live turn narration stopped before the run could be fully narrated",
                "model_calls": len(calls),
                "cost": total_cost,
                "turns": narrated,
                "calls": calls,
            }
    return {
        "status": "completed",
        "model_calls": len(calls),
        "cost": total_cost,
        "turns": narrated,
        "calls": calls,
    }


def reference_narration() -> dict[str, object]:
    """Truthful marker for a zero-cost run that intentionally called no narrator."""
    return {
        "status": "not_requested",
        "reason": "turn narration is created only for live LLM runs",
        "model_calls": 0,
        "cost": 0.0,
        "turns": [],
        "calls": [],
    }


def _turn_inputs(document: Mapping[str, object]) -> list[dict[str, object]]:
    timeline = _list_of_mappings(document.get("timeline"))
    traces = _list_of_mappings(document.get("traces"))
    events_by_activation: dict[str, list[dict[str, object]]] = {}
    for event in timeline:
        activation = event.get("activation")
        if isinstance(activation, str):
            events_by_activation.setdefault(activation, []).append(
                {
                    key: event[key]
                    for key in ("event_id", "kind", "summary", "logical_time", "state_revision")
                    if key in event
                }
            )
    turns: list[dict[str, object]] = []
    for trace in traces:
        activation = trace.get("activation")
        person = trace.get("person")
        logical_time = trace.get("logical_time")
        if not isinstance(activation, str) or not isinstance(person, str) or not isinstance(logical_time, int):
            continue
        events = events_by_activation.get(activation, [])
        if not events:
            # A silent activation is still a turn, but it needs a retained anchor.
            events = [{"event_id": f"{activation}:silence", "kind": "no_action", "summary": "No action was committed during this activation.", "logical_time": logical_time, "state_revision": None}]
        turns.append(
            {
                "activation": activation,
                "person": person,
                "logical_time": logical_time,
                "events": events,
                "agent_trace": {
                    key: trace[key]
                    for key in ("orientation", "actions", "observations", "status")
                    if key in trace
                },
            }
        )
    return sorted(
        turns,
        key=lambda item: (cast(int, item["logical_time"]), str(item["activation"])),
    )


def _list_of_mappings(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, Mapping)]


def _render_prompt(
    *, turn: Mapping[str, object], prior: Sequence[Mapping[str, object]],
) -> tuple[str, str]:
    raw = resources.files("cybernetic_influence.active_runtime").joinpath(
        "prompts/turn_narrator.yaml"
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
            turn=turn,
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
