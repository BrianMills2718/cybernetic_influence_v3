"""Operator-facing projection of one retained coordination measurement."""

from __future__ import annotations

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
