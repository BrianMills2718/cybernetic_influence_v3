"""Read-only evidence retention and post-run analysis for V2 simulations."""

from __future__ import annotations

import json
from collections import Counter
from typing import Literal, cast

from pydantic import JsonValue

from cybernetic_influence.analysis.theory_analysis import (
    AnalysisFindingV2,
    AnalysisResultV2,
    AnalysisSpecV2,
    EvidenceKind,
    EvidenceRecordV1,
    RunEvidenceBundleV2,
)

from .compiler import CompiledGeneralSimulationV2
from .contracts_v2 import contract_digest
from .models import GeneralGroupSimulationResultV2


def _json_mapping(value: JsonValue) -> dict[str, JsonValue]:
    return value if isinstance(value, dict) else {}


def build_run_evidence_bundle_v2(
    compiled: CompiledGeneralSimulationV2,
    result: GeneralGroupSimulationResultV2,
) -> RunEvidenceBundleV2:
    """Project one completed run into immutable, theory-neutral evidence."""
    if result.run_id != compiled.run_spec.run_id:
        raise ValueError("result run identity does not match compiled RunSpec")
    if result.scenario_digest != compiled.scenario_digest:
        raise ValueError("result scenario digest does not match compiled ScenarioSpec")
    if result.run_spec_digest != compiled.run_spec_digest:
        raise ValueError("result RunSpec digest does not match compiled RunSpec")

    records: list[EvidenceRecordV1] = [
        EvidenceRecordV1(
            evidence_ref=f"configuration:{compiled.scenario.scenario_id}",
            evidence_kind="configuration",
            summary="Approved separated scenario and run configuration.",
            payload={
                "scenario_id": compiled.scenario.scenario_id,
                "scenario_digest": compiled.scenario_digest,
                "run_id": compiled.run_spec.run_id,
                "run_spec_digest": compiled.run_spec_digest,
                "configuration_graph": cast(JsonValue, compiled.configuration_graph),
            },
        ),
        EvidenceRecordV1(
            evidence_ref=f"initial_state:{result.run_id}",
            evidence_kind="initial_state",
            summary="Canonical world state before the first scheduled moment.",
            payload=compiled.world_spec.initial_state.model_dump(mode="json"),
        ),
        EvidenceRecordV1(
            evidence_ref=f"terminal_state:{result.run_id}",
            evidence_kind="terminal_state",
            summary="Canonical world state after the completed run.",
            payload=result.final_state.model_dump(mode="json"),
        ),
    ]
    for representation in compiled.scenario.information_extension.representations if compiled.scenario.information_extension else []:
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"information:{representation.representation_id}",
                evidence_kind="information_lineage",
                summary="Configured information representation and its authorized recipients.",
                source_refs=[f"configuration:{compiled.scenario.scenario_id}"],
                payload=representation.model_dump(mode="json"),
            )
        )
    for index, receipt in enumerate(result.model_calls, start=1):
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"call:{index}:{receipt.role}",
                evidence_kind=(
                    "participant_activation"
                    if receipt.role == "actor"
                    else "mechanism_decision"
                ),
                summary=(
                    "One simulated person produced an assimilation and action attempt."
                    if receipt.role == "actor"
                    else "The joint transition authority proposed one bounded transaction."
                ),
                source_refs=[f"configuration:{compiled.scenario.scenario_id}"],
                payload={
                    "role": receipt.role,
                    "provider": receipt.provider,
                    "model": receipt.model,
                    "trace_id": receipt.trace_id,
                    "input_context": json.loads(receipt.input_context),
                    "structured_output": receipt.structured_output,
                    "decoding": receipt.decoding,
                    "exact_replay_possible": receipt.exact_replay_possible,
                },
            )
        )
    for index, transition in enumerate(result.transition_evidence, start=1):
        records.append(
            EvidenceRecordV1(
                evidence_ref=f"transition:{index}",
                evidence_kind="causal_event",
                summary="One proposed transition and its canonical validation result.",
                source_refs=[f"configuration:{compiled.scenario.scenario_id}"],
                payload=transition.model_dump(mode="json"),
            )
        )
    records.append(
        EvidenceRecordV1(
            evidence_ref=f"completion:{result.run_id}",
            evidence_kind="completion",
            summary="The configured run lifecycle completed.",
            source_refs=[f"terminal_state:{result.run_id}"],
            payload={
                "moment_count": len(result.moments),
                "model_call_count": len(result.model_calls),
                "final_revision": result.final_state.revision,
            },
        )
    )
    payload = {
        "bundle_version": 2,
        "bundle_id": f"bundle_{result.run_id}",
        "run_id": result.run_id,
        "scenario_id": compiled.scenario.scenario_id,
        "scenario_digest": compiled.scenario_digest,
        "run_spec_digest": compiled.run_spec_digest,
        "initial_state_digest": contract_digest(
            compiled.world_spec.initial_state.model_dump(mode="json")
        ),
        "terminal_state_digest": contract_digest(
            result.final_state.model_dump(mode="json")
        ),
        "evidence_records": [item.model_dump(mode="json") for item in records],
        "fidelity_assumptions": compiled.scenario.fidelity_assumptions,
        "known_omissions": [],
    }
    return RunEvidenceBundleV2(
        bundle_id=f"bundle_{result.run_id}",
        run_id=result.run_id,
        scenario_id=compiled.scenario.scenario_id,
        scenario_digest=compiled.scenario_digest,
        run_spec_digest=compiled.run_spec_digest,
        initial_state_digest=cast(str, payload["initial_state_digest"]),
        terminal_state_digest=cast(str, payload["terminal_state_digest"]),
        evidence_records=records,
        fidelity_assumptions=compiled.scenario.fidelity_assumptions,
        known_omissions=[],
        record_digest=contract_digest(payload),
    )


