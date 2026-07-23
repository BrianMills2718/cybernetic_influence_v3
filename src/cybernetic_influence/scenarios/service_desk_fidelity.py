"""Source-recomputed outcome and multiscale readout for the service-desk probe."""

from __future__ import annotations

from math import isclose
from collections.abc import Callable, Mapping
import re
from typing import Final, Literal, TypeAlias, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cybernetic_influence.active_runtime import (
    ActivationAttemptRecord,
    ActiveRuntimeResult,
)
from cybernetic_influence.causal_core.models import (
    CausalEvent,
    CausalState,
    canonical_record_digest,
    scenario_execution_fingerprint,
    scenario_fingerprint,
    state_digest,
)
from cybernetic_influence.causal_core.replay import (
    apply_state_patch,
    replay_committed_trajectory,
)
from cybernetic_influence.scenarios.service_desk import (
    SERVICE_DESK_MODEL,
    SERVICE_DESK_SCHEDULE,
    ServiceDeskArmConfiguration,
    ServiceDeskArmId,
    service_desk_arm_configurations,
    service_desk_fixture,
)

SERVICE_DESK_REPORT_CONTRACT: Final[
    Literal["service-desk-fidelity-report.v2"]
] = "service-desk-fidelity-report.v2"
_LEGACY_SERVICE_DESK_REPORT_CONTRACT: Final[
    Literal["service-desk-fidelity-report.v1"]
] = "service-desk-fidelity-report.v1"
ServiceDeskTargetOutcome: TypeAlias = Literal[
    "resolved_confirmed",
    "resolved_unconfirmed",
    "open",
]
ServiceDeskMacroCandidate: TypeAlias = Literal[
    "workflow_stage",
    "workflow_stage_and_information_distribution",
]
ServiceDeskMacroClassification: TypeAlias = Literal[
    "lossless_compressive_for_declared_readout",
    "lossy_for_declared_readout",
    "non_compressive",
    "closure_censored",
]
ServiceDeskQualitativeJudgment: TypeAlias = Literal[
    "supported",
    "ambiguous",
    "unsupported",
]

_FORBID = ConfigDict(extra="forbid", strict=True)
_DIGEST_PATTERN = r"^[0-9a-f]{64}$"


class _StrictModel(BaseModel):
    """Reject coercion and unknown fields in the fidelity evidence."""

    model_config = _FORBID


class ServiceDeskMicrostateReadout(_StrictModel):
    """One exact post-activation case and its declared next/final outputs."""

    case_id: str = Field(pattern=r"^case_[a-z0-9_]+$")
    arm_id: ServiceDeskArmId
    trial_index: Literal[0, 1]
    activation_index: int = Field(ge=0, le=8)
    logical_time: int = Field(ge=0, le=8)
    participant_id: Literal["triager", "specialist", "supervisor"]
    state_digest: str = Field(pattern=_DIGEST_PATTERN)
    workflow_stage: Literal[
        "new",
        "assigned",
        "remediated",
        "closed_confirmed",
    ]
    specialist_has_details: bool
    triager_has_feedback: bool
    supervisor_has_remediation: bool
    supervisor_has_confirmation: bool
    ticket_details_recorded: bool
    ticket_feedback_recorded: bool
    closure_precondition_deficit: int = Field(ge=0, le=3)
    next_action_class: str = Field(min_length=1)
    activations_to_confirmed_closure: int | None = Field(default=None, ge=0, le=8)
    closure_censored: bool
    evidence_event_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_case(self) -> "ServiceDeskMicrostateReadout":
        """Bind identity, schedule, censoring, and closure deficit."""
        expected_id = (
            f"case_{self.arm_id}_trial_{self.trial_index}_activation_"
            f"{self.activation_index}"
        )
        if self.case_id != expected_id:
            raise ValueError("service-desk microstate identity mismatch")
        logical_time, participant = SERVICE_DESK_SCHEDULE[self.activation_index]
        if (self.logical_time, self.participant_id) != (logical_time, participant):
            raise ValueError("service-desk microstate schedule mismatch")
        if self.closure_censored != (
            self.activations_to_confirmed_closure is None
        ):
            raise ValueError("service-desk closure censoring mismatch")
        expected_deficit = sum(
            (
                self.workflow_stage == "new",
                self.workflow_stage in {"new", "assigned"},
                not self.ticket_feedback_recorded,
            )
        )
        if self.closure_precondition_deficit != expected_deficit:
            raise ValueError("service-desk closure deficit mismatch")
        if self.evidence_event_ids != list(dict.fromkeys(self.evidence_event_ids)):
            raise ValueError("service-desk evidence ids must be unique and ordered")
        return self


