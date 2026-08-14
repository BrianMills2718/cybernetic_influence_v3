"""Conversational convenience envelope over separated simulator contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cybernetic_influence.analysis.theory_analysis import AnalysisSpecV2

from .authoring_models import GeneralSimulationProposalV1
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
        return contract_digest(self)


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
        legacy_presentation_question=proposal.question,
    )
