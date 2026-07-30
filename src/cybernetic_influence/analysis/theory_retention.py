"""Retain and independently reopen per-run theory analyses."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.analysis.theory_analysis import (
    FrameworkReadoutV1,
    RunSpecV1,
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


def theory_analysis_contract() -> dict[str, object]:
    """Describe selected per-run analysis calls and retained typed boundaries."""

    def digest(model: type[FrameworkReadoutV1] | type[RunEvidenceBundleV1]) -> str:
        schema = model.model_json_schema()
        return sha256(
            json.dumps(schema, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()

    return {
        "maximum_model_calls_per_run": 0,
        "route": None,
        "reasoning_effort": None,
        "modules": [
            {
                "analysis_id": "waltzman_decision_environment_v1",
                "label": "Decision environment",
                "implemented_methods": ["exact", "calculated"],
                "llm_coded_status": "not_computed_in_mvp",
            },
            {
                "analysis_id": "levin_collective_competence_v1",
                "label": "Collective competence",
                "implemented_methods": ["exact", "calculated"],
                "llm_coded_status": "not_applicable",
            },
        ],
        "schemas": {
            "run_evidence_bundle_v1": digest(RunEvidenceBundleV1),
            "framework_readout_v1": digest(FrameworkReadoutV1),
        },
        "exposure": (
            "Selected MVP theory analyses make no provider call; they inspect the "
            "completed run's retained typed evidence."
        ),
    }


def build_reference_theory_analysis(
    compiled: CompiledScenario,
    result: ActiveRuntimeResult,
) -> dict[str, object]:
    """Build both configured provider-free readouts over one evidence bundle."""

    workflow = compiled.proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("configured theory analysis requires a coordination draft")
    return _build_theory_analysis(
        compiled,
        result,
        run_spec=reference_run_spec(
            run_id=result.run_id,
            horizon_minutes=workflow.deadline_day * MINUTES_PER_DAY,
        ),
    )


def build_live_theory_analysis(
    compiled: CompiledScenario,
    result: ActiveRuntimeResult,
    *,
    model: str,
    reasoning_effort: str,
    per_call_budget: float,
    per_run_budget: float,
) -> dict[str, object]:
    """Build selected deterministic findings over a completed live trajectory."""

    workflow = compiled.proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("configured theory analysis requires a coordination draft")
    return _build_theory_analysis(
        compiled,
        result,
        run_spec=RunSpecV1(
            run_id=result.run_id,
            execution_mode="live",
            model=model,
            reasoning_effort=reasoning_effort,
            horizon_minutes=workflow.deadline_day * MINUTES_PER_DAY,
            per_call_budget=per_call_budget,
            per_run_budget=per_run_budget,
        ),
    )


def _build_theory_analysis(
    compiled: CompiledScenario,
    result: ActiveRuntimeResult,
    *,
    run_spec: RunSpecV1,
) -> dict[str, object]:
    workflow = compiled.proposal.workflow
    if not isinstance(workflow, CoordinationDecisionWorkflowDraft):
        raise ValueError("configured theory analysis requires a coordination draft")
    selected = set(workflow.analysis.analysis_ids)
    specs = [
        item
        for item in coordination_analysis_specs(
            boundary_ref=workflow.analysis.candidate_boundary_ref,
            goal_ref=workflow.analysis.candidate_goal_ref,
        )
        if item.analysis_id in selected
    ]
    try:
        bundle = build_run_evidence_bundle(
            compiled,
            result,
            run_spec=run_spec,
            analysis_specs=specs,
        )
    except (TypeError, ValueError) as error:
        return _invalid_analysis(type(error).__name__)
    modules: dict[str, dict[str, object]] = {}
    if "waltzman_decision_environment_v1" in selected:
        try:
            readout = build_waltzman_reference_readout(bundle, result)
        except (TypeError, ValueError) as error:
            modules["decision_environment"] = {
                "status": "invalid",
                "error_type": type(error).__name__,
            }
        else:
            modules["decision_environment"] = {
                "readout": readout.model_dump(mode="json")
            }
    if "levin_collective_competence_v1" in selected:
        try:
            readout = build_levin_reference_readout(bundle, result)
        except (TypeError, ValueError) as error:
            modules["collective_competence"] = {
                "status": "invalid",
                "error_type": type(error).__name__,
            }
        else:
            modules["collective_competence"] = {
                "readout": readout.model_dump(mode="json")
            }
    retained = {
        "bundle": bundle.model_dump(mode="json"),
        "modules": modules,
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
    selected = {item.analysis_id for item in bundle.analysis_specs}
    projected: dict[str, object] = {}
    for module_id, analysis_id in _MODULES.items():
        if analysis_id not in selected:
            projected[module_id] = {"status": "not_selected"}
            continue
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