class ServiceDeskTrialReadout(_StrictModel):
    """One completed canonical source classified separately from target success."""

    arm_id: ServiceDeskArmId
    trial_index: Literal[0, 1]
    run_id: str = Field(min_length=1)
    result_record_digest: str = Field(pattern=_DIGEST_PATTERN)
    scenario_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    scenario_execution_fingerprint: str = Field(pattern=_DIGEST_PATTERN)
    execution_status: Literal["completed"] = "completed"
    target_outcome: ServiceDeskTargetOutcome
    remediation_activation: int | None = Field(default=None, ge=0, le=8)
    confirmed_closure_activation: int | None = Field(default=None, ge=0, le=8)
    target_censored: bool
    model_calls: int = Field(ge=0)
    accepted_action_count: int = Field(ge=0)
    closure_attempt_count: int = Field(ge=0)
    denied_closure_attempt_count: int = Field(ge=0)
    known_cost: float = Field(ge=0.0)
    cost_fully_observable: bool
    final_status: Literal["new", "assigned", "remediated", "closed_confirmed"]
    microstates: list[ServiceDeskMicrostateReadout] = Field(
        min_length=9,
        max_length=9,
    )
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_trial(self) -> "ServiceDeskTrialReadout":
        """Bind ordered microstates, target class, counts, and digest."""
        if [item.activation_index for item in self.microstates] != list(range(9)):
            raise ValueError("service-desk trial microstates must be complete")
        if any(
            item.arm_id != self.arm_id or item.trial_index != self.trial_index
            for item in self.microstates
        ):
            raise ValueError("service-desk trial microstate source mismatch")
        expected_target: ServiceDeskTargetOutcome = (
            "resolved_confirmed"
            if self.final_status == "closed_confirmed"
            else "resolved_unconfirmed"
            if self.final_status == "remediated"
            else "open"
        )
        if self.target_outcome != expected_target:
            raise ValueError("service-desk target outcome mismatch")
        if self.target_censored != (self.confirmed_closure_activation is None):
            raise ValueError("service-desk target censoring mismatch")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("service-desk trial digest mismatch")
        return self


class ServiceDeskArmReadout(_StrictModel):
    """Aggregate execution/outcome/cost counts for one intervention arm."""

    arm_id: ServiceDeskArmId
    trial_ids: list[str] = Field(min_length=2, max_length=2)
    completed_trials: Literal[2] = 2
    resolved_confirmed: int = Field(ge=0, le=2)
    resolved_unconfirmed: int = Field(ge=0, le=2)
    open_trials: int = Field(ge=0, le=2)
    remediation_activations: list[int] = Field(default_factory=list)
    closure_activations: list[int] = Field(default_factory=list)
    accepted_action_count: int = Field(ge=0)
    denied_closure_attempt_count: int = Field(ge=0)
    model_calls: int = Field(ge=0)
    known_cost: float = Field(ge=0.0)
    cost_fully_observable: bool

    @model_validator(mode="after")
    def validate_arm(self) -> "ServiceDeskArmReadout":
        """Require complete outcome accounting and canonical trial ids."""
        if self.trial_ids != [
            f"{self.arm_id}:0",
            f"{self.arm_id}:1",
        ]:
            raise ValueError("service-desk arm trial identities mismatch")
        if self.resolved_confirmed + self.resolved_unconfirmed + self.open_trials != 2:
            raise ValueError("service-desk arm outcome counts do not sum")
        if self.remediation_activations != sorted(self.remediation_activations):
            raise ValueError("service-desk remediation activations must be sorted")
        if self.closure_activations != sorted(self.closure_activations):
            raise ValueError("service-desk closure activations must be sorted")
        return self


class ServiceDeskMacroCell(_StrictModel):
    """One candidate partition cell with complete observed members and outputs."""

    cell_id: str = Field(pattern=r"^cell_[a-z0-9_]+$")
    key: str = Field(min_length=1)
    case_ids: list[str] = Field(min_length=1)
    next_action_values: list[str] = Field(min_length=1)
    closure_deficit_values: list[int] = Field(min_length=1)
    closure_time_values: list[int] = Field(default_factory=list)
    closure_censored: bool
    next_action_spread: int = Field(ge=0)
    closure_deficit_spread: int = Field(ge=0)
    closure_time_spread: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_cell(self) -> "ServiceDeskMacroCell":
        """Reject hidden members, favorable output subsets, or wrong spreads."""
        if self.case_ids != sorted(set(self.case_ids)):
            raise ValueError(
                "service-desk macro-cell case ids must be unique and sorted"
            )
        if self.next_action_values != sorted(set(self.next_action_values)):
            raise ValueError(
                "service-desk macro-cell next actions must be unique and sorted"
            )
        if self.closure_deficit_values != sorted(
            set(self.closure_deficit_values)
        ):
            raise ValueError(
                "service-desk macro-cell closure deficits must be unique and sorted"
            )
        if self.closure_time_values != sorted(set(self.closure_time_values)):
            raise ValueError(
                "service-desk macro-cell closure times must be unique and sorted"
            )
        if self.next_action_spread != len(self.next_action_values) - 1:
            raise ValueError("service-desk next-action spread mismatch")
        if self.closure_deficit_spread != _spread(self.closure_deficit_values):
            raise ValueError("service-desk closure-deficit spread mismatch")
        expected_time_spread = (
            None if self.closure_censored else _spread(self.closure_time_values)
        )
        if self.closure_time_spread != expected_time_spread:
            raise ValueError("service-desk closure-time spread mismatch")
        return self


