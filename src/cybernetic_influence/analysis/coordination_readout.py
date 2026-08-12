"""Operator-facing projection of one retained coordination measurement."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from cybernetic_influence.analysis.coordination_measurement import (
    COORDINATION_MEASUREMENT_SPEC,
    MeasureDefinition,
    RunMeasurementConsumer,
)

_EVENT_ID = re.compile(r"^event_[0-9]{6}$")


class _ReadModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ExactMeasureReadout(_ReadModel):
    measure_id: str
    construct_name: str
    label: str
    unit: str
    value: JsonValue
    limitations: list[str]
    source_event_ids: list[str]
    evidence_basis: Literal["embedded_citation", "required_event_kind"]


class CodedIndicatorReadout(_ReadModel):
    indicator_id: str
    construct_name: str
    label: str
    unit: str
    direction: Literal["increase", "decrease", "no_change", "unclear"]
    explanation: str
    limitations: list[str]
    source_event_ids: list[str]
    source_trace_ids: list[str]


class CoderProvenanceReadout(_ReadModel):
    label: Literal["Model interpretation"] = "Model interpretation"
    task: str
    trace_id: str
    schema_revision: int
    prompt_version: str
    model: str
    reasoning_effort: str
    max_budget: float
    observed_cost: float | None
    cost_source: str
    cost_covers_all_attempts: bool


class CoordinationMeasurementReadout(_ReadModel):
    status: Literal[
        "not_applicable", "not_measured", "measuring", "available", "invalid"
    ]
    headline: str
    explanation: str
    measurement_id: str | None = None
    exact_measures: list[ExactMeasureReadout] = Field(default_factory=list)
    coded_indicators: list[CodedIndicatorReadout] = Field(default_factory=list)
    coder_provenance: CoderProvenanceReadout | None = None
    limitations: list[str] = Field(default_factory=list)
    error_type: str | None = None


def coordination_measurement_readout(
    document: Mapping[str, object],
) -> CoordinationMeasurementReadout:
    """Validate and project analysis without changing the retained world run."""

    authoring = document.get("authoring")
    if (
        isinstance(authoring, Mapping)
        and authoring.get("template_id") == "influence_network_v1"
    ):
        return _influence_network_readout(document)
    if document.get("scenario") != "coordination_decision":
        return CoordinationMeasurementReadout(
            status="not_applicable",
            headline="No coordination assay",
            explanation="This run does not use the coordination-decision scenario.",
        )
    if document.get("coordination_measurement_status") == "running":
        return CoordinationMeasurementReadout(
            status="measuring",
            headline="The simulation completed; its analysis is finishing",
            explanation=(
                "One post-run model call is classifying the retained evidence. "
                "The world outcome is already fixed and cannot be changed by it."
            ),
        )
    failure = document.get("coordination_measurement_failure")
    payload = document.get("coordination_measurement")
    if payload is None:
        if isinstance(failure, Mapping):
            return CoordinationMeasurementReadout(
                status="invalid",
                headline="The simulation completed, but its analysis did not",
                explanation=(
                    "The world run and outcome remain valid. The post-run evidence "
                    "coding failed and may be retried without replaying the simulation."
                ),
                error_type=_optional_string(failure.get("error_type")),
            )
        return CoordinationMeasurementReadout(
            status="not_measured",
            headline="This run has not been measured",
            explanation=(
                "Reference runs make no model calls. A retained coordination assay is "
                "added only to an authorized completed live run."
            ),
        )
    try:
        measurement = RunMeasurementConsumer.model_validate(payload)
        if measurement.run_id != document.get("run_id"):
            raise ValueError("measurement belongs to a different run")
        events = _retained_events(document.get("events"))
        definitions = {
            item.measure_id: item for item in COORDINATION_MEASUREMENT_SPEC.measures
        }
        exact = [
            _exact_readout(
                definition=definitions[measure_id],
                value=value,
                events=events,
            )
            for measure_id, value in measurement.exact_values.items()
        ]
        coded = []
        for indicator in measurement.coded_indicators:
            unknown = set(indicator.source_event_ids) - set(events)
            if unknown:
                raise ValueError(
                    f"coded indicator cites unknown events: {sorted(unknown)!r}"
                )
            definition = definitions[indicator.indicator_id]
            coded.append(
                CodedIndicatorReadout(
                    indicator_id=indicator.indicator_id,
                    construct_name=definition.construct_name,
                    label=definition.label,
                    unit=definition.unit,
                    direction=indicator.direction,
                    explanation=indicator.explanation,
                    limitations=definition.limitations,
                    source_event_ids=indicator.source_event_ids,
                    source_trace_ids=indicator.source_trace_ids,
                )
            )
        call = measurement.coder_call
        return CoordinationMeasurementReadout(
            status="available",
            headline="How coordination changed across the run",
            explanation=(
                "Recorded measures come directly from the synthetic trace. Model "
                "interpretations classify only supplied retained evidence and may "
                "be disputed."
            ),
            measurement_id=measurement.measurement_id,
            exact_measures=exact,
            coded_indicators=coded,
            coder_provenance=CoderProvenanceReadout(
                task=call.task,
                trace_id=call.trace_id,
                schema_revision=call.schema_revision,
                prompt_version=call.prompt_version,
                model=call.model,
                reasoning_effort=call.reasoning_effort,
                max_budget=call.max_budget,
                observed_cost=call.observed_cost,
                cost_source=call.cost_source,
                cost_covers_all_attempts=call.cost_covers_all_attempts,
            ),
            limitations=measurement.limitations,
        )
    except (TypeError, ValueError) as error:
        return CoordinationMeasurementReadout(
            status="invalid",
            headline="The simulation completed, but its analysis is invalid",
            explanation=(
                "The retained world run and outcome remain available. This analysis "
                "cannot be used until its evidence contract is repaired."
            ),
            error_type=type(error).__name__,
        )


def _influence_network_readout(
    document: Mapping[str, object],
) -> CoordinationMeasurementReadout:
    """Project exact round evidence without claiming an inferred construct."""

    try:
        traces = document.get("traces")
        if not isinstance(traces, Sequence) or isinstance(traces, (str, bytes)):
            raise ValueError("influence-network run lacks retained traces")
        events = _retained_events(document.get("events"))
        action_events: dict[str, list[str]] = {}
        information_delivery_event_ids: list[str] = []
        decision_gate_event_ids: list[str] = []
        for event_id, event in events.items():
            actor = event.get("actor_entity_id")
            if (
                event.get("event_kind") == "action_attempted"
                and isinstance(actor, str)
            ):
                action_events.setdefault(actor, []).append(event_id)
                if actor == "network_clock":
                    decision_gate_event_ids.append(event_id)
            if event.get("event_kind") == "observation_delivered":
                representation_id = event.get("representation_id")
                if isinstance(representation_id, str) and not representation_id.startswith(
                    "round_snapshot_"
                ):
                    information_delivery_event_ids.append(event_id)

        by_round: dict[int, dict[str, object]] = {}
        delivered_by_round: dict[int, list[dict[str, object]]] = {}
        source_event_ids: list[str] = []
        action_event_indexes: dict[str, int] = {}
        for raw_trace in traces:
            if not isinstance(raw_trace, Mapping):
                continue
            person_id = raw_trace.get("person")
            logical_time = raw_trace.get("logical_time")
            if (
                raw_trace.get("participant_kind") != "person"
                or not isinstance(person_id, str)
                or not isinstance(logical_time, int)
                or isinstance(logical_time, bool)
            ):
                continue
            round_index: int | None = None
            new_messages: list[dict[str, object]] = []
            raw_observations = raw_trace.get("observations")
            observations = (
                raw_observations
                if isinstance(raw_observations, Sequence)
                and not isinstance(raw_observations, (str, bytes))
                else []
            )
            for observation in observations:
                if not isinstance(observation, Mapping):
                    continue
                content = _json_mapping(observation.get("apparent_content"))
                if content is None:
                    continue
                if content.get("document_kind") == "decision_round_snapshot":
                    candidate = content.get("round_index")
                    if isinstance(candidate, int) and not isinstance(candidate, bool):
                        round_index = candidate
                elif content.get("document_kind") == "influence_message":
                    new_messages.append(
                        {
                            "delivery_id": content.get("delivery_id"),
                            "topic": content.get("topic"),
                            "apparent_source_ref": observation.get(
                                "apparent_source_ref"
                            ),
                        }
                    )
            if round_index is None:
                continue
            raw_actions = raw_trace.get("actions")
            actions = (
                raw_actions
                if isinstance(raw_actions, Sequence)
                and not isinstance(raw_actions, (str, bytes))
                else []
            )
            payload: Mapping[str, object] | None = None
            for action in actions:
                if isinstance(action, Mapping) and isinstance(
                    action.get("payload"), Mapping
                ):
                    candidate = cast(Mapping[str, object], action["payload"])
                    if isinstance(candidate.get("stance"), str):
                        payload = candidate
                        break
            stance = payload.get("stance") if payload is not None else "defer"
            if stance not in {"support", "conditional", "defer", "oppose"}:
                raise ValueError("influence-network trace contains an invalid stance")
            round_item = by_round.setdefault(
                round_index,
                {
                    "round_index": round_index,
                    "logical_time": logical_time,
                    "counts": {
                        "support": 0,
                        "conditional": 0,
                        "defer": 0,
                        "oppose": 0,
                    },
                    "actor_reports": [],
                },
            )
            counts = cast(dict[str, int], round_item["counts"])
            counts[stance] += 1
            actor_reports = cast(list[dict[str, object]], round_item["actor_reports"])
            actor_reports.append(
                {
                    "person_id": person_id,
                    "stance": stance,
                    "reason": payload.get("reason") if payload is not None else None,
                    "source_assessment": (
                        payload.get("source_assessment") if payload is not None else None
                    ),
                    "primary_risk": (
                        payload.get("primary_risk") if payload is not None else None
                    ),
                    "blocking_dependency": (
                        payload.get("blocking_dependency")
                        if payload is not None
                        else None
                    ),
                }
            )
            if new_messages:
                delivered_by_round.setdefault(round_index, []).append(
                    {"person_id": person_id, "new_messages": new_messages}
                )
            if payload is not None:
                actor_events = action_events.get(person_id, [])
                event_index = action_event_indexes.get(person_id, 0)
                if event_index >= len(actor_events):
                    raise ValueError(
                        "influence-network trace lacks its retained stance event"
                    )
                source_event_ids.append(actor_events[event_index])
                action_event_indexes[person_id] = event_index + 1

        rounds = [by_round[index] for index in sorted(by_round)]
        if not rounds:
            raise ValueError("influence-network run has no decision-round evidence")
        outcome = document.get("outcome")
        gate = dict(outcome) if isinstance(outcome, Mapping) else {}
        evidence_ids = list(dict.fromkeys(source_event_ids))
        exact = [
            ExactMeasureReadout(
                measure_id="influence_round_stance_trajectory",
                construct_name="coordination_readiness",
                label="Decision-round trajectory",
                unit="actor-reported stances and reasons",
                value=cast(JsonValue, rounds),
                limitations=[
                    "Stances and explanations are synthetic model outputs, not observations of people.",
                    "Actor-reported risks, source assessments, and dependencies are not validated latent constructs.",
                ],
                source_event_ids=evidence_ids,
                evidence_basis="embedded_citation",
            ),
            ExactMeasureReadout(
                measure_id="influence_final_decision_gate",
                construct_name="collective_coordination_result",
                label="Final collective decision gate",
                unit="exact authored threshold checks",
                value=cast(JsonValue, gate),
                limitations=[
                    "The decision rule is an authored institutional mechanism.",
                    "A passed or failed gate does not establish successful real-world collective action.",
                ],
                source_event_ids=(
                    decision_gate_event_ids[-1:]
                    if decision_gate_event_ids
                    else evidence_ids
                ),
                evidence_basis="embedded_citation",
            ),
            ExactMeasureReadout(
                measure_id="influence_observation_topology",
                construct_name="distributed_information_exposure",
                label="New information visible at each decision round",
                unit="delivered message-recipient records",
                value=cast(
                    JsonValue,
                    [
                        {
                            "round_index": index,
                            "recipients": delivered_by_round[index],
                        }
                        for index in sorted(delivered_by_round)
                    ],
                ),
                limitations=[
                    "Delivery establishes availability to an actor, not belief, persuasion, truth, or source intent."
                ],
                source_event_ids=information_delivery_event_ids,
                evidence_basis="embedded_citation",
            ),
        ]
        return CoordinationMeasurementReadout(
            status="available",
            headline="What changed across the decision rounds",
            explanation=(
                "This readout preserves who received which messages, each person's "
                "reported assessment, and the exact collective decision gate."
            ),
            measurement_id=f"{document.get('run_id')}_influence_network_exact_v1",
            exact_measures=exact,
            limitations=[
                "This is one synthetic LLM execution and does not estimate human or institutional behavior.",
                "Without a matched comparison, the run cannot attribute a change to influence rather than other modeled causes.",
                "Trust structure is not established unless relationships and reliance pathways are explicitly represented and analyzed.",
            ],
        )
    except (TypeError, ValueError) as error:
        return CoordinationMeasurementReadout(
            status="invalid",
            headline="The simulation completed, but its round analysis is invalid",
            explanation="The retained outcome remains available, but the round evidence could not be projected.",
            error_type=type(error).__name__,
        )


def _json_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return None
    return cast(Mapping[str, object], parsed) if isinstance(parsed, Mapping) else None


def _exact_readout(
    *,
    definition: MeasureDefinition,
    value: JsonValue,
    events: Mapping[str, Mapping[str, object]],
) -> ExactMeasureReadout:
    embedded = _embedded_event_ids(value)
    unknown = set(embedded) - set(events)
    if unknown:
        raise ValueError(f"exact measure cites unknown events: {sorted(unknown)!r}")
    sources = embedded or [
        event_id
        for event_id, event in events.items()
        if event.get("event_kind") in definition.required_source_event_kinds
    ]
    return ExactMeasureReadout(
        measure_id=str(definition.measure_id),
        construct_name=definition.construct_name,
        label=definition.label,
        unit=definition.unit,
        value=value,
        limitations=definition.limitations,
        source_event_ids=sources,
        evidence_basis=(
            "embedded_citation" if embedded else "required_event_kind"
        ),
    )


def _retained_events(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("retained run lacks an event list")
    events: dict[str, Mapping[str, object]] = {}
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("retained run contains a malformed event")
        event_id = item.get("event_id")
        if not isinstance(event_id, str) or _EVENT_ID.fullmatch(event_id) is None:
            raise ValueError("retained run contains an invalid event identity")
        if event_id in events:
            raise ValueError("retained run contains duplicate event identities")
        events[event_id] = cast(Mapping[str, object], item)
    return events


def _embedded_event_ids(value: JsonValue) -> list[str]:
    found: list[str] = []

    def visit(item: JsonValue) -> None:
        if isinstance(item, str) and _EVENT_ID.fullmatch(item):
            found.append(item)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, dict):
            for child in item.values():
                visit(child)

    visit(value)
    return list(dict.fromkeys(found))


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
