"""Conversational convenience envelope over separated simulator contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cybernetic_influence.analysis.theory_analysis import (
    RETAINABLE_EVIDENCE_KINDS,
    AnalysisSpecV2,
)

from .authoring_models import GeneralSimulationProposalV1
from .authoring_models import ScheduledMomentProposalV1
from .contracts_v2 import (
    RunSpecV2,
    ScenarioSpecV2,
    adapt_general_proposal_v1,
    contract_digest,
    validate_run_against_scenario,
)


class AuthoredSimulationBundleV2(BaseModel):
    """One editable study document; nested contracts retain separate authority."""

    model_config = ConfigDict(extra="forbid", strict=True)

    bundle_version: Literal[2] = 2
    authored_study_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    scenario: ScenarioSpecV2
    default_run: RunSpecV2
    analyses: list[AnalysisSpecV2] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    analyst_question: str | None = None
    legacy_presentation_question: str | None = None

    @model_validator(mode="after")
    def validate_contract_boundaries(self) -> "AuthoredSimulationBundleV2":
        validate_run_against_scenario(self.scenario, self.default_run)
        analysis_ids = [item.analysis_id for item in self.analyses]
        if len(analysis_ids) != len(set(analysis_ids)):
            raise ValueError("analysis identities must be unique within a study")
        return self

    @property
    def digest(self) -> str:
        # Keep retained pre-extension bundle identities readable.  This mirrors
        # ScenarioSpecV2.digest: absent transport completion fields have no
        # semantic effect, while populated fields remain part of the bundle.
        payload = self.model_dump(mode="json")
        for transport in payload["scenario"]["resource_transports"]:
            if transport.get("arrival_status_key") is None:
                transport.pop("arrival_status_key", None)
            if transport.get("arrival_status_value") is None:
                transport.pop("arrival_status_value", None)
        return contract_digest(payload)


class AuthoringRunProposalV2(BaseModel):
    """Model-authored run semantics before trusted identity/provider binding."""

    model_config = ConfigDict(extra="forbid", strict=True)

    horizon_minutes: int = Field(ge=1)
    scheduled_moments: list[ScheduledMomentProposalV1] = Field(min_length=1)
    termination_conditions: list[str] = Field(default_factory=list)


class AuthoredSimulationProposalV2(BaseModel):
    """Native separated authoring output; it grants no execution authority."""

    model_config = ConfigDict(extra="forbid", strict=True)

    proposal_kind: Literal["general_world_v2"] = "general_world_v2"
    authored_study_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    scenario: ScenarioSpecV2
    default_run: AuthoringRunProposalV2
    analyses: list[AnalysisSpecV2] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    analyst_question: str | None = None

    @model_validator(mode="after")
    def reject_analyses_no_run_can_satisfy(self) -> "AuthoredSimulationProposalV2":
        """Refuse a pre-registered analysis that could never produce a finding.

        An authored analysis asked for boundary_activity, which is a declared
        EvidenceKind that no execution path emits. Its lens reported itself
        unsupported on a perfectly good run, which reads to the analyst as their
        simulation being deficient rather than as a request that was never
        satisfiable by any run at all.

        Checked here, on the model's proposal, rather than on AnalysisSpecV2:
        constraining the spec itself made every already-retained draft holding
        such an analysis fail to parse, so saved work became unopenable. A new
        invariant governs what may be created, not what is already on disk.
        """
        for analysis in self.analyses:
            unsatisfiable = sorted(
                set(analysis.required_evidence_kinds) - RETAINABLE_EVIDENCE_KINDS
            )
            if unsatisfiable:
                raise ValueError(
                    f"analysis {analysis.analysis_id} requires evidence no run can "
                    "retain: " + ", ".join(unsatisfiable)
                    + "; it could never produce a finding"
                )
        return self


class AuthoredSimulationProposalEnvelopeV2(BaseModel):
    """Provider-friendly envelope for one native V2 proposal."""

    model_config = ConfigDict(extra="forbid", strict=True)

    proposal: AuthoredSimulationProposalV2


def materialize_authored_bundle_v2(
    proposal: AuthoredSimulationProposalV2,
    *,
    run_id: str,
) -> AuthoredSimulationBundleV2:
    """Bind trusted identities while preserving the model-authored separation."""

    run = RunSpecV2(
        run_id=run_id,
        scenario_digest=proposal.scenario.digest,
        execution_mode="reference",
        horizon_minutes=proposal.default_run.horizon_minutes,
        scheduled_moments=proposal.default_run.scheduled_moments,
        termination_conditions=proposal.default_run.termination_conditions,
    )
    return AuthoredSimulationBundleV2(
        authored_study_id=proposal.authored_study_id,
        scenario=proposal.scenario,
        default_run=run,
        analyses=proposal.analyses,
        unresolved_questions=proposal.unresolved_questions,
        analyst_question=proposal.analyst_question,
    )


def adapt_authored_bundle_v1(
    proposal: GeneralSimulationProposalV1,
    *,
    run_id: str,
) -> AuthoredSimulationBundleV2:
    """Read a retained V1 proposal through the new separated contracts."""
    scenario, run_spec = adapt_general_proposal_v1(proposal, run_id=run_id)
    analyses: list[AnalysisSpecV2] = []
    if proposal.analysis_spec is not None:
        analyses.append(
            AnalysisSpecV2(
                analysis_id=proposal.analysis_spec.analysis_id,
                profile=proposal.analysis_spec.profile,
                purpose=proposal.analysis_spec.purpose,
                construct_definitions=[
                    "information topology, stated source reliance, perceived risk, "
                    "dependencies, and coordination readiness are derived from retained evidence"
                ],
                required_evidence_kinds=[
                    "configuration",
                    "terminal_state",
                    "causal_event",
                    "information_lineage",
                    "participant_activation",
                ],
                method_classes=["exact", "calculated", "llm_coded"],
                aggregation="Retain per-actor and per-moment evidence before any synthesis.",
                uncertainty=(
                    "This is a Waltzman-informed interpretation of synthetic model behavior."
                ),
                limitations=[
                    "The result does not estimate human or institutional behavior.",
                    "One retained run does not establish a directional invariant.",
                ],
            )
        )
    return AuthoredSimulationBundleV2(
        authored_study_id=proposal.simulation_id,
        scenario=scenario,
        default_run=run_spec,
        analyses=analyses,
        unresolved_questions=proposal.unresolved_questions,
        analyst_question=proposal.question,
        legacy_presentation_question=proposal.question,
    )
