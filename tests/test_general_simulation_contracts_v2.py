from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import ValidationError

from cybernetic_influence.analysis.theory_analysis import (
    AnalysisSpecV2,
    EvidenceRecordV1,
    RunEvidenceBundleV2,
)
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralSimulationProposalV1,
    SensingRuleProposalV1,
    StateEntryV1,
)
from cybernetic_influence.general_simulation.analysis_service import (
    analyze_run_evidence_v2,
    build_run_evidence_bundle_v2,
)
from cybernetic_influence.general_simulation.compiler import (
    CompiledGeneralSimulationV2,
    compile_general_simulation_v2,
)
from cybernetic_influence.general_simulation.models import (
    ActorDecision,
    Assimilation,
    SemanticActionIntent,
    WorldTransactionProposal,
)
from cybernetic_influence.general_simulation.runner import run_general_simulation_v2
from cybernetic_influence.general_simulation.projection import project_general_run
from cybernetic_influence.general_simulation.contracts_v2 import (
    ScenarioSpecV2,
    adapt_general_proposal_v1,
)
from cybernetic_influence.general_simulation.study_models import (
    AuthoredSimulationBundleV2,
    adapt_authored_bundle_v1,
)


FIXTURE = Path("tests/fixtures/general_simulation/port_coordination.json")


def _digest(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _waltzman_spec() -> AnalysisSpecV2:
    return AnalysisSpecV2(
        analysis_id="coordination_lens",
        profile="waltzman_coordination_v1",
        purpose="Inspect information-to-coordination patterns after the run.",
        construct_definitions=["Coordination constructs are derived from evidence."],
        required_evidence_kinds=["configuration", "terminal_state"],
        method_classes=["exact", "calculated"],
        aggregation="Preserve actor and moment variation.",
        uncertainty="Synthetic model behavior only.",
        limitations=["One execution does not establish an invariant."],
    )


def test_retained_port_proposal_adapts_to_independent_v2_contracts() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )

    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_relief_port_v2",
    )

    scenario_payload = scenario.model_dump(mode="json")
    run_payload = run_spec.model_dump(mode="json")
    assert "question" not in scenario_payload
    assert "schedule" not in scenario_payload
    assert "analysis_spec" not in scenario_payload
    assert "analysis_requests" not in scenario_payload
    assert "question" not in run_payload
    assert "analysis_spec" not in run_payload
    assert run_spec.scenario_digest == scenario.digest
    assert ScenarioSpecV2.model_validate_json(scenario.model_dump_json()) == scenario

    compiled = compile_general_simulation_v2(scenario, run_spec)
    assert isinstance(compiled, CompiledGeneralSimulationV2)
    assert compiled.scenario_digest == scenario.digest
    assert compiled.run_spec_digest == run_spec.digest
    assert compiled.coverage.approvable


def test_legacy_scenario_digest_survives_optional_transport_completion_fields() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, _ = adapt_general_proposal_v1(proposal, run_id="run_legacy_digest")
    legacy_payload = scenario.model_dump(mode="json")
    for transport in legacy_payload["resource_transports"]:
        transport.pop("arrival_status_key", None)
        transport.pop("arrival_status_value", None)

    restored = ScenarioSpecV2.model_validate(legacy_payload)

    assert restored.digest == scenario.digest

    run = adapt_authored_bundle_v1(proposal, run_id="run_legacy_bundle")
    legacy_bundle_payload = run.model_dump(mode="json")
    for transport in legacy_bundle_payload["scenario"]["resource_transports"]:
        transport.pop("arrival_status_key", None)
        transport.pop("arrival_status_value", None)
    restored_bundle = AuthoredSimulationBundleV2.model_validate(legacy_bundle_payload)
    assert restored_bundle.digest == run.digest


