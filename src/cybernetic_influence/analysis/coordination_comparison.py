"""Frozen, zero-authority comparison contract for Slice 21C.

The comparison consumes retained run measurements. It cannot execute a run,
call a model, repair an invalid result, or update simulated state.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.analysis.coordination_measurement import (
    COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    ExactMeasureId,
    IndicatorDirection,
    RunMeasurementConsumer,
)
from cybernetic_influence.scenarios.coordination_decision import PERSON_IDS

COMPARISON_SCHEMA_VERSION = 2
COMPARISON_REPLICATES_PER_CONDITION = 2
COMPARISON_CONDITIONS = (
    "baseline",
    "heterogeneous_pressure",
    "stabilization",
)
BASELINE_CONDITION = "baseline"

type Condition = Literal[
    "baseline",
    "heterogeneous_pressure",
    "stabilization",
]
type PatternDirection = Literal[
    "increase",
    "decrease",
    "no_change",
    "unclear",
]
type ValidityIssue = Literal[
    "provider_or_schema_failure",
    "unobservable_spend",
    "premature_safety_limit",
    "missing_scheduled_activity",
    "measurement_corruption",
    "incomplete_trace",
]


class _ProducedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ComparisonRunInput(_ProducedModel):
    """One fixed comparison slot, valid or visibly excluded."""

    run_id: str = Field(pattern=r"^run_[a-z0-9]+$")
    condition: Condition
    replicate: int = Field(ge=1, le=COMPARISON_REPLICATES_PER_CONDITION)
    run_status: str = Field(min_length=1)
    execution: Literal["scripted", "live"]
    participant_model: str = Field(min_length=1)
    participant_reasoning_effort: str = Field(min_length=1)
    coder_model: str = Field(min_length=1)
    coder_reasoning_effort: str = Field(min_length=1)
    scenario_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    measurement_spec_version: Literal[1] = 1
    measurement_spec_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cost_fully_observable: bool
    validity_issues: list[ValidityIssue] = Field(default_factory=list)
    measurement: RunMeasurementConsumer | None = None

    @model_validator(mode="after")
    def validate_slot(self) -> ComparisonRunInput:
        if len(self.validity_issues) != len(set(self.validity_issues)):
            raise ValueError("comparison run validity issues must be unique")
        if not self.validity_issues:
            if self.run_status != "completed":
                raise ValueError("a valid comparison run must be completed")
            if self.measurement is None:
                raise ValueError("a valid comparison run requires a measurement")
        if self.measurement is not None:
            if self.measurement.run_id != self.run_id:
                raise ValueError("comparison measurement belongs to another run")
            if self.measurement.scenario_fingerprint != self.scenario_fingerprint:
                raise ValueError("comparison measurement scenario fingerprint mismatch")
            if (
                self.measurement.measurement_spec_version
                != self.measurement_spec_version
            ):
                raise ValueError("comparison measurement specification version mismatch")
            if (
                self.measurement.measurement_spec_fingerprint
                != self.measurement_spec_fingerprint
            ):
                raise ValueError(
                    "comparison measurement specification fingerprint mismatch"
                )
            if self.measurement.coder_call.model != self.coder_model:
                raise ValueError("comparison coder model does not match measurement")
            if (
                self.measurement.coder_call.reasoning_effort
                != self.coder_reasoning_effort
            ):
                raise ValueError(
                    "comparison coder reasoning does not match measurement"
                )
        coder_cost_observable = self.measurement is None or (
            self.measurement.coder_call.observed_cost is not None
            and self.measurement.coder_call.cost_covers_all_attempts
        )
        has_cost_issue = "unobservable_spend" in self.validity_issues
        if (not self.cost_fully_observable or not coder_cost_observable) and not (
            has_cost_issue
        ):
            raise ValueError(
                "unobservable comparison cost requires an unobservable_spend validity issue"
            )
        if self.cost_fully_observable and coder_cost_observable and has_cost_issue:
            raise ValueError(
                "unobservable_spend cannot be retained when all costs are observable"
            )
        return self


class ComparisonExcludedAttempt(_ProducedModel):
    """One failed or otherwise invalid attempt replaced outside the six slots."""

    run_id: str = Field(pattern=r"^run_[a-z0-9]+$")
    condition: Condition
    requested_replicate: int = Field(ge=1, le=COMPARISON_REPLICATES_PER_CONDITION)
    run_status: str = Field(min_length=1)
    execution: Literal["scripted", "live"]
    participant_model: str = Field(min_length=1)
    participant_reasoning_effort: str = Field(min_length=1)
    coder_model: str = Field(min_length=1)
    coder_reasoning_effort: str = Field(min_length=1)
    scenario_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    scenario_fingerprint_status: Literal["known", "unavailable_before_result"]
    measurement_spec_version: Literal[1] = 1
    measurement_spec_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    cost_fully_observable: bool
    observed_cost: float | None = Field(default=None, ge=0.0)
    cost_source: str = Field(min_length=1)
    validity_issues: list[ValidityIssue]

    @model_validator(mode="after")
    def validate_exclusion(self) -> ComparisonExcludedAttempt:
        if len(self.validity_issues) != len(set(self.validity_issues)):
            raise ValueError("excluded attempt validity issues must be unique")
        if not self.validity_issues:
            raise ValueError("an excluded attempt must retain a validity issue")
        has_cost_issue = "unobservable_spend" in self.validity_issues
        if not self.cost_fully_observable and not has_cost_issue:
            raise ValueError(
                "an excluded attempt with incomplete cost coverage requires an unobservable_spend validity issue"
            )
        if self.cost_fully_observable and has_cost_issue:
            raise ValueError(
                "a fully observable excluded attempt cannot retain unobservable_spend"
            )
        if self.cost_fully_observable and self.observed_cost is None:
            raise ValueError(
                "a fully observable excluded attempt requires an observed cost"
            )
        if self.scenario_fingerprint_status == "known":
            if self.scenario_fingerprint is None:
                raise ValueError(
                    "a known excluded-attempt scenario fingerprint is required"
                )
        elif self.scenario_fingerprint is not None:
            raise ValueError(
                "an excluded attempt unavailable before a result must omit its scenario fingerprint"
            )
        if (
            self.scenario_fingerprint_status == "unavailable_before_result"
            and self.run_status == "completed"
        ):
            raise ValueError(
                "a completed excluded attempt cannot mark its scenario fingerprint unavailable before a result"
            )
        return self


class NumericMetricSpec(_ProducedModel):
    metric_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    measure_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    value_path: tuple[str, ...] = Field(min_length=1)
    unit: str = Field(min_length=1)


NUMERIC_METRICS = (
    NumericMetricSpec(
        metric_id="modeled_time_to_terminal",
        measure_id="modeled_time_to_terminal",
        value_path=("scenario_minutes",),
        unit="scenario_minute",
    ),
    NumericMetricSpec(
        metric_id="partners_retained",
        measure_id="partners_retained",
        value_path=("count",),
        unit="person_count",
    ),
    NumericMetricSpec(
        metric_id="verification_requests",
        measure_id="verification_requests",
        value_path=("total",),
        unit="request_count",
    ),
    NumericMetricSpec(
        metric_id="risk_register_expansion",
        measure_id="risk_register_expansion",
        value_path=("distinct_risks",),
        unit="risk_count",
    ),
    NumericMetricSpec(
        metric_id="unresolved_risk_load",
        measure_id="unresolved_risk_load",
        value_path=("final_open_count",),
        unit="open_risk_count",
    ),
    NumericMetricSpec(
        metric_id="decision_latency",
        measure_id="decision_latency",
        value_path=("scenario_minutes",),
        unit="scenario_minute",
    ),
    NumericMetricSpec(
        metric_id="meeting_cycles",
        measure_id="deliberation_load",
        value_path=("meeting_cycles",),
        unit="meeting_count",
    ),
    NumericMetricSpec(
        metric_id="external_action_attempts",
        measure_id="deliberation_load",
        value_path=("external_action_attempts",),
        unit="attempt_count",
    ),
    NumericMetricSpec(
        metric_id="issue_reopening",
        measure_id="issue_reopening",
        value_path=("count",),
        unit="issue_count",
    ),
    NumericMetricSpec(
        metric_id="informal_alignment",
        measure_id="informal_alignment",
        value_path=("message_count",),
        unit="message_count",
    ),
    NumericMetricSpec(
        metric_id="disengagement",
        measure_id="disengagement",
        value_path=("count",),
        unit="person_count",
    ),
)


def _comparison_contract_fingerprint() -> str:
    payload = {
        "comparison_schema_version": COMPARISON_SCHEMA_VERSION,
        "conditions": list(COMPARISON_CONDITIONS),
        "replicates_per_condition": COMPARISON_REPLICATES_PER_CONDITION,
        "numeric_metrics": [item.model_dump(mode="json") for item in NUMERIC_METRICS],
        "coded_indicators": [
            "conditional_trust_episode",
            "precautionary_hedging_episode",
            "relevance_classification",
        ],
        "subgroup_dispositions": [
            "relied_on",
            "rejected",
            "validation_pending",
        ],
        "excluded_attempts": {
            "retained_outside_selected_slots": True,
            "contribute_measurement_values": False,
            "count_as_invalid_runs": True,
            "known_configuration_must_match": True,
            "scenario_fingerprint_status_is_explicit": True,
        },
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


COMPARISON_CONTRACT_FINGERPRINT = _comparison_contract_fingerprint()


class PerRunNumericValue(_ProducedModel):
    run_id: str
    replicate: int
    value: float | None


class NumericConditionSummary(_ProducedModel):
    condition: Condition
    unit: str
    per_run: list[PerRunNumericValue]
    valid_run_count: int = Field(ge=0)
    invalid_run_count: int = Field(ge=0)
    missing_value_count: int = Field(ge=0)
    minimum: float | None
    maximum: float | None
    direction_relative_to_baseline: PatternDirection
    magnitude_relative_to_baseline: float | None
    proportion_with_summary_direction: float | None = Field(ge=0.0, le=1.0)


class NumericCandidatePattern(_ProducedModel):
    pattern_kind: Literal["candidate_directional_pattern"] = (
        "candidate_directional_pattern"
    )
    metric_id: str
    measure_id: str
    unit: str
    conditions: list[NumericConditionSummary]


class PerRunIndicatorValue(_ProducedModel):
    run_id: str
    replicate: int
    direction: IndicatorDirection | None


class CodedConditionSummary(_ProducedModel):
    condition: Condition
    per_run: list[PerRunIndicatorValue]
    valid_run_count: int = Field(ge=0)
    invalid_run_count: int = Field(ge=0)
    missing_indicator_count: int = Field(ge=0)
    direction_counts: dict[IndicatorDirection, int]
    shared_direction: IndicatorDirection
    between_run_disagreement: bool


class CodedIndicatorComparison(_ProducedModel):
    indicator_id: str
    unit: Literal["coded_direction"] = "coded_direction"
    conditions: list[CodedConditionSummary]


class SubgroupDirection(_ProducedModel):
    subgroup_id: str
    baseline_values: list[int | None]
    condition_values: list[int | None]
    valid_run_count: int = Field(ge=0)
    invalid_run_count: int = Field(ge=0)
    missing_value_count: int = Field(ge=0)
    direction_relative_to_baseline: PatternDirection
    magnitude_relative_to_baseline: float | None


class SubgroupDisagreement(_ProducedModel):
    measure_id: Literal["source_reliance_topology"] = "source_reliance_topology"
    condition: Condition
    disposition: Literal["relied_on", "rejected", "validation_pending"]
    unit: Literal["source_edge_count"] = "source_edge_count"
    subgroups: list[SubgroupDirection]
    direction_disagreement: bool


class ComparisonRunRecord(ComparisonRunInput):
    """One retained input plus its explicit calculation disposition."""

    included: bool

    @model_validator(mode="after")
    def validate_inclusion(self) -> ComparisonRunRecord:
        if self.included == bool(self.validity_issues):
            raise ValueError("comparison inclusion disagrees with run validity")
        return self


class CoordinationComparison(_ProducedModel):
    comparison_schema_version: Literal[2] = 2
    comparison_id: str = Field(pattern=r"^comparison_[0-9a-f]{16}$")
    comparison_contract_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    batch_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_id: Literal["coordination_decision_v1"] = "coordination_decision_v1"
    baseline_condition: Literal["baseline"] = "baseline"
    replicates_per_condition: Literal[2] = 2
    execution: Literal["scripted", "live"]
    participant_model: str
    participant_reasoning_effort: str
    coder_model: str
    coder_reasoning_effort: str
    scenario_fingerprints: dict[Condition, str]
    measurement_spec_version: Literal[1] = 1
    measurement_spec_fingerprint: str
    runs: list[ComparisonRunRecord]
    excluded_attempts: list[ComparisonExcludedAttempt]
    numeric_patterns: list[NumericCandidatePattern]
    coded_indicators: list[CodedIndicatorComparison]
    subgroup_disagreement: list[SubgroupDisagreement]
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_complete_comparison(self) -> CoordinationComparison:
        if self.comparison_contract_fingerprint != COMPARISON_CONTRACT_FINGERPRINT:
            raise ValueError("retained comparison contract fingerprint is not current")
        if self.measurement_spec_fingerprint != (
            COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
        ):
            raise ValueError("retained measurement specification is not current")
        run_inputs = _validate_matrix(
            [
                ComparisonRunInput.model_validate(
                    item.model_dump(mode="json", exclude={"included"})
                )
                for item in self.runs
            ]
        )
        excluded_attempts = _validate_excluded_attempts(
            run_inputs,
            self.excluded_attempts,
        )
        if self.batch_fingerprint != _batch_fingerprint(
            run_inputs,
            excluded_attempts,
        ):
            raise ValueError("retained comparison batch fingerprint mismatch")
        first = run_inputs[0]
        expected_scenarios = {
            cast(Condition, condition): next(
                item.scenario_fingerprint
                for item in run_inputs
                if item.condition == condition
            )
            for condition in COMPARISON_CONDITIONS
        }
        if self.scenario_fingerprints != expected_scenarios:
            raise ValueError("retained comparison condition fingerprints disagree")
        if (
            self.execution,
            self.participant_model,
            self.participant_reasoning_effort,
            self.coder_model,
            self.coder_reasoning_effort,
        ) != (
            first.execution,
            first.participant_model,
            first.participant_reasoning_effort,
            first.coder_model,
            first.coder_reasoning_effort,
        ):
            raise ValueError("retained comparison configuration disagrees with runs")
        expected_metrics = {item.metric_id for item in NUMERIC_METRICS}
        if {item.metric_id for item in self.numeric_patterns} != expected_metrics:
            raise ValueError("retained comparison lacks a frozen numeric metric")
        if len(self.numeric_patterns) != len(expected_metrics):
            raise ValueError("retained comparison has duplicate numeric metrics")
        expected_indicators = {
            "conditional_trust_episode",
            "precautionary_hedging_episode",
            "relevance_classification",
        }
        if {item.indicator_id for item in self.coded_indicators} != (
            expected_indicators
        ) or len(self.coded_indicators) != len(expected_indicators):
            raise ValueError("retained comparison lacks a frozen coded indicator")
        condition_groups = [
            [summary.condition for summary in item.conditions]
            for item in self.numeric_patterns
        ] + [
            [summary.condition for summary in item.conditions]
            for item in self.coded_indicators
        ]
        for conditions in condition_groups:
            if len(conditions) != len(COMPARISON_CONDITIONS) or set(
                conditions
            ) != set(COMPARISON_CONDITIONS):
                raise ValueError("retained comparison summary conditions are incomplete")
        expected_invalid_counts = Counter(
            item.condition for item in run_inputs if item.validity_issues
        )
        expected_invalid_counts.update(
            item.condition for item in excluded_attempts
        )
        condition_summaries = [
            summary
            for pattern in self.numeric_patterns
            for summary in pattern.conditions
        ] + [
            summary
            for indicator in self.coded_indicators
            for summary in indicator.conditions
        ]
        for summary in condition_summaries:
            if summary.invalid_run_count != expected_invalid_counts[summary.condition]:
                raise ValueError(
                    "retained comparison invalid-run count disagrees with run dispositions"
                )
        subgroup_slots = {
            (item.condition, item.disposition)
            for item in self.subgroup_disagreement
        }
        expected_subgroup_slots = {
            (condition, disposition)
            for condition in COMPARISON_CONDITIONS
            for disposition in ("relied_on", "rejected", "validation_pending")
        }
        if len(self.subgroup_disagreement) != len(expected_subgroup_slots) or (
            subgroup_slots != expected_subgroup_slots
        ):
            raise ValueError("retained comparison subgroup summaries are incomplete")
        for subgroup_summary in self.subgroup_disagreement:
            for subgroup in subgroup_summary.subgroups:
                if (
                    subgroup.invalid_run_count
                    != expected_invalid_counts[subgroup_summary.condition]
                ):
                    raise ValueError(
                        "retained comparison subgroup invalid-run count disagrees with run dispositions"
                    )
        return self


def compare_coordination_runs(
    inputs: Sequence[ComparisonRunInput],
    *,
    excluded_attempts: Sequence[ComparisonExcludedAttempt] = (),
) -> CoordinationComparison:
    """Validate and compare exactly two retained slots per condition."""

    ordered = _validate_matrix(inputs)
    ordered_excluded = _validate_excluded_attempts(ordered, excluded_attempts)
    excluded_counts = Counter(item.condition for item in ordered_excluded)
    first = ordered[0]
    records = [
        ComparisonRunRecord.model_validate(
            {
                **item.model_dump(mode="json"),
                "included": not item.validity_issues,
            }
        )
        for item in ordered
    ]
    fingerprint = _batch_fingerprint(ordered, ordered_excluded)
    return CoordinationComparison(
        comparison_id=f"comparison_{fingerprint[:16]}",
        comparison_contract_fingerprint=COMPARISON_CONTRACT_FINGERPRINT,
        batch_fingerprint=fingerprint,
        execution=first.execution,
        participant_model=first.participant_model,
        participant_reasoning_effort=first.participant_reasoning_effort,
        coder_model=first.coder_model,
        coder_reasoning_effort=first.coder_reasoning_effort,
        scenario_fingerprints={
            cast(Condition, condition): next(
                item.scenario_fingerprint
                for item in ordered
                if item.condition == condition
            )
            for condition in COMPARISON_CONDITIONS
        },
        measurement_spec_fingerprint=first.measurement_spec_fingerprint,
        runs=records,
        excluded_attempts=ordered_excluded,
        numeric_patterns=[
            _numeric_pattern(spec, ordered, excluded_counts)
            for spec in NUMERIC_METRICS
        ],
        coded_indicators=_coded_comparisons(ordered, excluded_counts),
        subgroup_disagreement=_subgroup_comparisons(ordered, excluded_counts),
        limitations=[
            "This is an exploratory two-replicate synthetic comparison, not statistical inference.",
            "Invalid runs remain visible and are excluded from directional calculations.",
            "Each measure retains its native unit; measures are never combined into a trust, risk, readiness, or agency score.",
            "A candidate directional pattern describes only this frozen scenario batch and does not establish a real-world effect or invariant.",
        ],
    )


def _validate_matrix(
    inputs: Sequence[ComparisonRunInput],
) -> list[ComparisonRunInput]:
    expected_slots = {
        (cast(Condition, condition), replicate)
        for condition in COMPARISON_CONDITIONS
        for replicate in range(1, COMPARISON_REPLICATES_PER_CONDITION + 1)
    }
    slots = [(item.condition, item.replicate) for item in inputs]
    if len(slots) != len(set(slots)):
        raise ValueError("comparison contains duplicate condition/replicate slots")
    if set(slots) != expected_slots:
        raise ValueError("comparison requires exactly two slots per frozen condition")
    run_ids = [item.run_id for item in inputs]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("comparison run IDs must be unique")
    compatibility = {
        (
            item.execution,
            item.participant_model,
            item.participant_reasoning_effort,
            item.coder_model,
            item.coder_reasoning_effort,
            item.measurement_spec_version,
            item.measurement_spec_fingerprint,
        )
        for item in inputs
    }
    if len(compatibility) != 1:
        raise ValueError(
            "comparison runs must share execution mode, participant and coder models/reasoning, and measurement specification fingerprints"
        )
    for condition in COMPARISON_CONDITIONS:
        fingerprints = {
            item.scenario_fingerprint
            for item in inputs
            if item.condition == condition
        }
        if len(fingerprints) != 1:
            raise ValueError(
                f"comparison condition {condition!r} has mismatched scenario fingerprints"
            )
    first = inputs[0]
    if first.measurement_spec_fingerprint != COORDINATION_MEASUREMENT_SPEC_FINGERPRINT:
        raise ValueError("comparison measurement specification fingerprint is not current")
    order = {condition: index for index, condition in enumerate(COMPARISON_CONDITIONS)}
    return sorted(inputs, key=lambda item: (order[item.condition], item.replicate))


def _validate_excluded_attempts(
    inputs: Sequence[ComparisonRunInput],
    excluded_attempts: Sequence[ComparisonExcludedAttempt],
) -> list[ComparisonExcludedAttempt]:
    selected_ids = {item.run_id for item in inputs}
    excluded_ids = [item.run_id for item in excluded_attempts]
    if len(excluded_ids) != len(set(excluded_ids)) or selected_ids.intersection(
        excluded_ids
    ):
        raise ValueError("comparison selected and excluded run IDs must be unique")
    first = inputs[0]
    expected_configuration = (
        first.execution,
        first.participant_model,
        first.participant_reasoning_effort,
        first.coder_model,
        first.coder_reasoning_effort,
        first.measurement_spec_version,
        first.measurement_spec_fingerprint,
    )
    fingerprints = {
        cast(Condition, condition): next(
            item.scenario_fingerprint
            for item in inputs
            if item.condition == condition
        )
        for condition in COMPARISON_CONDITIONS
    }
    for attempt in excluded_attempts:
        configuration = (
            attempt.execution,
            attempt.participant_model,
            attempt.participant_reasoning_effort,
            attempt.coder_model,
            attempt.coder_reasoning_effort,
            attempt.measurement_spec_version,
            attempt.measurement_spec_fingerprint,
        )
        if configuration != expected_configuration:
            raise ValueError(
                "excluded attempt configuration does not match the selected batch"
            )
        if (
            attempt.scenario_fingerprint is not None
            and attempt.scenario_fingerprint != fingerprints[attempt.condition]
        ):
            raise ValueError(
                f"excluded attempt scenario fingerprint does not match condition {attempt.condition!r}"
            )
    order = {condition: index for index, condition in enumerate(COMPARISON_CONDITIONS)}
    return sorted(
        excluded_attempts,
        key=lambda item: (
            order[item.condition],
            item.requested_replicate,
            item.run_id,
        ),
    )


def _batch_fingerprint(
    inputs: Sequence[ComparisonRunInput],
    excluded_attempts: Sequence[ComparisonExcludedAttempt],
) -> str:
    payload = {
        "comparison_schema_version": COMPARISON_SCHEMA_VERSION,
        "comparison_contract_fingerprint": COMPARISON_CONTRACT_FINGERPRINT,
        "replicates_per_condition": COMPARISON_REPLICATES_PER_CONDITION,
        "conditions": list(COMPARISON_CONDITIONS),
        "runs": [item.model_dump(mode="json") for item in inputs],
        "excluded_attempts": [
            item.model_dump(mode="json") for item in excluded_attempts
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _numeric_pattern(
    spec: NumericMetricSpec,
    inputs: Sequence[ComparisonRunInput],
    excluded_counts: Mapping[Condition, int],
) -> NumericCandidatePattern:
    values = {
        condition: [
            _numeric_value(item, spec)
            for item in inputs
            if item.condition == condition and not item.validity_issues
        ]
        for condition in COMPARISON_CONDITIONS
    }
    baseline_values = [
        value for value in values[BASELINE_CONDITION] if value is not None
    ]
    baseline_mean = _mean(baseline_values)
    summaries: list[NumericConditionSummary] = []
    for condition_name in COMPARISON_CONDITIONS:
        condition = cast(Condition, condition_name)
        condition_inputs = [item for item in inputs if item.condition == condition]
        per_run = [
            PerRunNumericValue(
                run_id=item.run_id,
                replicate=item.replicate,
                value=(None if item.validity_issues else _numeric_value(item, spec)),
            )
            for item in condition_inputs
        ]
        observed = [item.value for item in per_run if item.value is not None]
        condition_mean = _mean(observed)
        direction, magnitude = _direction_and_magnitude(
            condition_mean,
            baseline_mean,
            baseline=(condition == BASELINE_CONDITION),
        )
        individual_directions = [
            _direction(value, baseline_mean)
            for value in observed
            if baseline_mean is not None
        ]
        summaries.append(
            NumericConditionSummary(
                condition=condition,
                unit=spec.unit,
                per_run=per_run,
                valid_run_count=sum(not item.validity_issues for item in condition_inputs),
                invalid_run_count=(
                    sum(bool(item.validity_issues) for item in condition_inputs)
                    + excluded_counts.get(condition, 0)
                ),
                missing_value_count=sum(
                    not item.validity_issues and value is None
                    for item, value in zip(condition_inputs, [x.value for x in per_run])
                ),
                minimum=min(observed) if observed else None,
                maximum=max(observed) if observed else None,
                direction_relative_to_baseline=direction,
                magnitude_relative_to_baseline=magnitude,
                proportion_with_summary_direction=(
                    1.0
                    if condition == BASELINE_CONDITION and observed
                    else (
                        None
                        if not individual_directions or direction == "unclear"
                        else sum(item == direction for item in individual_directions)
                        / len(individual_directions)
                    )
                ),
            )
        )
    return NumericCandidatePattern(
        metric_id=spec.metric_id,
        measure_id=spec.measure_id,
        unit=spec.unit,
        conditions=summaries,
    )


def _numeric_value(
    item: ComparisonRunInput,
    spec: NumericMetricSpec,
) -> float | None:
    if item.measurement is None:
        return None
    value: JsonValue = item.measurement.exact_values[
        cast(ExactMeasureId, spec.measure_id)
    ]
    for key in spec.value_path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _coded_comparisons(
    inputs: Sequence[ComparisonRunInput],
    excluded_counts: Mapping[Condition, int],
) -> list[CodedIndicatorComparison]:
    indicator_ids = (
        "conditional_trust_episode",
        "precautionary_hedging_episode",
        "relevance_classification",
    )
    output: list[CodedIndicatorComparison] = []
    for indicator_id in indicator_ids:
        summaries: list[CodedConditionSummary] = []
        for condition_name in COMPARISON_CONDITIONS:
            condition = cast(Condition, condition_name)
            condition_inputs = [item for item in inputs if item.condition == condition]
            per_run: list[PerRunIndicatorValue] = []
            for item in condition_inputs:
                direction: IndicatorDirection | None = None
                if not item.validity_issues and item.measurement is not None:
                    matched = [
                        indicator
                        for indicator in item.measurement.coded_indicators
                        if indicator.indicator_id == indicator_id
                    ]
                    if matched:
                        direction = matched[0].direction
                per_run.append(
                    PerRunIndicatorValue(
                        run_id=item.run_id,
                        replicate=item.replicate,
                        direction=direction,
                    )
                )
            directions = [item.direction for item in per_run if item.direction is not None]
            counts = Counter(directions)
            shared: IndicatorDirection = (
                directions[0]
                if directions and len(set(directions)) == 1
                else "unclear"
            )
            summaries.append(
                CodedConditionSummary(
                    condition=condition,
                    per_run=per_run,
                    valid_run_count=sum(not item.validity_issues for item in condition_inputs),
                    invalid_run_count=(
                        sum(bool(item.validity_issues) for item in condition_inputs)
                        + excluded_counts.get(condition, 0)
                    ),
                    missing_indicator_count=sum(
                        not source.validity_issues and value.direction is None
                        for source, value in zip(condition_inputs, per_run)
                    ),
                    direction_counts=cast(dict[IndicatorDirection, int], dict(counts)),
                    shared_direction=shared,
                    between_run_disagreement=len(set(directions)) > 1,
                )
            )
        output.append(
            CodedIndicatorComparison(
                indicator_id=indicator_id,
                conditions=summaries,
            )
        )
    return output


def _subgroup_comparisons(
    inputs: Sequence[ComparisonRunInput],
    excluded_counts: Mapping[Condition, int],
) -> list[SubgroupDisagreement]:
    counts: dict[tuple[str, int, str, str], int] = defaultdict(int)
    for item in inputs:
        if item.validity_issues or item.measurement is None:
            continue
        topology = item.measurement.exact_values["source_reliance_topology"]
        if not isinstance(topology, Mapping):
            continue
        edges = topology.get("edges")
        if not isinstance(edges, list):
            continue
        for edge in edges:
            if not isinstance(edge, Mapping):
                continue
            actor = edge.get("actor_id")
            disposition = edge.get("disposition")
            if actor in PERSON_IDS and disposition in {
                "relied_on",
                "rejected",
                "validation_pending",
            }:
                counts[(item.condition, item.replicate, str(actor), str(disposition))] += 1

    output: list[SubgroupDisagreement] = []
    for condition_name in COMPARISON_CONDITIONS:
        condition = cast(Condition, condition_name)
        for disposition in ("relied_on", "rejected", "validation_pending"):
            subgroups: list[SubgroupDirection] = []
            for person_id in PERSON_IDS:
                baseline_values = [
                    (
                        counts[(BASELINE_CONDITION, item.replicate, person_id, disposition)]
                        if not item.validity_issues
                        else None
                    )
                    for item in inputs
                    if item.condition == BASELINE_CONDITION
                ]
                condition_values = [
                    (
                        counts[(condition, item.replicate, person_id, disposition)]
                        if not item.validity_issues
                        else None
                    )
                    for item in inputs
                    if item.condition == condition
                ]
                baseline_observed = [
                    float(value) for value in baseline_values if value is not None
                ]
                condition_observed = [
                    float(value) for value in condition_values if value is not None
                ]
                baseline_mean = _mean(baseline_observed)
                condition_mean = _mean(condition_observed)
                direction, magnitude = _direction_and_magnitude(
                    condition_mean,
                    baseline_mean,
                    baseline=(condition == BASELINE_CONDITION),
                )
                subgroups.append(
                    SubgroupDirection(
                        subgroup_id=person_id,
                        baseline_values=baseline_values,
                        condition_values=condition_values,
                        valid_run_count=len(condition_observed),
                        invalid_run_count=(
                            sum(
                                bool(item.validity_issues)
                                for item in inputs
                                if item.condition == condition
                            )
                            + excluded_counts.get(condition, 0)
                        ),
                        missing_value_count=sum(
                            value is None for value in condition_values
                        ),
                        direction_relative_to_baseline=direction,
                        magnitude_relative_to_baseline=magnitude,
                    )
                )
            output.append(
                SubgroupDisagreement(
                    condition=condition,
                    disposition=cast(
                        Literal["relied_on", "rejected", "validation_pending"],
                        disposition,
                    ),
                    subgroups=subgroups,
                    direction_disagreement=(
                        len(
                            {
                                item.direction_relative_to_baseline
                                for item in subgroups
                                if item.direction_relative_to_baseline != "unclear"
                            }
                        )
                        > 1
                    ),
                )
            )
    return output


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _direction(value: float, baseline: float | None) -> PatternDirection:
    if baseline is None:
        return "unclear"
    if value > baseline:
        return "increase"
    if value < baseline:
        return "decrease"
    return "no_change"


def _direction_and_magnitude(
    value: float | None,
    baseline_value: float | None,
    *,
    baseline: bool,
) -> tuple[PatternDirection, float | None]:
    if value is None or baseline_value is None:
        return "unclear", None
    if baseline:
        return "no_change", 0.0
    return _direction(value, baseline_value), value - baseline_value