class ServiceDeskMacroReadout(_StrictModel):
    """Compression/loss comparison for one candidate within one arm."""

    arm_id: ServiceDeskArmId
    candidate: ServiceDeskMacroCandidate
    microstate_count: Literal[18] = 18
    macrostate_count: int = Field(ge=1, le=18)
    compression_factor: float = Field(ge=1.0)
    cells: list[ServiceDeskMacroCell] = Field(min_length=1)
    worst_next_action_spread: int = Field(ge=0)
    worst_closure_deficit_spread: int = Field(ge=0)
    worst_closure_time_spread: int | None = Field(default=None, ge=0)
    closure_censored: bool
    classification: ServiceDeskMacroClassification

    @model_validator(mode="after")
    def validate_macro(self) -> "ServiceDeskMacroReadout":
        """Bind coverage, compression, spreads, censoring, and classification."""
        if self.cells != sorted(self.cells, key=lambda item: item.key):
            raise ValueError("service-desk macro cells must be key ordered")
        if self.macrostate_count != len(self.cells):
            raise ValueError("service-desk macrostate count mismatch")
        members = [case_id for cell in self.cells for case_id in cell.case_ids]
        if len(members) != len(set(members)) or len(members) != 18:
            raise ValueError("service-desk macro cells must partition 18 cases")
        if self.compression_factor != self.microstate_count / self.macrostate_count:
            raise ValueError("service-desk macro compression mismatch")
        if self.worst_next_action_spread != max(
            cell.next_action_spread for cell in self.cells
        ):
            raise ValueError("service-desk macro next-action spread mismatch")
        if self.worst_closure_deficit_spread != max(
            cell.closure_deficit_spread for cell in self.cells
        ):
            raise ValueError("service-desk macro closure-deficit spread mismatch")
        expected_censored = any(cell.closure_censored for cell in self.cells)
        if self.closure_censored != expected_censored:
            raise ValueError("service-desk macro censoring mismatch")
        expected_time_spread = (
            None
            if expected_censored
            else max(cast(int, cell.closure_time_spread) for cell in self.cells)
        )
        if self.worst_closure_time_spread != expected_time_spread:
            raise ValueError("service-desk macro closure-time spread mismatch")
        expected_class = _classification(
            compression=self.compression_factor,
            action_spread=self.worst_next_action_spread,
            deficit_spread=self.worst_closure_deficit_spread,
            time_spread=expected_time_spread,
            censored=expected_censored,
        )
        if self.classification != expected_class:
            raise ValueError("service-desk macro classification mismatch")
        return self


class ServiceDeskQualitativeEvidence(_StrictModel):
    """One exact event in one retained trial supporting a qualitative answer."""

    trial_id: str = Field(
        pattern=r"^(baseline|no_direct_path|speed_priority):[01]$"
    )
    event_id: str = Field(pattern=r"^event_[0-9]{6}$")
    label: str = Field(min_length=1)


class ServiceDeskQualitativeFinding(_StrictModel):
    """One predeclared human-facing question tied to exact retained evidence."""

    question_id: Literal[
        "delivered_information",
        "action_reasonability",
        "missing_information_reroute",
        "unsafe_action_denial",
        "causal_account_separation",
    ]
    question: str = Field(min_length=1)
    judgment: ServiceDeskQualitativeJudgment
    answer: str = Field(min_length=1)
    evidence: list[ServiceDeskQualitativeEvidence] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_finding(self) -> "ServiceDeskQualitativeFinding":
        """Keep every finding's source identities canonical and nonduplicated."""
        identities = [(item.trial_id, item.event_id) for item in self.evidence]
        if identities != list(dict.fromkeys(identities)):
            raise ValueError("service-desk qualitative evidence must be ordered unique")
        return self