def test_exact_request_blocks_when_declared_dependency_is_not_read_by_contract() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_relief_port_closure",
    )
    records = [
        item.model_copy(
            update={
                "public_state": [
                    *item.public_state,
                    StateEntryV1(key="sealed", value=False),
                ],
                "hidden_state": [
                    *item.hidden_state,
                    StateEntryV1(key="sealed", value=True),
                ],
            }
        )
        if item.record_id == "relief_cargo"
        else item
        for item in scenario.world_records
    ]
    requests = [
        item.model_copy(
            update={
                "required_reads": ["relief_cargo", "temporary_route"],
                "transition_contract_ids": ["inspect_relief_cargo"],
            }
        )
        if item.request_id == "information_routes"
        else item
        for item in scenario.component_requests
    ]
    scenario = ScenarioSpecV2.model_validate(
        {
            **scenario.model_dump(mode="json"),
            "world_records": [item.model_dump(mode="json") for item in records],
            "component_requests": [item.model_dump(mode="json") for item in requests],
            "sensing_rules": [
                SensingRuleProposalV1(
                    rule_id="inspect_relief_cargo",
                    subject_ref="relief_cargo",
                    observer_ids=["port_coordinator"],
                    reveal_hidden_keys=["sealed"],
                    output_record_id="relief_cargo",
                    result_recipient_ids=["port_coordinator"],
                ).model_dump(mode="json")
            ],
        }
    )
    moments = [
        item.model_copy(
            update={
                "active_transition_contract_ids": [
                    *item.active_transition_contract_ids,
                    "inspect_relief_cargo",
                ]
            }
        )
        if item.moment_id == "initial_claims"
        else item
        for item in run_spec.scheduled_moments
    ]
    run_spec = run_spec.model_copy(
        update={"scenario_digest": scenario.digest, "scheduled_moments": moments}
    )

    compiled = compile_general_simulation_v2(scenario, run_spec)
    item = next(
        item
        for item in compiled.coverage.items
        if item.request_id == "information_routes"
    )

    assert item.classification == "exact"
    assert item.causal_closure == "partial"
    assert item.unenforced_dependency_refs == ["temporary_route"]
    assert [
        (dependency.dependency_ref, dependency.enforcement)
        for dependency in item.dependency_enforcement
    ] == [
        ("relief_cargo", "exact_read"),
        ("temporary_route", "unsupported"),
    ]
    assert item.blocking
    assert "information_routes" in compiled.coverage.blocking_request_ids

    fixed_requests = [
        request.model_copy(update={"required_reads": ["relief_cargo"]})
        if request.request_id == "information_routes"
        else request
        for request in scenario.component_requests
    ]
    fixed_scenario = ScenarioSpecV2.model_validate(
        {
            **scenario.model_dump(mode="json"),
            "component_requests": [
                request.model_dump(mode="json") for request in fixed_requests
            ],
        }
    )
    fixed_run = run_spec.model_copy(update={"scenario_digest": fixed_scenario.digest})
    fixed = compile_general_simulation_v2(fixed_scenario, fixed_run)
    fixed_item = next(
        item for item in fixed.coverage.items if item.request_id == "information_routes"
    )

    assert fixed_item.causal_closure == "exact"
    assert not fixed_item.unenforced_dependency_refs
    assert fixed.coverage.approvable
    assert fixed.world_spec.sensing_contracts[0].hidden_to_output_fields == {
        "sealed": "sealed"
    }


def test_runtime_module_does_not_load_analysis_package() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; import cybernetic_influence.general_simulation.runner; "
                "assert not any(name.startswith('cybernetic_influence.analysis') "
                "for name in sys.modules), sorted(name for name in sys.modules "
                "if name.startswith('cybernetic_influence.analysis'))"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr


def test_v2_exact_registry_match_without_contract_does_not_claim_exact_reads() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_bounded_route_determination",
    )
    request = scenario.component_requests[0].model_copy(
        update={
            "behavior_description": (
                "The union representative considers route evidence and attempts "
                "to communicate a labor-safe dispatch determination."
            ),
            "required_reads": ["temporary_route"],
            "transition_contract_ids": [],
            "fidelity_need": "bounded",
            "blocks_if_unexecutable": True,
        }
    )
    scenario = ScenarioSpecV2.model_validate(
        {
            **scenario.model_dump(mode="json"),
            "component_requests": [
                request.model_dump(mode="json"),
                *[
                    item.model_dump(mode="json")
                    for item in scenario.component_requests[1:]
                ],
            ],
        }
    )
    run_spec = run_spec.model_copy(update={"scenario_digest": scenario.digest})

    compiled = compile_general_simulation_v2(scenario, run_spec)
    item = next(
        item
        for item in compiled.coverage.items
        if item.request_id == request.request_id
    )

    assert item.classification == "coarse_llm"
    assert item.causal_closure == "coarse"
    assert item.unenforced_dependency_refs == ["temporary_route"]
    assert item.dependency_enforcement[0].enforcement == "coarse_llm"
    assert "not promoted to an exact structural component" in " ".join(
        item.compiler_evidence
    )
    assert not item.blocking