def analyze_run_evidence_v2(
    bundle: RunEvidenceBundleV2,
    specification: AnalysisSpecV2,
) -> AnalysisResultV2:
    """Apply one deterministic evidence-linked lens without simulation authority."""
    by_kind: dict[EvidenceKind, list[EvidenceRecordV1]] = {}
    for record in bundle.evidence_records:
        by_kind.setdefault(record.evidence_kind, []).append(record)
    missing = sorted(
        set(specification.required_evidence_kinds) - set(by_kind)
    )
    findings: list[AnalysisFindingV2] = []
    if not missing:
        coverage_ref = bundle.evidence_records[0].evidence_ref
        findings.append(
            AnalysisFindingV2(
                finding_id="evidence_coverage",
                construct_id="retained_evidence_coverage",
                method_class="exact",
                value={kind: len(records) for kind, records in sorted(by_kind.items())},
                evidence_refs=[coverage_ref],
                uncertainty="Counts retained records; it does not validate a theory construct.",
            )
        )
        if specification.profile == "waltzman_coordination_v1":
            information = by_kind.get("information_lineage", [])
            recipient_counts = [
                len(recipients)
                for record in information
                if isinstance(
                    (recipients := record.payload.get("recipient_ids")), list
                )
            ]
            actor_calls = by_kind.get("participant_activation", [])
            transitions = by_kind.get("causal_event", [])
            operation_count = sum(
                len(operations)
                for record in transitions
                if isinstance(
                    (
                        operations := _json_mapping(
                            record.payload.get("transaction")
                        ).get("operations")
                    ),
                    list,
                )
            )
            findings.extend(
                [
                    AnalysisFindingV2(
                        finding_id="information_topology",
                        construct_id="information_topology",
                        method_class="calculated",
                        value=cast(
                            JsonValue,
                            {
                                "representation_count": len(information),
                                "recipient_count_distribution": recipient_counts,
                            },
                        ),
                        evidence_refs=[item.evidence_ref for item in information]
                        or [coverage_ref],
                        uncertainty=(
                            "Configured delivery topology does not establish attention, belief, "
                            "persuasion, or hostile influence."
                        ),
                    ),
                    AnalysisFindingV2(
                        finding_id="coordination_execution",
                        construct_id="coordination_execution",
                        method_class="calculated",
                        value={
                            "actor_activation_count": len(actor_calls),
                            "transition_count": len(transitions),
                            "committed_operation_count": operation_count,
                        },
                        evidence_refs=[item.evidence_ref for item in transitions]
                        or [coverage_ref],
                        uncertainty=(
                            "Execution counts describe this retained trajectory and do not "
                            "measure human coordination readiness."
                        ),
                    ),
                ]
            )
        else:
            terminal = by_kind["terminal_state"][0]
            transitions = by_kind.get("causal_event", [])
            status_counts: Counter[bool] = Counter(
                bool(
                    _json_mapping(record.payload.get("validation")).get(
                        "accepted"
                    )
                )
                for record in transitions
                if isinstance(record.payload.get("validation"), dict)
            )
            findings.append(
                AnalysisFindingV2(
                    finding_id="terminal_outcome",
                    construct_id="terminal_outcome",
                    method_class="exact",
                    value={
                        "terminal_state_digest": bundle.terminal_state_digest,
                        "accepted_transitions": status_counts[True],
                        "rejected_transitions": status_counts[False],
                    },
                    evidence_refs=[terminal.evidence_ref],
                    uncertainty="Exact only at the configured canonical-state boundary.",
                )
            )
    coverage_status: Literal["supported", "degraded", "unsupported"] = (
        "unsupported" if missing else "supported"
    )
    payload = {
        "analysis_result_version": 2,
        "result_id": f"analysis_{bundle.run_id}_{specification.analysis_id}",
        "run_evidence_bundle_digest": bundle.record_digest,
        "analysis_spec_digest": specification.digest,
        "findings": [item.model_dump(mode="json") for item in findings],
        "coverage_status": coverage_status,
        "missing_evidence": missing,
        "model_call_receipts": [],
    }
    return AnalysisResultV2(
        result_id=f"analysis_{bundle.run_id}_{specification.analysis_id}",
        run_evidence_bundle_digest=bundle.record_digest,
        analysis_spec_digest=specification.digest,
        findings=findings,
        coverage_status=coverage_status,
        missing_evidence=missing,
        model_call_receipts=[],
        result_digest=contract_digest(payload),
    )
