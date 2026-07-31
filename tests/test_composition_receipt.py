"""Focused Slice-25A contracts for observable reviewed composition."""

from __future__ import annotations

from cybernetic_influence.authoring import compile_scenario
from cybernetic_influence.authoring.composition import (
    ComponentSelectionV1,
    resolve_component_selections,
    reviewed_component_registry,
)
from cybernetic_influence.authoring.examples import reviewed_coordination_proposal
from cybernetic_influence.authoring.service import DraftAuthoringService
from cybernetic_influence.authoring.store import AuthoringDraftStore
from cybernetic_influence.run_store import now_iso
from pathlib import Path


def test_compiled_scenario_retains_deterministic_reviewed_component_receipt() -> None:
    compiled = compile_scenario(reviewed_coordination_proposal())

    receipt = compiled.composition_receipt

    assert receipt.scenario_id == compiled.scenario.scenario_id
    assert receipt.workflow_template_id == "coordination_decision_v1"
    assert len(receipt.registry_digest) == 64
    assert len(receipt.digest) == 64
    kinds = {item.component_kind for item in receipt.selected_components}
    assert {"person_participant", "exact_mechanism", "directed_connection"} <= kinds
    assert "analytical_boundary" in kinds
    assert receipt.diagnostics[0].code == "runtime_surfaces_resolved"


def test_reviewed_registry_exposes_only_execution_or_analysis_surfaces() -> None:
    registry = reviewed_component_registry()

    assert {item.component_kind for item in registry} == {
        "person_participant",
        "stateful_object",
        "information_carrier",
        "place",
        "directed_connection",
        "exact_mechanism",
        "analytical_boundary",
    }
    assert all(item.version == 1 for item in registry)


def test_component_selection_rejects_unknown_versions_and_duplicate_ids() -> None:
    resolved = resolve_component_selections(
        [
            ComponentSelectionV1(
                component_id="triager", component_kind="person_participant", version=1
            )
        ]
    )
    assert resolved[0].component_kind == "person_participant"

    try:
        resolve_component_selections(
            [
                ComponentSelectionV1(
                    component_id="unknown", component_kind="person_participant", version=2
                )
            ]
        )
    except ValueError as error:
        assert "unknown reviewed component" in str(error)
    else:  # pragma: no cover - documents the mandatory negative control.
        raise AssertionError("unknown component version was accepted")

    try:
        resolve_component_selections(
            [
                ComponentSelectionV1(
                    component_id="duplicate", component_kind="person_participant", version=1
                ),
                ComponentSelectionV1(
                    component_id="duplicate", component_kind="exact_mechanism", version=1
                ),
            ]
        )
    except ValueError as error:
        assert "duplicate component_id" in str(error)
    else:  # pragma: no cover - documents the mandatory negative control.
        raise AssertionError("duplicate component ID was accepted")


def test_existing_approved_draft_without_receipt_digest_remains_runnable(tmp_path: Path) -> None:
    store = AuthoringDraftStore(tmp_path / "drafts")
    document = store.create(now=now_iso())
    proposal = reviewed_coordination_proposal().model_dump(mode="json")
    approved = {
        **document,
        "revision": 1,
        "status": "approved",
        "proposal": proposal,
        "approval": {
            "approved_from_revision": 0,
            "proposal_digest": compile_scenario(
                reviewed_coordination_proposal()
            ).proposal_digest,
            "template_id": "coordination_decision_v1",
            "approved_at": now_iso(),
        },
        "updated_at": now_iso(),
    }
    saved = store.replace(
        str(document["draft_id"]), expected_revision=0, document=approved
    )

    compiled = DraftAuthoringService(store=store).approved_compile(str(saved["draft_id"]))

    assert compiled.composition_receipt.workflow_template_id == "coordination_decision_v1"