def test_analysis_attachment_changes_neither_scenario_nor_run_identity() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    bundle = adapt_authored_bundle_v1(proposal, run_id="run_relief_port_v2")
    scenario_digest = bundle.scenario.digest
    run_digest = bundle.default_run.digest

    analyzed = bundle.model_copy(update={"analyses": [_waltzman_spec()]})

    assert analyzed.scenario.digest == scenario_digest
    assert analyzed.default_run.digest == run_digest
    assert analyzed.digest != bundle.digest


def test_v2_evidence_bundle_requires_no_analysis_specification() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_relief_port_v2",
    )
    evidence = EvidenceRecordV1(
        evidence_ref="configuration:relief_port",
        evidence_kind="configuration",
        summary="The separated relief-port scenario and run were retained.",
    )
    payload = {
        "bundle_version": 2,
        "bundle_id": "bundle_run_relief_port_v2",
        "run_id": "run_relief_port_v2",
        "scenario_id": scenario.scenario_id,
        "scenario_digest": scenario.digest,
        "run_spec_digest": run_spec.digest,
        "initial_state_digest": "0" * 64,
        "terminal_state_digest": "1" * 64,
        "evidence_records": [evidence.model_dump(mode="json")],
        "fidelity_assumptions": scenario.fidelity_assumptions,
        "known_omissions": [],
    }
    bundle = RunEvidenceBundleV2(
        bundle_id="bundle_run_relief_port_v2",
        run_id="run_relief_port_v2",
        scenario_id=scenario.scenario_id,
        scenario_digest=scenario.digest,
        run_spec_digest=run_spec.digest,
        initial_state_digest="0" * 64,
        terminal_state_digest="1" * 64,
        evidence_records=[evidence],
        fidelity_assumptions=scenario.fidelity_assumptions,
        known_omissions=[],
        record_digest=_digest(payload),
    )

    assert bundle.bundle_version == 2
    assert "analysis_specs" not in bundle.model_dump(mode="json")


def test_analysis_contract_rejects_execution_authority_fields() -> None:
    payload = _waltzman_spec().model_dump(mode="json")
    payload["schedule"] = []

    with pytest.raises(ValidationError, match="schedule"):
        AnalysisSpecV2.model_validate(payload)


def test_v2_runtime_contexts_exclude_analyst_question_and_analysis() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_relief_port_v2",
    )
    compiled = compile_general_simulation_v2(scenario, run_spec)

    def isolated_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        user = json.loads(args[1][1]["content"])
        if kwargs["response_model"] is ActorDecision:
            context = user["actor_context"]
            return ActorDecision(
                assimilation=Assimilation(
                    attended_observation_ids=[],
                    memory_additions=[],
                    memory_revisions=[],
                    provenance_links=[],
                    interpretation="Retain the authorized situation without adding facts.",
                ),
                intent=SemanticActionIntent(
                    intent_id=(
                        f"intent_{context['actor_id']}_{context['base_revision']}"
                    ),
                    actor_id=context["actor_id"],
                    base_revision=context["base_revision"],
                    action="Request a bounded coordination check.",
                    target_refs=[],
                    purpose="Address the current phase responsibilities.",
                    expected_effect="Produce one reviewable attempt.",
                    stated_rationale="Only authorized context is available.",
                ),
            ), SimpleNamespace(provider="fixture")
        assert kwargs["response_model"] is WorldTransactionProposal
        return WorldTransactionProposal(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="The bounded intents do not require a world mutation.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation_v2(
        compiled,
        call=isolated_call,
        max_additional_moments=1,
    )

    assert result.scenario_digest == scenario.digest
    assert result.run_spec_digest == run_spec.digest
    retained_result = result.model_dump(mode="json")
    evidence_bundle = build_run_evidence_bundle_v2(compiled, result)
    analysis = analyze_run_evidence_v2(evidence_bundle, _waltzman_spec())
    assert analysis.coverage_status == "supported"
    assert analysis.model_call_receipts == []
    assert analysis.run_evidence_bundle_digest == evidence_bundle.record_digest
    findings = {item.construct_id: item for item in analysis.findings}
    assert set(findings) == {
        "retained_evidence_coverage",
        "coordination_pattern_summary",
        "information_exposure_topology",
        "trust_structure_proxies",
        "perceived_risk_signals",
        "coordination_dependencies",
        "coordination_readiness_signals",
    }
    assert findings["coordination_pattern_summary"].method_class == "calculated"
    assert "hidden trust score" in findings["trust_structure_proxies"].uncertainty
    readiness = findings["coordination_readiness_signals"].value
    assert isinstance(readiness, dict)
    assert isinstance(readiness["by_moment"], list)
    assert readiness["by_moment"]
    assert result.model_dump(mode="json") == retained_result
    assert len(result.model_calls) == len(scenario.people) + 1
    assert all(
        item.transaction.objective_assessment is None
        for item in result.transition_evidence
    )
    for receipt in result.model_calls:
        supplied = json.loads(receipt.input_context)
        serialized = json.dumps(supplied, sort_keys=True)
        assert "research_question" not in serialized
        assert "analysis_spec" not in serialized
        assert "analysis_requests" not in serialized

    unsupported_spec = _waltzman_spec().model_copy(
        update={"required_evidence_kinds": ["boundary_activity"]}
    )
    unsupported = analyze_run_evidence_v2(evidence_bundle, unsupported_spec)
    assert unsupported.coverage_status == "unsupported"
    assert unsupported.missing_evidence == ["boundary_activity"]
    assert result.model_dump(mode="json") == retained_result


