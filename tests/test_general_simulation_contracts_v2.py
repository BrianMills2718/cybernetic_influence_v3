from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cybernetic_influence.analysis.theory_analysis import (
    AnalysisSpecV2,
    EvidenceRecordV1,
    RunEvidenceBundleV2,
)
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.compiler import (
    CompiledGeneralSimulationV2,
    compile_general_simulation_v2,
)
from cybernetic_influence.general_simulation.contracts_v2 import (
    ScenarioSpecV2,
    adapt_general_proposal_v1,
)
from cybernetic_influence.general_simulation.study_models import (
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
        **payload,
        record_digest=_digest(payload),
    )

    assert bundle.bundle_version == 2
    assert "analysis_specs" not in bundle.model_dump(mode="json")


def test_analysis_contract_rejects_execution_authority_fields() -> None:
    payload = _waltzman_spec().model_dump(mode="json")
    payload["schedule"] = []

    with pytest.raises(ValidationError, match="schedule"):
        AnalysisSpecV2.model_validate(payload)
