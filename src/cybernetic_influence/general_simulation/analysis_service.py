"""Read-only evidence retention and post-run analysis for V2 simulations."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
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


_RISK_SIGNAL_MARKERS: dict[str, tuple[str, ...]] = {
    "evidentiary_uncertainty": (
        "uncertain",
        "unverified",
        "pending",
        "unresolved",
        "verify",
        "evidence",
        "documented",
        "confirm",
    ),
    "safety_or_harm": (
        "risk",
        "unsafe",
        "safe",
        "harm",
        "contamination",
        "failure",
    ),
    "authorization_or_legitimacy": (
        "authoriz",
        "legal",
        "lawful",
        "permission",
        "clearance",
        "approval",
        "custody",
    ),
    "capacity_or_scarcity": (
        "scarce",
        "limited",
        "capacity",
        "resource",
        "reserve",
        "shortage",
    ),
    "dependency_or_coordination": (
        "prerequisite",
        "depend",
        "conditional",
        "joint",
        "coordinat",
        "withheld",
        "blocked",
    ),
}
_HOLD_MARKERS = (
    "defer",
    "decline",
    "do not",
    "hold",
    "no action",
    "no dispatch",
    "not attempt",
    "on hold",
    "wait",
    "withhold",
)
_VERIFICATION_MARKERS = (
    "audit",
    "confirm",
    "document",
    "inspect",
    "review",
    "test",
    "validat",
    "verif",
)


def _string_items(value: JsonValue) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _activation_rows(
    records: list[EvidenceRecordV1],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        output = _json_mapping(record.payload.get("structured_output"))
        assimilation = _json_mapping(output.get("assimilation"))
        intent = _json_mapping(output.get("intent"))
        actor_id = intent.get("actor_id")
        base_revision = intent.get("base_revision")
        if not isinstance(actor_id, str) or not isinstance(base_revision, int):
            continue
        cognition_parts = [
            *_string_items(assimilation.get("interpretation")),
            *_string_items(assimilation.get("memory_additions")),
            *_string_items(assimilation.get("memory_revisions")),
        ]
        intent_parts = [
            *_string_items(intent.get("action")),
            *_string_items(intent.get("purpose")),
            *_string_items(intent.get("expected_effect")),
            *_string_items(intent.get("stated_rationale")),
        ]
        rows.append(
            {
                "evidence_ref": record.evidence_ref,
                "actor_id": actor_id,
                "moment": base_revision + 1,
                "text": " ".join([*cognition_parts, *intent_parts]).lower(),
                "intent_text": " ".join(intent_parts).lower(),
                "attended_observation_ids": _string_items(
                    assimilation.get("attended_observation_ids")
                ),
                "provenance_links": _string_items(
                    assimilation.get("provenance_links")
                ),
                "target_refs": _string_items(intent.get("target_refs")),
                "transition_contract_ids": _string_items(
                    intent.get("transition_contract_ids")
                ),
            }
        )
    return rows


def _normal_representation_id(value: str) -> str:
    return value.removeprefix("representation:")


def _pairwise_overlap(sets: list[set[str]]) -> dict[str, JsonValue]:
    values = [
        len(left & right) / len(left | right) if left | right else 1.0
        for left, right in combinations(sets, 2)
    ]
    if not values:
        return {"pair_count": 0, "minimum": 0.0, "mean": 0.0, "maximum": 0.0}
    return {
        "pair_count": len(values),
        "minimum": round(min(values), 3),
        "mean": round(sum(values) / len(values), 3),
        "maximum": round(max(values), 3),
    }


def _transition_rows(
    records: list[EvidenceRecordV1],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for record in records:
        transaction = _json_mapping(record.payload.get("transaction"))
        validation = _json_mapping(record.payload.get("validation"))
        base_revision = validation.get("base_revision")
        if not isinstance(base_revision, int):
            base_revision = transaction.get("base_revision")
        if not isinstance(base_revision, int):
            continue
        operations = transaction.get("operations")
        accepted = validation.get("accepted") is True
        operation_count = len(operations) if isinstance(operations, list) else 0
        preconditions = transaction.get("preconditions")
        precondition_refs: list[str] = []
        if isinstance(preconditions, list):
            for item in preconditions:
                if not isinstance(item, dict):
                    continue
                target = item.get("target")
                if isinstance(target, dict):
                    record_id = target.get("record_id")
                    if isinstance(record_id, str):
                        precondition_refs.append(record_id)
        rows.append(
            {
                "evidence_ref": record.evidence_ref,
                "moment": base_revision + 1,
                "accepted": accepted,
                "proposed_operation_count": operation_count,
                "committed_operation_count": operation_count if accepted else 0,
                "precondition_refs": precondition_refs,
            }
        )
    return rows


def _waltzman_findings(
    by_kind: dict[EvidenceKind, list[EvidenceRecordV1]],
    coverage_ref: str,
) -> list[AnalysisFindingV2]:
    information = by_kind.get("information_lineage", [])
    actor_records = by_kind.get("participant_activation", [])
    transition_records = by_kind.get("causal_event", [])
    activations = _activation_rows(actor_records)
    transitions = _transition_rows(transition_records)

    representation_sources: dict[str, str] = {}
    configured_recipients: dict[str, list[str]] = {}
    for record in information:
        representation_id = record.payload.get("representation_id")
        apparent_source = record.payload.get("apparent_source")
        recipients = record.payload.get("recipient_ids")
        if not isinstance(representation_id, str):
            continue
        if isinstance(apparent_source, str):
            representation_sources[representation_id] = apparent_source
        configured_recipients[representation_id] = (
            [item for item in recipients if isinstance(item, str)]
            if isinstance(recipients, list)
            else []
        )

    actor_representation_sets: dict[str, set[str]] = defaultdict(set)
    actor_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in activations:
        actor_id = cast(str, row["actor_id"])
        actor_rows[actor_id].append(row)
        actor_representation_sets.setdefault(actor_id, set())
        observations = cast(list[str], row["attended_observation_ids"])
        provenance = cast(list[str], row["provenance_links"])
        for reference in [*observations, *provenance]:
            representation_id = _normal_representation_id(reference)
            if representation_id in representation_sources:
                actor_representation_sets[actor_id].add(representation_id)

    configured_links = sum(len(items) for items in configured_recipients.values())
    configured_actor_count = len(
        set(actor_rows)
        | {
            actor_id
            for recipient_ids in configured_recipients.values()
            for actor_id in recipient_ids
        }
    )
    targeted = sum(
        1
        for recipient_ids in configured_recipients.values()
        if configured_actor_count and len(recipient_ids) < configured_actor_count
    )
    broadcast = len(configured_recipients) - targeted
    observed_counts = {
        actor_id: len(representations)
        for actor_id, representations in sorted(actor_representation_sets.items())
    }
    information_refs = [item.evidence_ref for item in information]
    actor_refs = [item.evidence_ref for item in actor_records]
    transition_refs = [item.evidence_ref for item in transition_records]

    reliance_rows: list[dict[str, object]] = []
    for actor_id, rows in sorted(actor_rows.items()):
        observed = actor_representation_sets.get(actor_id, set())
        sources = sorted(
            {
                representation_sources[item]
                for item in observed
                if item in representation_sources
            }
        )
        basis_counts: Counter[str] = Counter()
        verification_count = 0
        for row in rows:
            text = cast(str, row["intent_text"])
            if any(marker in text for marker in _VERIFICATION_MARKERS):
                verification_count += 1
            for reference in cast(list[str], row["provenance_links"]):
                normalized = _normal_representation_id(reference)
                if normalized in representation_sources:
                    basis_counts["configured_information"] += 1
                elif reference.startswith("consequence:"):
                    basis_counts["world_consequence"] += 1
                elif reference.startswith("private_memory:"):
                    basis_counts["private_memory"] += 1
                else:
                    basis_counts["canonical_record_or_other"] += 1
        reliance_rows.append(
            {
                "actor_id": actor_id,
                "observed_representation_count": len(observed),
                "apparent_sources_cited": sources,
                "provenance_basis_counts": dict(sorted(basis_counts.items())),
                "verification_or_review_intents": verification_count,
            }
        )

    risk_by_moment: dict[int, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    target_ref_actors: dict[str, set[str]] = defaultdict(set)
    for row in activations:
        actor_id = cast(str, row["actor_id"])
        moment = cast(int, row["moment"])
        text = cast(str, row["text"])
        for domain, markers in _RISK_SIGNAL_MARKERS.items():
            if any(marker in text for marker in markers):
                risk_by_moment[moment][domain].add(actor_id)
        for reference in cast(list[str], row["target_refs"]):
            target_ref_actors[reference].add(actor_id)
    risk_trajectory: list[dict[str, object]] = []
    for moment in sorted({cast(int, row["moment"]) for row in activations}):
        domains = risk_by_moment[moment]
        actors = sorted({actor for values in domains.values() for actor in values})
        risk_trajectory.append(
            {
                "moment": moment,
                "actors_with_expressed_risk_or_uncertainty": len(actors),
                "actors_by_signal_domain": {
                    domain: sorted(values) for domain, values in sorted(domains.items())
                },
            }
        )

    precondition_counts: Counter[str] = Counter(
        reference
        for row in transitions
        for reference in cast(list[str], row["precondition_refs"])
    )
    dependency_rows = [
        {
            "reference": reference,
            "actors_targeting_it": sorted(actor_ids),
            "actor_count": len(actor_ids),
            "transition_guard_count": precondition_counts[reference],
        }
        for reference, actor_ids in sorted(
            target_ref_actors.items(),
            key=lambda item: (-len(item[1]), item[0]),
        )
        if len(actor_ids) > 1 or precondition_counts[reference]
    ][:12]

    transitions_by_moment: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in transitions:
        transitions_by_moment[cast(int, row["moment"])].append(row)
    readiness_trajectory: list[dict[str, object]] = []
    for moment in sorted({cast(int, row["moment"]) for row in activations}):
        rows = [row for row in activations if row["moment"] == moment]
        transition_rows = transitions_by_moment.get(moment, [])
        per_ref: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            actor_id = cast(str, row["actor_id"])
            for reference in cast(list[str], row["target_refs"]):
                per_ref[reference].add(actor_id)
        readiness_trajectory.append(
            {
                "moment": moment,
                "participating_people": len({row["actor_id"] for row in rows}),
                "people_expressing_hold_or_nonattempt": sum(
                    any(
                        marker in cast(str, row["intent_text"])
                        for marker in _HOLD_MARKERS
                    )
                    for row in rows
                ),
                "people_seeking_verification_or_review": sum(
                    any(
                        marker in cast(str, row["intent_text"])
                        for marker in _VERIFICATION_MARKERS
                    )
                    for row in rows
                ),
                "people_selecting_exact_transition_contract": sum(
                    bool(row["transition_contract_ids"]) for row in rows
                ),
                "shared_dependency_count": sum(
                    len(actor_ids) > 1 for actor_ids in per_ref.values()
                ),
                "accepted_world_transitions": sum(
                    bool(row["accepted"]) for row in transition_rows
                ),
                "committed_world_operations": sum(
                    cast(int, row["committed_operation_count"])
                    for row in transition_rows
                ),
            }
        )

    if readiness_trajectory:
        initial_readiness = readiness_trajectory[0]
        final_readiness = readiness_trajectory[-1]
        pattern_summary = (
            "Within this retained simulation, expressed holds or non-attempts changed "
            f"from {initial_readiness['people_expressing_hold_or_nonattempt']} of "
            f"{initial_readiness['participating_people']} people at the first moment to "
            f"{final_readiness['people_expressing_hold_or_nonattempt']} of "
            f"{final_readiness['participating_people']} at the last. Exact world-action attempts "
            f"changed from {initial_readiness['people_selecting_exact_transition_contract']} "
            f"to {final_readiness['people_selecting_exact_transition_contract']}; shared "
            f"dependencies changed from {initial_readiness['shared_dependency_count']} to "
            f"{final_readiness['shared_dependency_count']}."
        )
        pattern_value: JsonValue = cast(
            JsonValue,
            {
                "summary": pattern_summary,
                "first_moment": initial_readiness,
                "last_moment": final_readiness,
                "peak_shared_dependencies": max(
                    cast(int, item["shared_dependency_count"])
                    for item in readiness_trajectory
                ),
            },
        )
    else:
        pattern_value = {
            "summary": "No typed participant activations were available for a coordination-pattern summary."
        }

    return [
        AnalysisFindingV2(
            finding_id="observed_coordination_pattern",
            construct_id="coordination_pattern_summary",
            method_class="calculated",
            value=pattern_value,
            evidence_refs=sorted(set([*actor_refs, *transition_refs]))
            or [coverage_ref],
            uncertainty=(
                "This summarizes observable changes inside one retained synthetic run. It "
                "does not establish causation, a stable behavioral tendency, or a Waltzman invariant."
            ),
            limitations=[
                "The summary inherits the operational definitions and limitations of the detailed findings below.",
            ],
        ),
        AnalysisFindingV2(
            finding_id="information_exposure_topology",
            construct_id="information_exposure_topology",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "configured_representations": len(configured_recipients),
                    "configured_delivery_links": configured_links,
                    "broadcast_representations": broadcast,
                    "targeted_representations": targeted,
                    "observed_representation_counts_by_person": observed_counts,
                },
            ),
            evidence_refs=information_refs or [coverage_ref],
            uncertainty=(
                "Configured delivery and model-reported attention do not establish truth, "
                "belief change, persuasion, or hostile influence."
            ),
            limitations=[
                "Attention is retained from each simulated person's typed assimilation output.",
                "No claim is made about unrecorded cognition.",
            ],
        ),
        AnalysisFindingV2(
            finding_id="source_reliance_structure",
            construct_id="trust_structure_proxies",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "per_person_reliance": reliance_rows,
                    "observed_information_overlap": _pairwise_overlap(
                        list(actor_representation_sets.values())
                    ),
                },
            ),
            evidence_refs=actor_refs or [coverage_ref],
            uncertainty=(
                "This reports cited provenance, source exposure, and verification behavior; "
                "it does not infer a hidden trust score or label trust as fragmented."
            ),
            limitations=[
                "Apparent source is not guaranteed true provenance.",
                "Model-produced citations are behavioral evidence inside this run, not validated human trust measures.",
            ],
        ),
        AnalysisFindingV2(
            finding_id="perceived_risk_signal_trajectory",
            construct_id="perceived_risk_signals",
            method_class="calculated",
            value=cast(JsonValue, {"by_moment": risk_trajectory}),
            evidence_refs=actor_refs or [coverage_ref],
            uncertainty=(
                "Signal domains are transparent lexical indicators in retained interpretations "
                "and rationales, not calibrated psychological risk estimates."
            ),
            limitations=[
                "Counts show expressed concern categories and preserve person/moment variation.",
                "Silence does not prove absence of perceived risk.",
            ],
        ),
        AnalysisFindingV2(
            finding_id="coordination_dependency_structure",
            construct_id="coordination_dependencies",
            method_class="calculated",
            value=cast(
                JsonValue,
                {
                    "shared_or_guarded_dependencies": dependency_rows,
                    "unique_target_references": len(target_ref_actors),
                    "guarded_reference_count": len(precondition_counts),
                },
            ),
            evidence_refs=sorted(set([*actor_refs, *transition_refs]))
            or [coverage_ref],
            uncertainty=(
                "References show what people targeted and what transitions guarded; they do "
                "not prove that every real dependency was represented."
            ),
            limitations=[
                "Dependency completeness is bounded by the approved scenario and retained outputs.",
            ],
        ),
        AnalysisFindingV2(
            finding_id="coordination_readiness_signal_trajectory",
            construct_id="coordination_readiness_signals",
            method_class="calculated",
            value=cast(JsonValue, {"by_moment": readiness_trajectory}),
            evidence_refs=sorted(set([*actor_refs, *transition_refs]))
            or [coverage_ref],
            uncertainty=(
                "These are observable action-readiness proxies: holds, verification, exact "
                "attempts, shared dependencies, and committed changes. They are not a scalar "
                "readiness state."
            ),
            limitations=[
                "One trajectory cannot establish a directional invariant.",
                "More committed operations are not necessarily better coordination.",
                "Correct refusal may be the appropriate coordinated outcome.",
            ],
        ),
    ]


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
            findings.extend(_waltzman_findings(by_kind, coverage_ref))
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
