"""Retain and independently reopen per-run theory analyses."""

from __future__ import annotations

from collections.abc import Mapping

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.analysis.theory_analysis import (
    FrameworkReadoutV1,
    RunEvidenceBundleV1,
    build_levin_reference_readout,
    build_run_evidence_bundle,
    build_waltzman_reference_readout,
    coordination_analysis_specs,
    reference_run_spec,
    validate_readout_against_bundle,
)
from cybernetic_influence.authoring.compiler import CompiledScenario
from cybernetic_influence.authoring.models import CoordinationDecisionWorkflowDraft
from cybernetic_influence.scenarios.coordination_decision import MINUTES_PER_DAY


_MODULES = {
    "decision_environment": "waltzman_decision_environment_v1",
    "collective_competence": "levin_collective_competence_v1",
}


def build_reference_theory_analysis(
    compiled: CompiledScenario,
    result: ActiveRuntimeResult,
) -> dict[str, object]:
    """Build both configured provider-free readouts over one evidence bundle."""

    workflow = compiled.proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("configured theory analysis requires a coordination draft")
    specs = coordination_analysis_specs(
        boundary_ref=workflow.analysis.candidate_boundary_ref,
        goal_ref=workflow.analysis.candidate_goal_ref,
    )
    bundle = build_run_evidence_bundle(
        compiled,
        result,
        run_spec=reference_run_spec(
            run_id=result.run_id,
            horizon_minutes=workflow.deadline_day * MINUTES_PER_DAY,
        ),
        analysis_specs=specs,
    )
    retained = {
        "bundle": bundle.model_dump(mode="json"),
        "modules": {
            "decision_environment": {
                "readout": build_waltzman_reference_readout(
                    bundle, result
                ).model_dump(mode="json")
            },
            "collective_competence": {
                "readout": build_levin_reference_readout(
                    bundle, result
                ).model_dump(mode="json")
            },
        },
    }
    projected = project_retained_theory_analysis(retained)
    if projected is None:  # pragma: no cover - retained is present above
        raise AssertionError("built theory analysis unexpectedly disappeared")
    return projected


def project_retained_theory_analysis(value: object) -> dict[str, object] | None:
    """Validate modules independently without changing the completed world run."""

    if value is None:
        return None
    if not isinstance(value, Mapping):
        return _invalid_analysis("TheoryAnalysisFormatError")
    raw_bundle = value.get("bundle")
    try:
        bundle = RunEvidenceBundleV1.model_validate(raw_bundle)
    except (TypeError, ValueError) as error:
        return _invalid_analysis(type(error).__name__, bundle=raw_bundle)

    raw_modules = value.get("modules")
    modules = raw_modules if isinstance(raw_modules, Mapping) else {}
    projected: dict[str, object] = {}
    for module_id, analysis_id in _MODULES.items():
        raw_module = modules.get(module_id)
        raw_readout = (
            raw_module.get("readout")
            if isinstance(raw_module, Mapping)
            else None
        )
        try:
            readout = FrameworkReadoutV1.model_validate(raw_readout)
            if readout.analysis_id != analysis_id:
                raise ValueError("retained analysis identity does not match module")
            validate_readout_against_bundle(readout, bundle)
        except (TypeError, ValueError) as error:
            projected[module_id] = {
                "status": "invalid",
                "error_type": type(error).__name__,
            }
        else:
            projected[module_id] = {
                "status": "available",
                "readout": readout.model_dump(mode="json"),
            }
    return {
        "bundle": bundle.model_dump(mode="json"),
        "modules": projected,
    }


def _invalid_analysis(
    error_type: str,
    *,
    bundle: object = None,
) -> dict[str, object]:
    return {
        "bundle": bundle,
        "modules": {
            module_id: {"status": "invalid", "error_type": error_type}
            for module_id in _MODULES
        },
    }