def test_staged_cognition_retains_assimilation_before_action_selection() -> None:
    proposal = GeneralSimulationProposalV1.model_validate_json(
        FIXTURE.read_text(encoding="utf-8")
    )
    scenario, run_spec = adapt_general_proposal_v1(
        proposal,
        run_id="run_staged_cognition",
        cognition_mode="staged",
    )
    compiled = compile_general_simulation_v2(scenario, run_spec)
    call_sequence: list[tuple[str, str]] = []

    def staged_call(*args: Any, **kwargs: Any) -> tuple[object, object]:
        user = json.loads(args[1][1]["content"])
        response_model = kwargs["response_model"]
        if response_model is Assimilation:
            context = user["actor_context"]
            call_sequence.append((context["actor_id"], "assimilation"))
            return Assimilation(
                attended_observation_ids=[
                    item["observation_id"] for item in context["observations"]
                ],
                memory_additions=["I retained the currently authorized evidence."],
                memory_revisions=[],
                provenance_links=[
                    item["observation_id"] for item in context["observations"]
                ],
                interpretation="The evidence remains incomplete but actionable.",
            ), SimpleNamespace(provider="fixture")
        if response_model is SemanticActionIntent:
            context = user["actor_context"]
            call_sequence.append((context["actor_id"], "action"))
            assert user["retained_assimilation"]["interpretation"] == (
                "The evidence remains incomplete but actionable."
            )
            assert "I retained the currently authorized evidence." in user[
                "assimilated_private_memory"
            ]
            return SemanticActionIntent(
                intent_id=f"intent_{context['actor_id']}_{context['base_revision']}",
                actor_id=context["actor_id"],
                base_revision=context["base_revision"],
                action="Request a bounded coordination check.",
                target_refs=[],
                purpose="Address the current phase responsibilities.",
                expected_effect="Produce one reviewable attempt.",
                stated_rationale="The retained assimilation supports a bounded check.",
            ), SimpleNamespace(provider="fixture")
        assert response_model is WorldTransactionProposal
        return WorldTransactionProposal(
            transaction_id=f"transaction_{user['moment']['moment_id']}",
            base_revision=user["requirements"]["base_revision"],
            authority_id=user["requirements"]["authority_id"],
            intent_ids=user["requirements"]["intent_ids"],
            operations=[],
            preconditions=[],
            consequences=[],
            evidence_refs=user["requirements"]["intent_ids"],
            stated_rationale="The bounded intents require no world mutation.",
        ), SimpleNamespace(provider="fixture")

    result = run_general_simulation_v2(
        compiled,
        call=staged_call,
        max_additional_moments=1,
    )

    expected_actor_calls = len(proposal.people) * 2
    assert len(result.model_calls) == expected_actor_calls + 1
    assert len(call_sequence) == expected_actor_calls
    for person in proposal.people:
        assert [
            phase for actor_id, phase in call_sequence if actor_id == person.entity_id
        ] == ["assimilation", "action"]
    assert sum(item.trace_id.endswith("/assimilation") for item in result.model_calls) == len(proposal.people)
    assert sum(item.trace_id.endswith("/action") for item in result.model_calls) == len(proposal.people)
    projected = project_general_run(
        compiled,
        result,
        run_id=run_spec.run_id,
        created_at="2026-08-16T00:00:00Z",
        execution="live",
    )
    traces = cast(list[dict[str, object]], projected["traces"])
    assert len(traces) == len(proposal.people)
    assert all(cast(int, trace["model_call_count"]) == 2 for trace in traces)
    assert all(trace["assimilation"] for trace in traces)
    assert all(trace["intent"] for trace in traces)
    assert all(
        cast(list[object], trace["memory_after"])
        == [*cast(list[object], trace["memory_before"]), "I retained the currently authorized evidence."]
        for trace in traces
    )
    assert all(
        len(cast(list[object], trace["attended_observations"]))
        == len(cast(list[object], cast(dict[str, object], trace["assimilation"])["attended_observation_ids"]))
        for trace in traces
    )