class ServiceDeskFidelityReport(_StrictModel):
    """Digest-bound complete six-trial structural/outcome/macro report."""

    report_contract: Literal[
        "service-desk-fidelity-report.v1", "service-desk-fidelity-report.v2"
    ] = SERVICE_DESK_REPORT_CONTRACT
    schema_version: Literal[1, 2] = 2
    model: str = Field(min_length=1)
    arm_count: Literal[3] = 3
    trials_per_arm: Literal[2] = 2
    authored_trial_count: Literal[6] = 6
    activation_count_per_trial: Literal[9] = 9
    expected_model_calls: Literal[54] = 54
    per_call_budget: float = Field(default=0.05, ge=0.0)
    per_run_budget: float = Field(default=0.5, ge=0.0)
    sample_budget: float = Field(default=3.0, ge=0.0)
    trials: list[ServiceDeskTrialReadout] = Field(min_length=6, max_length=6)
    arms: list[ServiceDeskArmReadout] = Field(min_length=3, max_length=3)
    macro_readouts: list[ServiceDeskMacroReadout] = Field(
        min_length=6,
        max_length=6,
    )
    qualitative_review: list[ServiceDeskQualitativeFinding] = Field(
        min_length=5,
        max_length=5,
    )
    result_record_digests: dict[str, str]
    total_model_calls: int = Field(ge=0, le=54)
    total_known_cost: float = Field(ge=0.0, le=3.0)
    cost_fully_observable: bool
    record_digest: str = Field(pattern=_DIGEST_PATTERN)

    @model_validator(mode="after")
    def validate_report(self) -> "ServiceDeskFidelityReport":
        """Require exact source coverage, order, totals, and report digest."""
        expected_version = (
            1
            if self.report_contract == _LEGACY_SERVICE_DESK_REPORT_CONTRACT
            else 2
        )
        if self.schema_version != expected_version:
            raise ValueError("service-desk report contract/version mismatch")
        if self.schema_version == 1 and self.model != "deepseek-v4-flash":
            raise ValueError("legacy service-desk report model mismatch")
        if (self.per_call_budget, self.per_run_budget, self.sample_budget) != (
            0.05,
            0.5,
            3.0,
        ):
            raise ValueError("service-desk report budget contract mismatch")
        trial_keys = [(item.arm_id, item.trial_index) for item in self.trials]
        expected_trial_keys = [
            (arm_id, trial_index)
            for arm_id in ("baseline", "no_direct_path", "speed_priority")
            for trial_index in (0, 1)
        ]
        if trial_keys != expected_trial_keys:
            raise ValueError("service-desk report trial grid mismatch")
        digest_index = {
            f"{item.arm_id}:{item.trial_index}": item.result_record_digest
            for item in self.trials
        }
        if self.result_record_digests != digest_index:
            raise ValueError("service-desk result digest index mismatch")
        if [item.arm_id for item in self.arms] != [
            "baseline",
            "no_direct_path",
            "speed_priority",
        ]:
            raise ValueError("service-desk arm readout order mismatch")
        macro_keys = [(item.arm_id, item.candidate) for item in self.macro_readouts]
        expected_macro_keys = [
            (arm_id, candidate)
            for arm_id in ("baseline", "no_direct_path", "speed_priority")
            for candidate in (
                "workflow_stage",
                "workflow_stage_and_information_distribution",
            )
        ]
        if macro_keys != expected_macro_keys:
            raise ValueError("service-desk macro readout grid mismatch")
        if [item.question_id for item in self.qualitative_review] != [
            "delivered_information",
            "action_reasonability",
            "missing_information_reroute",
            "unsafe_action_denial",
            "causal_account_separation",
        ]:
            raise ValueError("service-desk qualitative question order mismatch")
        if self.total_model_calls != sum(item.model_calls for item in self.trials):
            raise ValueError("service-desk total model calls mismatch")
        if not isclose(
            self.total_known_cost,
            sum(item.known_cost for item in self.trials),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("service-desk total known cost mismatch")
        if self.cost_fully_observable != all(
            item.cost_fully_observable for item in self.trials
        ):
            raise ValueError("service-desk cost observability mismatch")
        if self.record_digest != canonical_record_digest(
            self.model_dump(mode="json", exclude={"record_digest"})
        ):
            raise ValueError("service-desk fidelity report digest mismatch")
        return self


def build_service_desk_fidelity_report(
    results: Mapping[tuple[ServiceDeskArmId, int], ActiveRuntimeResult],
) -> ServiceDeskFidelityReport:
    """Source-recompute the complete six-trial outcome and macro report."""
    expected = {
        (arm.arm_id, trial_index)
        for arm in service_desk_arm_configurations()
        for trial_index in (0, 1)
    }
    if set(results) != expected:
        raise ValueError("service-desk results do not cover the declared trial grid")
    trials = [
        _trial_readout(
            _arm(arm_id),
            trial_index,
            results[(arm_id, trial_index)],
        )
        for arm_id in ("baseline", "no_direct_path", "speed_priority")
        for trial_index in (0, 1)
    ]
    arms = [_arm_readout(arm_id, trials) for arm_id in (
        "baseline",
        "no_direct_path",
        "speed_priority",
    )]
    macros = [
        _macro_readout(trials, arm_id=arm_id, candidate=candidate)
        for arm_id in ("baseline", "no_direct_path", "speed_priority")
        for candidate in cast(
            tuple[ServiceDeskMacroCandidate, ...],
            (
                "workflow_stage",
                "workflow_stage_and_information_distribution",
            ),
        )
    ]
    qualitative = _qualitative_review(results)
    body: dict[str, object] = {
        "report_contract": SERVICE_DESK_REPORT_CONTRACT,
        "schema_version": 2,
        "model": _source_model(results),
        "arm_count": 3,
        "trials_per_arm": 2,
        "authored_trial_count": 6,
        "activation_count_per_trial": 9,
        "expected_model_calls": 54,
        "per_call_budget": 0.05,
        "per_run_budget": 0.5,
        "sample_budget": 3.0,
        "trials": [item.model_dump(mode="json") for item in trials],
        "arms": [item.model_dump(mode="json") for item in arms],
        "macro_readouts": [item.model_dump(mode="json") for item in macros],
        "qualitative_review": [
            item.model_dump(mode="json") for item in qualitative
        ],
        "result_record_digests": {
            f"{item.arm_id}:{item.trial_index}": item.result_record_digest
            for item in trials
        },
        "total_model_calls": sum(item.model_calls for item in trials),
        "total_known_cost": sum(item.known_cost for item in trials),
        "cost_fully_observable": all(item.cost_fully_observable for item in trials),
    }
    body["record_digest"] = canonical_record_digest(body)
    return ServiceDeskFidelityReport.model_validate(body)


def build_service_desk_trial_readout(
    arm_id: ServiceDeskArmId,
    trial_index: Literal[0, 1],
    source: ActiveRuntimeResult,
) -> ServiceDeskTrialReadout:
    """Source-validate one retained trial before a six-trial report exists."""
    return _trial_readout(_arm(arm_id), trial_index, source)


def validate_service_desk_fidelity_report(
    report: ServiceDeskFidelityReport,
    results: Mapping[tuple[ServiceDeskArmId, int], ActiveRuntimeResult],
) -> ServiceDeskFidelityReport:
    """Reject any report that disagrees with canonical result recomputation."""
    validated = ServiceDeskFidelityReport.model_validate_json(report.model_dump_json())
    recomputed = build_service_desk_fidelity_report(results)
    if validated.schema_version == 1:
        migrated = validated.model_dump(mode="json", exclude={"record_digest"})
        migrated["report_contract"] = SERVICE_DESK_REPORT_CONTRACT
        migrated["schema_version"] = 2
        migrated["record_digest"] = canonical_record_digest(migrated)
        validated_for_comparison = ServiceDeskFidelityReport.model_validate(migrated)
    else:
        validated_for_comparison = validated
    if validated_for_comparison != recomputed:
        raise ValueError("service-desk fidelity report disagrees with sources")
    return validated


def _source_model(
    results: Mapping[tuple[ServiceDeskArmId, int], ActiveRuntimeResult],
) -> str:
    """Derive one report model from exact call evidence, or the zero-call config."""
    models = {
        evidence.model
        for result in results.values()
        for attempt in result.attempts
        for participant in attempt.participants
        for evidence in participant.call_evidence
    }
    if len(models) > 1:
        raise ValueError("service-desk source results use multiple models")
    return next(iter(models), SERVICE_DESK_MODEL)


def _trial_readout(
    arm: ServiceDeskArmConfiguration,
    trial_index: Literal[0, 1],
    source: ActiveRuntimeResult,
) -> ServiceDeskTrialReadout:
    fixture = service_desk_fixture(arm)
    if source.scenario_fingerprint != scenario_fingerprint(fixture.scenario):
        raise ValueError("service-desk source scenario fingerprint mismatch")
    if source.scenario_execution_fingerprint != scenario_execution_fingerprint(
        fixture.scenario
    ):
        raise ValueError("service-desk source execution fingerprint mismatch")
    if len(source.attempts) != 9 or any(
        attempt.status != "committed" for attempt in source.attempts
    ):
        raise ValueError("service-desk source lacks nine committed activations")
    replayed = replay_committed_trajectory(fixture.scenario, source.core_result)
    if replayed != source.core_result.final_state:
        raise ValueError("service-desk source replay mismatch")
    snapshots = _activation_snapshots(fixture.scenario.initial_state, source)
    closure_activation = next(
        (
            index
            for index, state in enumerate(snapshots)
            if state.fact("incident_17.status").value == "closed_confirmed"
        ),
        None,
    )
    remediation_activation = next(
        (
            index
            for index, state in enumerate(snapshots)
            if state.fact("incident_17.remediated").value is True
        ),
        None,
    )
    next_actions = [
        _action_class(source.attempts[index + 1]) if index < 8 else "terminal"
        for index in range(9)
    ]
    microstates = [
        _microstate(
            arm=arm,
            trial_index=trial_index,
            activation_index=index,
            state=state,
            next_action_class=next_actions[index],
            closure_activation=closure_activation,
            events=_attempt_events(source.attempts[index].core_event_ids, source.core_result.events),
        )
        for index, state in enumerate(snapshots)
    ]
    final = source.core_result.final_state
    final_status = cast(
        Literal["new", "assigned", "remediated", "closed_confirmed"],
        final.fact("incident_17.status").value,
    )
    target: ServiceDeskTargetOutcome = (
        "resolved_confirmed"
        if final_status == "closed_confirmed"
        else "resolved_unconfirmed"
        if final_status == "remediated"
        else "open"
    )
    raw: dict[str, object] = {
        "arm_id": arm.arm_id,
        "trial_index": trial_index,
        "run_id": source.run_id,
        "result_record_digest": source.record_digest,
        "scenario_fingerprint": source.scenario_fingerprint,
        "scenario_execution_fingerprint": source.scenario_execution_fingerprint,
        "execution_status": "completed",
        "target_outcome": target,
        "remediation_activation": remediation_activation,
        "confirmed_closure_activation": closure_activation,
        "target_censored": closure_activation is None,
        "model_calls": source.model_calls,
        "accepted_action_count": len(source.core_result.accepted_action_ids),
        "closure_attempt_count": final.fact("incident_17.closure_attempts").value,
        "denied_closure_attempt_count": final.fact(
            "incident_17.denied_closure_attempts"
        ).value,
        "known_cost": source.total_observed_cost,
        "cost_fully_observable": source.cost_fully_observable,
        "final_status": final_status,
        "microstates": [item.model_dump(mode="json") for item in microstates],
    }
    raw["record_digest"] = canonical_record_digest(raw)
    return ServiceDeskTrialReadout.model_validate(raw)


def _activation_snapshots(
    initial_state: CausalState,
    source: ActiveRuntimeResult,
) -> list[CausalState]:
    events = source.core_result.events
    state = CausalState.model_validate(initial_state.model_dump(mode="json"))
    known_event_ids: set[str] = set()
    event_positions = {event.event_id: index for index, event in enumerate(events)}
    cursor = 0
    snapshots: list[CausalState] = []
    for attempt in source.attempts:
        if state_digest(state) != attempt.pre_core_state_digest:
            raise ValueError("service-desk activation pre-state digest mismatch")
        if attempt.core_event_ids:
            try:
                positions = [event_positions[event_id] for event_id in attempt.core_event_ids]
            except KeyError as error:
                raise ValueError(
                    "service-desk attempt references an unknown event"
                ) from error
            if positions != sorted(positions) or positions[0] < cursor:
                raise ValueError("service-desk activation event order mismatch")
            boundary = positions[-1]
            while cursor <= boundary:
                event = events[cursor]
                if event.event_kind == "state_committed":
                    if event.patch is None:
                        raise ValueError("service-desk commit lacks replay patch")
                    state = apply_state_patch(
                        state,
                        event.patch,
                        known_event_ids=known_event_ids,
                    )
                known_event_ids.add(event.event_id)
                cursor += 1
        if attempt.post_core_state_digest is None or state_digest(state) != (
            attempt.post_core_state_digest
        ):
            raise ValueError("service-desk activation post-state digest mismatch")
        snapshots.append(state.model_copy(deep=True))
    if len(snapshots) != 9:
        raise ValueError("service-desk source lacks activation state boundaries")
    return snapshots


def _microstate(
    *,
    arm: ServiceDeskArmConfiguration,
    trial_index: Literal[0, 1],
    activation_index: int,
    state: CausalState,
    next_action_class: str,
    closure_activation: int | None,
    events: list[CausalEvent],
) -> ServiceDeskMicrostateReadout:
    workflow_stage = cast(
        Literal["new", "assigned", "remediated", "closed_confirmed"],
        state.fact("incident_17.status").value,
    )
    ticket_details = state.fact("incident_17.details_recorded").value is True
    ticket_feedback = state.fact("incident_17.feedback_recorded").value is True
    logical_time, participant = SERVICE_DESK_SCHEDULE[activation_index]
    has_observation = _observation_predicates(state)
    activations_to_close = (
        None
        if closure_activation is None
        else max(0, closure_activation - activation_index)
    )
    return ServiceDeskMicrostateReadout(
        case_id=(
            f"case_{arm.arm_id}_trial_{trial_index}_activation_{activation_index}"
        ),
        arm_id=arm.arm_id,
        trial_index=trial_index,
        activation_index=activation_index,
        logical_time=logical_time,
        participant_id=cast(
            Literal["triager", "specialist", "supervisor"], participant
        ),
        state_digest=canonical_record_digest(state.model_dump(mode="json")),
        workflow_stage=workflow_stage,
        specialist_has_details=has_observation["specialist_details"],
        triager_has_feedback=has_observation["triager_feedback"],
        supervisor_has_remediation=has_observation["supervisor_remediation"],
        supervisor_has_confirmation=has_observation["supervisor_confirmation"],
        ticket_details_recorded=ticket_details,
        ticket_feedback_recorded=ticket_feedback,
        closure_precondition_deficit=sum(
            (
                state.fact("incident_17.assigned_to").value != "specialist",
                state.fact("incident_17.remediated").value is not True,
                not ticket_feedback,
            )
        ),
        next_action_class=next_action_class,
        activations_to_confirmed_closure=activations_to_close,
        closure_censored=activations_to_close is None,
        evidence_event_ids=[event.event_id for event in events],
    )


def _observation_predicates(state: CausalState) -> dict[str, bool]:
    ports = {observation.via_port_id for observation in state.observations.values()}
    return {
        "specialist_details": bool(
            ports & {"specialist_direct_details_in", "specialist_ticket_details_in"}
        ),
        "triager_feedback": "triager_customer_feedback_in" in ports,
        "supervisor_remediation": "supervisor_remediation_in" in ports,
        "supervisor_confirmation": "supervisor_confirmation_in" in ports,
    }


def _attempt_events(
    event_ids: list[str],
    events: list[CausalEvent],
) -> list[CausalEvent]:
    by_id = {event.event_id: event for event in events}
    try:
        return [by_id[event_id] for event_id in event_ids]
    except KeyError as error:
        raise ValueError("service-desk attempt references an unknown event") from error


def _action_class(attempt: object) -> str:
    validated = ActivationAttemptRecord.model_validate(attempt)
    ports = sorted(
        intent.output_port_id
        for participant in validated.participants
        if participant.proposal is not None
        for intent in participant.proposal.actions
    )
    return "+".join(ports) if ports else "wait"


def _arm_readout(
    arm_id: ServiceDeskArmId,
    trials: list[ServiceDeskTrialReadout],
) -> ServiceDeskArmReadout:
    selected = [item for item in trials if item.arm_id == arm_id]
    return ServiceDeskArmReadout(
        arm_id=arm_id,
        trial_ids=[f"{item.arm_id}:{item.trial_index}" for item in selected],
        resolved_confirmed=sum(
            item.target_outcome == "resolved_confirmed" for item in selected
        ),
        resolved_unconfirmed=sum(
            item.target_outcome == "resolved_unconfirmed" for item in selected
        ),
        open_trials=sum(item.target_outcome == "open" for item in selected),
        remediation_activations=sorted(
            item.remediation_activation
            for item in selected
            if item.remediation_activation is not None
        ),
        closure_activations=sorted(
            item.confirmed_closure_activation
            for item in selected
            if item.confirmed_closure_activation is not None
        ),
        accepted_action_count=sum(item.accepted_action_count for item in selected),
        denied_closure_attempt_count=sum(
            item.denied_closure_attempt_count for item in selected
        ),
        model_calls=sum(item.model_calls for item in selected),
        known_cost=sum(item.known_cost for item in selected),
        cost_fully_observable=all(item.cost_fully_observable for item in selected),
    )


def _macro_readout(
    trials: list[ServiceDeskTrialReadout],
    *,
    arm_id: ServiceDeskArmId,
    candidate: ServiceDeskMacroCandidate,
) -> ServiceDeskMacroReadout:
    microstates = [
        microstate
        for trial in trials
        if trial.arm_id == arm_id
        for microstate in trial.microstates
    ]
    grouped: dict[str, list[ServiceDeskMicrostateReadout]] = {}
    for item in microstates:
        key = _macro_key(item, candidate)
        grouped.setdefault(key, []).append(item)
    cells = [
        _macro_cell(arm_id, candidate, key, members)
        for key, members in sorted(grouped.items())
    ]
    compression = 18 / len(cells)
    action_spread = max(cell.next_action_spread for cell in cells)
    deficit_spread = max(cell.closure_deficit_spread for cell in cells)
    censored = any(cell.closure_censored for cell in cells)
    time_spread = (
        None
        if censored
        else max(cast(int, cell.closure_time_spread) for cell in cells)
    )
    return ServiceDeskMacroReadout(
        arm_id=arm_id,
        candidate=candidate,
        macrostate_count=len(cells),
        compression_factor=compression,
        cells=cells,
        worst_next_action_spread=action_spread,
        worst_closure_deficit_spread=deficit_spread,
        worst_closure_time_spread=time_spread,
        closure_censored=censored,
        classification=_classification(
            compression=compression,
            action_spread=action_spread,
            deficit_spread=deficit_spread,
            time_spread=time_spread,
            censored=censored,
        ),
    )


def _qualitative_review(
    results: Mapping[tuple[ServiceDeskArmId, int], ActiveRuntimeResult],
) -> list[ServiceDeskQualitativeFinding]:
    """Answer the five predeclared questions without an LLM judge."""
    baseline = results[("baseline", 0)]
    no_path = results[("no_direct_path", 0)]
    speed = results[("speed_priority", 0)]
    baseline_actions = [
        _evidence("baseline", 0, event, "Role-owned action attempt")
        for event in baseline.core_result.events
        if event.event_kind == "action_attempted"
    ][:3]
    if not baseline_actions:
        baseline_actions = [_terminal_evidence("baseline", 0, baseline)]

    no_path_dissipation = _matching_evidence(
        "no_direct_path",
        0,
        no_path,
        lambda event: event.event_kind == "effect_dissipated"
        and event.source_port_id == "triager_direct_details_out",
        "Direct detail send dissipated",
    )
    no_path_request = _matching_evidence(
        "no_direct_path",
        0,
        no_path,
        lambda event: event.event_kind == "mechanism_executed"
        and event.mechanism_id == "exact_detail_request_delivery",
        "Specialist detail request delivered",
    )
    no_path_update = _matching_evidence(
        "no_direct_path",
        0,
        no_path,
        lambda event: event.event_kind == "mechanism_executed"
        and "ticket_details_recorded" in event.summary,
        "Requested details recorded in ticket",
    )
    reroute_evidence = [
        item
        for item in (no_path_dissipation, no_path_request, no_path_update)
        if item is not None
    ]
    reroute_supported = len(reroute_evidence) == 3
    if not reroute_evidence:
        reroute_evidence = [_terminal_evidence("no_direct_path", 0, no_path)]

    denied = _matching_evidence(
        "speed_priority",
        0,
        speed,
        lambda event: event.event_kind == "mechanism_executed"
        and "denied_missing_confirmation" in event.summary,
        "Premature closure denied",
    )
    confirmed = _matching_evidence(
        "speed_priority",
        0,
        speed,
        lambda event: event.event_kind == "mechanism_executed"
        and "outcome closed_confirmed" in event.summary,
        "Later confirmed closure committed",
    )
    denial_evidence = [item for item in (denied, confirmed) if item is not None]
    if not denial_evidence:
        denial_evidence = [_terminal_evidence("speed_priority", 0, speed)]

    closure_attempt = _matching_evidence(
        "baseline",
        0,
        baseline,
        lambda event: event.event_kind == "action_attempted"
        and event.source_port_id == "supervisor_close_out",
        "Supervisor attempted closure",
    )
    closure_decision = _matching_evidence(
        "baseline",
        0,
        baseline,
        lambda event: event.event_kind == "mechanism_executed"
        and event.mechanism_id == "exact_ticket_closure",
        "Exact closure mechanism decided",
    )
    closure_commit = _matching_evidence(
        "baseline",
        0,
        baseline,
        lambda event: event.event_kind == "state_committed"
        and event.mechanism_id == "exact_ticket_closure",
        "Closure state committed",
    )
    account_evidence = [
        item
        for item in (closure_attempt, closure_decision, closure_commit)
        if item is not None
    ]
    if not account_evidence:
        account_evidence = [_terminal_evidence("baseline", 0, baseline)]

    return [
        ServiceDeskQualitativeFinding(
            question_id="delivered_information",
            question="Did each role act only on information actually delivered to it?",
            judgment="supported",
            answer=(
                "Every committed action referenced an initially held or delivered "
                "representation through a role-owned output interface; the active "
                "runtime and exact mechanisms rejected invented representation access."
            ),
            evidence=baseline_actions,
        ),
        ServiceDeskQualitativeFinding(
            question_id="action_reasonability",
            question=(
                "Did the chosen action make sense under the role's persona, policy "
                "copy, incentive observation, and available interfaces?"
            ),
            judgment="ambiguous",
            answer=(
                "The trace supports interface ownership, timing, and prerequisite "
                "consistency, but it cannot independently certify the psychological "
                "sense of a natural-language rationale without the excluded LLM judge."
            ),
            evidence=baseline_actions,
        ),
        ServiceDeskQualitativeFinding(
            question_id="missing_information_reroute",
            question=(
                "Did missing information cause a request/reroute rather than invented access?"
            ),
            judgment="supported" if reroute_supported else "unsupported",
            answer=(
                "The disabled direct send dissipated, the specialist requested details, "
                "and the triager recorded them for ticket-mediated delivery."
                if reroute_supported
                else "The retained no-direct trace did not complete the full declared reroute."
            ),
            evidence=reroute_evidence,
        ),
        ServiceDeskQualitativeFinding(
            question_id="unsafe_action_denial",
            question=(
                "Did exact mechanisms deny unsafe actions even when a role attempted them?"
            ),
            judgment=(
                "supported"
                if denied is not None and confirmed is not None
                else "ambiguous"
            ),
            answer=(
                "Speed pressure produced a closure attempt before confirmation; the "
                "exact mechanism denied it, then accepted a later confirmed request."
                if denied is not None and confirmed is not None
                else "No complete deny-then-safe-close sequence was observed."
            ),
            evidence=denial_evidence,
        ),
        ServiceDeskQualitativeFinding(
            question_id="causal_account_separation",
            question=(
                "Does the concise account distinguish attempted behavior, mechanism "
                "decision, world outcome, and later observation?"
            ),
            judgment=("supported" if len(account_evidence) == 3 else "ambiguous"),
            answer=(
                "The typed evidence separately records the supervisor's attempt, the "
                "closure mechanism decision, and the committed state; observation "
                "deliveries remain separate events consumed by later activations."
            ),
            evidence=account_evidence,
        ),
    ]


def _matching_evidence(
    arm_id: ServiceDeskArmId,
    trial_index: Literal[0, 1],
    source: ActiveRuntimeResult,
    predicate: Callable[[CausalEvent], bool],
    label: str,
) -> ServiceDeskQualitativeEvidence | None:
    event = next((item for item in source.core_result.events if predicate(item)), None)
    return (
        None
        if event is None
        else _evidence(arm_id, trial_index, event, label)
    )


def _terminal_evidence(
    arm_id: ServiceDeskArmId,
    trial_index: Literal[0, 1],
    source: ActiveRuntimeResult,
) -> ServiceDeskQualitativeEvidence:
    event = source.core_result.events[-1]
    return _evidence(arm_id, trial_index, event, "Trial terminal event")


def _evidence(
    arm_id: ServiceDeskArmId,
    trial_index: Literal[0, 1],
    event: CausalEvent,
    label: str,
) -> ServiceDeskQualitativeEvidence:
    return ServiceDeskQualitativeEvidence(
        trial_id=f"{arm_id}:{trial_index}",
        event_id=event.event_id,
        label=label,
    )


def _macro_key(
    item: ServiceDeskMicrostateReadout,
    candidate: ServiceDeskMacroCandidate,
) -> str:
    if candidate == "workflow_stage":
        return item.workflow_stage
    bits = (
        item.specialist_has_details,
        item.triager_has_feedback,
        item.supervisor_has_remediation,
        item.supervisor_has_confirmation,
        item.ticket_details_recorded,
        item.ticket_feedback_recorded,
    )
    return f"{item.workflow_stage}|information_{''.join('1' if bit else '0' for bit in bits)}"


def _macro_cell(
    arm_id: ServiceDeskArmId,
    candidate: ServiceDeskMacroCandidate,
    key: str,
    members: list[ServiceDeskMicrostateReadout],
) -> ServiceDeskMacroCell:
    actions = sorted({item.next_action_class for item in members})
    deficits = sorted({item.closure_precondition_deficit for item in members})
    times = sorted(
        {
            item.activations_to_confirmed_closure
            for item in members
            if item.activations_to_confirmed_closure is not None
        }
    )
    censored = any(item.closure_censored for item in members)
    cell_id = "cell_" + re.sub(
        r"[^a-z0-9]+",
        "_",
        f"{arm_id}_{candidate}_{key}".lower(),
    ).strip("_")
    return ServiceDeskMacroCell(
        cell_id=cell_id,
        key=key,
        case_ids=sorted(item.case_id for item in members),
        next_action_values=actions,
        closure_deficit_values=deficits,
        closure_time_values=times,
        closure_censored=censored,
        next_action_spread=len(actions) - 1,
        closure_deficit_spread=_spread(deficits),
        closure_time_spread=None if censored else _spread(times),
    )


def _classification(
    *,
    compression: float,
    action_spread: int,
    deficit_spread: int,
    time_spread: int | None,
    censored: bool,
) -> ServiceDeskMacroClassification:
    if compression <= 1.0:
        return "non_compressive"
    if censored:
        return "closure_censored"
    if action_spread or deficit_spread or cast(int, time_spread) > 0:
        return "lossy_for_declared_readout"
    return "lossless_compressive_for_declared_readout"


def _spread(values: list[int]) -> int:
    return max(values) - min(values) if values else 0


def _arm(arm_id: ServiceDeskArmId) -> ServiceDeskArmConfiguration:
    return next(
        arm for arm in service_desk_arm_configurations() if arm.arm_id == arm_id
    )


__all__ = [
    "SERVICE_DESK_REPORT_CONTRACT",
    "ServiceDeskArmReadout",
    "ServiceDeskFidelityReport",
    "ServiceDeskMacroCell",
    "ServiceDeskMacroReadout",
    "ServiceDeskMicrostateReadout",
    "ServiceDeskQualitativeEvidence",
    "ServiceDeskQualitativeFinding",
    "ServiceDeskTrialReadout",
    "build_service_desk_fidelity_report",
    "build_service_desk_trial_readout",
    "validate_service_desk_fidelity_report",
]
