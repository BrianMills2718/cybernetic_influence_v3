"""Packet 21C0 comparison contract and zero-cost matrix controls."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from cybernetic_influence.analysis.coordination import analyze_coordination_run
from cybernetic_influence.analysis.coordination_comparison import (
    COMPARISON_CONDITIONS,
    COMPARISON_CONTRACT_FINGERPRINT,
    ComparisonExcludedAttempt,
    ComparisonRunInput,
    Condition,
    CoordinationComparison,
    compare_coordination_runs,
)
from cybernetic_influence.analysis.coordination_measurement import (
    CODED_MEASURE_IDS,
    COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    RunMeasurementConsumer,
)
from cybernetic_influence.scenarios.coordination_decision import (
    baseline_coordination_fixture,
    coordination_runtime_fixture,
    heterogeneous_pressure_coordination_fixture,
    run_scripted_coordination,
    stabilization_coordination_fixture,
)


def _coder_output(condition: str) -> dict[str, object]:
    directions = {
        "baseline": "no_change",
        "heterogeneous_pressure": "increase",
        "stabilization": "unclear",
    }
    return {
        "coded_indicators": [
            {
                "indicator_id": indicator_id,
                "direction": directions[condition],
                "explanation": (
                    f"Zero-cost fixture classification for {condition}; it is "
                    "retained only to exercise the comparison contract."
                ),
            }
            for indicator_id in CODED_MEASURE_IDS
        ]
    }


def _matrix() -> list[ComparisonRunInput]:
    builders = {
        "baseline": baseline_coordination_fixture,
        "heterogeneous_pressure": heterogeneous_pressure_coordination_fixture,
        "stabilization": stabilization_coordination_fixture,
    }
    output: list[ComparisonRunInput] = []
    run_number = 0
    for condition in COMPARISON_CONDITIONS:
        for replicate in (1, 2):
            run_number += 1
            run_id = f"run_{run_number:012d}"
            result = run_scripted_coordination(
                coordination_runtime_fixture(builders[condition]()),
                run_id=run_id,
            )

            # mock-ok: 21C0 requires a provider-free six-run comparison matrix.
            measurement = analyze_coordination_run(
                result,
                expected_scenario_fingerprint=result.scenario_fingerprint,
                model="fixture-evidence-coder",
                reasoning_effort="none",
                trace_id=f"{run_id}/measurement/v1",
                max_budget=0.1,
                structured_call=lambda *_args, _condition=condition, **kwargs: (
                    kwargs["response_model"].model_validate(
                        _coder_output(_condition)
                    ),
                    SimpleNamespace(
                        cost=0.0,
                        cost_source="fixture",
                        cost_covers_all_attempts=True,
                    ),
                ),
            )
            output.append(
                ComparisonRunInput(
                    run_id=run_id,
                    condition=cast(Condition, condition),
                    replicate=replicate,
                    run_status="completed",
                    execution="scripted",
                    participant_model="scripted/reference",
                    participant_reasoning_effort="none",
                    coder_model="fixture-evidence-coder",
                    coder_reasoning_effort="none",
                    scenario_fingerprint=result.scenario_fingerprint,
                    measurement_spec_fingerprint=(
                        COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
                    ),
                    cost_fully_observable=True,
                    measurement=RunMeasurementConsumer.model_validate(
                        measurement.model_dump(mode="json")
                    ),
                )
            )
    return output


@pytest.fixture(scope="module")
def matrix() -> list[ComparisonRunInput]:
    return _matrix()


def _replace_run(
    matrix: list[ComparisonRunInput],
    run_id: str,
    **updates: Any,
) -> list[ComparisonRunInput]:
    return [
        ComparisonRunInput.model_validate(
            {**item.model_dump(mode="json"), **updates}
        )
        if item.run_id == run_id
        else item
        for item in matrix
    ]


def _replace_measurement(
    item: ComparisonRunInput,
    measurement: RunMeasurementConsumer,
) -> ComparisonRunInput:
    return ComparisonRunInput.model_validate(
        {
            **item.model_dump(mode="json"),
            "measurement": measurement.model_dump(mode="json"),
        }
    )


def test_zero_cost_six_run_matrix_freezes_truthful_comparison(
    matrix: list[ComparisonRunInput],
) -> None:
    comparison = compare_coordination_runs(matrix)

    assert comparison.comparison_schema_version == 2
    assert comparison.replicates_per_condition == 2
    assert len(comparison.runs) == 6
    assert all(item.included for item in comparison.runs)
    assert len(comparison.batch_fingerprint) == 64
    assert comparison.comparison_contract_fingerprint == (
        COMPARISON_CONTRACT_FINGERPRINT
    )
    assert comparison.comparison_id.endswith(comparison.batch_fingerprint[:16])
    assert set(comparison.scenario_fingerprints) == set(COMPARISON_CONDITIONS)
    assert {item.pattern_kind for item in comparison.numeric_patterns} == {
        "candidate_directional_pattern"
    }
    for pattern in comparison.numeric_patterns:
        for condition in pattern.conditions:
            if condition.minimum is not None:
                assert condition.maximum is not None
                assert condition.minimum <= condition.maximum
    assert all(pattern.unit for pattern in comparison.numeric_patterns)
    assert len(comparison.subgroup_disagreement) == 9
    assert all(
        {item.subgroup_id for item in summary.subgroups}
        for summary in comparison.subgroup_disagreement
    )
    serialized = comparison.model_dump(mode="json")
    assert "trust_score" not in str(serialized)
    assert "risk_score" not in str(serialized)
    assert "readiness_score" not in str(serialized)
    assert "agency_score" not in str(serialized)


def test_batch_fingerprint_is_order_independent_and_content_bound(
    matrix: list[ComparisonRunInput],
) -> None:
    first = compare_coordination_runs(matrix)
    reversed_batch = compare_coordination_runs(list(reversed(matrix)))

    assert reversed_batch.batch_fingerprint == first.batch_fingerprint

    changed = _replace_run(
        matrix,
        "run_000000000003",
        validity_issues=["incomplete_trace"],
    )
    assert compare_coordination_runs(changed).batch_fingerprint != (
        first.batch_fingerprint
    )


def test_invalid_run_remains_visible_but_is_excluded(
    matrix: list[ComparisonRunInput],
) -> None:
    changed = _replace_run(
        matrix,
        "run_000000000004",
        validity_issues=["provider_or_schema_failure"],
        measurement=None,
    )

    comparison = compare_coordination_runs(changed)
    excluded = next(
        item for item in comparison.runs if item.run_id == "run_000000000004"
    )
    assert excluded.included is False
    assert excluded.validity_issues == ["provider_or_schema_failure"]
    pressure = next(
        item
        for item in comparison.numeric_patterns[0].conditions
        if item.condition == "heterogeneous_pressure"
    )
    assert pressure.valid_run_count == 1
    assert pressure.invalid_run_count == 1
    assert pressure.per_run[1].value is None
    pressure_subgroups = next(
        item
        for item in comparison.subgroup_disagreement
        if item.condition == "heterogeneous_pressure"
        and item.disposition == "relied_on"
    )
    assert all(item.invalid_run_count == 1 for item in pressure_subgroups.subgroups)
    assert all(item.condition_values[1] is None for item in pressure_subgroups.subgroups)


def _excluded_attempt(
    matrix: list[ComparisonRunInput],
    **updates: Any,
) -> ComparisonExcludedAttempt:
    selected = matrix[0]
    payload: dict[str, object] = {
        "run_id": "run_capacityfailure",
        "condition": selected.condition,
        "requested_replicate": 2,
        "run_status": "failed",
        "execution": selected.execution,
        "participant_model": selected.participant_model,
        "participant_reasoning_effort": selected.participant_reasoning_effort,
        "coder_model": selected.coder_model,
        "coder_reasoning_effort": selected.coder_reasoning_effort,
        "scenario_fingerprint": None,
        "scenario_fingerprint_status": "unavailable_before_result",
        "measurement_spec_version": selected.measurement_spec_version,
        "measurement_spec_fingerprint": selected.measurement_spec_fingerprint,
        "cost_fully_observable": False,
        "observed_cost": 0.0,
        "cost_source": "unavailable",
        "validity_issues": [
            "provider_or_schema_failure",
            "unobservable_spend",
        ],
    }
    return ComparisonExcludedAttempt.model_validate({**payload, **updates})


def test_replaced_failure_remains_fingerprinted_and_counted(
    matrix: list[ComparisonRunInput],
) -> None:
    excluded = _excluded_attempt(matrix)
    comparison = compare_coordination_runs(
        matrix,
        excluded_attempts=[excluded],
    )

    assert len(comparison.runs) == 6
    assert all(item.included for item in comparison.runs)
    assert comparison.excluded_attempts == [excluded]
    baseline = next(
        item
        for item in comparison.numeric_patterns[0].conditions
        if item.condition == "baseline"
    )
    assert baseline.valid_run_count == 2
    assert baseline.invalid_run_count == 1
    baseline_coded = next(
        item
        for item in comparison.coded_indicators[0].conditions
        if item.condition == "baseline"
    )
    assert baseline_coded.invalid_run_count == 1
    baseline_subgroups = next(
        item
        for item in comparison.subgroup_disagreement
        if item.condition == "baseline" and item.disposition == "relied_on"
    )
    assert all(
        item.invalid_run_count == 1 for item in baseline_subgroups.subgroups
    )
    assert comparison.batch_fingerprint != compare_coordination_runs(
        matrix
    ).batch_fingerprint
    changed_exclusion = ComparisonExcludedAttempt.model_validate(
        {
            **excluded.model_dump(mode="json"),
            "cost_source": "different-retained-source",
        }
    )
    assert compare_coordination_runs(
        matrix,
        excluded_attempts=[changed_exclusion],
    ).batch_fingerprint != comparison.batch_fingerprint


def test_excluded_attempt_must_be_invalid_and_cost_truthful(
    matrix: list[ComparisonRunInput],
) -> None:
    with pytest.raises(ValueError, match="must retain a validity issue"):
        _excluded_attempt(matrix, validity_issues=[])

    with pytest.raises(ValueError, match="requires an unobservable_spend"):
        _excluded_attempt(
            matrix,
            validity_issues=["provider_or_schema_failure"],
        )

    with pytest.raises(ValueError, match="cannot retain unobservable_spend"):
        _excluded_attempt(
            matrix,
            cost_fully_observable=True,
            cost_source="subscription_included",
        )


def test_excluded_attempt_must_match_known_batch_identity(
    matrix: list[ComparisonRunInput],
) -> None:
    with pytest.raises(ValueError, match="excluded attempt configuration"):
        compare_coordination_runs(
            matrix,
            excluded_attempts=[
                _excluded_attempt(matrix, participant_model="another-model")
            ],
        )

    with pytest.raises(ValueError, match="scenario fingerprint"):
        compare_coordination_runs(
            matrix,
            excluded_attempts=[
                _excluded_attempt(
                    matrix,
                    scenario_fingerprint="f" * 64,
                    scenario_fingerprint_status="known",
                )
            ],
        )

    with pytest.raises(ValueError, match="run IDs must be unique"):
        compare_coordination_runs(
            matrix,
            excluded_attempts=[
                _excluded_attempt(matrix, run_id=matrix[0].run_id)
            ],
        )


def test_excluded_attempt_cannot_hide_known_fingerprint_or_corrupt_counts(
    matrix: list[ComparisonRunInput],
) -> None:
    with pytest.raises(ValueError, match="must omit its scenario fingerprint"):
        _excluded_attempt(matrix, scenario_fingerprint="f" * 64)

    with pytest.raises(ValueError, match="cannot mark its scenario fingerprint"):
        _excluded_attempt(matrix, run_status="completed")

    comparison = compare_coordination_runs(
        matrix,
        excluded_attempts=[_excluded_attempt(matrix)],
    ).model_dump(mode="json")
    numeric_patterns = cast(list[dict[str, object]], comparison["numeric_patterns"])
    conditions = cast(list[dict[str, object]], numeric_patterns[0]["conditions"])
    baseline = next(item for item in conditions if item["condition"] == "baseline")
    baseline["invalid_run_count"] = 0
    with pytest.raises(ValueError, match="invalid-run count disagrees"):
        CoordinationComparison.model_validate(comparison)

    coded_comparison = compare_coordination_runs(
        matrix,
        excluded_attempts=[_excluded_attempt(matrix)],
    ).model_dump(mode="json")
    coded_indicators = cast(
        list[dict[str, object]],
        coded_comparison["coded_indicators"],
    )
    coded_conditions = cast(
        list[dict[str, object]],
        coded_indicators[0]["conditions"],
    )
    coded_baseline = next(
        item for item in coded_conditions if item["condition"] == "baseline"
    )
    coded_baseline["invalid_run_count"] = 0
    with pytest.raises(ValueError, match="invalid-run count disagrees"):
        CoordinationComparison.model_validate(coded_comparison)

    subgroup_comparison = compare_coordination_runs(
        matrix,
        excluded_attempts=[_excluded_attempt(matrix)],
    ).model_dump(mode="json")
    subgroup_summaries = cast(
        list[dict[str, object]],
        subgroup_comparison["subgroup_disagreement"],
    )
    baseline_subgroup = next(
        item
        for item in subgroup_summaries
        if item["condition"] == "baseline" and item["disposition"] == "relied_on"
    )
    subgroups = cast(list[dict[str, object]], baseline_subgroup["subgroups"])
    subgroups[0]["invalid_run_count"] = 0
    with pytest.raises(ValueError, match="subgroup invalid-run count disagrees"):
        CoordinationComparison.model_validate(subgroup_comparison)


def test_unobservable_cost_requires_visible_exclusion(
    matrix: list[ComparisonRunInput],
) -> None:
    payload = matrix[0].model_dump(mode="json")
    payload["cost_fully_observable"] = False
    with pytest.raises(ValueError, match="requires an unobservable_spend"):
        ComparisonRunInput.model_validate(payload)

    payload["validity_issues"] = ["unobservable_spend"]
    excluded = ComparisonRunInput.model_validate(payload)
    comparison = compare_coordination_runs([excluded, *matrix[1:]])
    retained = next(item for item in comparison.runs if item.run_id == excluded.run_id)
    assert retained.included is False
    assert retained.cost_fully_observable is False


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("execution", "live", "must share execution mode"),
        ("participant_model", "another-model", "must share execution mode"),
        (
            "participant_reasoning_effort",
            "high",
            "must share execution mode",
        ),
        (
            "measurement_spec_fingerprint",
            "f" * 64,
            "must share execution mode",
        ),
    ],
)
def test_incompatible_global_configuration_cannot_enter_batch(
    matrix: list[ComparisonRunInput],
    field: str,
    value: object,
    message: str,
) -> None:
    payload = matrix[1].model_dump(mode="json")
    payload[field] = value
    if field == "measurement_spec_fingerprint":
        payload["measurement"] = None
        payload["validity_issues"] = ["measurement_corruption"]
    changed = [matrix[0], ComparisonRunInput.model_validate(payload), *matrix[2:]]

    with pytest.raises(ValueError, match=message):
        compare_coordination_runs(changed)


def test_mismatched_coder_identity_cannot_enter_batch(
    matrix: list[ComparisonRunInput],
) -> None:
    payload = matrix[1].model_dump(mode="json")
    measurement = cast(dict[str, object], payload["measurement"])
    coder_call = cast(dict[str, object], measurement["coder_call"])
    coder_call["model"] = "another-coder"
    payload["coder_model"] = "another-coder"
    changed_item = ComparisonRunInput.model_validate(payload)

    with pytest.raises(ValueError, match="must share execution mode"):
        compare_coordination_runs([matrix[0], changed_item, *matrix[2:]])


def test_mismatched_fingerprint_within_condition_cannot_enter_batch(
    matrix: list[ComparisonRunInput],
) -> None:
    item = matrix[1]
    assert item.measurement is not None
    measurement_payload = item.measurement.model_dump(mode="json")
    measurement_payload["scenario_fingerprint"] = "f" * 64
    changed_item = ComparisonRunInput.model_validate(
        {
            **item.model_dump(mode="json"),
            "scenario_fingerprint": "f" * 64,
            "measurement": measurement_payload,
        }
    )

    with pytest.raises(ValueError, match="mismatched scenario fingerprints"):
        compare_coordination_runs([matrix[0], changed_item, *matrix[2:]])


def test_missing_native_value_is_counted_without_invalidating_run(
    matrix: list[ComparisonRunInput],
) -> None:
    item = matrix[0]
    assert item.measurement is not None
    payload = item.measurement.model_dump(mode="json")
    exact = cast(dict[str, object], payload["exact_values"])
    latency = cast(dict[str, object], exact["decision_latency"])
    latency["scenario_minutes"] = None
    changed_measurement = RunMeasurementConsumer.model_validate(payload)
    changed = [_replace_measurement(item, changed_measurement), *matrix[1:]]

    comparison = compare_coordination_runs(changed)
    latency_pattern = next(
        item
        for item in comparison.numeric_patterns
        if item.metric_id == "decision_latency"
    )
    baseline = next(
        item for item in latency_pattern.conditions if item.condition == "baseline"
    )
    assert baseline.valid_run_count == 2
    assert baseline.invalid_run_count == 0
    assert baseline.missing_value_count == 1
    assert baseline.minimum == baseline.maximum


def test_changing_one_pressure_measurement_changes_only_its_arm_readout(
    matrix: list[ComparisonRunInput],
) -> None:
    original = compare_coordination_runs(matrix)
    item = matrix[2]
    assert item.condition == "heterogeneous_pressure"
    assert item.measurement is not None
    payload = item.measurement.model_dump(mode="json")
    exact = cast(dict[str, object], payload["exact_values"])
    requests = cast(dict[str, object], exact["verification_requests"])
    requests["total"] = cast(int, requests["total"]) + 1
    changed_measurement = RunMeasurementConsumer.model_validate(payload)
    changed_matrix = [
        _replace_measurement(source, changed_measurement)
        if source.run_id == item.run_id
        else source
        for source in matrix
    ]
    changed = compare_coordination_runs(changed_matrix)

    original_pattern = next(
        value
        for value in original.numeric_patterns
        if value.metric_id == "verification_requests"
    )
    changed_pattern = next(
        value
        for value in changed.numeric_patterns
        if value.metric_id == "verification_requests"
    )
    original_by_condition = {
        value.condition: value for value in original_pattern.conditions
    }
    changed_by_condition = {
        value.condition: value for value in changed_pattern.conditions
    }
    assert changed_by_condition["baseline"] == original_by_condition["baseline"]
    assert changed_by_condition["stabilization"] == (
        original_by_condition["stabilization"]
    )
    assert changed_by_condition["heterogeneous_pressure"] != (
        original_by_condition["heterogeneous_pressure"]
    )


def test_contracts_forbid_extras(matrix: list[ComparisonRunInput]) -> None:
    payload = matrix[0].model_dump(mode="json")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ComparisonRunInput.model_validate({**payload, "aggregate_score": 0.9})

    excluded = _excluded_attempt(matrix).model_dump(mode="json")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        ComparisonExcludedAttempt.model_validate({**excluded, "replacement": True})

    comparison = compare_coordination_runs(matrix).model_dump(mode="json")
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CoordinationComparison.model_validate({**comparison, "invariant": True})

    comparison["runs"] = cast(list[object], comparison["runs"])[1:]
    with pytest.raises(ValueError, match="exactly two slots"):
        CoordinationComparison.model_validate(comparison)