def test_waltzman_lens_does_not_count_rejected_operations_as_committed() -> None:
    records = [
        EvidenceRecordV1(
            evidence_ref="configuration:blocked_dispatch",
            evidence_kind="configuration",
            summary="Configuration.",
            payload={},
        ),
        EvidenceRecordV1(
            evidence_ref="terminal_state:blocked_dispatch",
            evidence_kind="terminal_state",
            summary="Terminal state.",
            payload={"revision": 0},
        ),
        EvidenceRecordV1(
            evidence_ref="call:operator",
            evidence_kind="participant_activation",
            summary="Operator attempt.",
            payload={
                "input_context": {"actor_context": {"current_minute": 75}},
                "structured_output": {
                    "assimilation": {
                        "interpretation": "Dispatch remains blocked.",
                        "attended_observation_ids": [],
                        "provenance_links": [],
                    },
                    "intent": {
                        "actor_id": "operator",
                        "intent_id": "attempt_dispatch_75",
                        "base_revision": 0,
                        "action": "Attempt dispatch.",
                        "purpose": "Move cargo.",
                        "expected_effect": "Cargo may move.",
                        "stated_rationale": "Attempt the guarded transition.",
                        "target_refs": ["cargo"],
                        "transition_contract_ids": ["cargo_transport"],
                    },
                }
            },
        ),
        EvidenceRecordV1(
            evidence_ref="transition:blocked_dispatch",
            evidence_kind="causal_event",
            summary="Rejected dispatch.",
            payload={
                "transaction": {
                    "base_revision": 0,
                    "intent_ids": ["attempt_dispatch_75"],
                    "operations": [
                        {"operation": "replace", "target": {}, "value": index}
                        for index in range(5)
                    ],
                    "preconditions": [],
                },
                "validation": {
                    "base_revision": 0,
                    "accepted": False,
                    "errors": ["precondition failed"],
                },
            },
        ),
    ]
    bundle_payload = {
        "bundle_version": 2,
        "bundle_id": "bundle_run_blocked_dispatch",
        "run_id": "run_blocked_dispatch",
        "scenario_id": "blocked_dispatch",
        "scenario_digest": _digest("scenario"),
        "run_spec_digest": _digest("run"),
        "initial_state_digest": _digest("initial"),
        "terminal_state_digest": _digest("terminal"),
        "evidence_records": [item.model_dump(mode="json") for item in records],
        "fidelity_assumptions": ["Rejected operations do not change canonical state."],
        "known_omissions": [],
    }
    bundle = RunEvidenceBundleV2.model_validate(
        {**bundle_payload, "record_digest": _digest(bundle_payload)}
    )

    analysis = analyze_run_evidence_v2(bundle, _waltzman_spec())

    finding = next(
        item
        for item in analysis.findings
        if item.construct_id == "coordination_readiness_signals"
    )
    assert isinstance(finding.value, dict)
    assert finding.value["by_moment"] == [
        {
            "moment": 75,
            "participating_people": 1,
            "people_expressing_hold_or_nonattempt": 0,
            "people_seeking_verification_or_review": 0,
            "people_selecting_exact_transition_contract": 1,
            "shared_dependency_count": 0,
            "accepted_world_transitions": 0,
            "committed_world_operations": 0,
        }
    ]
