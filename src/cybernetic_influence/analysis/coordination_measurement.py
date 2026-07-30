"""Frozen Slice-21 coordination measurement contracts.

These records describe post-run analysis only. They cannot update a person,
mechanism, world state, run outcome, or completion decision.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.causal_core.models import EventKind

MEASUREMENT_SPEC_VERSION = 1
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_EVENT_ID_PATTERN = r"^event_[0-9]{6}$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_EVIDENCE_REF_PATTERN = r"^[A-Za-z0-9_.:-]+$"

ProvenanceClass: TypeAlias = Literal[
    "exact_trace",
    "evidence_coded",
    "derived_comparison",
]
IndicatorDirection: TypeAlias = Literal[
    "increase",
    "decrease",
    "no_change",
    "unclear",
]

EXACT_MEASURE_IDS = (
    "final_deployment_status",
    "modeled_time_to_terminal",
    "partners_retained",
    "final_approved_scope",
    "verification_requests",
    "source_reliance_topology",
    "intermediary_bypass",
    "risk_register_expansion",
    "action_threshold_change",
    "unresolved_risk_load",
    "decision_latency",
    "deliberation_load",
    "issue_reopening",
    "informal_alignment",
    "disengagement",
)
CODED_MEASURE_IDS = (
    "conditional_trust_episode",
    "precautionary_hedging_episode",
    "relevance_classification",
)
DERIVED_MEASURE_IDS = (
    "authority_divergence",
    "commitment_divergence",
    "candidate_directional_pattern",
)
ALL_MEASURE_IDS = frozenset(
    (*EXACT_MEASURE_IDS, *CODED_MEASURE_IDS, *DERIVED_MEASURE_IDS)
)

ExactMeasureId: TypeAlias = Literal[
    "final_deployment_status",
    "modeled_time_to_terminal",
    "partners_retained",
    "final_approved_scope",
    "verification_requests",
    "source_reliance_topology",
    "intermediary_bypass",
    "risk_register_expansion",
    "action_threshold_change",
    "unresolved_risk_load",
    "decision_latency",
    "deliberation_load",
    "issue_reopening",
    "informal_alignment",
    "disengagement",
]
CodedMeasureId: TypeAlias = Literal[
    "conditional_trust_episode",
    "precautionary_hedging_episode",
    "relevance_classification",
]
DerivedMeasureId: TypeAlias = Literal[
    "authority_divergence",
    "commitment_divergence",
    "candidate_directional_pattern",
]
MeasureId: TypeAlias = ExactMeasureId | CodedMeasureId | DerivedMeasureId
EventId: TypeAlias = Annotated[str, Field(pattern=_EVENT_ID_PATTERN)]
EvidenceRef: TypeAlias = Annotated[str, Field(pattern=_EVIDENCE_REF_PATTERN)]


class _ProducedModel(BaseModel):
    """Strict producer boundary for newly retained analysis records."""

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class _ConsumerModel(BaseModel):
    """Forward-tolerant consumer boundary for reopening retained records."""

    model_config = ConfigDict(extra="ignore", strict=True)


class MeasureDefinition(_ProducedModel):
    """One stable, provenance-labelled measure in specification version 1."""

    measure_id: MeasureId
    construct_name: str = Field(
        min_length=1,
        alias="construct",
        serialization_alias="construct",
    )
    label: str = Field(min_length=1)
    provenance_class: ProvenanceClass
    unit: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    required_source_event_kinds: list[EventKind] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_definition(self) -> "MeasureDefinition":
        if len(self.limitations) != len(set(self.limitations)):
            raise ValueError("measure limitations must be unique")
        if len(self.required_source_event_kinds) != len(
            set(self.required_source_event_kinds)
        ):
            raise ValueError("required source event kinds must be unique")
        expected = (
            "exact_trace"
            if self.measure_id in EXACT_MEASURE_IDS
            else (
                "evidence_coded"
                if self.measure_id in CODED_MEASURE_IDS
                else "derived_comparison"
            )
        )
        if self.provenance_class != expected:
            raise ValueError("measure provenance does not match its frozen class")
        return self


class MeasurementSpec(_ProducedModel):
    """Complete frozen specification for the first coordination assay."""

    measurement_spec_version: Literal[1] = 1
    scenario_id: Literal["coordination_decision_v1"] = "coordination_decision_v1"
    measures: list[MeasureDefinition] = Field(min_length=1)
    global_limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_complete_spec(self) -> "MeasurementSpec":
        measure_ids = [item.measure_id for item in self.measures]
        if len(measure_ids) != len(set(measure_ids)):
            raise ValueError("measurement specification requires unique measure IDs")
        if set(measure_ids) != ALL_MEASURE_IDS:
            raise ValueError(
                "measurement specification must exactly enumerate the frozen measures"
            )
        return self


class IndicatorCoding(_ProducedModel):
    """One LLM-facing classification without simulator-assigned IDs."""

    indicator_id: CodedMeasureId = Field(
        description="Frozen evidence-coded indicator to classify."
    )
    direction: IndicatorDirection = Field(
        description="Direction supported by the supplied retained evidence."
    )
    explanation: str = Field(
        min_length=1,
        description="Concise evidence-grounded reason for the classification.",
    )


class EvidenceAttachment(_ProducedModel):
    """Simulator-owned evidence context attached after coding."""

    indicator_id: CodedMeasureId
    source_event_ids: list[EventId] = Field(min_length=1)
    source_trace_ids: list[EvidenceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_citations(self) -> "EvidenceAttachment":
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("attached evidence event IDs must be unique")
        if len(self.source_trace_ids) != len(set(self.source_trace_ids)):
            raise ValueError("attached evidence trace IDs must be unique")
        return self


class IndicatorEvidence(_ProducedModel):
    """Retained coding combined with simulator-owned evidence context."""

    indicator_id: CodedMeasureId
    direction: IndicatorDirection
    explanation: str = Field(min_length=1)
    source_event_ids: list[EventId] = Field(min_length=1)
    source_trace_ids: list[EvidenceRef] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_citations(self) -> "IndicatorEvidence":
        if len(self.source_event_ids) != len(set(self.source_event_ids)):
            raise ValueError("retained evidence event IDs must be unique")
        if len(self.source_trace_ids) != len(set(self.source_trace_ids)):
            raise ValueError("retained evidence trace IDs must be unique")
        return self


class IndicatorEvidenceConsumer(_ConsumerModel):
    """Forward-compatible read projection for retained coded evidence."""

    indicator_id: CodedMeasureId
    direction: IndicatorDirection
    explanation: str = Field(min_length=1)
    source_event_ids: list[str] = Field(min_length=1)
    source_trace_ids: list[str] = Field(min_length=1)


class CoderOutput(_ProducedModel):
    """Entire LLM-facing schema; system IDs and exact values are absent."""

    coded_indicators: list[IndicatorCoding] = Field(
        min_length=1,
        description="One classification for every frozen evidence-coded indicator.",
    )

    @model_validator(mode="after")
    def validate_unique_indicators(self) -> "CoderOutput":
        indicator_ids = [item.indicator_id for item in self.coded_indicators]
        if len(indicator_ids) != len(set(indicator_ids)):
            raise ValueError("coder output contains duplicate indicator IDs")
        if set(indicator_ids) != set(CODED_MEASURE_IDS):
            raise ValueError("coder output must classify every frozen coded indicator")
        return self


class MeasurementCallEvidence(_ProducedModel):
    """Completed shared-client call retained with one run measurement."""

    status: Literal["completed"] = "completed"
    task: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    schema_revision: Literal[1]
    prompt_version: str = Field(min_length=1)
    model: str = Field(min_length=1)
    reasoning_effort: str = Field(min_length=1)
    max_budget: float = Field(gt=0.0)
    observed_cost: float | None = Field(default=None, ge=0.0)
    cost_source: str = Field(min_length=1)
    cost_covers_all_attempts: bool
    structured_output: CoderOutput


class MeasurementCallEvidenceConsumer(_ConsumerModel):
    """Forward-compatible read projection for coder-call evidence."""

    status: Literal["completed"]
    task: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    schema_revision: Literal[1]
    prompt_version: str = Field(min_length=1)
    model: str = Field(min_length=1)
    reasoning_effort: str = Field(min_length=1)
    max_budget: float = Field(gt=0.0)
    observed_cost: float | None = Field(default=None, ge=0.0)
    cost_source: str = Field(min_length=1)
    cost_covers_all_attempts: bool
    structured_output: dict[str, JsonValue]


class AnalystVisibleEvent(_ProducedModel):
    """Minimal analyst-visible event supplied to the later evidence coder."""

    event_id: EventId
    run_id: str = Field(pattern=_ID_PATTERN)
    event_kind: EventKind
    summary: str = Field(min_length=1)
    trace_ids: list[EvidenceRef] = Field(min_length=1)


class MeasurementEvidenceBundle(_ProducedModel):
    """Validated completed-run context before any post-run coding."""

    run_id: str = Field(pattern=_ID_PATTERN)
    run_status: Literal["completed"]
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    expected_scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    measurement_spec_version: Literal[1]
    measurement_spec_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    expected_measurement_spec_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    visible_events: list[AnalystVisibleEvent] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bundle(self) -> "MeasurementEvidenceBundle":
        if self.scenario_fingerprint != self.expected_scenario_fingerprint:
            raise ValueError("scenario fingerprint mismatch")
        if (
            self.measurement_spec_fingerprint
            != self.expected_measurement_spec_fingerprint
        ):
            raise ValueError("measurement specification fingerprint mismatch")
        if (
            self.expected_measurement_spec_fingerprint
            != COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
        ):
            raise ValueError("measurement specification fingerprint is not current")
        event_ids = [item.event_id for item in self.visible_events]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("analyst-visible event IDs must be unique")
        return self


class RunMeasurement(_ProducedModel):
    """Retained post-run artifact with exact and coded values separated."""

    measurement_id: str = Field(pattern=_ID_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    measurement_spec_version: Literal[1]
    measurement_spec_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    exact_values: dict[ExactMeasureId, JsonValue]
    coded_indicators: list[IndicatorEvidence]
    coder_call: MeasurementCallEvidence
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_measurement(self) -> "RunMeasurement":
        if self.measurement_id != f"measurement_{self.run_id.removeprefix('run_')}":
            raise ValueError("measurement identity does not match its run")
        if not self.coder_call.trace_id.startswith(f"{self.run_id}/"):
            raise ValueError("measurement coder trace does not match its run")
        if self.measurement_spec_fingerprint != (
            COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
        ):
            raise ValueError("run measurement specification fingerprint is not current")
        if set(self.exact_values) != set(EXACT_MEASURE_IDS):
            raise ValueError("run measurement must retain every frozen exact measure")
        indicator_ids = [item.indicator_id for item in self.coded_indicators]
        if len(indicator_ids) != len(set(indicator_ids)):
            raise ValueError("run measurement contains duplicate coded indicators")
        if set(indicator_ids) != set(CODED_MEASURE_IDS):
            raise ValueError("run measurement must retain every frozen coded indicator")
        raw_by_id = {
            item.indicator_id: item
            for item in self.coder_call.structured_output.coded_indicators
        }
        for retained in self.coded_indicators:
            raw = raw_by_id[retained.indicator_id]
            if (retained.direction, retained.explanation) != (
                raw.direction,
                raw.explanation,
            ):
                raise ValueError(
                    "retained coded indicator disagrees with raw structured output"
                )
        return self


class RunMeasurementConsumer(_ConsumerModel):
    """Forward-compatible read projection for a retained measurement."""

    measurement_id: str = Field(pattern=_ID_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    measurement_spec_version: Literal[1]
    measurement_spec_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    exact_values: dict[ExactMeasureId, JsonValue]
    coded_indicators: list[IndicatorEvidenceConsumer]
    coder_call: MeasurementCallEvidenceConsumer
    limitations: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_retained_measurement(self) -> "RunMeasurementConsumer":
        if self.measurement_id != f"measurement_{self.run_id.removeprefix('run_')}":
            raise ValueError("retained measurement identity does not match its run")
        if not self.coder_call.trace_id.startswith(f"{self.run_id}/"):
            raise ValueError("retained measurement coder trace does not match its run")
        if set(self.exact_values) != set(EXACT_MEASURE_IDS):
            raise ValueError("retained measurement is missing a frozen exact measure")
        indicator_ids = [item.indicator_id for item in self.coded_indicators]
        if len(indicator_ids) != len(set(indicator_ids)) or set(indicator_ids) != set(
            CODED_MEASURE_IDS
        ):
            raise ValueError("retained measurement has invalid coded indicators")
        raw_items = self.coder_call.structured_output.get("coded_indicators")
        if not isinstance(raw_items, list):
            raise ValueError("retained coder call lacks structured indicators")
        raw_by_id: dict[str, tuple[object, object]] = {}
        for item in raw_items:
            if not isinstance(item, dict):
                raise ValueError("retained coder output contains a malformed indicator")
            indicator_id = item.get("indicator_id")
            if not isinstance(indicator_id, str) or indicator_id in raw_by_id:
                raise ValueError("retained coder output has invalid indicator identity")
            raw_by_id[indicator_id] = (item.get("direction"), item.get("explanation"))
        if set(raw_by_id) != set(CODED_MEASURE_IDS):
            raise ValueError("retained coder output is missing a frozen indicator")
        for retained in self.coded_indicators:
            if raw_by_id[retained.indicator_id] != (
                retained.direction,
                retained.explanation,
            ):
                raise ValueError(
                    "retained coded indicator disagrees with raw structured output"
                )
        return self


def validate_coder_output(
    bundle: MeasurementEvidenceBundle,
    output: CoderOutput,
    attachments: list[EvidenceAttachment],
) -> list[IndicatorEvidence]:
    """Bind coded claims to visible evidence from exactly one completed run."""

    events = {item.event_id: item for item in bundle.visible_events}
    visible_trace_ids = {
        trace_id for event in bundle.visible_events for trace_id in event.trace_ids
    }
    attachment_ids = [item.indicator_id for item in attachments]
    if len(attachment_ids) != len(set(attachment_ids)):
        raise ValueError("evidence attachments contain duplicate indicator IDs")
    if set(attachment_ids) != set(CODED_MEASURE_IDS):
        raise ValueError("evidence context must cover every frozen coded indicator")
    attachments_by_id = {item.indicator_id: item for item in attachments}
    retained: list[IndicatorEvidence] = []
    for coding in output.coded_indicators:
        attachment = attachments_by_id[coding.indicator_id]
        for event_id in attachment.source_event_ids:
            event = events.get(event_id)
            if event is None:
                raise ValueError(f"unknown source event {event_id!r}")
            if event.run_id != bundle.run_id:
                raise ValueError(
                    f"source event {event_id!r} does not belong to run "
                    f"{bundle.run_id!r}"
                )
        unknown_trace_ids = set(attachment.source_trace_ids) - visible_trace_ids
        if unknown_trace_ids:
            raise ValueError(f"unknown source trace IDs {sorted(unknown_trace_ids)!r}")
        retained.append(
            IndicatorEvidence(
                indicator_id=coding.indicator_id,
                direction=coding.direction,
                explanation=coding.explanation,
                source_event_ids=attachment.source_event_ids,
                source_trace_ids=attachment.source_trace_ids,
            )
        )
    return retained


_COMMON_LIMITATION = (
    "This synthetic measure describes retained scenario evidence and is not an "
    "empirically validated psychological or organizational score."
)


def _measure(
    measure_id: MeasureId,
    construct: str,
    label: str,
    provenance_class: ProvenanceClass,
    unit: str,
    *event_kinds: EventKind,
) -> MeasureDefinition:
    return MeasureDefinition(
        measure_id=measure_id,
        construct=construct,
        label=label,
        provenance_class=provenance_class,
        unit=unit,
        limitations=[_COMMON_LIMITATION],
        required_source_event_kinds=list(event_kinds),
    )


COORDINATION_MEASUREMENT_SPEC = MeasurementSpec(
    measures=[
        _measure(
            "final_deployment_status",
            "decision_result",
            "Final deployment status",
            "exact_trace",
            "category",
            "state_committed",
            "run_completed",
        ),
        _measure(
            "modeled_time_to_terminal",
            "decision_speed",
            "Modeled time to terminal status",
            "exact_trace",
            "scenario_minute",
            "state_committed",
        ),
        _measure(
            "partners_retained",
            "participation",
            "Partners retained at completion",
            "exact_trace",
            "count_and_proportion",
            "state_committed",
        ),
        _measure(
            "final_approved_scope",
            "scope",
            "Final approved deployment scope",
            "exact_trace",
            "category",
            "state_committed",
        ),
        _measure(
            "verification_requests",
            "trust_structure",
            "Verification demand",
            "exact_trace",
            "count_per_meeting",
            "action_attempted",
            "mechanism_executed",
        ),
        _measure(
            "source_reliance_topology",
            "trust_structure",
            "Source reliance topology",
            "exact_trace",
            "directed_edges",
            "action_attempted",
            "state_committed",
        ),
        _measure(
            "authority_divergence",
            "trust_structure",
            "Authority divergence",
            "derived_comparison",
            "pairwise_disagreement",
            "state_committed",
        ),
        _measure(
            "intermediary_bypass",
            "trust_structure",
            "Intermediary bypass",
            "exact_trace",
            "count",
            "effect_routed",
            "state_committed",
        ),
        _measure(
            "conditional_trust_episode",
            "trust_structure",
            "Conditional-trust episode",
            "evidence_coded",
            "coded_episode",
            "action_attempted",
        ),
        _measure(
            "risk_register_expansion",
            "perceived_risk",
            "Risk-register expansion",
            "exact_trace",
            "distinct_risk_count",
            "state_committed",
        ),
        _measure(
            "action_threshold_change",
            "perceived_risk",
            "Action-threshold change",
            "exact_trace",
            "count_and_category",
            "action_attempted",
            "state_committed",
        ),
        _measure(
            "precautionary_hedging_episode",
            "perceived_risk",
            "Precautionary or hedging episode",
            "evidence_coded",
            "coded_episode",
            "action_attempted",
        ),
        _measure(
            "relevance_classification",
            "perceived_risk",
            "Risk relevance classification",
            "evidence_coded",
            "direct_indirect_unsupported_or_unclear",
            "effect_routed",
            "action_attempted",
        ),
        _measure(
            "unresolved_risk_load",
            "perceived_risk",
            "Unresolved risk load",
            "exact_trace",
            "open_items_per_meeting",
            "state_committed",
        ),
        _measure(
            "decision_latency",
            "coordination_readiness",
            "Decision latency",
            "exact_trace",
            "scenario_minute",
            "state_committed",
        ),
        _measure(
            "deliberation_load",
            "coordination_readiness",
            "Deliberation load",
            "exact_trace",
            "meeting_and_external_action_counts",
            "action_attempted",
            "effect_routed",
        ),
        _measure(
            "issue_reopening",
            "coordination_readiness",
            "Issue reopening",
            "exact_trace",
            "count",
            "mechanism_executed",
            "state_committed",
        ),
        _measure(
            "commitment_divergence",
            "coordination_readiness",
            "Commitment divergence",
            "derived_comparison",
            "count_and_scenario_minutes",
            "state_committed",
        ),
        _measure(
            "informal_alignment",
            "coordination_readiness",
            "Informal alignment",
            "exact_trace",
            "message_count",
            "effect_routed",
        ),
        _measure(
            "disengagement",
            "coordination_readiness",
            "Partner disengagement",
            "exact_trace",
            "count",
            "mechanism_executed",
            "state_committed",
        ),
        _measure(
            "candidate_directional_pattern",
            "cross_run_pattern",
            "Candidate directional pattern",
            "derived_comparison",
            "native_unit_direction_and_variation",
            "run_completed",
        ),
    ],
    global_limitations=[
        "Exact measures are exact only relative to the retained synthetic trace.",
        "Evidence-coded indicators classify visible evidence and do not "
        "establish truth or intent.",
        "Measures remain separate and cannot be averaged into trust, risk, "
        "readiness, or agency scores.",
    ],
)


def measurement_spec_fingerprint(spec: MeasurementSpec) -> str:
    """Return the stable digest of a complete measurement specification."""

    payload = json.dumps(
        spec.model_dump(mode="json", by_alias=True),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


COORDINATION_MEASUREMENT_SPEC_FINGERPRINT = measurement_spec_fingerprint(
    COORDINATION_MEASUREMENT_SPEC
)
