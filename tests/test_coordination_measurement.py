"""Packet 21B0 contracts and frozen controls for coordination measurement."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cybernetic_influence.analysis.coordination_measurement import (
    CODED_MEASURE_IDS,
    COORDINATION_MEASUREMENT_SPEC,
    COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    EXACT_MEASURE_IDS,
    MEASUREMENT_SPEC_VERSION,
    CoderOutput,
    EvidenceAttachment,
    IndicatorEvidence,
    IndicatorEvidenceConsumer,
    MeasurementEvidenceBundle,
    MeasurementSpec,
    RunMeasurement,
    RunMeasurementConsumer,
    validate_coder_output,
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "coordination_measurement"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / f"{name}.json").read_text())


def _attachments(fixture: dict[str, object]) -> list[EvidenceAttachment]:
    payload = fixture["evidence_context"]
    assert isinstance(payload, list)
    return [EvidenceAttachment.model_validate(item) for item in payload]


def _exact_values() -> dict[str, object]:
    return {measure_id: None for measure_id in EXACT_MEASURE_IDS}


def test_spec_enumerates_every_measure_with_stable_provenance() -> None:
    spec = COORDINATION_MEASUREMENT_SPEC

    assert spec.measurement_spec_version == MEASUREMENT_SPEC_VERSION == 1
    assert len(COORDINATION_MEASUREMENT_SPEC_FINGERPRINT) == 64
    assert {item.measure_id for item in spec.measures} == {
        *EXACT_MEASURE_IDS,
        *CODED_MEASURE_IDS,
        "authority_divergence",
        "commitment_divergence",
        "candidate_directional_pattern",
    }
    assert all(item.construct_name and item.unit for item in spec.measures)
    assert all(item.limitations for item in spec.measures)
    assert all(item.required_source_event_kinds for item in spec.measures)
    assert {item.provenance_class for item in spec.measures} == {
        "exact_trace",
        "evidence_coded",
        "derived_comparison",
    }


def test_producers_forbid_extras_and_consumers_tolerate_them() -> None:
    payload = _fixture("positive")["coder_output"]
    assert isinstance(payload, dict)

    with pytest.raises(ValidationError, match="extra_forbidden"):
        CoderOutput.model_validate({**payload, "unexpected": True})

    fixture = _fixture("positive")
    retained_indicators = validate_coder_output(
        MeasurementEvidenceBundle.model_validate(fixture["evidence_bundle"]),
        CoderOutput.model_validate(payload),
        _attachments(fixture),
    )
    indicator = retained_indicators[0].model_dump(mode="json")
    reopened = IndicatorEvidenceConsumer.model_validate(
        {**indicator, "future_annotation": "preserved by the retained artifact"}
    )
    assert reopened.indicator_id == "conditional_trust_episode"

    retained = RunMeasurement(
        measurement_id="measurement_positive",
        run_id="run_positive",
        measurement_spec_version=1,
        measurement_spec_fingerprint=COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
        scenario_fingerprint="a" * 64,
        exact_values=_exact_values(),
        coded_indicators=retained_indicators,
        limitations=["Synthetic fixture."],
    ).model_dump(mode="json")
    consumer = RunMeasurementConsumer.model_validate(
        {**retained, "future_provenance": {"kind": "new"}}
    )
    assert consumer.run_id == "run_positive"


def test_llm_schema_has_no_system_ids_or_exact_values() -> None:
    schema_text = json.dumps(CoderOutput.model_json_schema(), sort_keys=True)

    for excluded in (
        "measurement_id",
        "run_id",
        "scenario_fingerprint",
        "exact_values",
        "source_event_ids",
        "source_trace_ids",
    ):
        assert excluded not in schema_text

    payload = _fixture("positive")["coder_output"]
    assert isinstance(payload, dict)
    with pytest.raises(ValidationError, match="extra_forbidden"):
        CoderOutput.model_validate({**payload, "exact_values": {"issue_reopening": 1}})


def test_unclear_coding_is_valid_and_grounded() -> None:
    fixture = _fixture("environmental_event")
    bundle = MeasurementEvidenceBundle.model_validate(fixture["evidence_bundle"])
    output = CoderOutput.model_validate(fixture["coder_output"])

    validated = validate_coder_output(bundle, output, _attachments(fixture))

    relevance = next(
        item for item in validated if item.indicator_id == "relevance_classification"
    )
    assert relevance.direction == "unclear"


@pytest.mark.parametrize(
    ("fixture_name", "message"),
    [
        ("corruption", "unknown source event"),
        ("cross_run", "does not belong to run"),
    ],
)
def test_invalid_and_cross_run_event_ids_fail_visibly(
    fixture_name: str,
    message: str,
) -> None:
    fixture = _fixture(fixture_name)
    bundle = MeasurementEvidenceBundle.model_validate(fixture["evidence_bundle"])
    output = CoderOutput.model_validate(fixture["coder_output"])

    with pytest.raises(ValueError, match=message):
        validate_coder_output(bundle, output, _attachments(fixture))


@pytest.mark.parametrize(
    ("fixture_name", "message"),
    [
        ("incomplete_run", "Input should be 'completed'"),
        ("scenario_fingerprint_mismatch", "scenario fingerprint mismatch"),
        ("spec_revision_mismatch", "Input should be 1"),
        (
            "spec_fingerprint_mismatch",
            "measurement specification fingerprint mismatch",
        ),
    ],
)
def test_invalid_analysis_contexts_fail_visibly(
    fixture_name: str,
    message: str,
) -> None:
    with pytest.raises((ValidationError, ValueError), match=message):
        MeasurementEvidenceBundle.model_validate(
            _fixture(fixture_name)["evidence_bundle"]
        )


def test_positive_and_negative_controls_are_frozen_and_valid() -> None:
    positive = _fixture("positive")
    negative = _fixture("negative")

    positive_output = validate_coder_output(
        MeasurementEvidenceBundle.model_validate(positive["evidence_bundle"]),
        CoderOutput.model_validate(positive["coder_output"]),
        _attachments(positive),
    )
    negative_output = validate_coder_output(
        MeasurementEvidenceBundle.model_validate(negative["evidence_bundle"]),
        CoderOutput.model_validate(negative["coder_output"]),
        _attachments(negative),
    )

    assert positive_output[0].direction == "increase"
    assert all(item.direction == "no_change" for item in negative_output)


def test_run_measurement_keeps_exact_and_coded_values_structurally_separate() -> None:
    fixture = _fixture("positive")
    output = CoderOutput.model_validate(fixture["coder_output"])
    coded_indicators = validate_coder_output(
        MeasurementEvidenceBundle.model_validate(fixture["evidence_bundle"]),
        output,
        _attachments(fixture),
    )
    exact_values = _exact_values()
    exact_values["issue_reopening"] = 1
    measurement = RunMeasurement(
        measurement_id="measurement_positive",
        run_id="run_positive",
        measurement_spec_version=1,
        measurement_spec_fingerprint=COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
        scenario_fingerprint="a" * 64,
        exact_values=exact_values,
        coded_indicators=coded_indicators,
        limitations=["Synthetic control evidence is not an empirical estimate."],
    )

    assert measurement.exact_values["issue_reopening"] == 1
    assert measurement.coded_indicators[0].indicator_id == ("conditional_trust_episode")

    invalid_exact_values = {**exact_values, "conditional_trust_episode": "increase"}
    with pytest.raises(ValidationError):
        RunMeasurement(
            measurement_id="measurement_invalid",
            run_id="run_positive",
            measurement_spec_version=1,
            measurement_spec_fingerprint=COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
            scenario_fingerprint="a" * 64,
            exact_values=invalid_exact_values,
            coded_indicators=coded_indicators,
            limitations=["Synthetic fixture."],
        )


def test_retained_indicator_evidence_rejects_duplicate_citations() -> None:
    with pytest.raises(ValidationError, match="event IDs must be unique"):
        IndicatorEvidence(
            indicator_id="conditional_trust_episode",
            direction="increase",
            explanation="The same event must not be cited twice.",
            source_event_ids=["event_000001", "event_000001"],
            source_trace_ids=["activation_000001"],
        )


def test_spec_rejects_missing_or_duplicate_measure_definitions() -> None:
    payload = COORDINATION_MEASUREMENT_SPEC.model_dump(mode="json")
    payload["measures"] = payload["measures"][:-1]
    with pytest.raises(ValidationError, match="exactly enumerate"):
        MeasurementSpec.model_validate(payload)

    payload = COORDINATION_MEASUREMENT_SPEC.model_dump(mode="json")
    payload["measures"].append(payload["measures"][0])
    with pytest.raises(ValidationError, match="unique measure IDs"):
        MeasurementSpec.model_validate(payload)
