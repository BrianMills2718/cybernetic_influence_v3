"""Scenario-neutral evidence and per-run Waltzman/Levin analysis contracts."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Annotated, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.analysis.coordination import calculate_exact_values
from cybernetic_influence.analysis.coordination_measurement import (
    COORDINATION_MEASUREMENT_SPEC,
    EXACT_MEASURE_IDS,
    ExactMeasureId,
)
from cybernetic_influence.authoring.compiler import CompiledScenario
from cybernetic_influence.authoring.models import (
    CoordinationDecisionWorkflowDraft,
)
from cybernetic_influence.presentation import (
    _temporal_states,
    analyst_event,
    project_boundary_activity,
)
from cybernetic_influence.scenarios.coordination_decision import (
    MINUTES_PER_DAY,
    scenario_fingerprint,
)


_ID_PATTERN = r"^[a-z][a-z0-9_]*$"
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"
_EVIDENCE_REF_PATTERN = r"^[A-Za-z0-9_.:-]+$"

MethodClass: TypeAlias = Literal["exact", "calculated", "llm_coded"]
EvidenceKind: TypeAlias = Literal[
    "configuration",
    "initial_state",
    "terminal_state",
    "causal_event",
    "information_lineage",
    "participant_activation",
    "mechanism_decision",
    "boundary_activity",
    "completion",
]
# Every evidence kind a completed run can actually retain. "boundary_activity"
# is declared in EvidenceKind but no execution path emits a record of that kind,
# so an analysis requiring it can never be satisfied by any run. An authored
# analysis that asked for it produced a lens that reported itself unsupported
# forever, which reads to the analyst as their run being deficient rather than
# as a request that was never satisfiable.
RETAINABLE_EVIDENCE_KINDS: frozenset[str] = frozenset(
    {
        "configuration",
        "initial_state",
        "terminal_state",
        "causal_event",
        "information_lineage",
        "participant_activation",
        "mechanism_decision",
        "completion",
    }
)
FrameworkId: TypeAlias = Literal["waltzman", "levin"]
AnalysisId: TypeAlias = Literal[
    "waltzman_decision_environment_v1",
    "levin_collective_competence_v1",
]
EvidenceRef = Annotated[str, Field(pattern=_EVIDENCE_REF_PATTERN)]


class _ProducedModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class _ConsumerModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class RunSpecV1(_ProducedModel):
    """Execution controls for one run, separate from scenario semantics."""

    run_spec_version: Literal[1] = 1
    run_id: str = Field(pattern=_ID_PATTERN)
    execution_mode: Literal["reference", "live"]
    model: str | None = Field(default=None, min_length=1)
    reasoning_effort: str | None = Field(default=None, min_length=1)
    horizon_minutes: int = Field(ge=1)
    per_call_budget: float | None = Field(default=None, gt=0)
    per_run_budget: float | None = Field(default=None, gt=0)
    checkpoint_id: str | None = Field(default=None, pattern=_ID_PATTERN)

    @model_validator(mode="after")
    def validate_execution_controls(self) -> "RunSpecV1":
        provider_fields = (
            self.model,
            self.reasoning_effort,
            self.per_call_budget,
            self.per_run_budget,
        )
        if self.execution_mode == "reference" and any(
            item is not None for item in provider_fields
        ):
            raise ValueError("reference RunSpec cannot contain provider controls")
        if self.execution_mode == "live" and any(
            item is None for item in provider_fields
        ):
            raise ValueError("live RunSpec requires complete provider controls")
        return self


class AnalysisSpecV1(_ProducedModel):
    """Versioned post-run construct definition with no world authority."""

    analysis_spec_version: Literal[1] = 1
    analysis_id: AnalysisId
    framework: FrameworkId
    construct_definitions: list[str] = Field(min_length=1)
    required_evidence_kinds: list[EvidenceKind] = Field(min_length=1)
    method_classes: list[MethodClass] = Field(min_length=1)
    aggregation: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    candidate_boundary_ref: str = Field(pattern=_ID_PATTERN)
    candidate_goal_ref: str | None = Field(default=None, pattern=_ID_PATTERN)

    @model_validator(mode="after")
    def validate_framework_contract(self) -> "AnalysisSpecV1":
        expected = {
            "waltzman_decision_environment_v1": "waltzman",
            "levin_collective_competence_v1": "levin",
        }[self.analysis_id]
        if self.framework != expected:
            raise ValueError("analysis framework does not match analysis identity")
        for label, values in (
            ("required evidence kinds", self.required_evidence_kinds),
            ("method classes", self.method_classes),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        if self.framework == "levin" and self.candidate_goal_ref is None:
            raise ValueError("Levin analysis requires a candidate goal")
        return self


class EvidenceRecordV1(_ProducedModel):
    """One typed retained source record; narrative is deliberately not a kind."""

    evidence_ref: EvidenceRef
    evidence_kind: EvidenceKind
    summary: str = Field(min_length=1)
    source_refs: list[EvidenceRef] = Field(default_factory=list)
    payload: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_unique_sources(self) -> "EvidenceRecordV1":
        if len(self.source_refs) != len(set(self.source_refs)):
            raise ValueError("evidence source references must be unique")
        if self.evidence_ref in self.source_refs:
            raise ValueError("evidence record cannot cite itself")
        return self


class RunEvidenceBundleV1(_ProducedModel):
    """Theory-neutral retained projection over one completed run."""

    bundle_version: Literal[1] = 1
    bundle_id: str = Field(pattern=_ID_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    proposal_digest: str = Field(pattern=_DIGEST_PATTERN)
    scenario_spec: dict[str, JsonValue]
    run_spec: RunSpecV1
    analysis_specs: list[AnalysisSpecV1] = Field(min_length=1)
    initial_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    terminal_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    evidence_records: list[EvidenceRecordV1] = Field(min_length=1)
    fidelity_assumptions: list[str] = Field(min_length=1)
    known_omissions: list[str] = Field(min_length=1)
    fidelity_questions: list[str] = Field(min_length=1)
    presentation_artifact_refs: list[str] = Field(default_factory=list)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_bundle_integrity(self) -> "RunEvidenceBundleV1":
        if self.bundle_id != f"bundle_{self.run_id}":
            raise ValueError("bundle identity does not match run")
        if self.run_spec.run_id != self.run_id:
            raise ValueError("RunSpec identity does not match bundle")
        if _digest(self.scenario_spec) != self.proposal_digest:
            raise ValueError("ScenarioSpec digest does not match approved proposal")
        analysis_ids = [item.analysis_id for item in self.analysis_specs]
        if len(analysis_ids) != len(set(analysis_ids)):
            raise ValueError("analysis specifications must be unique")
        records = {item.evidence_ref: item for item in self.evidence_records}
        if len(records) != len(self.evidence_records):
            raise ValueError("evidence record identities must be unique")
        for record in self.evidence_records:
            unknown = set(record.source_refs) - set(records)
            if unknown:
                raise ValueError(
                    f"evidence {record.evidence_ref!r} has unknown sources "
                    f"{sorted(unknown)!r}"
                )
        if any(ref.startswith("narrative:") for ref in records):
            raise ValueError("narrative cannot be retained as measurement evidence")
        if any(
            not ref.startswith("narrative:")
            for ref in self.presentation_artifact_refs
        ):
            raise ValueError("presentation artifact references must be narratives")
        if set(self.presentation_artifact_refs) & set(records):
            raise ValueError("presentation artifacts cannot also be source evidence")
        evidence_kinds = {item.evidence_kind for item in self.evidence_records}
        for spec in self.analysis_specs:
            missing = set(spec.required_evidence_kinds) - evidence_kinds
            if missing:
                raise ValueError(
                    f"analysis {spec.analysis_id!r} lacks required evidence kinds "
                    f"{sorted(missing)!r}"
                )
        expected = _digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        )
        if self.record_digest != expected:
            raise ValueError("run evidence bundle digest mismatch")
        return self


class EvidenceRecordConsumerV1(_ConsumerModel):
    evidence_ref: EvidenceRef
    evidence_kind: EvidenceKind
    source_refs: list[EvidenceRef] = Field(default_factory=list)


class RunEvidenceBundleConsumerV1(_ConsumerModel):
    """Forward-tolerant read projection retaining identity and reference checks."""

    bundle_version: Literal[1]
    bundle_id: str = Field(pattern=_ID_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    proposal_digest: str = Field(pattern=_DIGEST_PATTERN)
    evidence_records: list[EvidenceRecordConsumerV1] = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_read_projection(self) -> "RunEvidenceBundleConsumerV1":
        if self.bundle_id != f"bundle_{self.run_id}":
            raise ValueError("retained bundle identity does not match run")
        refs = [item.evidence_ref for item in self.evidence_records]
        if len(refs) != len(set(refs)):
            raise ValueError("retained evidence identities must be unique")
        known = set(refs)
        for record in self.evidence_records:
            if set(record.source_refs) - known:
                raise ValueError("retained evidence contains an unknown source")
        return self


class AnalysisSpecV2(_ProducedModel):
    """Execution-inert analysis request over retained run evidence."""

    analysis_spec_version: Literal[2] = 2
    analysis_id: str = Field(pattern=_ID_PATTERN)
    profile: Literal[
        "waltzman_coordination_v1", "exact_outcome_v1", "levin_collective_competence_v1"
    ]
    purpose: str = Field(min_length=1)
    construct_definitions: list[str] = Field(min_length=1)
    required_evidence_kinds: list[EvidenceKind] = Field(min_length=1)
    method_classes: list[MethodClass] = Field(min_length=1)
    aggregation: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    subject_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_analysis_fields(self) -> "AnalysisSpecV2":
        for label, values in (
            ("required evidence kinds", self.required_evidence_kinds),
            ("method classes", self.method_classes),
            ("subject references", self.subject_refs),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"{label} must be unique")
        unsatisfiable = sorted(
            set(self.required_evidence_kinds) - RETAINABLE_EVIDENCE_KINDS
        )
        if unsatisfiable:
            raise ValueError(
                "required evidence kinds that no run can retain: "
                + ", ".join(unsatisfiable)
                + "; an analysis requiring them can never produce a finding"
            )
        return self

    @property
    def digest(self) -> str:
        return _digest(self.model_dump(mode="json"))


class RunEvidenceBundleV2(_ProducedModel):
    """Immutable theory-neutral evidence for a separated scenario and run."""

    bundle_version: Literal[2] = 2
    bundle_id: str = Field(pattern=_ID_PATTERN)
    run_id: str = Field(pattern=_ID_PATTERN)
    scenario_id: str = Field(pattern=_ID_PATTERN)
    scenario_digest: str = Field(pattern=_DIGEST_PATTERN)
    run_spec_digest: str = Field(pattern=_DIGEST_PATTERN)
    initial_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    terminal_state_digest: str = Field(pattern=_DIGEST_PATTERN)
    evidence_records: list[EvidenceRecordV1] = Field(min_length=1)
    fidelity_assumptions: list[str] = Field(min_length=1)
    known_omissions: list[str] = Field(default_factory=list)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_bundle_integrity(self) -> "RunEvidenceBundleV2":
        if self.bundle_id != f"bundle_{self.run_id}":
            raise ValueError("bundle identity does not match run")
        records = {item.evidence_ref: item for item in self.evidence_records}
        if len(records) != len(self.evidence_records):
            raise ValueError("evidence record identities must be unique")
        for record in self.evidence_records:
            unknown = set(record.source_refs) - set(records)
            if unknown:
                raise ValueError(
                    f"evidence {record.evidence_ref!r} has unknown sources "
                    f"{sorted(unknown)!r}"
                )
        expected = _digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        )
        if self.record_digest != expected:
            raise ValueError("run evidence bundle digest mismatch")
        return self


class AnalysisFindingV2(_ProducedModel):
    finding_id: str = Field(pattern=_ID_PATTERN)
    construct_id: str = Field(pattern=_ID_PATTERN)
    method_class: MethodClass
    value: JsonValue
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class AnalysisResultV2(_ProducedModel):
    """One separately identified result that cannot mutate its source run."""

    analysis_result_version: Literal[2] = 2
    result_id: str = Field(pattern=_ID_PATTERN)
    run_evidence_bundle_digest: str = Field(pattern=_DIGEST_PATTERN)
    analysis_spec_digest: str = Field(pattern=_DIGEST_PATTERN)
    findings: list[AnalysisFindingV2] = Field(default_factory=list)
    coverage_status: Literal["supported", "degraded", "unsupported"]
    missing_evidence: list[EvidenceKind] = Field(default_factory=list)
    model_call_receipts: list[dict[str, JsonValue]] = Field(default_factory=list)
    result_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_result_integrity(self) -> "AnalysisResultV2":
        if self.coverage_status == "supported" and self.missing_evidence:
            raise ValueError("supported analysis cannot declare missing evidence")
        expected = _digest(
            self.model_dump(mode="json", exclude={"result_digest"})
        )
        if self.result_digest != expected:
            raise ValueError("analysis result digest mismatch")
        return self


class FrameworkFindingV1(_ProducedModel):
    """One method-labelled finding linked only to bundle evidence."""

    finding_id: str = Field(pattern=_ID_PATTERN)
    framework: FrameworkId
    construct_id: str = Field(pattern=_ID_PATTERN)
    method_class: MethodClass
    value: JsonValue
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    analysis_id: AnalysisId
    analysis_spec_version: Literal[1] = 1

    @model_validator(mode="after")
    def validate_finding_identity(self) -> "FrameworkFindingV1":
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("finding evidence references must be unique")
        expected = {
            "waltzman_decision_environment_v1": "waltzman",
            "levin_collective_competence_v1": "levin",
        }[self.analysis_id]
        if self.framework != expected:
            raise ValueError("finding framework does not match analysis")
        return self


class FrameworkReadoutV1(_ProducedModel):
    """Independent per-framework readout over one immutable evidence bundle."""

    readout_version: Literal[1] = 1
    readout_id: str = Field(pattern=_ID_PATTERN)
    framework: FrameworkId
    analysis_id: AnalysisId
    bundle_id: str = Field(pattern=_ID_PATTERN)
    bundle_digest: str = Field(pattern=_DIGEST_PATTERN)
    findings: list[FrameworkFindingV1] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_readout_integrity(self) -> "FrameworkReadoutV1":
        if self.readout_id != f"{self.framework}_{self.bundle_id}":
            raise ValueError("readout identity does not match its bundle")
        if any(item.framework != self.framework for item in self.findings):
            raise ValueError("readout mixes frameworks")
        expected_framework = {
            "waltzman_decision_environment_v1": "waltzman",
            "levin_collective_competence_v1": "levin",
        }[self.analysis_id]
        if self.framework != expected_framework:
            raise ValueError("readout framework does not match analysis")
        finding_ids = [item.finding_id for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("readout finding identities must be unique")
        expected = _digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        )
        if self.record_digest != expected:
            raise ValueError("framework readout digest mismatch")
        return self


class FrameworkFindingConsumerV1(_ConsumerModel):
    finding_id: str = Field(pattern=_ID_PATTERN)
    framework: FrameworkId
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    analysis_id: AnalysisId


class FrameworkReadoutConsumerV1(_ConsumerModel):
    """Forward-tolerant read projection retaining readout identity and refs."""

    readout_version: Literal[1]
    readout_id: str = Field(pattern=_ID_PATTERN)
    framework: FrameworkId
    analysis_id: AnalysisId
    bundle_id: str = Field(pattern=_ID_PATTERN)
    bundle_digest: str = Field(pattern=_DIGEST_PATTERN)
    findings: list[FrameworkFindingConsumerV1] = Field(min_length=1)
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_readout_projection(self) -> "FrameworkReadoutConsumerV1":
        if self.readout_id != f"{self.framework}_{self.bundle_id}":
            raise ValueError("retained readout identity does not match bundle")
        if any(item.framework != self.framework for item in self.findings):
            raise ValueError("retained readout mixes frameworks")
        finding_ids = [item.finding_id for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise ValueError("retained readout finding identities must be unique")
        return self


def reference_run_spec(*, run_id: str, horizon_minutes: int) -> RunSpecV1:
    return RunSpecV1(
        run_id=run_id,
        execution_mode="reference",
        horizon_minutes=horizon_minutes,
    )


def coordination_analysis_specs(
    *,
    boundary_ref: str,
    goal_ref: str,
) -> list[AnalysisSpecV1]:
    """Return the closed, reviewed Waltzman and Levin per-run specifications."""

    return [
        AnalysisSpecV1(
            analysis_id="waltzman_decision_environment_v1",
            framework="waltzman",
            construct_definitions=[
                "Trust structure is represented through concrete source reliance, authority divergence, and verification behavior.",
                "Perceived risk is represented through expressed concerns, retained issue records, and precautionary behavior.",
                "Coordination readiness is represented through latency, deliberation, commitment divergence, and disengagement.",
            ],
            required_evidence_kinds=[
                "causal_event",
                "information_lineage",
                "participant_activation",
                "mechanism_decision",
                "completion",
            ],
            method_classes=["exact", "calculated", "llm_coded"],
            aggregation="Keep measures separate within one run; do not emit a score or invariant.",
            uncertainty="Coded judgments remain conditional on visible retained evidence.",
            limitations=[
                "One synthetic run cannot establish causal influence or a directional invariant.",
                "Trust, risk, and readiness are analyst constructs, not hidden world state.",
            ],
            candidate_boundary_ref=boundary_ref,
        ),
        AnalysisSpecV1(
            analysis_id="levin_collective_competence_v1",
            framework="levin",
            construct_definitions=[
                "Collective competence is assessed relative to one candidate boundary, goal, and constraints.",
                "Boundary crossings, internal coordination, error correction, persistence, and adaptation are observed rather than attributed to an organization mind.",
            ],
            required_evidence_kinds=[
                "configuration",
                "initial_state",
                "terminal_state",
                "causal_event",
                "information_lineage",
                "boundary_activity",
                "completion",
            ],
            method_classes=["exact", "calculated"],
            aggregation="Report a profile of observed capacities and not-tested dimensions; do not calculate an agency score.",
            uncertainty="Unobserved capacities remain not_tested rather than absent.",
            limitations=[
                "No controlled perturbation is present in one ordinary run.",
                "The analytical boundary is execution-inert and adds no organization-level cognition.",
            ],
            candidate_boundary_ref=boundary_ref,
            candidate_goal_ref=goal_ref,
        ),
    ]


def build_run_evidence_bundle(
    compiled: CompiledScenario,
    result: ActiveRuntimeResult,
    *,
    run_spec: RunSpecV1,
    analysis_specs: list[AnalysisSpecV1],
) -> RunEvidenceBundleV1:
    """Project one completed trajectory into a validated theory-neutral bundle."""

    workflow = compiled.proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("theory bundle currently requires a coordination draft")
    if result.status != "completed" or result.completion is None:
        raise ValueError("theory bundle requires a completed run")
    if result.run_id != run_spec.run_id:
        raise ValueError("RunSpec does not describe the supplied result")
    if result.scenario_id != compiled.scenario.scenario_id:
        raise ValueError("result scenario identity does not match compilation")
    if result.scenario_fingerprint != scenario_fingerprint(compiled.scenario):
        raise ValueError("result scenario fingerprint does not match compilation")
    if result.scenario_fingerprint != result.core_result.scenario_fingerprint:
        raise ValueError("runtime and core scenario fingerprints disagree")
    if run_spec.horizon_minutes != workflow.deadline_day * MINUTES_PER_DAY:
        raise ValueError("RunSpec horizon does not match the reviewed deadline")
    if run_spec.execution_mode == "reference" and result.model_calls != 0:
        raise ValueError("reference RunSpec cannot bind a provider-backed result")
    if {item.analysis_id for item in analysis_specs} != set(
        workflow.analysis.analysis_ids
    ):
        raise ValueError("analysis snapshots do not match the approved selection")
    for spec in analysis_specs:
        if spec.candidate_boundary_ref != (
            workflow.analysis.candidate_boundary_ref
        ):
            raise ValueError("analysis boundary drifted from approved ScenarioSpec")
        if (
            spec.framework == "levin"
            and spec.candidate_goal_ref != workflow.analysis.candidate_goal_ref
        ):
            raise ValueError("analysis goal drifted from approved ScenarioSpec")

    records: list[EvidenceRecordV1] = [
        EvidenceRecordV1(
            evidence_ref="configuration:scenario",
            evidence_kind="configuration",
            summary="Approved reviewed scenario configuration.",
            payload=cast(
                dict[str, JsonValue],
                compiled.proposal.model_dump(mode="json"),
            ),
        ),
        EvidenceRecordV1(
            evidence_ref="configuration:run",
            evidence_kind="configuration",
            summary="Execution controls for this run.",
            source_refs=["configuration:scenario"],
            payload=cast(dict[str, JsonValue], run_spec.model_dump(mode="json")),
        ),
        EvidenceRecordV1(
            evidence_ref="state:initial",
            evidence_kind="initial_state",
            summary="Digest of the compiled initial world state.",
            source_refs=["configuration:scenario"],
            payload={"state_digest": result.core_result.initial_state_digest},
        ),
    ]
    for spec in analysis_specs:
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"configuration:analysis:{spec.analysis_id}",
                evidence_kind="configuration",
                summary=f"Reviewed {spec.framework} per-run analysis specification.",
                source_refs=["configuration:scenario"],
                payload=cast(dict[str, JsonValue], spec.model_dump(mode="json")),
            )
        )

    for event in result.core_result.events:
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"event:{event.event_id}",
                evidence_kind="causal_event",
                summary=event.summary,
                source_refs=[
                    f"event:{parent_id}" for parent_id in event.causal_parent_event_ids
                ],
                payload=cast(dict[str, JsonValue], analyst_event(event)),
            )
        )

    final_state = result.core_result.final_state
    for representation in final_state.representations.values():
        payload = representation.model_dump(mode="json")
        if representation.visibility == "mechanism":
            payload["content"] = "[redacted]"
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"information:{representation.representation_id}",
                evidence_kind="information_lineage",
                summary=(
                    f"Representation {representation.representation_id} retained "
                    f"on {representation.carrier_id}."
                ),
                source_refs=[
                    f"information:{parent_id}"
                    for parent_id in representation.parent_representation_ids
                ],
                payload=cast(dict[str, JsonValue], payload),
            )
        )

    for attempt in result.attempts:
        participant_payload: list[JsonValue] = []
        source_refs = [f"event:{event_id}" for event_id in attempt.core_event_ids]
        for participant in attempt.participants:
            observations = [
                {
                    "observation_id": item.observation_id,
                    "representation_id": item.representation_id,
                    "via_port_id": item.via_port_id,
                }
                for item in participant.input.observations
            ]
            actions = (
                [
                    {
                        "action_id": action_id,
                        "output_port_id": action.output_port_id,
                        "representation_id": action.representation_id,
                        "public_summary": action.public_summary,
                    }
                    for action_id, action in zip(
                        participant.assigned_action_ids,
                        participant.proposal.actions,
                        strict=True,
                    )
                ]
                if participant.proposal is not None
                else []
            )
            participant_payload.append(
                cast(
                    JsonValue,
                    {
                        "participant_id": participant.requested_active_system_id,
                        "observations": observations,
                        "actions": actions,
                        "call_trace_ids": [
                            item.trace_id for item in participant.call_evidence
                        ],
                    },
                )
            )
            source_refs.extend(
                f"information:{item.representation_id}"
                for item in participant.input.observations
                if item.representation_id is not None
            )
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"participant:{attempt.activation_id}",
                evidence_kind="participant_activation",
                summary=(
                    f"Activation {attempt.activation_id} retained "
                    f"{len(attempt.participants)} participant record(s)."
                ),
                source_refs=list(dict.fromkeys(source_refs)),
                payload={
                    "logical_time": attempt.logical_time,
                    "participants": participant_payload,
                },
            )
        )

    for work in result.exact_work:
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"mechanism:{work.work_id}",
                evidence_kind="mechanism_decision",
                summary=f"Exact work {work.work_id} committed.",
                source_refs=[
                    f"event:{event_id}" for event_id in work.core_event_ids
                ],
                payload={
                    "logical_time": work.logical_time,
                    "event_ids": list(work.core_event_ids),
                },
            )
        )

    temporal_states = _temporal_states(
        compiled.scenario.initial_state,
        result.core_result.events,
    )
    for boundary in compiled.scenario.analytical_boundaries:
        activity = project_boundary_activity(
            boundary,
            temporal_states,
            result.core_result.events,
        )
        event_ids = list(
            dict.fromkeys(
                [
                    *(item.event_id for item in activity.crossings),
                    *(
                        event_id
                        for episode in activity.episodes
                        for event_id in (
                            *episode.trigger_event_ids,
                            *episode.internal_event_ids,
                            *episode.external_result_event_ids,
                        )
                    ),
                ]
            )
        )
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"boundary:{boundary.boundary_id}:activity",
                evidence_kind="boundary_activity",
                summary=(
                    f"Exact boundary crossings and coordination episodes for "
                    f"{boundary.label}."
                ),
                source_refs=[f"event:{event_id}" for event_id in event_ids],
                payload=cast(dict[str, JsonValue], activity.model_dump(mode="json")),
            )
        )

    records.extend(
        [
            EvidenceRecordV1(
                evidence_ref="state:terminal",
                evidence_kind="terminal_state",
                summary="Digest and public outcome of the terminal world state.",
                source_refs=[f"event:{result.core_result.events[-1].event_id}"],
                payload={
                    "state_digest": result.core_result.final_state_digest,
                    "state_revision": final_state.revision,
                    "logical_time": final_state.logical_time,
                    "outcome_summary": result.outcome_summary,
                },
            ),
            EvidenceRecordV1(
                evidence_ref="completion:run",
                evidence_kind="completion",
                summary=result.completion.public_summary,
                source_refs=[
                    f"event:{event_id}"
                    for event_id in result.completion.evidence_event_ids
                ],
                payload=cast(
                    dict[str, JsonValue],
                    result.completion.model_dump(mode="json"),
                ),
            ),
        ]
    )

    payload = {
        "bundle_version": 1,
        "bundle_id": f"bundle_{result.run_id}",
        "run_id": result.run_id,
        "scenario_id": result.scenario_id,
        "scenario_fingerprint": result.scenario_fingerprint,
        "proposal_digest": compiled.proposal_digest,
        "scenario_spec": compiled.proposal.model_dump(mode="json"),
        "run_spec": run_spec.model_dump(mode="json"),
        "analysis_specs": [
            item.model_dump(mode="json") for item in analysis_specs
        ],
        "initial_state_digest": result.core_result.initial_state_digest,
        "terminal_state_digest": result.core_result.final_state_digest,
        "evidence_records": [
            item.model_dump(mode="json") for item in records
        ],
        "fidelity_assumptions": workflow.assumptions,
        "known_omissions": workflow.known_omissions,
        "fidelity_questions": compiled.scenario.fidelity_questions,
        "presentation_artifact_refs": [],
    }
    return RunEvidenceBundleV1.model_validate(
        {**payload, "record_digest": _digest(payload)}
    )


def build_waltzman_reference_readout(
    bundle: RunEvidenceBundleV1,
    result: ActiveRuntimeResult,
) -> FrameworkReadoutV1:
    """Adapt exact existing coordination measures to the common envelope."""

    _require_analysis(bundle, "waltzman_decision_environment_v1")
    exact_values = calculate_exact_values(result)
    definitions = {
        item.measure_id: item for item in COORDINATION_MEASUREMENT_SPEC.measures
    }
    known_refs = {item.evidence_ref for item in bundle.evidence_records}
    findings: list[FrameworkFindingV1] = []
    for raw_measure_id in EXACT_MEASURE_IDS:
        measure_id = cast(ExactMeasureId, raw_measure_id)
        value = exact_values[measure_id]
        event_refs = [
            f"event:{event_id}"
            for event_id in _event_ids_in_value(value)
            if f"event:{event_id}" in known_refs
        ]
        refs = event_refs or ["state:terminal", "completion:run"]
        definition = definitions[measure_id]
        findings.append(
            FrameworkFindingV1(
                finding_id=f"waltzman_{measure_id}",
                framework="waltzman",
                construct_id=definition.construct_name,
                method_class="exact",
                value=value,
                evidence_refs=list(dict.fromkeys(refs)),
                uncertainty=(
                    "Exact relative to this retained synthetic run; interpretation "
                    "of the construct remains analyst-dependent."
                ),
                limitations=definition.limitations,
                analysis_id="waltzman_decision_environment_v1",
            )
        )
    findings.append(
        FrameworkFindingV1(
            finding_id="waltzman_authority_divergence_scope",
            framework="waltzman",
            construct_id="trust_structure",
            method_class="exact",
            value=cast(
                JsonValue,
                {
                    "status": "not_computed",
                    "reason": (
                        "The retained authority-divergence definition is cross-run "
                        "and no ExperimentSpec is present."
                    ),
                },
            ),
            evidence_refs=[
                "configuration:analysis:waltzman_decision_environment_v1"
            ],
            uncertainty="No per-run authority-divergence value is asserted.",
            limitations=[
                "A later ExperimentSpec must define matching and aggregation before comparison."
            ],
            analysis_id="waltzman_decision_environment_v1",
        )
    )
    return _make_readout(
        framework="waltzman",
        analysis_id="waltzman_decision_environment_v1",
        bundle=bundle,
        findings=findings,
        limitations=[
            "Provider-free output includes exact retained measures only.",
            "Evidence-coded trust and hedging judgments remain unavailable until "
            "a separately retained coded-analysis call is authorized.",
            "One run does not support an invariant or causal influence claim.",
        ],
    )


def build_levin_reference_readout(
    bundle: RunEvidenceBundleV1,
    result: ActiveRuntimeResult,
) -> FrameworkReadoutV1:
    """Derive an observational collective-competence profile without an executor."""

    spec = _require_analysis(bundle, "levin_collective_competence_v1")
    assert spec.candidate_goal_ref is not None
    workflow = bundle.scenario_spec["workflow"]
    if not isinstance(workflow, dict):
        raise ValueError("ScenarioSpec workflow is malformed")
    goal = workflow.get("collective_goal")
    if not isinstance(goal, dict):
        raise ValueError("ScenarioSpec collective goal is malformed")
    acceptable = goal.get("acceptable_outcomes")
    if not isinstance(acceptable, list):
        raise ValueError("ScenarioSpec acceptable outcomes are malformed")
    final_status = result.core_result.final_state.fact(
        "external_decision_registry.received_status"
    ).value

    records = {item.evidence_ref: item for item in bundle.evidence_records}
    boundary_ref = f"boundary:{spec.candidate_boundary_ref}:activity"
    boundary = records.get(boundary_ref)
    if boundary is None:
        raise ValueError("Levin analysis lacks candidate boundary activity")
    crossings = boundary.payload.get("crossings")
    episodes = boundary.payload.get("episodes")
    if not isinstance(crossings, list) or not isinstance(episodes, list):
        raise ValueError("candidate boundary activity is malformed")

    events = result.core_result.events
    outcome_refs: dict[str, list[str]] = {}
    for event in events:
        outcome = event.details.get("outcome_code")
        if isinstance(outcome, str):
            outcome_refs.setdefault(outcome, []).append(f"event:{event.event_id}")
    meeting_refs = outcome_refs.get("meeting_wake_recorded", [])
    error_signal_refs = [
        *outcome_refs.get("issue_reopened", []),
        *outcome_refs.get("issue_open", []),
    ]
    correction_refs = [
        *outcome_refs.get("issue_resolved", []),
        *outcome_refs.get("verification_answered", []),
    ]
    adaptation_refs = [
        *outcome_refs.get("commitment_recorded", []),
        *outcome_refs.get("scope_threshold_recorded", []),
        *outcome_refs.get("partner_withdrawal_recorded", []),
    ]
    incoming = sum(
        isinstance(item, dict) and item.get("direction") == "incoming"
        for item in crossings
    )
    outgoing = sum(
        isinstance(item, dict) and item.get("direction") == "outgoing"
        for item in crossings
    )
    completed_episodes = sum(
        isinstance(item, dict) and item.get("status") == "completed"
        for item in episodes
    )
    scenario_state = result.core_result.final_state
    findings = [
        FrameworkFindingV1(
            finding_id="levin_goal_progress",
            framework="levin",
            construct_id="candidate_collective_goal",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "goal_id": spec.candidate_goal_ref,
                    "terminal_status": final_status,
                    "acceptable_outcome": final_status in acceptable,
                    "constraints": goal.get("constraints"),
                },
            ),
            evidence_refs=[
                "configuration:scenario",
                "state:terminal",
                "completion:run",
            ],
            uncertainty="Goal evaluation uses the reviewed outcome set and retained exact terminal state.",
            limitations=[
                "Goal achievement is configuration-relative and does not imply consciousness or unitary intent."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_boundary_activity",
            framework="levin",
            construct_id="boundary_inputs_outputs",
            method_class="exact",
            value=cast(
                JsonValue,
                {
                    "incoming_crossings": incoming,
                    "outgoing_crossings": outgoing,
                    "completed_coordination_episodes": completed_episodes,
                },
            ),
            evidence_refs=[boundary_ref],
            uncertainty="Crossings are exact only for the reviewed analytical boundary.",
            limitations=[
                "The boundary groups activity but never executes or thinks."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_collective_glue",
            framework="levin",
            construct_id="collective_glue",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "people": len(
                        [
                            item
                            for item in scenario_state.entities.values()
                            if item.entity_kind == "person"
                        ]
                    ),
                    "connections": len(scenario_state.connections),
                    "records": len(
                        [
                            item
                            for item in scenario_state.entities.values()
                            if item.entity_kind.endswith("_record")
                        ]
                    ),
                    "exact_mechanisms": len(scenario_state.mechanisms),
                    "information_representations": len(
                        scenario_state.representations
                    ),
                },
            ),
            evidence_refs=[
                "configuration:scenario",
                "state:initial",
                boundary_ref,
            ],
            uncertainty="Counts identify concrete coordination substrate, not its sufficiency in other worlds.",
            limitations=[
                "The profile does not assign a scalar amount of organizational agency."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_error_correction",
            framework="levin",
            construct_id="observed_error_correction",
            method_class="exact",
            value=cast(
                JsonValue,
                {
                    "error_signal_events": len(error_signal_refs),
                    "correction_events": len(correction_refs),
                    "correction_observed": bool(correction_refs),
                },
            ),
            evidence_refs=list(
                dict.fromkeys(
                    [*error_signal_refs, *correction_refs]
                    or ["completion:run"]
                )
            ),
            uncertainty="Only signals and corrections retained through exact issue or verification mechanisms count.",
            limitations=[
                "Absence in one run would not prove the system lacks corrective capacity."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_persistence_adaptation",
            framework="levin",
            construct_id="persistence_and_adaptation",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "meeting_cycles": len(meeting_refs),
                    "modeled_days": result.completion.logical_time
                    / MINUTES_PER_DAY
                    if result.completion is not None
                    else None,
                    "adaptation_events": len(adaptation_refs),
                    "terminal_status": final_status,
                },
            ),
            evidence_refs=list(
                dict.fromkeys(
                    [*meeting_refs, *adaptation_refs, "completion:run"]
                )
            ),
            uncertainty="Persistence and adaptation describe the realized path only.",
            limitations=[
                "The run does not establish robustness to an unmodeled disturbance."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_scale_scope",
            framework="levin",
            construct_id="scale_specific_competence",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "spatial_places": len(scenario_state.places),
                    "temporal_minutes": result.completion.logical_time
                    if result.completion is not None
                    else None,
                    "state_revisions": scenario_state.revision,
                    "candidate_boundary": spec.candidate_boundary_ref,
                },
            ),
            evidence_refs=[
                "configuration:scenario",
                "state:terminal",
                boundary_ref,
            ],
            uncertainty="Scope is bounded to the authored topology, horizon, and retained state variables.",
            limitations=[
                "No competence claim is made outside the configured state space."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
        FrameworkFindingV1(
            finding_id="levin_not_tested",
            framework="levin",
            construct_id="unobserved_agency_dimensions",
            method_class="exact",
            value=cast(
                JsonValue,
                {
                    "robustness": "not_tested",
                    "controlled_shock_recovery": "not_tested",
                    "member_replacement_tolerance": "not_tested",
                    "persuadability": "not_tested",
                },
            ),
            evidence_refs=[
                "configuration:analysis:levin_collective_competence_v1"
            ],
            uncertainty="These dimensions require an ExperimentSpec and additional runs.",
            limitations=[
                "Not tested is neither positive nor negative evidence."
            ],
            analysis_id="levin_collective_competence_v1",
        ),
    ]
    return _make_readout(
        framework="levin",
        analysis_id="levin_collective_competence_v1",
        bundle=bundle,
        findings=findings,
        limitations=[
            "This is an observational profile, not an agency score.",
            "Organizations remain execution-inert analytical boundaries.",
            "Controlled perturbation and comparison are post-MVP experiments.",
        ],
    )


def validate_readout_against_bundle(
    readout: FrameworkReadoutV1,
    bundle: RunEvidenceBundleV1,
) -> None:
    """Fail if a readout cites absent or presentation-only evidence."""

    if readout.bundle_id != bundle.bundle_id:
        raise ValueError("readout refers to another evidence bundle")
    if readout.bundle_digest != bundle.record_digest:
        raise ValueError("readout evidence-bundle digest mismatch")
    _require_analysis(bundle, readout.analysis_id)
    known = {item.evidence_ref for item in bundle.evidence_records}
    for finding in readout.findings:
        unknown = set(finding.evidence_refs) - known
        if unknown:
            raise ValueError(
                f"finding {finding.finding_id!r} cites unknown evidence "
                f"{sorted(unknown)!r}"
            )
        if set(finding.evidence_refs) & set(bundle.presentation_artifact_refs):
            raise ValueError("narrative presentation cannot support a finding")


def _make_readout(
    *,
    framework: FrameworkId,
    analysis_id: AnalysisId,
    bundle: RunEvidenceBundleV1,
    findings: list[FrameworkFindingV1],
    limitations: list[str],
) -> FrameworkReadoutV1:
    payload = {
        "readout_version": 1,
        "readout_id": f"{framework}_{bundle.bundle_id}",
        "framework": framework,
        "analysis_id": analysis_id,
        "bundle_id": bundle.bundle_id,
        "bundle_digest": bundle.record_digest,
        "findings": [item.model_dump(mode="json") for item in findings],
        "limitations": limitations,
    }
    readout = FrameworkReadoutV1.model_validate(
        {**payload, "record_digest": _digest(payload)}
    )
    validate_readout_against_bundle(readout, bundle)
    return readout


def _require_analysis(
    bundle: RunEvidenceBundleV1,
    analysis_id: AnalysisId,
) -> AnalysisSpecV1:
    matches = [
        item for item in bundle.analysis_specs if item.analysis_id == analysis_id
    ]
    if len(matches) != 1:
        raise ValueError(f"bundle does not select analysis {analysis_id!r}")
    return matches[0]


def _event_ids_in_value(value: JsonValue) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"event_id", "proposal_event_id", "terminal_event_id"} and isinstance(
                nested, str
            ):
                found.append(nested)
            elif key == "event_ids" and isinstance(nested, list):
                found.extend(item for item in nested if isinstance(item, str))
            else:
                found.extend(_event_ids_in_value(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_event_ids_in_value(nested))
    return list(dict.fromkeys(found))


def _digest(payload: Mapping[str, object] | dict[str, JsonValue]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
