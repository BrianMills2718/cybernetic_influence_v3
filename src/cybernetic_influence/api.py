"""Operator-first API for retained, temporally inspectable simulator runs."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
from collections.abc import Awaitable, Callable, Sequence
from copy import deepcopy
from pathlib import Path
from threading import Event, Lock, Thread, local
from time import sleep
from typing import Literal, cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, JsonValue

from cybernetic_influence.authoring.compiler import AuthoringCompilationError
from cybernetic_influence.authoring.models import (
    ComponentCompositionConfigurationReview,
    CoordinationDecisionWorkflowDraft,
    CoordinationScenarioReview,
    InfluenceNetworkWorkflowDraft,
    PersonDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.influence_network import influence_network_outcome
from cybernetic_influence.authoring.service import (
    AUTHORING_MAX_ATTEMPTS,
    AUTHORING_MAX_BUDGET,
    AUTHORING_MODEL,
    AUTHORING_MODEL_OPTIONS,
    AUTHORING_REASONING_EFFORT,
    AUTHORING_REASONING_EFFORTS,
    AuthoringModel,
    AuthoringReasoningEffort,
    DraftAuthoringService,
    StructuredCall,
    authoring_contract,
)
from cybernetic_influence.authoring.store import (
    AuthoringDraftStore,
    DraftConflictError,
    DraftNotFoundError,
)
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralSimulationProposalV1,
)
from cybernetic_influence.general_simulation.analysis_service import (
    analyze_run_evidence_v2,
    build_run_evidence_bundle_v2,
)
from cybernetic_influence.general_simulation.compiler import (
    CompiledGeneralSimulationV1,
    CompiledGeneralSimulationV2,
    GeneralCompilationError,
    compile_general_simulation_v2,
)
from cybernetic_influence.general_simulation.contracts_v2 import (
    RunSpecV2,
    adapt_general_proposal_v1,
)
from cybernetic_influence.general_simulation.projection import project_general_run
from cybernetic_influence.general_simulation.runner import run_general_simulation_v2
from cybernetic_influence.general_simulation.study_models import (
    AuthoredSimulationBundleV2,
    AuthoredSimulationProposalV2,
    adapt_authored_bundle_v1,
)

from cybernetic_influence import __version__
from cybernetic_influence.active_runtime import (
    ActiveRuntimeCheckpoint,
    ActiveRuntimeResult,
    RuntimeProgressUpdate,
)
from cybernetic_influence.active_runtime.run_control import (
    ResolvedRunControlPlan,
    RunControlSelection,
    resolve_run_control,
)
from cybernetic_influence.analysis.coordination import (
    CODER_MAX_BUDGET,
    StructuredCall as MeasurementStructuredCall,
    analyze_coordination_run,
    retain_coordination_measurement,
)
from cybernetic_influence.analysis.coordination_readout import (
    coordination_measurement_readout,
)
from cybernetic_influence.analysis.theory_analysis import (
    AnalysisSpecV2,
    RunEvidenceBundleV2,
)
from cybernetic_influence.analysis.composite_agency import (
    CompositeControlReadoutConsumer,
)
from cybernetic_influence.analysis.theory_retention import (
    build_live_theory_analysis,
    build_reference_theory_analysis,
    project_retained_theory_analysis,
    theory_analysis_contract,
)
from cybernetic_influence.causal_core.models import AnalyticalBoundary, CausalState
from cybernetic_influence.presentation import (
    BoundaryActivityProjection,
    analyst_boundaries,
    analyst_edges,
    analyst_graph_diagnostics,
    analyst_progress_projection,
    analyst_nodes,
    analyst_world,
    build_analyst_document,
    build_service_desk_analyst_document,
    clip_boundary_activity_projection,
    coalesce_retained_exact_work_moments,
    event_driven_service_desk_outcome,
    validate_retained_boundary_activities,
)
from cybernetic_influence.narration import (
    narrate_live_moments,
    reference_narration,
    validate_retained_narration,
)
from cybernetic_influence.run_store import (
    InvalidRunIdError,
    RunCorruptError,
    RunNotFoundError,
    RunStore,
    now_iso,
)
from cybernetic_influence.run_configuration import (
    EffectiveRunLlmConfiguration,
    MAXIMUM_PARTICIPANT_CALLS,
    RunLlmOptions,
    authoring_model_ids,
    coordination_live_model_ids,
    live_options_contract,
    llm_client_revision,
    model_catalog,
    resolve_live_configuration,
)
from cybernetic_influence.experiment_store import (
    ExperimentConditionResultV2,
    ExperimentNotFoundError,
    ExperimentRequestV2,
    ExperimentResultV2,
    ExperimentStore,
    InvalidExperimentIdError,
)
from cybernetic_influence.experiments.composite_agency import (
    PerturbationRowId,
    run_scripted_composite_assay,
)
from cybernetic_influence.experiments.coordination_experiment import (
    EXPERIMENT_CONDITIONS,
    EXPERIMENT_REPLICATES,
    EXPERIMENT_RUN_COUNT,
    CoordinationExperimentReadoutV1,
    CoordinationExperimentRuntimeFixture,
    LIVE_COORDINATION_PROBE_CONDITIONS,
    LiveCoordinationProbeCondition,
    coordination_experiment_fixture,
    coordination_live_probe_bindings,
    coordination_live_probe_fixture,
    run_scripted_coordination_experiment,
)
from cybernetic_influence.scenarios.service_desk import (
    RuntimePaused,
    SERVICE_DESK_MODEL,
    SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
    ServiceDeskCognitionProfile,
    run_event_driven_service_desk,
    service_desk_runtime_config,
    service_desk_run_control_options,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_native_bindings,
    service_desk_scripted_bindings,
)
from cybernetic_influence.scenarios.physical_access import (
    PHYSICAL_ACCESS_MODEL,
    PHYSICAL_ACCESS_REASONING_EFFORT,
    build_physical_access_readout,
    physical_access_arm_configurations,
    physical_access_fixture,
    physical_access_native_bindings,
    physical_access_scripted_bindings,
    physical_access_summary,
    run_physical_access,
    physical_access_runtime_config,
)
from cybernetic_influence.scenarios.purchase_payment import (
    PURCHASE_PAYMENT_MODEL,
    PURCHASE_PAYMENT_REASONING_EFFORT,
    build_purchase_payment_readout,
    purchase_payment_arm_configurations,
    purchase_payment_fixture,
    purchase_payment_native_bindings,
    purchase_payment_scripted_bindings,
    purchase_payment_summary,
    run_purchase_payment,
    purchase_payment_runtime_config,
)
from cybernetic_influence.scenarios.coordination_decision import (
    MINUTES_PER_DAY,
    CoordinationDecisionFixture,
    CoordinationRuntimePaused,
    CoordinationRuntimeFixture,
    baseline_coordination_fixture,
    coordination_native_bindings,
    coordination_run_control_plan,
    coordination_runtime_config,
    coordination_runtime_fixture,
    coordination_scripted_bindings,
    heterogeneous_pressure_coordination_fixture,
    run_coordination,
    stabilization_coordination_fixture,
)
from cybernetic_influence.scenarios.regional_outbreak import (
    AGENT_IDS as OUTBREAK_AGENT_IDS,
    CSO_IDS as OUTBREAK_CSO_IDS,
    MAX_ROUNDS as OUTBREAK_MAX_ROUNDS,
    SOURCE_IDS as OUTBREAK_SOURCE_IDS,
    OutbreakCondition,
    OutbreakFixture,
    OutbreakScenarioConfiguration,
    default_outbreak_configuration,
    outbreak_bindings,
    outbreak_fixture as regional_outbreak_fixture,
    outbreak_readout,
    outbreak_runtime_config,
    run_outbreak,
)

logger = logging.getLogger(__name__)


class RunRequest(BaseModel):
    """One request from the closed PoC scenario catalog."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal[
        "service_desk",
        "physical_access",
        "purchase_payment",
        "coordination_decision",
        "regional_outbreak",
    ] = "service_desk"
    cognition_profile: ServiceDeskCognitionProfile = "position_context"
    arm_id: str = "baseline"
    execution: Literal["scripted", "live"] = "scripted"
    llm_options: RunLlmOptions | None = None
    run_control: RunControlSelection | None = None
    regional_outbreak_configuration: OutbreakScenarioConfiguration | None = None
    run_id: str | None = None


class DraftMessageRequest(BaseModel):
    """One idempotent conversational update to an authoring draft."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    message_id: str
    message: str
    model: AuthoringModel = AUTHORING_MODEL
    reasoning_effort: AuthoringReasoningEffort = AUTHORING_REASONING_EFFORT
    mode: Literal["discuss", "configure"] = "configure"


AUTHORING_PHASE_LABELS = {
    "queued": "Starting the authoring model",
    "discussion": "Understanding the simulation",
    "proposal_generation": "Drafting people and world",
    "contract_materialization": "Resolving exact references",
    "compiling": "Checking runnable contracts",
    "dependency_review": "Reviewing causal dependencies",
    "repairing": "Repairing the configuration",
    "retaining": "Saving the editable simulation",
    "complete": "Step complete",
    "failed": "Generation stopped",
}


class DraftApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int


class DraftPersonEditRequest(BaseModel):
    """One idempotent direct edit to a person in a retained proposal."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    edit_id: str
    person: PersonDraft


class DraftProposalEditRequest(BaseModel):
    """One idempotent complete typed-proposal edit."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    edit_id: str
    proposal: ScenarioDraftProposal


class DraftGeneralProposalEditRequest(BaseModel):
    """One idempotent complete general-world semantic edit."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    edit_id: str
    proposal: (
        GeneralSimulationProposalV1
        | AuthoredSimulationProposalV2
        | AuthoredSimulationBundleV2
    )


class DraftCoordinationEditRequest(BaseModel):
    """One idempotent semantic edit to a coordination proposal."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    edit_id: str
    configuration: CoordinationScenarioReview


class DraftComponentCompositionEditRequest(BaseModel):
    """One idempotent semantic edit to the reviewed component composition."""

    model_config = ConfigDict(extra="forbid", strict=True)
    expected_revision: int
    edit_id: str
    configuration: ComponentCompositionConfigurationReview


class AuthoredRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    execution: Literal["scripted", "live"] = "scripted"
    llm_options: RunLlmOptions | None = None
    narration: Literal["deterministic", "llm"] = "deterministic"


class RunAnalysisAttachmentRequest(BaseModel):
    """One execution-inert analysis lens attached to retained evidence."""

    model_config = ConfigDict(extra="forbid", strict=True)
    analysis_spec: AnalysisSpecV2


class CompositeAssayRowResponse(BaseModel):
    """One retained comparison row projected for the analyst UI."""

    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str
    created_at: str
    status: Literal["completed"]
    row_id: PerturbationRowId
    readout: CompositeControlReadoutConsumer
    boundary_activity: BoundaryActivityProjection
    configuration_diff: dict[str, JsonValue]


class CompositeAssayResponse(BaseModel):
    """The exact five-row comparison envelope."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal[1] = 1
    assay_id: str
    status: Literal["completed"] = "completed"
    execution: Literal["scripted_reference"] = "scripted_reference"
    provider_calls: Literal[0] = 0
    rows: list[CompositeAssayRowResponse]


class CompositeAssayTrashResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    assay_id: str
    trashed_run_count: Literal[5]


class SimulationReplayFact(BaseModel):
    """One compact fact shown alongside a guided replay scene."""

    model_config = ConfigDict(extra="forbid", strict=True)

    label: str
    value: str


class SimulationReplayNodeOverride(BaseModel):
    """Scene-specific retained state for one otherwise stable graph node."""

    model_config = ConfigDict(extra="forbid", strict=True)

    node_id: str
    description: str


class SimulationReplayScene(BaseModel):
    """One evidence-backed step in a progressively disclosed run replay."""

    model_config = ConfigDict(extra="forbid", strict=True)

    scene_id: str
    sequence: int
    kind: Literal[
        "question", "setup", "information", "cognition", "decisions", "event", "outcome"
    ]
    title: str
    summary: str
    round_index: int | None = None
    visible_node_ids: list[str]
    visible_edge_ids: list[str]
    focus_node_ids: list[str]
    focus_edge_ids: list[str]
    node_overrides: list[SimulationReplayNodeOverride]
    facts: list[SimulationReplayFact]


class SimulationReplay(BaseModel):
    """Shared walkthrough projection for every completed simulation."""

    model_config = ConfigDict(extra="forbid", strict=True)

    contract: Literal["simulation-replay.v1"] = "simulation-replay.v1"
    question: str
    scenes: list[SimulationReplayScene]


class CoordinationExperimentTrashResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    experiment_id: str
    trashed_run_count: Literal[8]


def _coordination_contract(condition: str) -> CoordinationDecisionFixture:
    builders = {
        "baseline": baseline_coordination_fixture,
        "heterogeneous_pressure": heterogeneous_pressure_coordination_fixture,
        "stabilization": stabilization_coordination_fixture,
    }
    builder = builders.get(condition)
    if builder is not None:
        return builder()
    if condition in EXPERIMENT_CONDITIONS:
        return coordination_experiment_fixture(condition).runtime.contract
    raise ValueError("unknown coordination-decision condition")


def _coordination_outcome(
    result: ActiveRuntimeResult,
) -> tuple[dict[str, object], str, str]:
    state = result.core_result.final_state
    status = str(
        state.fact("external_decision_registry.received_status").value
    )
    scope = str(state.fact("external_decision_registry.received_scope").value)
    labels = {
        "deploy_on_time": "The full proposal was approved",
        "scope_reduced": "A narrower proposal was approved",
        "no_decision_by_horizon": "The group did not reach a decision",
    }
    summaries = {
        "deploy_on_time": (
            "After reviewing the proposal, all five team members supported the "
            "full plan and the final decision was recorded."
        ),
        "scope_reduced": (
            "New technical, policy, and local safety concerns made the original plan "
            "too risky. Independent checks resolved enough uncertainty for all five "
            "team members to support a smaller version, and that decision was recorded."
        ),
        "no_decision_by_horizon": (
            "No proposal satisfied the final decision gate before the modeled "
            "deadline, so no collective decision was recorded."
        ),
    }
    outcome = {
        "final_status": status,
        "final_scope": scope,
        "meeting_cycles": 4,
        "causal_moment_count": len(result.attempts) + len(result.exact_work),
        "participant_activation_count": sum(
            len(attempt.participants) for attempt in result.attempts
        ),
        "model_calls": result.model_calls,
        "known_cost": result.total_observed_cost,
        "cost_fully_observable": result.cost_fully_observable,
    }
    return outcome, labels.get(status, status.replace("_", " ").title()), summaries.get(
        status,
        "The exact decision registry retained the terminal coordination outcome.",
    )


def _coordination_reference_narration(
    document: dict[str, object],
) -> dict[str, object]:
    """Render the scripted proof without claiming a narrator model call."""
    raw_timeline = document.get("timeline", [])
    raw_moments = document.get("moments", [])
    if not isinstance(raw_timeline, list) or not isinstance(raw_moments, list):
        raise ValueError("coordination narration evidence is malformed")
    timeline = {
        str(item["event_id"]): item
        for item in raw_timeline
        if isinstance(item, dict) and isinstance(item.get("event_id"), str)
    }
    raw_outcome = document.get("outcome")
    final_status = (
        str(raw_outcome.get("final_status"))
        if isinstance(raw_outcome, dict)
        and isinstance(raw_outcome.get("final_status"), str)
        else None
    )
    moments: list[dict[str, object]] = []

    def readable_summary(value: str) -> str:
        replacements = {
            "The coordinator proposed scope_reduced at reduced scope.": (
                "The coordinator submitted the smaller plan for final approval."
            ),
            "changed commitment to support_reduced": "supported a smaller deployment",
            "changed commitment to support_full": "supported the full deployment",
            "changed commitment to defer": "decided to wait for more information",
            "The retained scheduler": "The schedule",
            "modeled day": "day",
            "technical_validation_lead": "The technical lead",
            "local_public_health_liaison": "The local health liaison",
            "partner_representative": "The partner representative",
            "Technical_pressure_source": "The technical concern source",
            "Policy_pressure_source": "The government-oversight concern source",
            "Local_pressure_source": "The local safety concern source",
            "technical_pressure_source": "The technical concern source",
            "policy_pressure_source": "The government-oversight concern source",
            "local_pressure_source": "The local safety concern source",
            "oversight_review": "the oversight review",
            "sovereignty_concern": "the government-oversight concern",
            "validation_pending": "the local concern as awaiting verification",
            "scope_reduced": "a smaller deployment",
        }
        result = value
        for source, target in replacements.items():
            result = result.replace(source, target)
        return result[0].upper() + result[1:] if result else result

    def exact_result_paragraphs(
        events: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        outcomes: list[tuple[str, str]] = []
        for event in events:
            summary = event.get("summary")
            event_id = event.get("event_id")
            if (
                event.get("kind") != "mechanism_executed"
                or not isinstance(summary, str)
                or not isinstance(event_id, str)
                or " outcome " not in summary
            ):
                continue
            outcomes.append((summary.rpartition(" outcome ")[2].rstrip("."), event_id))
        if not outcomes:
            return []
        ordered_codes = list(dict.fromkeys(code for code, _ in outcomes))
        counts = {code: sum(item == code for item, _ in outcomes) for code in ordered_codes}
        labels = {
            "meeting_wake_recorded": "The schedule retained the next meeting.",
            "issue_open": "The relevant issue was recorded as open.",
            "issue_resolved": "The relevant issue was recorded as resolved.",
            "commitment_recorded": "The latest participant commitment was recorded.",
            "source_disposition_recorded": "The team's disposition of the new concern was recorded.",
            "verification_answered": "The independent verification result was recorded.",
            "scope_threshold_denied_no_change": (
                "The proposal record rejected the requested scope because the required support was absent."
            ),
            "scope_threshold_recorded": "The proposal record accepted the selected scope.",
            "terminal_decision_accepted": (
                "The deadline gate recorded that no collective decision had "
                "been approved."
                if final_status == "no_decision_by_horizon"
                else "The final decision passed the exact support and review gate."
            ),
            "external_decision_received": (
                "The external registry recorded that the deadline passed "
                "without an approved collective decision."
                if final_status == "no_decision_by_horizon"
                else "The external decision registry received the final decision."
            ),
        }
        sentences: list[str] = []
        for code in ordered_codes:
            count = counts[code]
            if code == "alignment_message_delivered":
                sentences.append(
                    f"The coordinator's request for explicit review reached {count} "
                    f"team member{'s' if count != 1 else ''}."
                )
            elif code == "source_message_delivered":
                sentences.append(
                    f"{count} new concern{'s' if count != 1 else ''} reached "
                    f"the responsible team member{'s' if count != 1 else ''}."
                )
            elif code == "verification_response_delivered":
                sentences.append(
                    f"The verification result reached {count} "
                    f"team member{'s' if count != 1 else ''}."
                )
            elif code in labels:
                sentences.append(labels[code])
            else:
                sentences.append(
                    f"The exact workflow recorded {code.replace('_', ' ')}."
                )
        return [
            {
                "text": " ".join(sentences),
                "source_event_ids": [event_id for _, event_id in outcomes],
            }
        ]

    for raw_moment in raw_moments:
        if not isinstance(raw_moment, dict):
            raise ValueError("coordination causal moment is malformed")
        event_ids = raw_moment.get("event_ids", [])
        participants = raw_moment.get("participants", [])
        if (
            not isinstance(event_ids, list)
            or not all(isinstance(item, str) for item in event_ids)
            or not isinstance(participants, list)
            or not all(isinstance(item, str) for item in participants)
        ):
            raise ValueError("coordination causal moment evidence is malformed")
        if raw_moment.get("silent") is True and not event_ids:
            # Participant traces retain these no-action opportunities. The
            # human narrative stays focused on material causal development.
            continue
        events = [timeline[item] for item in event_ids if item in timeline]
        if len(events) != len(event_ids):
            raise ValueError("coordination narrative references an unknown event")
        summaries = [
            str(item.get("summary"))
            for item in events
            if isinstance(item.get("summary"), str)
        ]
        participant_labels = [item.replace("_", " ") for item in participants]
        participant_text = (
            " and ".join(participant_labels)
            if len(participant_labels) <= 3
            else f"{len(participant_labels)} scheduled participants"
        ) or "the exact runtime"
        logical_time = raw_moment.get("logical_time")
        if not isinstance(logical_time, int) or isinstance(logical_time, bool):
            raise ValueError("coordination causal moment time is malformed")
        day, minute = divmod(logical_time, MINUTES_PER_DAY)
        modeled_time = f"day {day}" if minute == 0 else f"day {day}, minute {minute}"
        if summaries:
            selected_summaries = [summaries[0]]
            if len(summaries) > 1 and summaries[-1] != summaries[0]:
                selected_summaries.append(summaries[-1])
            concise = (
                f"{participant_text.capitalize()} advanced the "
                f"decision process. {' '.join(selected_summaries)}"
            )
        else:
            concise = (
                f"{participant_text.capitalize()} completed its "
                "scheduled opportunity without a retained external action or world change."
            )
        action_summaries = [
            readable_summary(str(item["summary"]))
            for item in events
            if item.get("kind") == "action_attempted"
            and isinstance(item.get("summary"), str)
        ]
        if participants and all(item.endswith("_pressure_source") for item in participants):
            concise = (
                "New technical, government-oversight, and "
                "local safety concerns reached the team."
            )
        elif action_summaries:
            concise = " ".join(action_summaries)
        if len(concise) > 360:
            concise = f"{concise[:357].rstrip()}…"
        number = len(moments) + 1
        exact_paragraphs = exact_result_paragraphs(events)
        action_event_ids = [
            str(item["event_id"])
            for item in events
            if item.get("kind") == "action_attempted"
            and isinstance(item.get("event_id"), str)
        ]
        detailed_paragraphs: list[dict[str, object]] = []
        if action_summaries:
            detailed_paragraphs.append(
                {
                    "text": concise,
                    "source_event_ids": action_event_ids,
                }
            )
        detailed_paragraphs.extend(exact_paragraphs)
        if not detailed_paragraphs:
            detailed_paragraphs.append(
                {
                    "text": readable_summary(concise),
                    "source_event_ids": event_ids,
                }
            )
        moments.append(
            {
                "narrative_version": 2,
                "moment": number,
                "activation": raw_moment.get("activation"),
                "participants": participants,
                "causal_time": raw_moment.get("causal_time"),
                "causal_timestamp": raw_moment.get("causal_timestamp"),
                "logical_time": logical_time,
                "narrative": concise,
                "concise_narrative": concise,
                "source_event_ids": event_ids,
                "detailed_paragraphs": detailed_paragraphs,
            }
        )
    return {
        "status": "completed",
        "reason": (
            "Deterministic reference narration derived from retained exact events; "
            "no narrator model was called."
        ),
        "model_calls": 0,
        "cost": 0.0,
        "moments": moments,
        "calls": [],
    }


def _decision_stance(step: dict[str, object]) -> str:
    actions = step.get("actions")
    if not isinstance(actions, list):
        return "defer"
    for action in actions:
        if not isinstance(action, dict):
            continue
        payload = action.get("payload")
        if not isinstance(payload, dict):
            continue
        stance = payload.get("stance", payload.get("commitment"))
        if isinstance(stance, str):
            return stance
    return "defer"


def _stance_summary(decisions: list[dict[str, object]]) -> str:
    counts = {"support": 0, "conditional": 0, "defer": 0, "oppose": 0}
    for decision in decisions:
        stance = _decision_stance(decision)
        counts[stance] = counts.get(stance, 0) + 1
    return " · ".join(
        f"{count} {stance}"
        for stance, count in counts.items()
        if count
    ) or "No retained positions"


def _replay_node_kind(raw_kind: object) -> str:
    """Map canonical subsystem kinds to the small shared visual language."""

    kind = str(raw_kind or "thing")
    if kind in {"person", "autonomous_participant"}:
        return "person"
    if kind in {"source", "source_process", "exercise_control"}:
        return "source"
    if kind in {"information", "document"} or kind.endswith("_record"):
        return "information"
    if kind in {"physical_space", "place"}:
        return "place"
    if kind in {"equipment", "resource"}:
        return "resource"
    if kind in {
        "mechanism",
        "deterministic_process",
        "state_machine",
        "authentication_service",
        "authorization_service",
        "decision_register",
        "allocation_authority",
    }:
        return "mechanism"
    return "thing"


def _canonical_replay_network(
    nodes: list[object],
    edges: list[object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Adapt any retained canonical graph to the shared replay graph contract."""

    projected_nodes: list[dict[str, object]] = []
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            continue
        projected_node: dict[str, object] = {
            "id": str(node["id"]),
            "kind": _replay_node_kind(node.get("kind")),
            "canonical_kind": str(node.get("kind") or "thing"),
            "label": str(node.get("label") or node["id"]).replace("_", " "),
            "description": str(node.get("description") or "Retained world entity."),
        }
        if isinstance(node.get("mechanism_kind"), str):
            projected_node["mechanism_kind"] = str(node["mechanism_kind"])
        projected_nodes.append(projected_node)
    node_ids = {str(node["id"]) for node in projected_nodes}
    projected_edges: list[dict[str, object]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        edge_id = edge.get("id")
        source = edge.get("source")
        target = edge.get("target")
        if not all(isinstance(value, str) for value in (edge_id, source, target)):
            continue
        if source not in node_ids or target not in node_ids:
            continue
        exact_routes = edge.get("exact_route_ids")
        route_ids = (
            [str(item) for item in exact_routes if isinstance(item, str)]
            if isinstance(exact_routes, list)
            else [str(edge_id)]
        )
        projected_edges.append(
            {
                "id": str(edge_id),
                "kind": str(edge.get("kind") or "connection"),
                "source": str(source),
                "target": str(target),
                "enabled": edge.get("enabled") is not False,
                "directed": True,
                "description": str(
                    edge.get("description") or "Retained directed connection."
                ),
                "routeIds": route_ids or [str(edge_id)],
            }
        )
    return projected_nodes, projected_edges


def _general_world_node_overrides(
    raw_general_simulation: object,
) -> dict[int, list[SimulationReplayNodeOverride]]:
    """Project the retained canonical state at each committed revision."""

    if not isinstance(raw_general_simulation, dict):
        return {}
    raw_checkpoints = raw_general_simulation.get("checkpoints")
    checkpoints = raw_checkpoints if isinstance(raw_checkpoints, list) else []

    def canonical_component(checkpoint: object) -> dict[str, object] | None:
        if not isinstance(checkpoint, dict):
            return None
        try:
            component = checkpoint["game_masters"]["general_world_game_master"][
                "components"
            ]["context_components"]["canonical_world"]
        except (KeyError, TypeError):
            return None
        return component if isinstance(component, dict) else None

    def readable_state(record_state: object) -> str:
        """A record's retained state, in the same shape the resource branch uses.

        This was json.dumps(..., sort_keys=True), so every person node in an
        authored run displayed its description as {"position": "Clinical lead for
        Ward A"} -- braces, quotes and all -- on the replay graph. The flagship
        case study never showed it because its people carry authored descriptions,
        so the defect only ever appeared in a simulation a reader made themselves.
        Nothing parses this field; it is display text.
        """
        if not isinstance(record_state, dict) or not record_state:
            return "no retained state"
        parts: list[str] = []
        for key in sorted(record_state):
            value = record_state[key]
            rendered = (
                json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else str(value)
            )
            parts.append(f"{key.replace('_', ' ')}: {rendered}")
        return "; ".join(parts)

    def descriptions(state: object) -> list[SimulationReplayNodeOverride]:
        if not isinstance(state, dict):
            return []
        projected: list[SimulationReplayNodeOverride] = []
        raw_records = state.get("records")
        if isinstance(raw_records, dict):
            for record_id, record in raw_records.items():
                if not isinstance(record_id, str) or not isinstance(record, dict):
                    continue
                record_state = record.get("state")
                projected.append(
                    SimulationReplayNodeOverride(
                        node_id=record_id,
                        description=readable_state(record_state),
                    )
                )
        raw_resources = state.get("resources")
        if isinstance(raw_resources, dict):
            for resource_id, resource in raw_resources.items():
                if not isinstance(resource_id, str) or not isinstance(resource, dict):
                    continue
                projected.append(
                    SimulationReplayNodeOverride(
                        node_id=resource_id,
                        description=(
                            f"quantity: {resource.get('quantity', 0)}; "
                            f"custodian: {str(resource.get('custodian_id') or 'unassigned').replace('_', ' ')}"
                        ),
                    )
                )
        return projected

    revisions: dict[int, list[SimulationReplayNodeOverride]] = {}
    first_component = canonical_component(checkpoints[0]) if checkpoints else None
    if first_component is not None:
        spec = first_component.get("spec")
        initial_state = spec.get("initial_state") if isinstance(spec, dict) else None
        revisions[0] = descriptions(initial_state)
    for checkpoint in checkpoints:
        component = canonical_component(checkpoint)
        state = component.get("state") if component is not None else None
        if not isinstance(state, dict):
            continue
        revision = state.get("revision")
        if isinstance(revision, int) and not isinstance(revision, bool):
            revisions[revision] = descriptions(state)
    return revisions


def _attach_transitions_to_causal_moments(
    raw_moments: list[object],
    transition_evidence: list[object],
) -> list[dict[str, object]]:
    """Join transaction attempts to their authored moment, never by list position."""
    moments = [dict(item) for item in raw_moments if isinstance(item, dict)]
    moment_ids = {
        str(moment_id): index
        for index, moment in enumerate(moments)
        if isinstance(
            (moment_id := moment.get("event_id", moment.get("moment_id"))), str
        )
    }
    intent_to_moment: dict[str, int] = {}
    for index, moment in enumerate(moments):
        intent_ids = moment.get("intent_ids")
        if isinstance(intent_ids, list):
            for intent_id in intent_ids:
                if isinstance(intent_id, str):
                    intent_to_moment[intent_id] = index
    grouped: list[list[dict[str, object]]] = [[] for _ in moments]
    unresolved: list[dict[str, object]] = []
    for raw_transition in transition_evidence:
        if not isinstance(raw_transition, dict):
            continue
        transaction = raw_transition.get("transaction")
        refs = (
            transaction.get("evidence_refs")
            if isinstance(transaction, dict)
            else None
        )
        matching_indices = {
            moment_ids[item]
            for item in refs
            if isinstance(item, str) and item in moment_ids
        } if isinstance(refs, list) else set()
        if not matching_indices and isinstance(transaction, dict):
            intent_ids = transaction.get("intent_ids")
            matching_indices = {
                intent_to_moment[item]
                for item in intent_ids
                if isinstance(item, str) and item in intent_to_moment
            } if isinstance(intent_ids, list) else set()
        if len(matching_indices) == 1:
            grouped[matching_indices.pop()].append(raw_transition)
        else:
            unresolved.append(raw_transition)
    if unresolved and len(unresolved) == len(moments):
        for index, transition in enumerate(unresolved):
            grouped[index].append(transition)
        unresolved = []
    if unresolved:
        raise ValueError(
            f"could not attach {len(unresolved)} transition attempt(s) to a causal moment"
        )
    return [
        {**moment, "transitions": grouped[index]}
        for index, moment in enumerate(moments)
    ]


def _simulation_replay(
    *,
    title: object,
    headline: object,
    summary: object,
    outcome: dict[str, object],
    rounds: list[dict[str, object]],
    network_nodes: list[dict[str, object]],
    network_edges: list[dict[str, object]],
    raw_moments: object,
    cognitive_traces: object = None,
    general_world: bool = False,
    question_is_analyst_framing: bool = False,
    node_overrides_by_revision: dict[int, list[SimulationReplayNodeOverride]] | None = None,
) -> dict[str, object]:
    """Build one small, evidence-backed walkthrough independent of page layout."""

    def replay_value(value: object) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, str):
            return value.replace("_", " ")
        if isinstance(value, dict):
            return "; ".join(
                f"{str(key).replace('_', ' ')}: {replay_value(item)}"
                for key, item in list(value.items())[:4]
            )
        if isinstance(value, list):
            return ", ".join(replay_value(item) for item in value[:4])
        return str(value)

    question = "What collective outcome will emerge?"
    for round_item in rounds:
        decisions = round_item.get("decisions")
        if not isinstance(decisions, list):
            continue
        for decision in decisions:
            if not isinstance(decision, dict):
                continue
            observations = decision.get("observations")
            if not isinstance(observations, list):
                continue
            for observation in observations:
                if (
                    isinstance(observation, dict)
                    and observation.get("kind") == "decision_round"
                    and isinstance(observation.get("collective_question"), str)
                ):
                    question = str(observation["collective_question"])
                    break
            if question != "What collective outcome will emerge?":
                break
        if question != "What collective outcome will emerge?":
            break

    node_ids = {
        str(node["id"])
        for node in network_nodes
        if isinstance(node.get("id"), str)
    }
    edge_by_id = {
        str(edge["id"]): edge
        for edge in network_edges
        if isinstance(edge.get("id"), str)
    }
    source_ids = [
        str(node["id"])
        for node in network_nodes
        if node.get("kind") in {"source", "thing"}
        and isinstance(node.get("id"), str)
    ]
    person_ids = [
        str(node["id"])
        for node in network_nodes
        if node.get("kind") == "person" and isinstance(node.get("id"), str)
    ]
    node_kind_by_id = {
        str(node["id"]): node.get("kind")
        for node in network_nodes
        if isinstance(node.get("id"), str)
    }
    node_label_by_id = {
        str(node["id"]): str(node.get("label") or node["id"])
        for node in network_nodes
        if isinstance(node.get("id"), str)
    }
    gate_ids = ["collective_decision"] if "collective_decision" in node_ids else []
    if not gate_ids:
        gate_ids = [
            str(node["id"])
            for node in network_nodes
            if node.get("kind") == "mechanism"
            and isinstance(node.get("id"), str)
            and any(
                marker in (
                    f"{node.get('id', '')} {node.get('label', '')}"
                ).lower()
                for marker in ("decision", "outcome", "gate")
            )
        ][:1]
    if general_world:
        resource_ids = [
            str(node["id"])
            for node in network_nodes
            if node.get("kind") == "resource" and isinstance(node.get("id"), str)
        ][:3]
        orienting_mechanism_ids = [
            str(node["id"])
            for node in network_nodes
            if node.get("kind") == "mechanism"
            and isinstance(node.get("id"), str)
            and str(node["id"]) not in gate_ids
        ][:2]
        setup_ids = list(
            dict.fromkeys(
                [*person_ids, *gate_ids, *resource_ids, *orienting_mechanism_ids]
            )
        )
    else:
        setup_ids = source_ids + person_ids + gate_ids
    decision_edge_ids = [
        edge_id
        for edge_id, edge in edge_by_id.items()
        if edge.get("kind") == "contributed_to_decision"
        or (
            edge.get("source") in person_ids
            and node_kind_by_id.get(str(edge.get("target"))) == "mechanism"
        )
    ]
    scenes: list[SimulationReplayScene] = []

    def add_scene(
        *,
        scene_id: str,
        kind: Literal[
            "question", "setup", "information", "cognition", "decisions", "event", "outcome"
        ],
        scene_title: str,
        scene_summary: str,
        visible_nodes: list[str],
        visible_edges: list[str],
        focus_nodes: list[str] | None = None,
        focus_edges: list[str] | None = None,
        facts: list[tuple[str, str]] | None = None,
        round_index: int | None = None,
        state_revision: int | None = None,
    ) -> None:
        scene = SimulationReplayScene(
            scene_id=scene_id,
            sequence=len(scenes) + 1,
            kind=kind,
            title=scene_title,
            summary=scene_summary,
            round_index=round_index,
            visible_node_ids=list(dict.fromkeys(visible_nodes)),
            visible_edge_ids=list(dict.fromkeys(visible_edges)),
            focus_node_ids=list(dict.fromkeys(focus_nodes or [])),
            focus_edge_ids=list(dict.fromkeys(focus_edges or [])),
            node_overrides=(node_overrides_by_revision or {}).get(
                state_revision if state_revision is not None else -1, []
            ),
            facts=[
                SimulationReplayFact(label=label, value=value)
                for label, value in (facts or [])
            ],
        )
        unknown_nodes = (set(scene.visible_node_ids) | set(scene.focus_node_ids)) - node_ids
        unknown_edges = (set(scene.visible_edge_ids) | set(scene.focus_edge_ids)) - set(edge_by_id)
        if unknown_nodes or unknown_edges:
            raise ValueError(
                "simulation replay references missing graph items: "
                f"nodes={sorted(unknown_nodes)} edges={sorted(unknown_edges)}"
            )
        scenes.append(scene)

    objective_assessment = outcome.get("objective_assessment")
    assessment_summary = (
        objective_assessment.get("summary")
        if isinstance(objective_assessment, dict)
        else None
    )
    assessment_status = (
        objective_assessment.get("status")
        if isinstance(objective_assessment, dict)
        else None
    )
    if not general_world or question_is_analyst_framing or gate_ids:
        add_scene(
            scene_id="question",
            kind="question",
            scene_title=(
                "Your review question"
                if question_is_analyst_framing
                else "The collective question"
                if gate_ids
                else "Simulation brief"
            ),
            scene_summary=question,
            visible_nodes=gate_ids,
            visible_edges=[],
            focus_nodes=gate_ids,
            facts=[("Simulation", str(title or "Retained simulation"))],
        )
    add_scene(
        scene_id="setup",
        kind="setup",
        scene_title="Who and what begin in the system",
        scene_summary=(
            (
                f"The retained simulation begins with {len(person_ids)} people. "
                "This opening view shows only the key decision, resources, and "
                "mechanisms; other world components appear when they become relevant."
            )
            if general_world
            else (
                f"The retained simulation begins with {len(person_ids)} people and "
                f"{len(source_ids)} configured information sources. Later messages "
                "and decisions remain hidden until their replay step."
            )
        ),
        visible_nodes=setup_ids,
        visible_edges=[],
        focus_nodes=setup_ids,
        facts=[
            ("People", str(len(person_ids))),
            (
                "Other world components" if general_world else "Information sources",
                str(len(node_ids) - len(person_ids) if general_world else len(source_ids)),
            ),
        ],
        state_revision=0 if general_world else None,
    )

    visible_nodes = list(setup_ids)
    visible_edges: list[str] = []
    decisions_have_entered = False
    for round_item in ([] if general_world else rounds):
        round_index = round_item.get("round_index")
        if not isinstance(round_index, int) or isinstance(round_index, bool):
            continue
        raw_information = round_item.get("new_information")
        information = raw_information if isinstance(raw_information, list) else []
        delivery_ids = list(
            dict.fromkeys(
                str(item["delivery_id"])
                for item in information
                if isinstance(item, dict) and isinstance(item.get("delivery_id"), str)
            )
        )
        new_message_ids = [
            f"message_{delivery_id}"
            for delivery_id in delivery_ids
            if f"message_{delivery_id}" in node_ids
        ]
        new_edge_ids = [
            edge_id
            for edge_id, edge in edge_by_id.items()
            if edge.get("source") in new_message_ids
            or edge.get("target") in new_message_ids
        ]
        visible_nodes.extend(new_message_ids)
        visible_edges.extend(new_edge_ids)
        if new_message_ids:
            add_scene(
                scene_id=f"round_{round_index}_information",
                kind="information",
                scene_title=f"New information before round {round_index}",
                scene_summary=(
                    f"{len(delivery_ids)} retained message"
                    f"{'s' if len(delivery_ids) != 1 else ''} entered through explicit delivery routes."
                ),
                visible_nodes=visible_nodes,
                visible_edges=visible_edges,
                focus_nodes=new_message_ids,
                focus_edges=new_edge_ids,
                facts=[("Messages introduced", str(len(delivery_ids)))],
                round_index=round_index,
            )

        raw_decisions = round_item.get("decisions")
        decisions = (
            [item for item in raw_decisions if isinstance(item, dict)]
            if isinstance(raw_decisions, list)
            else []
        )
        if decisions:
            if not decisions_have_entered:
                visible_edges.extend(decision_edge_ids)
                decisions_have_entered = True
            add_scene(
                scene_id=f"round_{round_index}_decisions",
                kind="decisions",
                scene_title=f"Round {round_index}: each person decides",
                scene_summary=(
                    "Each simulated person responded from their own retained context and received information."
                ),
                visible_nodes=visible_nodes,
                visible_edges=visible_edges,
                focus_nodes=person_ids + gate_ids,
                focus_edges=decision_edge_ids,
                facts=[("Positions", _stance_summary(decisions))],
                round_index=round_index,
            )

    visible_event_nodes = list(setup_ids)
    visible_event_edges: list[str] = []
    outcome_changed_nodes: list[str] = []
    if (general_world or not rounds) and isinstance(raw_moments, list):
        for index, moment in enumerate(raw_moments[:10], start=1):
            if not isinstance(moment, dict):
                continue
            narrative = moment.get("concise_narrative", moment.get("narrative"))
            if not isinstance(narrative, str) or not narrative.strip():
                continue
            raw_participants = moment.get("participants")
            participants = [
                str(item)
                for item in raw_participants
                if isinstance(item, str) and item in node_ids
            ] if isinstance(raw_participants, list) else []
            moment_minute = moment.get("minute")
            moment_traces = [
                trace
                for trace in cognitive_traces
                if isinstance(trace, dict)
                and trace.get("moment") == moment_minute
                and isinstance(trace.get("person"), str)
            ] if isinstance(cognitive_traces, list) else []
            cognition_facts: list[tuple[str, str]] = []
            cognition_people: list[str] = []
            for trace in moment_traces:
                person_id = str(trace["person"])
                cognition_people.append(person_id)
                assimilation = trace.get("assimilation")
                assimilation = assimilation if isinstance(assimilation, dict) else {}
                attended = trace.get("attended_observations")
                attended = attended if isinstance(attended, list) else []
                sources = list(
                    dict.fromkeys(
                        str(item["apparent_source"])
                        for item in attended
                        if isinstance(item, dict)
                        and isinstance(item.get("apparent_source"), str)
                    )
                )
                interpretation = str(
                    assimilation.get("interpretation") or "No interpretation retained."
                )
                additions = assimilation.get("memory_additions")
                revisions = assimilation.get("memory_revisions")
                memory_changes = [
                    str(item) for item in additions if isinstance(item, str)
                ] if isinstance(additions, list) else []
                if isinstance(revisions, list):
                    memory_changes.extend(
                        str(item.get("revised_memory"))
                        for item in revisions
                        if isinstance(item, dict)
                        and isinstance(item.get("revised_memory"), str)
                    )
                intent = trace.get("intent")
                intent = intent if isinstance(intent, dict) else {}
                contract_arguments = intent.get("transition_contract_arguments")
                structured_attempts = []
                if isinstance(contract_arguments, list):
                    for arguments in contract_arguments:
                        if not isinstance(arguments, dict):
                            continue
                        contract_id = arguments.get("contract_id")
                        if not isinstance(contract_id, str):
                            continue
                        rendered_arguments = ", ".join(
                            f"{str(key).replace('_', ' ')}={value}"
                            for key, value in arguments.items()
                            if key != "contract_id" and value is not None
                        )
                        structured_attempts.append(
                            f"{str(contract_id).replace('_', ' ')} ({rendered_arguments})"
                        )
                attempted = str(
                    intent.get("action") or "No action retained."
                ).replace("_", " ")
                if structured_attempts:
                    attempted += " · Exact attempt: " + "; ".join(structured_attempts)
                cognition_facts.append(
                    (
                        node_label_by_id.get(person_id, person_id.replace("_", " ").title()),
                        " · ".join(
                            [
                                (
                                    f"Noticed {len(attended)} observation"
                                    f"{'s' if len(attended) != 1 else ''}"
                                    + (f" from {', '.join(sources)}" if sources else "")
                                ),
                                f"Interpreted: {interpretation}",
                                (
                                    f"Memory changed: {'; '.join(memory_changes)}"
                                    if memory_changes
                                    else "Memory unchanged"
                                ),
                                f"Then attempted: {attempted}",
                            ]
                        ),
                    )
                )
            if cognition_facts:
                add_scene(
                    scene_id=f"moment_{index}_cognition",
                    kind="cognition",
                    scene_title=f"Moment {index}: what each person noticed and retained",
                    scene_summary=(
                        "Each person first interpreted only their authorized context and "
                        "updated natural-language memory. A separate model call then selected "
                        "their action; these private records are not canonical world truth."
                    ),
                    visible_nodes=[
                        person_id for person_id in cognition_people if person_id in node_ids
                    ],
                    visible_edges=[],
                    focus_nodes=[
                        person_id for person_id in cognition_people if person_id in node_ids
                    ],
                    facts=cognition_facts,
                    round_index=index,
                    state_revision=index - 1,
                )
            execution_parent = moment.get("execution_parent")
            parent_revision = (
                int(execution_parent.removeprefix("revision:"))
                if isinstance(execution_parent, str)
                and execution_parent.removeprefix("revision:").isdigit()
                else None
            )
            resulting_revision = moment.get("resulting_revision")
            transition_committed = (
                isinstance(resulting_revision, int)
                and not isinstance(resulting_revision, bool)
                and isinstance(parent_revision, int)
                and resulting_revision > parent_revision
            )
            raw_transitions = moment.get("transitions")
            transitions = (
                [item for item in raw_transitions if isinstance(item, dict)]
                if isinstance(raw_transitions, list)
                else []
            )
            if not transitions and isinstance(moment.get("transition"), dict):
                transitions = [moment["transition"]]
            operations: list[dict[str, object]] = []
            consequences: list[dict[str, object]] = []
            evidence_refs: list[str] = []
            raw_attributions: list[dict[str, object]] = []
            accepted_rationales: list[str] = []
            validation_errors: list[str] = []
            rejected_attempt_count = 0
            rejected_operation_count = 0
            accepted_attempt_count = 0
            for transition in transitions:
                transaction = transition.get("transaction")
                if not isinstance(transaction, dict):
                    continue
                raw_operations = transaction.get("operations")
                transaction_operations = (
                    [item for item in raw_operations if isinstance(item, dict)]
                    if isinstance(raw_operations, list)
                    else []
                )
                validation = transition.get("validation")
                validation = validation if isinstance(validation, dict) else None
                accepted = (
                    validation.get("accepted")
                    if isinstance(validation, dict)
                    and isinstance(validation.get("accepted"), bool)
                    else transition_committed
                )
                if accepted is False:
                    rejected_attempt_count += 1
                    rejected_operation_count += len(transaction_operations)
                    raw_errors = validation.get("errors") if validation else None
                    if isinstance(raw_errors, list):
                        validation_errors.extend(str(item) for item in raw_errors)
                    continue
                accepted_attempt_count += 1
                operation_offset = len(operations)
                operations.extend(transaction_operations)
                corrections = transition.get("envelope_corrections")
                pruned_unlicensed_effects = (
                    isinstance(corrections, list)
                    and any(
                        isinstance(item, str)
                        and "removed only the explicitly unlicensed operations" in item
                        for item in corrections
                    )
                )
                raw_consequences = transaction.get("consequences")
                if isinstance(raw_consequences, list) and not pruned_unlicensed_effects:
                    consequences.extend(
                        item for item in raw_consequences if isinstance(item, dict)
                    )
                raw_evidence_refs = transaction.get("evidence_refs")
                if isinstance(raw_evidence_refs, list):
                    evidence_refs.extend(
                        str(item) for item in raw_evidence_refs if isinstance(item, str)
                    )
                rationale = transaction.get("stated_rationale")
                if isinstance(rationale, str) and rationale.strip():
                    accepted_rationales.append(rationale.strip())
                transition_attributions = transition.get("operation_attributions")
                if isinstance(transition_attributions, list):
                    for item in transition_attributions:
                        if not isinstance(item, dict):
                            continue
                        operation_index = item.get("operation_index")
                        if not isinstance(operation_index, int) or isinstance(
                            operation_index, bool
                        ):
                            continue
                        raw_attributions.append(
                            {
                                **item,
                                "operation_index": operation_offset + operation_index,
                            }
                        )
            rejected_attempt = rejected_attempt_count > 0
            rationale = (
                accepted_rationales[0]
                if len(transitions) == 1 and accepted_rationales
                else None
            )
            contract_node_ids = list(
                dict.fromkeys(
                    str(item["contract_id"])
                    for item in raw_attributions
                    if isinstance(item, dict)
                    and isinstance(item.get("contract_id"), str)
                    and str(item["contract_id"]) in node_ids
                )
            )
            attribution_by_operation: dict[int, object] = {}
            for item in raw_attributions:
                if (
                    isinstance(item, dict)
                    and isinstance(item.get("operation_index"), int)
                    and not isinstance(item.get("operation_index"), bool)
                ):
                    op_index = cast(int, item.get("operation_index"))
                    attribution_by_operation[op_index] = item
            ranked_change_facts: list[tuple[int, int, tuple[str, str]]] = []
            changed_node_ids: list[str] = []
            changed_edge_ids: list[str] = []
            ranked_changed_node_ids: list[tuple[int, int, str]] = []
            for operation_index, operation in enumerate(operations):
                if not isinstance(operation, dict):
                    continue
                target = operation.get("target")
                if not isinstance(target, dict) or not isinstance(
                    target.get("record_id"), str
                ):
                    continue
                target_id = str(target["record_id"])
                target_type = target.get("record_type")
                attribution = attribution_by_operation.get(operation_index, {})
                exact_contract = (
                    isinstance(attribution, dict)
                    and attribution.get("classification") == "exact_contract"
                )
                target_is_resource = node_kind_by_id.get(target_id) == "resource"
                priority = (
                    0
                    if exact_contract and target_is_resource
                    else 1
                    if target_is_resource
                    else 2
                    if exact_contract
                    else 3
                )
                if target_type == "route" and target_id in edge_by_id:
                    changed_edge_ids.append(target_id)
                elif target_type == "placement":
                    placement_edge_id = f"placement:{target_id}"
                    if placement_edge_id in edge_by_id:
                        changed_edge_ids.append(placement_edge_id)
                elif target_id in node_ids:
                    changed_node_ids.append(target_id)
                    ranked_changed_node_ids.append(
                        (priority, operation_index, target_id)
                    )
                target_label = node_label_by_id.get(
                    target_id, target_id.replace("_", " ").title()
                )
                raw_value = operation.get("value")
                if operation.get("operation") == "create":
                    created_label = (
                        raw_value.get("label")
                        if isinstance(raw_value, dict)
                        and isinstance(raw_value.get("label"), str)
                        else target_label
                    )
                    ranked_change_facts.append(
                        (
                            priority if target_id in node_ids else 3,
                            operation_index,
                            ("World change", f"Created {created_label}"),
                        )
                    )
                    continue
                field = str(target.get("field") or "state").replace("_", " ")
                rendered_value = replay_value(raw_value)
                ranked_change_facts.append(
                    (
                        priority if target_id in node_ids else 3,
                        operation_index,
                        (
                            "World change",
                            f"{target_label} · {field}: {rendered_value}",
                        ),
                    )
                )
            changed_node_ids = list(
                dict.fromkeys(item[2] for item in sorted(ranked_changed_node_ids))
            )
            change_facts = [item[2] for item in sorted(ranked_change_facts)[:6]]
            communication_facts: list[tuple[str, str]] = []
            for consequence in consequences[:2]:
                if not isinstance(consequence, dict):
                    continue
                recipient = consequence.get("recipient_id")
                content = consequence.get("content")
                if not isinstance(recipient, str) or not isinstance(content, str):
                    continue
                source = str(
                    consequence.get("apparent_source") or "world"
                ).replace("_", " ").capitalize()
                recipient_label = node_label_by_id.get(
                    recipient, recipient.replace("_", " ").title()
                )
                compact_content = (
                    content if len(content) <= 220 else f"{content[:217].rstrip()}…"
                )
                communication_facts.append(
                    ("Communication", f"{source} → {recipient_label}: {compact_content}")
                )
                representation_id = consequence.get("representation_id")
                if isinstance(representation_id, str):
                    delivery_edge_id = f"delivery:{representation_id}:{recipient}"
                    if delivery_edge_id in edge_by_id:
                        changed_edge_ids.append(delivery_edge_id)
            transition_facts = [*change_facts, *communication_facts]
            if transition_committed and not transition_facts:
                transition_facts = [
                    ("World change", "No canonical fields changed in this committed moment.")
                ]
            if rejected_attempt:
                unmet_preconditions = sum(
                    error.startswith("precondition failed")
                    for error in validation_errors
                )
                rejection_reason = (
                    f"{unmet_preconditions} required precondition"
                    f"{'s were' if unmet_preconditions != 1 else ' was'} not met."
                    if unmet_preconditions == len(validation_errors)
                    and unmet_preconditions > 0
                    else f"Canonical validation recorded {len(validation_errors)} error"
                    f"{'s' if len(validation_errors) != 1 else ''}."
                )
                rejection_summary = (
                    "Canonical validation rejected the joint attempt, so none of its "
                    f"{rejected_operation_count} proposed world change"
                    f"{'s' if rejected_operation_count != 1 else ''} committed. "
                    f"{rejection_reason}"
                )
            evidence_node_ids = [
                str(item)
                for item in evidence_refs
                if isinstance(item, str) and item in node_ids
            ][:6]
            # Expand from every node the moment actually touched, not only its
            # contract nodes. A moment whose nodes arrived through changed_node_ids
            # or as participants pulled in no neighbours at all, so the scene
            # rendered disconnected dots and induced_edge_ids -- which needs BOTH
            # endpoints visible -- found nothing. On the coordination example that
            # left all ten event scenes with an empty visible_edge_ids, and one of
            # them with no nodes at all.
            neighbor_seed_ids = {*contract_node_ids, *changed_node_ids, *participants}
            mechanism_neighbor_ids: list[str] = []
            for edge in network_edges:
                if not isinstance(edge, dict):
                    continue
                neighbor_source = edge.get("source")
                neighbor_target = edge.get("target")
                if neighbor_source in neighbor_seed_ids and isinstance(
                    neighbor_target, str
                ):
                    mechanism_neighbor_ids.append(neighbor_target)
                if neighbor_target in neighbor_seed_ids and isinstance(
                    neighbor_source, str
                ):
                    mechanism_neighbor_ids.append(neighbor_source)
            # Participants ahead of the neighbour expansion: the 12-node cap below
            # now has more candidates to choose from, and a scene that drops the
            # people who acted in order to show their wiring is the wrong trade.
            moment_node_ids = list(
                dict.fromkeys(
                    [
                        *contract_node_ids,
                        *changed_node_ids,
                        *participants,
                        *evidence_node_ids,
                        *mechanism_neighbor_ids,
                    ]
                )
            )
            if not moment_node_ids:
                # A V1 scripted run retains no transitions, so contract and
                # changed nodes are empty by construction; if the moment also
                # names no participants this resolved to nothing and the scene
                # rendered a blank canvas mid-walkthrough. Fall back to the same
                # orienting set the setup scene uses. Nothing is focused, so the
                # scene claims no change -- it just keeps the stage visible
                # while the narrative explains the beat.
                moment_node_ids = list(setup_ids)
            visible_event_nodes = list(dict.fromkeys(moment_node_ids))[:12]
            visible_event_node_set = set(visible_event_nodes)
            induced_edge_ids = [
                edge_id
                for edge_id, edge in edge_by_id.items()
                if edge.get("source") in visible_event_node_set
                and edge.get("target") in visible_event_node_set
            ]
            mechanism_edge_priority = {
                "resource_input": 0,
                "resource_output": 0,
                "mechanism_write": 1,
                "permitted_route": 2,
                "capability": 3,
            }
            induced_edge_ids.sort(
                key=lambda edge_id: (
                    mechanism_edge_priority.get(
                        str(edge_by_id[edge_id].get("kind")), 4
                    ),
                    edge_id,
                )
            )
            visible_event_edges = list(
                dict.fromkeys([*changed_edge_ids, *induced_edge_ids])
            )[:18]
            outcome_changed_nodes.extend(changed_node_ids)
            focused_node_ids = [
                node_id
                for node_id in [*contract_node_ids, *changed_node_ids]
                if node_id in visible_event_node_set
            ]
            if len(transitions) > 1 and rejected_attempt:
                scene_summary = (
                    f"{len(transitions)} transaction attempts were retained: "
                    f"{accepted_attempt_count} accepted and "
                    f"{rejected_attempt_count} rejected. {narrative}"
                    if transition_facts
                    and transition_facts
                    != [
                        (
                            "World change",
                            "No canonical fields changed in this committed moment.",
                        )
                    ]
                    else (
                        f"{rejected_attempt_count} transaction attempt"
                        f"{'s were' if rejected_attempt_count != 1 else ' was'} rejected, "
                        "and the accepted follow-up committed no canonical fields. "
                        f"{rejection_reason}"
                    )
                )
            elif rejected_attempt:
                scene_summary = rejection_summary
            elif rationale and rationale.strip():
                scene_summary = rationale.strip()
            else:
                scene_summary = narrative
            rejection_facts = (
                [
                    (
                        "Attempt" if len(transitions) == 1 else "Rejected attempts",
                        (
                            f"Rejected · {rejected_operation_count} proposed world change"
                            f"{'s' if rejected_operation_count != 1 else ''}"
                            if len(transitions) == 1
                            else (
                                f"{rejected_attempt_count} · {rejected_operation_count} "
                                "proposed world changes did not commit"
                            )
                        ),
                    ),
                    ("Why", rejection_reason),
                ]
                if rejected_attempt
                else []
            )
            committed_facts = (
                transition_facts
                if transition_committed
                else [("World change", "No change committed.")]
            )
            add_scene(
                scene_id=f"event_{index}",
                kind="event",
                scene_title=str(moment.get("event_id") or f"World moment {index}")
                .replace("_", " ")
                .capitalize(),
                scene_summary=scene_summary,
                visible_nodes=visible_event_nodes,
                visible_edges=visible_event_edges,
                focus_nodes=(focused_node_ids or participants),
                focus_edges=changed_edge_ids,
                facts=[
                    ("Moment", str(index)),
                    ("People acting", str(len(participants))),
                    *(
                        [("Transaction attempts", str(len(transitions)))]
                        if len(transitions) > 1
                        else []
                    ),
                    *(
                        [*rejection_facts, *committed_facts]
                        if len(transitions) > 1
                        else [
                            *rejection_facts,
                            *(
                                [("World change", "No change committed.")]
                                if rejected_attempt
                                else committed_facts
                            ),
                        ]
                    ),
                ],
                state_revision=(
                    resulting_revision
                    if isinstance(resulting_revision, int)
                    and not isinstance(resulting_revision, bool)
                    else None
                ),
            )

    final_status = outcome.get("final_status")
    counts = outcome.get("counts")
    final_count_text = ""
    if isinstance(counts, dict):
        final_count_text = " · ".join(
            f"{int(value)} {stance}"
            for stance in ("support", "conditional", "defer", "oppose")
            if isinstance((value := counts.get(stance)), int) and value
        )
    outcome_visible_nodes = (
        list(
            dict.fromkeys(
                [*person_ids, *gate_ids, *outcome_changed_nodes, *visible_event_nodes]
            )
        )[:12]
        if general_world
        else list(node_ids)
    )
    outcome_visible_node_set = set(outcome_visible_nodes)
    outcome_visible_edges = (
        [
            edge_id
            for edge_id, edge in edge_by_id.items()
            if edge.get("source") in outcome_visible_node_set
            and edge.get("target") in outcome_visible_node_set
        ][:18]
        if general_world
        else list(edge_by_id)
    )
    add_scene(
        scene_id="outcome",
        kind="outcome",
        scene_title=str(headline or "The retained outcome"),
        scene_summary=str(
            assessment_summary
            or outcome.get("terminal_summary")
            or summary
            or "The run reached its retained terminal state."
        ),
        visible_nodes=outcome_visible_nodes,
        visible_edges=outcome_visible_edges,
        focus_nodes=gate_ids,
        focus_edges=decision_edge_ids,
        facts=(
            [
                *((
                    [("Objective assessment", str(assessment_status).replace("_", " "))]
                    if assessment_status
                    else []
                )),
                (
                    "Committed transitions",
                    str(outcome.get("accepted_transactions", 0)),
                ),
                ("Final world revision", str(outcome.get("final_revision", 0))),
            ]
            if general_world
            else [
                (
                    "Collective outcome" if gate_ids else "Outcome",
                    str(final_status or "completed").replace("_", " "),
                ),
                *(([("Final positions", final_count_text)]) if final_count_text else []),
            ]
        ),
        state_revision=(
            int(cast(int | None, outcome.get("final_revision")) or 0) if general_world else None
        ),
    )
    return SimulationReplay(question=question, scenes=scenes).model_dump(mode="json")


def _compact_run_result(document: dict[str, object]) -> dict[str, object]:
    """Project one completed run into a small human-facing result contract."""

    story = document.get("story")
    if not isinstance(story, dict):
        story = {}
    authoring = document.get("authoring")
    if not isinstance(authoring, dict):
        authoring = {}
    raw_evidence_bundle = document.get("run_evidence_bundle")
    evidence_bundle = (
        raw_evidence_bundle if isinstance(raw_evidence_bundle, dict) else {}
    )
    raw_evidence_records = evidence_bundle.get("evidence_records")
    evidence_records = (
        raw_evidence_records if isinstance(raw_evidence_records, list) else []
    )
    raw_analysis_results = document.get("analysis_results")
    analysis_results = (
        raw_analysis_results if isinstance(raw_analysis_results, list) else []
    )
    raw_authored_people = authoring.get("people")
    authored_people = (
        raw_authored_people if isinstance(raw_authored_people, list) else []
    )
    authored_person_metadata = {
        str(person["entity_id"]): {
            "label": person.get("label"),
            "position": person.get("position"),
        }
        for person in authored_people
        if isinstance(person, dict) and isinstance(person.get("entity_id"), str)
    }
    raw_nodes = document.get("nodes")
    nodes = raw_nodes if isinstance(raw_nodes, list) else []
    raw_edges = document.get("edges")
    edges = raw_edges if isinstance(raw_edges, list) else []
    labels = {
        str(node["id"]): str(node.get("label", node["id"]))
        for node in nodes
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    labels.update(
        {
            person_id: str(metadata["label"])
            for person_id, metadata in authored_person_metadata.items()
            if isinstance(metadata.get("label"), str)
        }
    )
    raw_traces = document.get("traces")
    traces = raw_traces if isinstance(raw_traces, list) else []
    participants: dict[str, dict[str, object]] = {}
    decision_steps: list[dict[str, object]] = []
    influence_messages: dict[str, dict[str, object]] = {}
    influence_routes: set[tuple[str, str, str]] = set()
    for raw_trace in traces:
        if (
            not isinstance(raw_trace, dict)
            or raw_trace.get("participant_kind") != "person"
            or not isinstance(raw_trace.get("person"), str)
        ):
            continue
        person_id = str(raw_trace["person"])
        raw_observations = raw_trace.get("observations")
        observations = (
            raw_observations if isinstance(raw_observations, list) else []
        )
        observed_commitments: dict[str, str] = {}
        round_index: int | None = None
        projected_observations: list[dict[str, object]] = []
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            apparent_content = observation.get("apparent_content")
            if not isinstance(apparent_content, str):
                continue
            try:
                content = json.loads(apparent_content)
            except json.JSONDecodeError:
                continue
            if isinstance(content, dict) and content.get("document_kind") == (
                "decision_round_snapshot"
            ):
                candidate_round = content.get("round_index")
                if isinstance(candidate_round, int) and not isinstance(
                    candidate_round, bool
                ):
                    round_index = candidate_round
                    projected_observations.append(
                        {
                            "kind": "decision_round",
                            "round_index": candidate_round,
                            "collective_question": content.get(
                                "collective_question"
                            ),
                            "round_feedback": content.get("round_feedback"),
                        }
                    )
            elif isinstance(content, dict) and content.get("document_kind") == (
                "influence_message"
            ):
                delivery_id = content.get("delivery_id")
                source_ref = observation.get("apparent_source_ref")
                if isinstance(delivery_id, str) and isinstance(source_ref, str):
                    projected = {
                        "kind": "influence_message",
                        "delivery_id": delivery_id,
                        "topic": content.get("topic"),
                        "content": content.get("content"),
                        "apparent_source_ref": source_ref,
                    }
                    projected_observations.append(projected)
                    influence_messages.setdefault(delivery_id, projected)
                    influence_routes.add((source_ref, delivery_id, person_id))
            if (
                not isinstance(content, dict)
                or content.get("document_kind") != "meeting_snapshot"
                or not isinstance(content.get("commitments"), list)
            ):
                continue
            for raw_commitment in content["commitments"]:
                if (
                    isinstance(raw_commitment, dict)
                    and isinstance(raw_commitment.get("person_id"), str)
                    and isinstance(raw_commitment.get("commitment"), str)
                ):
                    observed_commitments[str(raw_commitment["person_id"])] = str(
                        raw_commitment["commitment"]
                    )
        for observed_person_id, observed_commitment in observed_commitments.items():
            observed_previous = participants.get(observed_person_id, {})
            participants[observed_person_id] = {
                "person_id": observed_person_id,
                "label": labels.get(
                    observed_person_id,
                    observed_person_id.replace("_", " ").title(),
                ),
                "position": authored_person_metadata.get(
                    observed_person_id, {}
                ).get("position"),
                "latest_orientation": observed_previous.get(
                    "latest_orientation"
                ),
                "latest_actions": observed_previous.get("latest_actions", []),
                "last_explicit_commitment": observed_commitment,
            }
        raw_actions = raw_trace.get("actions")
        actions = raw_actions if isinstance(raw_actions, list) else []
        projected_actions = [
            {
                "summary": action.get("public_summary"),
                "port": action.get("output_port_id"),
                "payload": action.get("payload"),
            }
            for action in actions
            if isinstance(action, dict)
        ]
        orientation = raw_trace.get("orientation")
        commitment: object = None
        for action in projected_actions:
            payload = action.get("payload")
            if (
                isinstance(payload, dict)
                and isinstance(
                    payload.get("commitment", payload.get("stance")),
                    str,
                )
            ):
                commitment = payload.get("commitment", payload.get("stance"))
        previous = participants.get(person_id, {})
        participants[person_id] = {
            "person_id": person_id,
            "label": labels.get(person_id, person_id.replace("_", " ").title()),
            "position": authored_person_metadata.get(person_id, {}).get(
                "position"
            ),
            "latest_orientation": (
                orientation
                if isinstance(orientation, str)
                else previous.get("latest_orientation")
            ),
            "latest_actions": (
                projected_actions
                if projected_actions
                else previous.get("latest_actions", [])
            ),
            "last_explicit_commitment": (
                commitment
                if commitment is not None
                else previous.get("last_explicit_commitment")
            ),
        }
        if projected_actions or isinstance(orientation, str):
            decision_steps.append(
                {
                    "activation": raw_trace.get("activation"),
                    "causal_time": raw_trace.get("causal_time"),
                    "logical_time": raw_trace.get("logical_time"),
                    "person_id": person_id,
                    "person_label": participants[person_id]["label"],
                    "orientation": orientation,
                    "actions": projected_actions,
                    "round_index": round_index,
                    "observations": projected_observations,
                    "model_call_count": raw_trace.get("model_call_count", 0),
                }
            )
    raw_outcome = document.get("outcome")
    outcome = deepcopy(raw_outcome) if isinstance(raw_outcome, dict) else {}
    completion = document.get("completion")
    if not isinstance(completion, dict):
        completion = {}
    headline = story.get("headline")
    summary = story.get("summary")
    projected_completion = deepcopy(completion)
    if (
        authoring.get("template_id") == "coordination_decision_v1"
        and (not isinstance(headline, str) or not isinstance(summary, str))
    ):
        final_status = outcome.get("final_status")
        if final_status == "deploy_on_time":
            headline = "The full proposal was approved"
            summary = (
                "All five participants supported the full proposal, and the final "
                "decision was recorded."
            )
            projected_completion["public_summary"] = (
                "The reviewed full proposal was accepted and recorded."
            )
        elif final_status == "scope_reduced":
            headline = "A narrower proposal was approved"
            summary = (
                "The participants approved a narrower proposal that satisfied the "
                "final decision gate."
            )
            projected_completion["public_summary"] = (
                "The reviewed narrower proposal was accepted and recorded."
            )
        elif final_status == "no_decision_by_horizon":
            headline = "The group did not reach a decision"
            summary = (
                "No proposal satisfied the final decision gate before the modeled "
                "deadline, so no collective decision was recorded."
            )
            projected_completion["public_summary"] = (
                "The decision deadline was recorded without an approved collective "
                "decision."
            )
    raw_events = document.get("events", [])
    narration = document.get("narration")
    narrated_moments = narration.get("moments") if isinstance(narration, dict) else None
    raw_moments = (
        narrated_moments
        if isinstance(narrated_moments, list)
        else document.get("moments", [])
    )
    if document.get("profile") in {"general_world_v1", "general_world_v2"} and isinstance(
        raw_moments, list
    ):
        general_simulation = document.get("general_simulation")
        transition_evidence = (
            general_simulation.get("transition_evidence")
            if isinstance(general_simulation, dict)
            else None
        )
        if isinstance(transition_evidence, list):
            raw_moments = _attach_transitions_to_causal_moments(
                raw_moments, transition_evidence
            )
            committed_moments = sum(
                isinstance(moment, dict)
                and isinstance(moment.get("resulting_revision"), int)
                and isinstance(moment.get("execution_parent"), str)
                and str(moment["execution_parent"]).removeprefix("revision:").isdigit()
                and int(cast(int, moment["resulting_revision"]))
                > int(str(moment["execution_parent"]).removeprefix("revision:"))
                for moment in raw_moments
            )
            outcome["terminal_summary"] = (
                f"The simulation completed {len(raw_moments)} scheduled moments. "
                f"{committed_moments} committed a validated transition; the retained final "
                f"world is revision {outcome.get('final_revision', 0)}."
            )
    rounds: dict[int, dict[str, object]] = {}
    for step in decision_steps:
        raw_round_index = step.get("round_index")
        if not isinstance(raw_round_index, int) or isinstance(raw_round_index, bool):
            continue
        round_index = raw_round_index
        round_item = rounds.setdefault(
            round_index,
            {"round_index": round_index, "decisions": [], "new_information": []},
        )
        cast(list[dict[str, object]], round_item["decisions"]).append(step)
        for observation in cast(list[dict[str, object]], step["observations"]):
            if observation.get("kind") == "influence_message":
                cast(list[dict[str, object]], round_item["new_information"]).append(
                    {**observation, "recipient_id": step["person_id"]}
                )
    if not rounds:
        outcome_rounds = outcome.get("round_history")
        if isinstance(outcome_rounds, list):
            for raw_round in outcome_rounds:
                if not isinstance(raw_round, dict):
                    continue
                round_index = raw_round.get("round")
                raw_stances = raw_round.get("stances")
                if (
                    not isinstance(round_index, int)
                    or isinstance(round_index, bool)
                    or not isinstance(raw_stances, dict)
                ):
                    continue
                decisions: list[dict[str, object]] = []
                for person_id, raw_stance in raw_stances.items():
                    if not isinstance(person_id, str) or not isinstance(raw_stance, dict):
                        continue
                    stance = raw_stance.get("decision", raw_stance.get("stance"))
                    payload = {
                        "stance": stance,
                        "reason": raw_stance.get("rationale", raw_stance.get("reason")),
                        "primary_risk": raw_stance.get("risk"),
                        "blocking_dependency": raw_stance.get("request"),
                    }
                    decisions.append(
                        {
                            "activation": None,
                            "causal_time": None,
                            "logical_time": None,
                            "person_id": person_id,
                            "person_label": labels.get(
                                person_id, person_id.replace("_", " ").title()
                            ),
                            "orientation": raw_stance.get("rationale"),
                            "actions": [
                                {
                                    "summary": raw_stance.get("rationale"),
                                    "port": None,
                                    "payload": payload,
                                }
                            ],
                            "round_index": round_index,
                            "observations": [],
                            "model_call_count": 1,
                        }
                    )
                if decisions:
                    rounds[round_index] = {
                        "round_index": round_index,
                        "decisions": decisions,
                        "new_information": [],
                    }

    network_nodes: list[dict[str, object]] = []
    network_edges: list[dict[str, object]] = []
    for source_ref in sorted({item[0] for item in influence_routes}):
        network_nodes.append(
            {
                "id": source_ref,
                "kind": "source",
                "label": labels.get(source_ref, source_ref.replace("_", " ").title()),
                "description": "Configured source of one or more delivered messages.",
            }
        )
    for delivery_id, message in sorted(influence_messages.items()):
        network_nodes.append(
            {
                "id": f"message_{delivery_id}",
                "kind": "information",
                "label": message.get("topic") or delivery_id.replace("_", " ").title(),
                "description": message.get("content") or "A delivered information item.",
            }
        )
    for person in participants.values():
        person_id = str(person["person_id"])
        network_nodes.append(
            {
                "id": person_id,
                "kind": "person",
                "label": person["label"],
                "description": person.get("position") or "A simulated decision participant.",
            }
        )
    if participants:
        network_nodes.append(
            {
                "id": "collective_decision",
                "kind": "mechanism",
                "label": "Collective decision gate",
                "description": "The authored rule evaluates the latest independent stances.",
            }
        )
    connected_source_messages: set[tuple[str, str]] = set()
    for source_ref, delivery_id, person_id in sorted(influence_routes):
        message_id = f"message_{delivery_id}"
        if (source_ref, message_id) not in connected_source_messages:
            edge_id = f"source_{source_ref}_{delivery_id}"
            network_edges.append(
                {
                    "id": edge_id,
                    "kind": "issued_information",
                    "source": source_ref,
                    "target": message_id,
                    "enabled": True,
                    "directed": True,
                    "description": "This source introduced the retained message.",
                    "routeIds": [edge_id],
                }
            )
            connected_source_messages.add((source_ref, message_id))
        delivery_edge_id = f"delivery_{delivery_id}_{person_id}"
        network_edges.append(
            {
                "id": delivery_edge_id,
                "kind": "delivered_to",
                "source": message_id,
                "target": person_id,
                "enabled": True,
                "directed": True,
                "description": "The retained route delivered this message to this person.",
                "routeIds": [delivery_edge_id],
            }
        )
    for person_id in sorted(participants):
        edge_id = f"decision_{person_id}"
        network_edges.append(
            {
                "id": edge_id,
                "kind": "contributed_to_decision",
                "source": person_id,
                "target": "collective_decision",
                "enabled": True,
                "directed": True,
                "description": "This person's latest stance enters the exact decision gate.",
                "routeIds": [edge_id],
            }
        )
    if document.get("profile") in {"general_world_v1", "general_world_v2"} and nodes:
        network_nodes, network_edges = _canonical_replay_network(nodes, edges)
    elif not influence_messages and nodes:
        network_nodes, network_edges = _canonical_replay_network(nodes, edges)
    ordered_rounds = [rounds[index] for index in sorted(rounds)]
    replay = _simulation_replay(
        title=authoring.get("title"),
        headline=headline,
        summary=summary,
        outcome=outcome,
        rounds=ordered_rounds,
        network_nodes=network_nodes,
        network_edges=network_edges,
        raw_moments=raw_moments,
        cognitive_traces=document.get("traces"),
        general_world=document.get("profile") in {"general_world_v1", "general_world_v2"},
        question_is_analyst_framing=(
            document.get("execution_contract") == "general_world_v2"
            and isinstance(authoring.get("question"), str)
            and bool(str(authoring["question"]).strip())
            and authoring.get("question") != authoring.get("description")
        ),
        node_overrides_by_revision=_general_world_node_overrides(
            document.get("general_simulation")
        ),
    )
    readout = coordination_measurement_readout(document).model_dump(mode="json")
    is_general_world = document.get("profile") in {"general_world_v1", "general_world_v2"}
    return {
        "run_id": document.get("run_id"),
        "created_at": document.get("created_at"),
        "status": document.get("status"),
        # A failed run already retains why it failed; without projecting it here
        # the reader sees an empty result with no explanation at all.
        "error": document.get("error"),
        "scenario": document.get("scenario"),
        "arm": document.get("arm"),
        "execution": document.get("execution"),
        "profile": document.get("profile"),
        "execution_contract": document.get("execution_contract"),
        "authoring": {
            "question": (
                None
                if document.get("execution_contract") == "general_world_v2"
                and authoring.get("question") == authoring.get("description")
                else authoring.get("question")
            ),
            "description": authoring.get("description"),
        },
        "title": authoring.get("title"),
        "description": authoring.get("description"),
        "template_id": authoring.get("template_id"),
        "headline": headline,
        "summary": summary,
        "outcome": outcome,
        "completion": projected_completion,
        "participant_model_calls": document.get(
            "agent_model_calls", document.get("model_calls", 0)
        ),
        "model": (
            cast(dict[str, object], document.get("llm_configuration", {})).get("model")
            if isinstance(document.get("llm_configuration"), dict)
            else None
        ),
        "execution_providers": document.get("execution_providers", []),
        "observed_cost": document.get("cost"),
        "cost_coverage": document.get("cost_coverage"),
        "causal_moments": (
            len(raw_moments)
            if is_general_world and isinstance(raw_moments, list)
            else None
        ),
        "narration_model_calls": document.get("narration_model_calls", 0),
        "participants": list(participants.values()),
        "decision_steps": decision_steps,
        "rounds": ordered_rounds,
        "influence_network": {"nodes": network_nodes, "edges": network_edges},
        "simulation_replay": replay,
        "coordination_measurement_readout": readout,
        "theory_analysis": document.get("theory_analysis"),
        "analysis_specs": document.get("analysis_specs", []),
        "analysis_results": analysis_results,
        "analysis_isolation_receipts": document.get(
            "analysis_isolation_receipts", []
        ),
        "evidence_bundle": (
            {
                "bundle_id": evidence_bundle.get("bundle_id"),
                "record_digest": evidence_bundle.get("record_digest"),
                "evidence_record_count": len(evidence_records),
            }
            if evidence_bundle
            else None
        ),
        "evidence_counts": {
            "events": len(raw_events)
            if isinstance(raw_events, list)
            else 0,
            "causal_moments": len(raw_moments)
            if isinstance(raw_moments, list)
            else 0,
            "decision_steps": len(decision_steps),
        },
    }


def _scenario_preview(
    scenario: str,
    arm_id: str,
    cognition_profile: str,
) -> dict[str, object]:
    """Project an initial scenario state without executing or retaining a run."""
    if scenario == "service_desk":
        arm = next(
            (item for item in service_desk_arm_configurations() if item.arm_id == arm_id),
            None,
        )
        if arm is None:
            raise ValueError("unknown Service Desk condition")
        if cognition_profile not in {"position_context", "procedural_control"}:
            raise ValueError("unknown Service Desk cognition profile")
        compiled_scenario = service_desk_fixture(
            arm,
            cognition_profile=cast(ServiceDeskCognitionProfile, cognition_profile),
        ).scenario
    elif scenario == "physical_access":
        physical_arm = next(
            (item for item in physical_access_arm_configurations() if item.arm_id == arm_id),
            None,
        )
        if physical_arm is None:
            raise ValueError("unknown Physical Access condition")
        compiled_scenario = physical_access_fixture(physical_arm).scenario
    elif scenario == "purchase_payment":
        purchase_arm = next(
            (item for item in purchase_payment_arm_configurations() if item.arm_id == arm_id),
            None,
        )
        if purchase_arm is None:
            raise ValueError("unknown Purchase to Payment condition")
        compiled_scenario = purchase_payment_fixture(purchase_arm).scenario
    elif scenario == "coordination_decision":
        compiled_scenario = _coordination_contract(arm_id).scenario
    elif scenario == "regional_outbreak":
        if arm_id not in {
            "baseline",
            "responsive_exercise_injects",
            "capacity_inject_replay_with_stabilization",
            "adaptive_cso_stabilization",
            "threshold_managed_evasion",
        }:
            raise ValueError("unknown Regional Outbreak condition")
        compiled_scenario = regional_outbreak_fixture(
            cast(OutbreakCondition, arm_id)
        ).scenario
    else:
        raise ValueError("unknown scenario")

    state = compiled_scenario.initial_state
    revision = str(state.revision)
    temporal_states = {revision: state}
    edges = analyst_edges(state)
    return {
        "status": "ready",
        "preview": True,
        "scenario": scenario,
        "profile": cognition_profile,
        "arm": arm_id,
        "initial_revision": state.revision,
        "world": analyst_world(temporal_states),
        "nodes": analyst_nodes(state),
        "snapshots": {revision: analyst_nodes(state)},
        "edges": edges,
        "graph_diagnostics": analyst_graph_diagnostics(
            state,
            compiled_scenario.analytical_boundaries,
        ),
        "boundaries": analyst_boundaries(
            compiled_scenario.analytical_boundaries,
            temporal_states,
            edges,
            [],
            events=(
                []
                if scenario in {"coordination_decision", "regional_outbreak"}
                else None
            ),
        ),
        "timeline": [],
        "trajectory": {"nodes": [], "edges": []},
    }


_INLINE_SCRIPT = re.compile(r"<script>(.*?)</script>", re.DOTALL)


def _inline_script_csp_hashes(index_html: Path) -> str:
    """CSP source expressions for the inline scripts the served page contains.

    The page carries one inline script, the redirect that makes the shared link
    work without its trailing slash. Under `script-src 'self'` the browser
    refuses to run it, which is how that fix silently did nothing the first time
    it was deployed. Allowing it by hash keeps the policy exact -- no
    'unsafe-inline' -- and deriving the hash from the file that is actually
    served means editing the script cannot leave the policy behind.

    Returns an empty string when the page has no inline script, so the policy is
    unchanged for surfaces that do not use one.
    """
    try:
        markup = index_html.read_text(encoding="utf-8")
    except OSError:
        return ""
    digests = [
        base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
        for body in _INLINE_SCRIPT.findall(markup)
    ]
    return "".join(f" 'sha256-{digest}'" for digest in digests)


def create_app(
    web_root: Path | None = None,
    run_root: Path | None = None,
    *,
    authoring_root: Path | None = None,
    authoring_call: StructuredCall | None = None,
    general_simulation_call: StructuredCall | None = None,
    measurement_call: MeasurementStructuredCall | None = None,
    allow_internal_scripted_coordination: bool = False,
    allow_inline_styles: bool = False,
) -> FastAPI:
    """Create the visibility-safe API without any legacy workbench."""
    app = FastAPI(title="Cybernetic Influence Simulator", version=__version__)
    root = web_root or Path(__file__).resolve().parents[2] / "web"
    inline_script_hashes = _inline_script_csp_hashes(root / "index.html")
    configured_run_root = os.getenv("CYBERNETIC_INFLUENCE_RUNS_DIR")
    runs = RunStore(
        run_root
        or (Path(configured_run_root) if configured_run_root else root.parent / "artifacts" / "runs")
    )
    runs.mark_incomplete_interrupted()
    drafts = AuthoringDraftStore(authoring_root or runs.root.parent / "authoring_drafts")
    experiments = ExperimentStore(runs.root.parent / "experiments")
    authoring = DraftAuthoringService(drafts, call=authoring_call)
    authoring_lock = Lock()
    authoring_job_lock = Lock()
    authoring_jobs: dict[str, dict[str, object]] = {}
    authoring_job_keys: dict[tuple[str, str], str] = {}
    live_lock = Lock()
    live_worker_context = local()
    authored_live_worker_context = local()
    resume_live_worker_context = local()
    pause_requests: dict[str, Event] = {}
    stop_requests: dict[str, Event] = {}
    pause_lock = Lock()
    progress_lock = Lock()
    composite_assay_lock = Lock()
    coordination_experiment_lock = Lock()

    def composite_assay_readout(assay_id: str) -> CompositeAssayResponse:
        """Project one retained five-row assay without rerunning its simulations."""

        if re.fullmatch(r"assay_[0-9a-f]{12}", assay_id) is None:
            raise HTTPException(status_code=422, detail="invalid composite assay ID")
        summaries, _ = runs.list_runs()
        matching: list[dict[str, object]] = []
        for item in summaries:
            item_metadata = item.get("composite_assay")
            if (
                isinstance(item_metadata, dict)
                and item_metadata.get("assay_id") == assay_id
            ):
                matching.append(item)
        if not matching:
            raise HTTPException(status_code=404, detail="composite assay not found")
        documents = [runs.get(cast(str, item["run_id"])) for item in matching]
        indexed_documents: list[tuple[int, dict[str, object]]] = []
        for document in documents:
            raw_metadata = document.get("composite_assay")
            if not isinstance(raw_metadata, dict):
                raise HTTPException(
                    status_code=409,
                    detail="retained composite assay metadata is malformed",
                )
            row_index = raw_metadata.get("row_index")
            if (
                not isinstance(row_index, int)
                or isinstance(row_index, bool)
                or row_index < 0
            ):
                raise HTTPException(
                    status_code=409,
                    detail="retained composite assay row order is malformed",
                )
            indexed_documents.append((row_index, document))
        indexed_documents.sort(key=lambda item: item[0])
        if [item[0] for item in indexed_documents] != list(range(5)):
            raise HTTPException(
                status_code=409,
                detail="retained composite assay row order is incomplete",
            )
        documents = [item[1] for item in indexed_documents]
        metadata = cast(dict[str, object], documents[0]["composite_assay"])
        expected_count = metadata.get("row_count")
        if expected_count != 5 or len(documents) != expected_count:
            raise HTTPException(
                status_code=409,
                detail="retained composite assay is incomplete",
            )
        rows: list[CompositeAssayRowResponse] = []
        for document in documents:
            row_metadata = document.get("composite_assay")
            readout = document.get("composite_control_readout")
            evidence = document.get("composite_assay_evidence")
            configuration_diff = document.get("configuration_diff")
            if not all(
                isinstance(value, dict)
                for value in (row_metadata, readout, evidence, configuration_diff)
            ):
                raise HTTPException(
                    status_code=409,
                    detail="retained composite assay evidence is malformed",
                )
            if cast(dict[str, object], row_metadata).get("assay_id") != assay_id:
                raise HTTPException(
                    status_code=409,
                    detail="retained composite assay identity is inconsistent",
                )
            rows.append(
                CompositeAssayRowResponse.model_validate(
                    {
                        "run_id": document["run_id"],
                        "created_at": document["created_at"],
                        "status": document["status"],
                        "row_id": document["arm"],
                        "readout": readout,
                        "boundary_activity": cast(dict[str, object], evidence)[
                            "boundary_activity"
                        ],
                        "configuration_diff": configuration_diff,
                    }
                )
            )
        return CompositeAssayResponse(assay_id=assay_id, rows=rows)

    def coordination_experiment_readout(
        experiment_id: str,
    ) -> CoordinationExperimentReadoutV1:
        """Revalidate one retained eight-run experiment without rerunning it."""

        if re.fullmatch(r"coordexp_[0-9a-f]{12}", experiment_id) is None:
            raise HTTPException(
                status_code=422,
                detail="invalid coordination experiment ID",
            )
        summaries, _ = runs.list_runs()
        matching = [
            item
            for item in summaries
            if isinstance((metadata := item.get("coordination_experiment")), dict)
            and metadata.get("experiment_id") == experiment_id
        ]
        if not matching:
            raise HTTPException(
                status_code=404,
                detail="coordination experiment not found",
            )
        documents = [runs.get(cast(str, item["run_id"])) for item in matching]
        indexed: dict[tuple[str, int], dict[str, object]] = {}
        for document in documents:
            metadata = document.get("coordination_experiment")
            if not isinstance(metadata, dict):
                raise HTTPException(
                    status_code=409,
                    detail="retained coordination experiment metadata is malformed",
                )
            condition = metadata.get("condition")
            replicate = metadata.get("replicate")
            slot = (condition, replicate)
            if (
                condition not in EXPERIMENT_CONDITIONS
                or isinstance(replicate, bool)
                or not isinstance(replicate, int)
                or replicate < 1
                or replicate > EXPERIMENT_REPLICATES
                or metadata.get("row_count") != EXPERIMENT_RUN_COUNT
                or metadata.get("provider_calls") != 0
                or metadata.get("experiment_id") != experiment_id
                or slot in indexed
            ):
                raise HTTPException(
                    status_code=409,
                    detail="retained coordination experiment matrix is malformed",
                )
            indexed[cast(tuple[str, int], slot)] = document
        expected_slots = [
            (condition, replicate)
            for condition in EXPERIMENT_CONDITIONS
            for replicate in range(1, EXPERIMENT_REPLICATES + 1)
        ]
        if set(indexed) != set(expected_slots):
            raise HTTPException(
                status_code=409,
                detail="retained coordination experiment is incomplete",
            )

        validated: list[CoordinationExperimentReadoutV1] = []
        for slot in expected_slots:
            document = indexed[slot]
            try:
                readout = CoordinationExperimentReadoutV1.model_validate(
                    document["coordination_experiment_readout"]
                )
                own_row = document["coordination_experiment_run_readout"]
                expected_row = next(
                    item
                    for item in readout.runs
                    if (item.condition, item.replicate) == slot
                )
                if (
                    own_row != expected_row.model_dump(mode="json")
                    or document.get("run_id") != expected_row.run_id
                    or readout.experiment_id != experiment_id
                ):
                    raise ValueError("retained row does not match the experiment readout")
            except (KeyError, StopIteration, TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=409,
                    detail="retained coordination experiment evidence is malformed",
                ) from error
            validated.append(readout)
        reference = validated[0].model_dump(mode="json")
        if any(item.model_dump(mode="json") != reference for item in validated[1:]):
            raise HTTPException(
                status_code=409,
                detail="retained coordination experiment readouts disagree",
            )
        return validated[0]

    def retain_progress(
        run_id: str,
        update: RuntimeProgressUpdate,
        checkpoint: ActiveRuntimeCheckpoint,
        *,
        initial_state: CausalState | None = None,
        analytical_boundaries: Sequence[AnalyticalBoundary] = (),
    ) -> None:
        """Append one analyst-safe live update before future runtime work.

        The callback runs on the simulation worker.  It deliberately fails
        loud if the authoritative run document cannot retain the update.
        """
        with progress_lock:
            document = runs.get(run_id)
            existing = document.get("live_progress", [])
            if not isinstance(existing, list):
                raise RuntimeError("retained live progress is malformed")
            sequence = len(existing) + 1
            record = {
                "sequence": sequence,
                "observed_at": now_iso(),
                **update.model_dump(mode="json"),
                "projection": analyst_progress_projection(
                    checkpoint,
                    update,
                    initial_state=initial_state,
                    analytical_boundaries=analytical_boundaries,
                ),
            }
            lifecycle = document.get("status")
            document.update(_checkpoint_progress_projection(checkpoint))
            document["continuation"] = _checkpoint_continuation(
                checkpoint,
                lifecycle=(
                    "paused"
                    if lifecycle == "pause_requested"
                    else "running"
                ),
            )
            document["live_progress"] = [*existing, record]
            document["progress_sequence"] = sequence
            runs.save(document)

    def retain_progress_history(
        document: dict[str, object], run_id: str
    ) -> dict[str, object]:
        """Carry public live progress into the final retained analyst record."""
        with progress_lock:
            prior = runs.get(run_id)
            progress = prior.get("live_progress", [])
            if not isinstance(progress, list):
                raise RuntimeError("retained live progress is malformed")
            copied = dict(document)
            copied["live_progress"] = progress
            copied["progress_sequence"] = len(progress)
            return copied

    def retained_live_configuration(
        document: dict[str, object],
        *,
        description: str,
    ) -> EffectiveRunLlmConfiguration:
        """Revalidate the exact retained route before spending on a later phase."""
        if os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        try:
            retained = EffectiveRunLlmConfiguration.model_validate(
                document["llm_configuration"]
            )
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=422,
                detail=f"{description} has invalid LLM configuration",
            ) from error
        if retained.llm_client_revision != llm_client_revision():
            raise HTTPException(
                status_code=409,
                detail=f"{description} requires its original shared-client revision",
            )
        try:
            current = resolve_live_configuration(
                RunLlmOptions(
                    model=retained.model,
                    agent_reasoning_effort=retained.agent_reasoning_effort,
                    max_total_cost=retained.max_total_cost,
                )
            )
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail=f"{description} route is not currently certified",
            ) from error
        if (
            current.model != retained.model
            or current.agent_reasoning_effort != retained.agent_reasoning_effort
            or current.narrator_reasoning_effort
            != retained.narrator_reasoning_effort
        ):
            raise HTTPException(
                status_code=409,
                detail=f"{description} requires its original model policy",
            )
        return retained

    def retain_live_coordination_measurement(
        document: dict[str, object],
        result: ActiveRuntimeResult,
        effective_llm: EffectiveRunLlmConfiguration,
    ) -> dict[str, object]:
        """Retain one post-run analysis without changing simulation validity."""

        stored = runs.save(
            {**document, "coordination_measurement_status": "running"}
        )
        trace_id = f"{result.run_id}/measurement/v1"
        try:
            measurement = analyze_coordination_run(
                result,
                expected_scenario_fingerprint=result.scenario_fingerprint,
                model=effective_llm.model,
                reasoning_effort=effective_llm.agent_reasoning_effort,
                trace_id=trace_id,
                max_budget=CODER_MAX_BUDGET,
                structured_call=measurement_call,
            )
            measured = retain_coordination_measurement(runs, measurement)
            observed = measurement.coder_call.observed_cost
            known_cost = float(cast(float, measured.get("cost", 0.0)))
            return runs.save(
                {
                    **measured,
                    "coordination_measurement_status": "completed",
                    "measurement_model_calls": 1,
                    "model_calls": int(cast(int, measured.get("model_calls", 0)))
                    + 1,
                    "cost": known_cost + (observed or 0.0),
                    "cost_fully_observable": bool(
                        measured.get("cost_fully_observable", True)
                        and observed is not None
                        and measurement.coder_call.cost_covers_all_attempts
                    ),
                }
            )
        except Exception as error:
            # Analysis is downstream of the completed world run. A failed or
            # invalid coding must remain visible without rewriting its outcome.
            return runs.save(
                {
                    **stored,
                    "coordination_measurement_status": "invalid",
                    # A failed shared-client boundary may have reached the
                    # provider before raising without returning priced call
                    # metadata. Never present the prior run cost as complete.
                    "cost_fully_observable": False,
                    "coordination_measurement_failure": {
                        "status": "invalid",
                        "error_type": type(error).__name__,
                        "trace_id": trace_id,
                        "model": effective_llm.model,
                        "reasoning_effort": effective_llm.agent_reasoning_effort,
                        "max_budget": CODER_MAX_BUDGET,
                    },
                }
            )

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        style_policy = (
            "style-src 'self' 'unsafe-inline'; "
            if allow_inline_styles
            else "style-src 'self'; "
        )
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; script-src 'self'{inline_script_hashes}; " + style_policy +
            "connect-src 'self'; img-src 'self' data:; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if request.url.path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/api/config")
    def config() -> dict[str, object]:
        live_options = live_options_contract()
        coordination_live_models = coordination_live_model_ids()
        live_defaults = cast(dict[str, object], live_options["defaults"])
        authoring_models = list(AUTHORING_MODEL_OPTIONS)
        if os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1":
            certified_model_ids = set(authoring_model_ids())
            authoring_models = [
                item
                for item in authoring_models
                if item["model"] in certified_model_ids
            ]
        authoring_available_model_ids = {
            item["model"] for item in authoring_models
        }
        authoring_default = (
            AUTHORING_MODEL
            if AUTHORING_MODEL in authoring_available_model_ids
            else (authoring_models[0]["model"] if authoring_models else None)
        )
        structured_authoring_contract = authoring_contract()
        structured_authoring_contract["model_options"] = deepcopy(
            authoring_models
        )
        return {
            "version": __version__,
            "build_commit": os.getenv("CYBERNETIC_INFLUENCE_BUILD_COMMIT", "development"),
            "scenario": "service_desk",
            "scenarios": {
                "service_desk": {
                    "label": "Service desk",
                    **_scenario_explanation("service_desk"),
                    "run_control_options": service_desk_run_control_options().model_dump(mode="json"),
                    "profiles": ["position_context", "procedural_control"],
                    "arms": [
                        {
                            "id": arm.arm_id,
                            "label": arm.arm_id.replace("_", " "),
                            "description": {
                                "baseline": "Normal conditions: the direct customer-report route is available.",
                                "no_direct_path": "The direct customer-report route is absent; people must find another grounded route.",
                                "speed_priority": "The direct route is available, while the supervisor also perceives pressure to close quickly.",
                            }[arm.arm_id],
                        }
                        for arm in service_desk_arm_configurations()
                    ],
                },
                "physical_access": {
                    "label": "Physical access",
                    **_scenario_explanation("physical_access"),
                    "profiles": ["position_context"],
                    "arms": [
                        {
                            "id": arm.arm_id,
                            "label": arm.arm_id.replace("_", " "),
                            "description": {
                                "authorized_access": "The credential is recognized, policy authorizes entry, and the door latch can operate.",
                                "authorization_absent": "The credential is recognized, but the stored policy does not authorize entry.",
                                "latch_jammed": "The credential and policy pass, but the physical latch cannot release.",
                            }[arm.arm_id],
                        }
                        for arm in physical_access_arm_configurations()
                    ],
                },
                "purchase_payment": {
                    "label": "Purchase to payment",
                    **_scenario_explanation("purchase_payment"),
                    "profiles": ["position_context"],
                    "model": "openrouter/openai/gpt-5.6-terra",
                    "reasoning_effort": "medium",
                    "maximum_live_calls": 8,
                    "maximum_live_cost": 0.38,
                    "arms": [
                        {
                            "id": arm.arm_id,
                            "label": arm.arm_id.replace("_", " "),
                            "description": {
                                "settled": (
                                    "The human approval and exact internal "
                                    "control pass; the coarse processor settles."
                                ),
                                "approval_denied": (
                                    "The amount exceeds the copied approval "
                                    "limit; no processor instruction is emitted."
                                ),
                                "processor_declined": (
                                    "Internal approval passes, but the coarse "
                                    "external processor returns declined."
                                ),
                            }[arm.arm_id],
                        }
                        for arm in purchase_payment_arm_configurations()
                    ],
                },
                "coordination_decision": {
                    "label": "Coordination decision",
                    **_scenario_explanation("coordination_decision"),
                    "profiles": ["position_context"],
                    "execution_modes": ["live"],
                    "scripted_execution": "internal_verification_only",
                    "supports_live": bool(coordination_live_models),
                    "live_model_ids": coordination_live_models,
                    "run_control_options": (
                        stabilization_coordination_fixture()
                        .run_control_options.model_dump(mode="json")
                    ),
                    "arms": [
                        {
                            "id": "baseline",
                            "label": "Baseline",
                            "description": (
                                "The team reviews the proposal using only the concerns "
                                "already available at the start."
                            ),
                        },
                        {
                            "id": "heterogeneous_pressure",
                            "label": "Heterogeneous pressure",
                            "description": (
                                "New technical, government-oversight, and local safety "
                                "concerns arrive, but the team has no reliable way to resolve them."
                            ),
                        },
                        {
                            "id": "stabilization",
                            "label": "Stabilization",
                            "description": (
                                "The same new concerns arrive, and the team can request "
                                "independent checks and track which issues remain unresolved."
                            ),
                        },
                        {
                            "id": "fixed_heterogeneous_pressure",
                            "label": "Experiment · fixed pressure",
                            "description": (
                                "Live participants receive the retained scheduled pressure "
                                "messages; the sources do not read meeting feedback."
                            ),
                        },
                        {
                            "id": "adaptive_heterogeneous_pressure",
                            "label": "Experiment · adaptive pressure",
                            "description": (
                                "Live participants face sources whose second retained message "
                                "changes after observing public meeting feedback."
                            ),
                        },
                        {
                            "id": "adaptive_pressure_with_stabilization",
                            "label": "Experiment · adaptive pressure + validation",
                            "description": (
                                "The adaptive sources remain active while an authoritative "
                                "validation record can answer verification requests."
                            ),
                        },
                    ],
                },
                "regional_outbreak": {
                    "label": "Cross-Border Early Warning Compact",
                    **_scenario_explanation("regional_outbreak"),
                    "profiles": ["position_context"],
                    "execution_modes": ["live"],
                    "supports_live": bool(coordination_live_models),
                    "live_model_ids": coordination_live_models,
                    "maximum_live_calls": (
                        len(OUTBREAK_AGENT_IDS) * OUTBREAK_MAX_ROUNDS
                        + len(OUTBREAK_SOURCE_IDS) * (OUTBREAK_MAX_ROUNDS - 1)
                        + len(OUTBREAK_CSO_IDS)
                    ),
                    "editable_configuration": default_outbreak_configuration().model_dump(
                        mode="json"
                    ),
                    "arms": [
                        {
                            "id": "baseline",
                            "label": "Baseline",
                            "description": (
                                "Twenty-six autonomous coalition roles receive only the common "
                                "results of each prior decision round."
                            ),
                        },
                        {
                            "id": "responsive_exercise_injects",
                            "label": "Autonomous source pressure",
                            "description": (
                                "Four bounded source agents observe the completed public round, "
                                "then a complete external-signal bundle enters before the next round."
                            ),
                        },
                        {
                            "id": "capacity_inject_replay_with_stabilization",
                            "label": "Autonomous source pressure + verified compact package",
                            "description": (
                                "The four source agents remain active, then a verified technical, "
                                "legal, capacity, and legitimacy package enters the round-two bundle."
                            ),
                        },
                        {
                            "id": "adaptive_cso_stabilization",
                            "label": "Autonomous source pressure + adaptive CSO cell",
                            "description": (
                                "After round two, a monitor detects directional changes, a "
                                "diagnostician identifies the coordination mechanism, and a "
                                "planner selects one authorized intervention before the coalition "
                                "decides independently again."
                            ),
                        },
                        {
                            "id": "threshold_managed_evasion",
                            "label": "Threshold-managed pressure + the same detection cell",
                            "description": (
                                "The same four sources apply the same directional pressure, but "
                                "each signal stays inside the range a reader would treat as "
                                "ordinary. The detection cell, its thresholds and its trigger are "
                                "unchanged. Whether it still fires is the result."
                            ),
                        },
                    ],
                },
            },
            "profiles": ["position_context", "procedural_control"],
            "arms": [arm.arm_id for arm in service_desk_arm_configurations()],
            "model": live_defaults["model"],
            "reasoning_effort": live_defaults["agent_reasoning_effort"],
            "live_authorized": os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1",
            "access_restricted": bool(_allowed_tailscale_users()),
            "scripted_cost": 0.0,
            "maximum_live_calls": MAXIMUM_PARTICIPANT_CALLS,
            "maximum_live_cost": 0.74,
            "coordination_measurement": {
                "maximum_coder_calls": 1,
                "coder_per_call_ceiling": CODER_MAX_BUDGET,
                "applies_to": "completed live coordination runs",
            },
            "live_options": live_options,
            "authoring": {
                "model": authoring_default,
                "reasoning_effort": AUTHORING_REASONING_EFFORT,
                "models": authoring_models,
                "reasoning_efforts": list(AUTHORING_REASONING_EFFORTS),
                "maximum_attempts_per_message": AUTHORING_MAX_ATTEMPTS,
                "maximum_cost_per_attempt": AUTHORING_MAX_BUDGET,
                "templates": [
                    "resource_request_v1",
                    "information_campaign_v1",
                    "coordination_decision_v1",
                    "influence_network_v1",
                ],
                "reviewed_coordination_example": True,
                "structured_contract": structured_authoring_contract,
            },
            "theory_analysis": theory_analysis_contract(),
            "cost_baselines": runs.cost_baselines(),
        }

    @app.get("/api/runs")
    def history(request: Request) -> dict[str, object]:
        _require_access(request)
        retained, corrupt = runs.list_runs()
        for summary in retained:
            run_id = summary.get("run_id")
            if (
                isinstance(run_id, str)
                and summary.get("coordination_measurement_status")
                == "needs_validation"
            ):
                summary["coordination_measurement_status"] = (
                    coordination_measurement_readout(runs.get(run_id)).status
                )
        return {"runs": retained, "corrupt_files": corrupt}

    @app.get("/api/regional-outbreak-comparison")
    def regional_outbreak_comparison(request: Request) -> dict[str, object]:
        """Project compact outcome evidence from completed authentic outbreak runs."""

        _require_access(request)
        retained, _ = runs.list_runs()
        rows: list[dict[str, object]] = []
        for summary in retained:
            if (
                summary.get("scenario") != "regional_outbreak"
                or summary.get("status") != "completed"
            ):
                continue
            run_id = summary.get("run_id")
            if not isinstance(run_id, str):
                continue
            document = runs.get(run_id)
            outcome = document.get("outcome")
            configuration = document.get("llm_configuration")
            rows.append(
                {
                    **summary,
                    "outcome": dict(outcome) if isinstance(outcome, dict) else None,
                    "llm_configuration": (
                        dict(configuration)
                        if isinstance(configuration, dict)
                        else None
                    ),
                }
            )
        return {"rows": rows}

    @app.post("/api/composite-assays")
    def create_composite_assay(request: Request) -> CompositeAssayResponse:
        """Run the reviewed five-row scripted assay without a provider call."""

        _require_access(request)
        if not composite_assay_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409,
                detail="a composite assay is already running",
            )
        try:
            execution = run_scripted_composite_assay(runs.root)
            return composite_assay_readout(execution.assay_id)
        finally:
            composite_assay_lock.release()

    @app.get("/api/composite-assays/{assay_id}")
    def retained_composite_assay(
        assay_id: str,
        request: Request,
    ) -> CompositeAssayResponse:
        """Reopen one retained assay without executing or calling a provider."""

        _require_access(request)
        return composite_assay_readout(assay_id)

    @app.delete("/api/composite-assays/{assay_id}")
    def trash_composite_assay(
        assay_id: str,
        request: Request,
    ) -> CompositeAssayTrashResponse:
        """Move all five retained rows to recoverable server trash."""

        _require_access(request)
        assay = composite_assay_readout(assay_id)
        runs.trash_many([row.run_id for row in assay.rows])
        return CompositeAssayTrashResponse(
            assay_id=assay_id,
            trashed_run_count=5,
        )

    @app.post("/api/coordination-experiments")
    def create_coordination_experiment(
        request: Request,
    ) -> CoordinationExperimentReadoutV1:
        """Run the frozen four-condition, eight-run provider-free experiment."""

        _require_access(request)
        if not coordination_experiment_lock.acquire(blocking=False):
            raise HTTPException(
                status_code=409,
                detail="a coordination experiment is already running",
            )
        try:
            execution = run_scripted_coordination_experiment(runs.root)
            return coordination_experiment_readout(execution.experiment_id)
        finally:
            coordination_experiment_lock.release()

    @app.get("/api/coordination-experiments/{experiment_id}")
    def retained_coordination_experiment(
        experiment_id: str,
        request: Request,
    ) -> CoordinationExperimentReadoutV1:
        """Reopen one complete experiment without executing any simulation."""

        _require_access(request)
        return coordination_experiment_readout(experiment_id)

    @app.delete("/api/coordination-experiments/{experiment_id}")
    def trash_coordination_experiment(
        experiment_id: str,
        request: Request,
    ) -> CoordinationExperimentTrashResponse:
        """Move all eight retained runs to recoverable server trash."""

        _require_access(request)
        experiment = coordination_experiment_readout(experiment_id)
        runs.trash_many([item.run_id for item in experiment.runs])
        return CoordinationExperimentTrashResponse(
            experiment_id=experiment_id,
            trashed_run_count=8,
        )

    @app.post("/api/authoring/drafts")
    def create_draft(request: Request) -> dict[str, object]:
        _require_access(request)
        return drafts.create(now=now_iso(), target_kind="general_world_v2")

    @app.post("/api/authoring/legacy-drafts")
    def create_legacy_draft(request: Request) -> dict[str, object]:
        """Create a backward-compatible closed-template draft."""

        _require_access(request)
        return drafts.create(now=now_iso(), target_kind="legacy_templates_v1")

    @app.post("/api/authoring/reviewed-coordination-drafts")
    def create_reviewed_coordination_draft(
        request: Request,
    ) -> dict[str, object]:
        """Create the canonical typed example without a provider call."""

        _require_access(request)
        with authoring_lock:
            return authoring.create_reviewed_coordination_draft()

    @app.post("/api/authoring/reviewed-component-composition-drafts")
    def create_reviewed_component_composition_draft(
        request: Request,
    ) -> dict[str, object]:
        """Create the first mixed reviewed-component example without a model call."""

        _require_access(request)
        with authoring_lock:
            return authoring.create_reviewed_component_composition_draft()

    @app.get("/api/authoring/drafts/{draft_id}")
    def get_draft(draft_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            document = drafts.get(draft_id)
            if (
                document.get("target_kind") in {"general_world_v1", "general_world_v2"}
                and isinstance(document.get("proposal"), dict)
            ):
                compiled = authoring.compile_general(document)
                document = deepcopy(document)
                document["coverage"] = compiled.coverage.model_dump(mode="json")
                document["configuration_graph"] = compiled.configuration_graph
            return document
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except DraftNotFoundError as error:
            raise HTTPException(status_code=404, detail="authoring draft not found") from error

    @app.post("/api/authoring/drafts/{draft_id}/messages", response_model=None)
    def add_draft_message(
        draft_id: str, body: DraftMessageRequest, request: Request
    ) -> dict[str, object] | Response:
        _require_access(request)
        if (
            os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1"
            and body.model not in set(authoring_model_ids())
        ):
            raise HTTPException(
                status_code=422,
                detail="authoring model route is not currently certified",
            )
        if os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1":
            try:
                current = drafts.get(draft_id)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            if current["revision"] != body.expected_revision:
                raise HTTPException(
                    status_code=409,
                    detail="draft revision has changed; reload before editing",
                )
            key = (draft_id, body.message_id)
            with authoring_job_lock:
                existing_job_id = authoring_job_keys.get(key)
                if existing_job_id is not None:
                    return JSONResponse(
                        status_code=202,
                        content=deepcopy(authoring_jobs[existing_job_id]),
                    )
                job_id = f"authoring_job_{uuid4().hex[:12]}"
                queued_detail = (
                    "Preparing the retained conversation for clarification."
                    if body.mode == "discuss"
                    else "Preparing the retained conversation for typed configuration."
                )
                queued_at = now_iso()
                queued_progress: dict[str, object] = {
                    "sequence": 1,
                    "phase": "queued",
                    "phase_label": AUTHORING_PHASE_LABELS["queued"],
                    "detail": queued_detail,
                    "attempt": None,
                    "recorded_at": queued_at,
                }
                job: dict[str, object] = {
                    "job_id": job_id,
                    "draft_id": draft_id,
                    "message_id": body.message_id,
                    "status": "generating",
                    "expected_revision": body.expected_revision,
                    "mode": body.mode,
                    "phase": "queued",
                    "phase_label": AUTHORING_PHASE_LABELS["queued"],
                    "detail": queued_detail,
                    "attempt": None,
                    "progress_sequence": 1,
                    "progress": [queued_progress],
                    "updated_at": queued_at,
                }
                authoring_jobs[job_id] = job
                authoring_job_keys[key] = job_id

            def execute_authoring_job() -> None:
                def report_progress(
                    phase: str, detail: str, attempt: int | None
                ) -> None:
                    recorded_at = now_iso()
                    with authoring_job_lock:
                        current_job = authoring_jobs[job_id]
                        prior_sequence = current_job.get("progress_sequence")
                        sequence = (
                            prior_sequence + 1
                            if isinstance(prior_sequence, int)
                            else 1
                        )
                        history = deepcopy(
                            cast(list[dict[str, object]], current_job.get("progress", []))
                        )
                        history.append(
                            {
                                "sequence": sequence,
                                "phase": phase,
                                "phase_label": AUTHORING_PHASE_LABELS[phase],
                                "detail": detail,
                                "attempt": attempt,
                                "recorded_at": recorded_at,
                            }
                        )
                        authoring_jobs[job_id] = {
                            **current_job,
                            "phase": phase,
                            "phase_label": AUTHORING_PHASE_LABELS[phase],
                            "detail": detail,
                            "attempt": attempt,
                            "progress_sequence": sequence,
                            "progress": history,
                            "updated_at": recorded_at,
                        }

                try:
                    authoring_method = authoring.discuss if body.mode == "discuss" else authoring.advance
                    document = authoring_method(
                        draft_id,
                        expected_revision=body.expected_revision,
                        message_id=body.message_id,
                        message=body.message,
                        model=body.model,
                        reasoning_effort=body.reasoning_effort,
                        progress=report_progress,
                    )
                except (DraftConflictError, DraftNotFoundError, ValueError) as error:
                    result_fields: dict[str, object] = {
                        "status": "failed",
                        "error": str(error),
                    }
                except Exception:
                    # The reader gets a stable sentence; the operator needs the
                    # real one. Without this line the 2026-08-19 JSON-truncation
                    # failure was only diagnosable from llm_client traces,
                    # because every provider fault reached the log as the same
                    # nine words.
                    logger.exception(
                        "authoring %s failed for draft %s (job %s)",
                        body.mode,
                        draft_id,
                        job_id,
                    )
                    result_fields = {
                        "status": "failed",
                        "error": (
                            "scenario drafting provider failed; the prior draft was preserved"
                        ),
                    }
                else:
                    result_fields = {"status": "completed", "draft": document}
                with authoring_job_lock:
                    current_job = authoring_jobs[job_id]
                    terminal_phase = (
                        "complete"
                        if result_fields["status"] == "completed"
                        else "failed"
                    )
                    terminal_detail = (
                        (
                            "The discussion and material questions are retained."
                            if body.mode == "discuss"
                            else (
                                "The editable retained simulation is ready for review."
                                if cast(dict[str, object], result_fields["draft"])[
                                    "status"
                                ]
                                == "ready_for_review"
                                else "The retained result is ready to inspect."
                            )
                        )
                        if terminal_phase == "complete"
                        else str(result_fields["error"])
                    )
                    prior_sequence = current_job.get("progress_sequence")
                    sequence = (
                        prior_sequence + 1
                        if isinstance(prior_sequence, int)
                        else 1
                    )
                    recorded_at = now_iso()
                    history = deepcopy(
                        cast(list[dict[str, object]], current_job.get("progress", []))
                    )
                    history.append(
                        {
                            "sequence": sequence,
                            "phase": terminal_phase,
                            "phase_label": AUTHORING_PHASE_LABELS[terminal_phase],
                            "detail": terminal_detail,
                            "attempt": None,
                            "recorded_at": recorded_at,
                        }
                    )
                    authoring_jobs[job_id] = {
                        **current_job,
                        **result_fields,
                        "phase": terminal_phase,
                        "phase_label": AUTHORING_PHASE_LABELS[terminal_phase],
                        "detail": terminal_detail,
                        "attempt": None,
                        "progress_sequence": sequence,
                        "progress": history,
                        "updated_at": recorded_at,
                    }

            Thread(target=execute_authoring_job, daemon=True).start()
            return JSONResponse(status_code=202, content=job)
        with authoring_lock:
            try:
                authoring_method = authoring.discuss if body.mode == "discuss" else authoring.advance
                return authoring_method(
                    draft_id,
                    expected_revision=body.expected_revision,
                    message_id=body.message_id,
                    message=body.message,
                    model=body.model,
                    reasoning_effort=body.reasoning_effort,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(status_code=404, detail="authoring draft not found") from error
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            except Exception as error:
                raise HTTPException(
                    status_code=502,
                    detail="scenario drafting provider failed; the prior draft was preserved",
                ) from error

    @app.get("/api/authoring/jobs/{job_id}")
    def get_authoring_job(job_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        if re.fullmatch(r"authoring_job_[0-9a-f]{12}", job_id) is None:
            raise HTTPException(status_code=422, detail="invalid authoring job ID")
        with authoring_job_lock:
            job = authoring_jobs.get(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="authoring job not found")
            return deepcopy(job)

    @app.get("/api/authoring/drafts/{draft_id}/preview")
    def preview_draft(draft_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            document = drafts.get(draft_id)
            if document.get("target_kind") in {"general_world_v1", "general_world_v2"}:
                compiled_general = authoring.compile_general(document)
                return {
                    "status": "ready",
                    "preview": True,
                    **compiled_general.preview(),
                    "draft_id": draft_id,
                    "draft_revision": document["revision"],
                }
            compiled = authoring.compile(document)
        except DraftNotFoundError as error:
            raise HTTPException(status_code=404, detail="authoring draft not found") from error
        except (ValueError, AuthoringCompilationError, GeneralCompilationError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        state = compiled.scenario.initial_state
        revision = str(state.revision)
        temporal_states = {revision: state}
        edges = analyst_edges(state)
        return {
            "status": "ready", "preview": True, "scenario": compiled.scenario.scenario_id,
            "profile": "authored_typed_scenario", "arm": "approved_draft",
            "initial_revision": state.revision, "world": analyst_world(temporal_states),
            "nodes": analyst_nodes(state), "snapshots": {revision: analyst_nodes(state)},
            "edges": edges,
            "graph_diagnostics": analyst_graph_diagnostics(
                state,
                compiled.scenario.analytical_boundaries,
            ),
            "timeline": [], "trajectory": {"nodes": [], "edges": []},
            "boundaries": analyst_boundaries(compiled.scenario.analytical_boundaries, temporal_states, edges, []),
            "composition_receipt": compiled.composition_receipt.model_dump(mode="json"),
            "composition_receipt_digest": compiled.composition_receipt.digest,
            "draft_id": draft_id, "draft_revision": document["revision"],
        }

    @app.put("/api/authoring/drafts/{draft_id}/people/{person_id}")
    def edit_draft_person(
        draft_id: str,
        person_id: str,
        body: DraftPersonEditRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_access(request)
        with authoring_lock:
            try:
                return authoring.edit_person(
                    draft_id,
                    expected_revision=body.expected_revision,
                    edit_id=body.edit_id,
                    person_id=person_id,
                    person=body.person,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            except (ValueError, AuthoringCompilationError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error

    @app.put("/api/authoring/drafts/{draft_id}/proposal")
    def edit_draft_proposal(
        draft_id: str,
        body: DraftProposalEditRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_access(request)
        with authoring_lock:
            try:
                return authoring.edit_proposal(
                    draft_id,
                    expected_revision=body.expected_revision,
                    edit_id=body.edit_id,
                    proposal=body.proposal,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            except (ValueError, AuthoringCompilationError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error

    @app.put("/api/authoring/drafts/{draft_id}/general-proposal")
    def edit_draft_general_proposal(
        draft_id: str,
        body: DraftGeneralProposalEditRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_access(request)
        with authoring_lock:
            try:
                return authoring.edit_general_proposal(
                    draft_id,
                    expected_revision=body.expected_revision,
                    edit_id=body.edit_id,
                    proposal=body.proposal,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            except (ValueError, GeneralCompilationError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error

    @app.put("/api/authoring/drafts/{draft_id}/coordination-configuration")
    def edit_draft_coordination_configuration(
        draft_id: str,
        body: DraftCoordinationEditRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_access(request)
        with authoring_lock:
            try:
                return authoring.edit_coordination_configuration(
                    draft_id,
                    expected_revision=body.expected_revision,
                    edit_id=body.edit_id,
                    configuration=body.configuration,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            except (ValueError, AuthoringCompilationError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error

    @app.put("/api/authoring/drafts/{draft_id}/component-composition-configuration")
    def edit_draft_component_composition_configuration(
        draft_id: str,
        body: DraftComponentCompositionEditRequest,
        request: Request,
    ) -> dict[str, object]:
        _require_access(request)
        with authoring_lock:
            try:
                return authoring.edit_component_composition_configuration(
                    draft_id,
                    expected_revision=body.expected_revision,
                    edit_id=body.edit_id,
                    configuration=body.configuration,
                )
            except DraftConflictError as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            except DraftNotFoundError as error:
                raise HTTPException(
                    status_code=404, detail="authoring draft not found"
                ) from error
            except (ValueError, AuthoringCompilationError) as error:
                raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/authoring/drafts/{draft_id}/approve")
    def approve_draft(
        draft_id: str, body: DraftApprovalRequest, request: Request
    ) -> dict[str, object]:
        _require_access(request)
        try:
            return authoring.approve(draft_id, expected_revision=body.expected_revision)
        except DraftConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except DraftNotFoundError as error:
            raise HTTPException(status_code=404, detail="authoring draft not found") from error
        except (ValueError, AuthoringCompilationError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/authoring/drafts/{draft_id}/runs", response_model=None)
    def run_approved_draft(
        draft_id: str, body: AuthoredRunRequest, request: Request
    ) -> dict[str, object] | Response:
        _require_access(request)
        live = body.execution == "live"
        if not live and body.llm_options is not None:
            raise HTTPException(
                status_code=422,
                detail="llm_options apply only to live execution",
            )
        if not live and body.narration == "llm":
            raise HTTPException(
                status_code=422,
                detail="llm narration applies only to live execution",
            )
        if live and os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        effective_llm: EffectiveRunLlmConfiguration | None = None
        if live:
            try:
                effective_llm = resolve_live_configuration(body.llm_options)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        try:
            draft_document = drafts.get(draft_id)
        except DraftNotFoundError as error:
            raise HTTPException(status_code=404, detail="authoring draft not found") from error
        if draft_document.get("target_kind") in {"general_world_v1", "general_world_v2"}:
            if not live or effective_llm is None:
                raise HTTPException(
                    status_code=422,
                    detail="general-world simulations require a selected live model route",
                )
            try:
                approved_general = authoring.approved_general_compile(draft_id)
            except (ValueError, GeneralCompilationError) as error:
                raise HTTPException(status_code=409, detail=str(error)) from error
            worker_execution = bool(getattr(authored_live_worker_context, "active", False))
            lock_acquired = True if worker_execution else live_lock.acquire(blocking=False)
            if not lock_acquired:
                raise HTTPException(status_code=409, detail="another live run is already active")
            run_id = (
                str(authored_live_worker_context.run_id)
                if worker_execution
                else f"run_{uuid4().hex[:12]}"
            )
            if isinstance(approved_general, CompiledGeneralSimulationV2):
                authored_bundle = AuthoredSimulationBundleV2.model_validate(
                    draft_document["proposal"]
                )
                scenario_v2 = authored_bundle.scenario
                run_spec_v2 = RunSpecV2.model_validate(
                    {
                        **authored_bundle.default_run.model_dump(mode="json"),
                        "run_id": run_id,
                        "execution_mode": "live",
                        "model": effective_llm.model,
                        "reasoning_effort": effective_llm.agent_reasoning_effort,
                        "per_call_budget": effective_llm.participant_per_call_ceiling,
                        "per_run_budget": effective_llm.max_total_cost,
                        "cognition_mode": "staged",
                    }
                )
                presentation_question = authored_bundle.analyst_question
                selected_analyses = authored_bundle.analyses
                profile = "general_world_v2"
            else:
                scenario_v2, run_spec_v2 = adapt_general_proposal_v1(
                    approved_general.proposal,
                    run_id=run_id,
                    execution_mode="live",
                    model=effective_llm.model,
                    reasoning_effort=effective_llm.agent_reasoning_effort,
                    per_call_budget=effective_llm.participant_per_call_ceiling,
                    per_run_budget=effective_llm.max_total_cost,
                    cognition_mode="staged",
                )
                authored_bundle = adapt_authored_bundle_v1(
                    approved_general.proposal, run_id=run_id
                )
                presentation_question = approved_general.proposal.question
                selected_analyses = authored_bundle.analyses
                profile = "general_world_v1"
            general_compiled = compile_general_simulation_v2(
                scenario_v2, run_spec_v2
            )
            if worker_execution:
                try:
                    initial = runs.get(run_id)
                except (InvalidRunIdError, RunNotFoundError, RunCorruptError) as error:
                    raise RuntimeError("general live worker could not reopen its run") from error
                created_at = str(initial["created_at"])
            else:
                created_at = now_iso()
                initial = {
                    "run_id": run_id,
                    "created_at": created_at,
                    "status": "running",
                    "scenario": scenario_v2.scenario_id,
                    "profile": profile,
                    "arm": "approved_draft",
                    "execution": "live",
                    "model_calls": 0,
                    "cost": 0.0,
                    "llm_configuration": effective_llm.model_dump(mode="json"),
                    "authoring": {
                        "draft_id": draft_id,
                        "proposal_kind": "general_world_v2",
                        "proposal_digest": general_compiled.scenario_digest,
                        "scenario_digest": general_compiled.scenario_digest,
                        "run_spec_digest": general_compiled.run_spec_digest,
                        "registry_digest": general_compiled.registry_digest,
                        "title": scenario_v2.title,
                        "description": scenario_v2.description,
                        "question": presentation_question,
                        "people": [
                            {
                                "entity_id": person.entity_id,
                                "label": person.label,
                                "position": person.position,
                            }
                            for person in scenario_v2.people
                        ],
                        "coverage": general_compiled.coverage.model_dump(mode="json"),
                    },
                    "live_progress": [],
                    "progress_sequence": 0,
                }
                runs.save(initial)
            if not worker_execution:
                def execute_general_live_worker() -> None:
                    authored_live_worker_context.active = True
                    authored_live_worker_context.run_id = run_id
                    try:
                        run_approved_draft(draft_id, body, request)
                    except Exception as error:
                        runs.save(
                            {
                                **initial,
                                "status": "failed",
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                        if live_lock.locked():
                            live_lock.release()
                    finally:
                        del authored_live_worker_context.run_id
                        del authored_live_worker_context.active

                Thread(
                    target=execute_general_live_worker,
                    name=f"cybernetic-general-live-{run_id}",
                    daemon=True,
                ).start()
                return JSONResponse(status_code=202, content=initial)

            def retain_general_progress(
                update: dict[str, object], checkpoint: dict[str, object]
            ) -> None:
                current = runs.get(run_id)
                history = current.get("live_progress")
                retained_history = history if isinstance(history, list) else []
                raw_sequence = current.get("progress_sequence", 0)
                sequence = (raw_sequence if isinstance(raw_sequence, int) else 0) + 1
                completed_moments = update.get("completed_moments", 0)
                completed_moment_count = (
                    completed_moments if isinstance(completed_moments, int) else 0
                )
                runs.save(
                    {
                        **current,
                        "live_progress": [*retained_history, {**update, "sequence": sequence}],
                        "progress_sequence": sequence,
                        "model_calls": update.get(
                            "model_calls",
                            completed_moment_count * ((len(scenario_v2.people) * 2) + 1),
                        ),
                        "general_checkpoint": checkpoint,
                    }
                )

            try:
                general_result = run_general_simulation_v2(
                    general_compiled,
                    call=general_simulation_call,
                    progress_observer=retain_general_progress,
                )
                projected = project_general_run(
                    general_compiled,
                    general_result,
                    run_id=run_id,
                    created_at=created_at,
                    execution="live",
                    presentation_question=(
                        presentation_question or scenario_v2.description
                    ),
                )
                evidence_bundle = build_run_evidence_bundle_v2(
                    general_compiled, general_result
                )
                projected["run_evidence_bundle"] = evidence_bundle.model_dump(
                    mode="json"
                )
                projected["analysis_results"] = [
                    analyze_run_evidence_v2(
                        evidence_bundle, analysis_spec
                    ).model_dump(mode="json")
                    for analysis_spec in selected_analyses
                ]
                projected["analysis_specs"] = [
                    item.model_dump(mode="json") for item in selected_analyses
                ]
                projected["analysis_isolation_receipts"] = []
                projected["llm_configuration"] = initial["llm_configuration"]
                retained = runs.get(run_id)
                projected["live_progress"] = retained.get("live_progress", [])
                projected["progress_sequence"] = retained.get("progress_sequence", 0)
                projected["general_checkpoint"] = retained.get("general_checkpoint")
                return runs.save(projected)
            except Exception as error:
                failed = runs.get(run_id)
                failed_progress = failed.get("live_progress")
                retained_failed = runs.save(
                    {
                        **failed,
                        "status": "failed",
                        "error": f"{type(error).__name__}: {error}",
                        "resume_boundary": {
                            "completed_moments": (
                                len(failed_progress)
                                if isinstance(failed_progress, list)
                                else 0
                            ),
                            "checkpoint_retained": isinstance(
                                failed.get("general_checkpoint"), dict
                            ),
                        },
                    }
                )
                return retained_failed
            finally:
                if live_lock.locked():
                    live_lock.release()
        try:
            compiled = authoring.approved_compile(draft_id)
        except DraftNotFoundError as error:
            raise HTTPException(
                status_code=404,
                detail="authoring draft not found",
            ) from error
        except (ValueError, AuthoringCompilationError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if (
            isinstance(
                compiled.proposal.workflow,
                (CoordinationDecisionWorkflowDraft, InfluenceNetworkWorkflowDraft),
            )
            and not live
            and not allow_internal_scripted_coordination
        ):
            scenario_label = (
                "coordination scenarios"
                if isinstance(
                    compiled.proposal.workflow, CoordinationDecisionWorkflowDraft
                )
                else "influence-network scenarios"
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{scenario_label} require live agent execution; "
                    "scripted people are internal verification fixtures"
                ),
            )

        worker_execution = live and bool(
            getattr(authored_live_worker_context, "active", False)
        )
        lock_acquired = (
            True
            if worker_execution
            else live and live_lock.acquire(blocking=False)
        )
        if live and not lock_acquired:
            raise HTTPException(
                status_code=409,
                detail="another live run is already active",
            )
        run_id = (
            str(authored_live_worker_context.run_id)
            if worker_execution
            else f"run_{uuid4().hex[:12]}"
        )
        if worker_execution:
            try:
                initial = runs.get(run_id)
            except (InvalidRunIdError, RunNotFoundError, RunCorruptError) as error:
                raise RuntimeError("authored live worker could not reopen its run") from error
            created_at = str(initial["created_at"])
        else:
            created_at = now_iso()
            initial = {
                "run_id": run_id,
                "created_at": created_at,
                "status": "running",
                "scenario": compiled.scenario.scenario_id,
                "profile": "authored_typed_scenario",
                "arm": "approved_draft",
                "execution": body.execution,
                "model_calls": 0,
                "cost": 0.0,
                "llm_configuration": (
                    effective_llm.model_dump(mode="json")
                    if effective_llm is not None
                    else None
                ),
                "authoring": {
                    "draft_id": draft_id,
                    "proposal_digest": compiled.proposal_digest,
                    "template_id": compiled.proposal.workflow.template_id,
                    "composition_receipt": compiled.composition_receipt.model_dump(
                        mode="json"
                    ),
                    "composition_receipt_digest": (
                        compiled.composition_receipt.digest
                    ),
                    "title": compiled.proposal.title,
                    "description": compiled.proposal.description,
                    "people": [
                        {
                            "entity_id": person.entity_id,
                            "label": person.label,
                            "position": person.position,
                        }
                        for person in compiled.proposal.people
                    ],
                },
                "live_progress": [],
                "progress_sequence": 0,
            }
            runs.save(initial)
            if live and isinstance(
                compiled.proposal.workflow,
                (
                    CoordinationDecisionWorkflowDraft,
                    InfluenceNetworkWorkflowDraft,
                ),
            ):
                with pause_lock:
                    stop_requests[run_id] = Event()
        if live and not worker_execution:
            def execute_authored_live_worker() -> None:
                authored_live_worker_context.active = True
                authored_live_worker_context.run_id = run_id
                try:
                    run_approved_draft(draft_id, body, request)
                except Exception as error:
                    # This only covers failures before the normal worker body
                    # can retain its own diagnostic.  A live lock must never
                    # remain held merely because setup itself failed.
                    try:
                        runs.save(
                            {
                                **initial,
                                "status": "failed",
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                    finally:
                        if live_lock.locked():
                            live_lock.release()
                finally:
                    with pause_lock:
                        stop_requests.pop(run_id, None)
                    del authored_live_worker_context.run_id
                    del authored_live_worker_context.active

            Thread(
                target=execute_authored_live_worker,
                name=f"cybernetic-authored-live-{run_id}",
                daemon=True,
            ).start()
            return JSONResponse(status_code=202, content=initial)
        result: ActiveRuntimeResult | None = None
        try:
            authored_stop: Event | None = None
            if live and isinstance(
                compiled.proposal.workflow,
                (
                    CoordinationDecisionWorkflowDraft,
                    InfluenceNetworkWorkflowDraft,
                ),
            ):
                with pause_lock:
                    authored_stop = stop_requests.get(run_id)
                if authored_stop is None:
                    raise RuntimeError(
                        "authored multi-person worker lacks its stop control"
                    )
            result = (
                compiled.run_live(
                    run_id=run_id,
                    model=effective_llm.model,
                    reasoning_effort=effective_llm.agent_reasoning_effort,
                    per_call_budget=effective_llm.participant_per_call_ceiling,
                    per_run_budget=effective_llm.max_total_cost,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id, update, checkpoint
                    ),
                    stop_requested=(
                        authored_stop.is_set
                        if authored_stop is not None
                        else None
                    ),
                    participant_concurrency=(
                        min(8, len(compiled.proposal.people))
                        if isinstance(
                            compiled.proposal.workflow,
                            (
                                CoordinationDecisionWorkflowDraft,
                                InfluenceNetworkWorkflowDraft,
                            ),
                        )
                        else 1
                    ),
                )
                if effective_llm is not None
                else compiled.run_scripted(
                    run_id=run_id,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id, update, checkpoint
                    ),
                )
            )
            workflow = compiled.proposal.workflow
            if isinstance(workflow, InfluenceNetworkWorkflowDraft):
                network_outcome, headline, summary = influence_network_outcome(
                    result
                )
                network_outcome.update(
                    {
                        "draft_id": draft_id,
                        "template_id": workflow.template_id,
                    }
                )
                document = build_analyst_document(
                    initial_state=compiled.scenario.initial_state,
                    analytical_boundaries=compiled.scenario.analytical_boundaries,
                    result=result,
                    scenario=compiled.scenario.scenario_id,
                    profile="authored_typed_scenario",
                    arm_id="approved_draft",
                    execution=body.execution,
                    created_at=created_at,
                    outcome=network_outcome,
                    headline=headline,
                    summary=summary,
                    include_boundary_activity=True,
                )
                document["completion"] = (
                    result.completion.model_dump(mode="json")
                    if result.completion is not None
                    else None
                )
                document["authoring"] = initial["authoring"]
                narrated = _attach_narration(
                    document,
                    live=live and body.narration == "llm",
                    run_id=run_id,
                    effective_llm=effective_llm,
                )
                narrated = retain_progress_history(narrated, run_id)
                narrated["llm_configuration"] = initial["llm_configuration"]
                narrated["model_call_summaries"] = _result_call_summaries(result)
                return runs.save(narrated)
            if isinstance(workflow, CoordinationDecisionWorkflowDraft):
                if not isinstance(compiled.fixture, CoordinationRuntimeFixture):
                    raise RuntimeError(
                        "compiled coordination workflow lacks its runtime fixture"
                    )
                coordination_outcome, headline, summary = _coordination_outcome(
                    result
                )
                document = build_analyst_document(
                    initial_state=compiled.scenario.initial_state,
                    analytical_boundaries=compiled.scenario.analytical_boundaries,
                    result=result,
                    scenario=compiled.scenario.scenario_id,
                    profile="authored_typed_scenario",
                    arm_id=workflow.condition,
                    execution=body.execution,
                    created_at=created_at,
                    outcome=coordination_outcome,
                    headline=headline,
                    summary=summary,
                    include_boundary_activity=True,
                )
                document["theory_analysis"] = (
                    build_live_theory_analysis(
                        compiled,
                        result,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                        per_call_budget=(
                            effective_llm.participant_per_call_ceiling
                        ),
                        per_run_budget=effective_llm.max_total_cost,
                    )
                    if effective_llm is not None
                    else build_reference_theory_analysis(compiled, result)
                )
                document["run_control"] = coordination_run_control_plan(
                    compiled.fixture
                ).model_dump(mode="json")
                document["completion"] = (
                    result.completion.model_dump(mode="json")
                    if result.completion is not None
                    else None
                )
                document["authoring"] = initial["authoring"]
                narrated = _attach_narration(
                    document,
                    live=live and body.narration == "llm",
                    run_id=run_id,
                    effective_llm=effective_llm,
                )
                if body.narration == "deterministic":
                    narrated["narration"] = _coordination_reference_narration(
                        narrated
                    )
                narrated = retain_progress_history(narrated, run_id)
                narrated["llm_configuration"] = initial["llm_configuration"]
                narrated["model_call_summaries"] = _result_call_summaries(
                    result
                )
                return runs.save(narrated)
            outcome_entity_id = (
                workflow.request_id
                if workflow.template_id == "resource_request_v1"
                else (
                    workflow.record_id
                    if workflow.template_id == "component_composition_v1"
                    else workflow.campaign_id
                )
            )
            outcome_status = result.core_result.final_state.entities[
                outcome_entity_id
            ].attributes["status"].value
            title = compiled.proposal.title
            resource_request = workflow.template_id == "resource_request_v1"
            component_composition = workflow.template_id == "component_composition_v1"
            outcome: dict[str, object] = {
                "status": outcome_status,
                "draft_id": draft_id,
                "template_id": workflow.template_id,
            }
            if resource_request:
                outcome["request_status"] = outcome_status
            document = build_analyst_document(
                initial_state=compiled.scenario.initial_state,
                analytical_boundaries=compiled.scenario.analytical_boundaries,
                result=result,
                scenario=compiled.scenario.scenario_id,
                profile="authored_typed_scenario",
                arm_id="approved_draft",
                execution=body.execution,
                created_at=created_at,
                outcome=outcome,
                headline=(
                    (
                        "Resource reserved"
                        if outcome_status == "reserved"
                        else "Resource request denied"
                    )
                    if resource_request
                    else (
                        "Report delivered and assessed"
                        if component_composition
                        else (
                        "Claim delivered and assessed"
                        if str(outcome_status).startswith("assessed_")
                        else "Claim was not delivered"
                        )
                    )
                ),
                summary=(
                    f"{title}: the exact "
                    f"{'reservation' if resource_request else ('component delivery-and-recording' if component_composition else 'information-delivery')} "
                    f"mechanisms recorded {outcome_status}."
                ),
            )
            document["authoring"] = initial["authoring"]
            narrated = _attach_narration(
                document,
                live=live and body.narration == "llm",
                run_id=run_id,
                effective_llm=effective_llm,
            )
            narrated = retain_progress_history(narrated, run_id)
            narrated["llm_configuration"] = initial["llm_configuration"]
            narrated["model_call_summaries"] = _result_call_summaries(result)
            return runs.save(narrated)
        except Exception as error:
            call_summaries = (
                _result_call_summaries(result)
                if result is not None
                else []
            )
            call_summaries.extend(_error_call_summaries(error))
            # A retained terminal worker failure must not advertise failure
            # while retaining the process-wide live slot.
            if worker_execution and lock_acquired:
                live_lock.release()
                lock_acquired = False
            failed = {
                **initial,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
                "model_call_summaries": call_summaries,
                "model_calls": len(call_summaries),
                "cost": sum(
                    _nonnegative_float(item.get("cost"))
                    for item in call_summaries
                ),
            }
            runs.save(failed)
            if worker_execution:
                return runs.save(failed)
            raise HTTPException(
                status_code=500,
                detail="authored simulation failed; retained for inspection",
            ) from error
        finally:
            if lock_acquired:
                live_lock.release()

    @app.post("/api/authoring/drafts/{draft_id}/experiments", response_model=None)
    def create_draft_experiment(
        draft_id: str, body: ExperimentRequestV2, request: Request
    ) -> Response:
        """Re-execute an already-approved draft under controlled RunLlmOptions.

        Never accepts a scenario-shaped field (ADR-014's Experiment/Scenario
        authority separation): the only per-condition input is RunLlmOptions.
        Conditions execute sequentially in a background thread, each one
        reusing run_approved_draft's own single-live-run codepath unchanged,
        so experimentation carries no duplicated compile/execution logic and
        cannot diverge from a normal single run's behavior.
        """
        _require_access(request)
        if os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        try:
            draft_document = drafts.get(draft_id)
        except DraftNotFoundError as error:
            raise HTTPException(
                status_code=404, detail="authoring draft not found"
            ) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        if draft_document.get("status") != "approved":
            raise HTTPException(
                status_code=422,
                detail="draft must be approved before experimentation",
            )
        if draft_document.get("target_kind") not in {
            "general_world_v1",
            "general_world_v2",
        }:
            raise HTTPException(
                status_code=422,
                detail="experimentation requires a general-world simulation",
            )
        for condition in body.conditions:
            try:
                resolve_live_configuration(condition.run_overrides)
            except ValueError as error:
                raise HTTPException(
                    status_code=422,
                    detail=f"condition {condition.condition_id!r}: {error}",
                ) from error

        experiment_id = experiments.new_id()
        created_at = now_iso()
        initial_record = ExperimentResultV2(
            experiment_id=experiment_id,
            draft_id=draft_id,
            base_scenario_digest=None,
            status="running",
            conditions=[],
            created_at=created_at,
            updated_at=created_at,
        )
        experiments.save(initial_record.model_dump(mode="json"))

        def execute_experiment() -> None:
            base_scenario_digest: str | None = None
            results: list[ExperimentConditionResultV2] = []

            def persist(status: Literal["running", "completed"]) -> None:
                experiments.save(
                    ExperimentResultV2(
                        experiment_id=experiment_id,
                        draft_id=draft_id,
                        base_scenario_digest=base_scenario_digest,
                        status=status,
                        conditions=results,
                        created_at=created_at,
                        updated_at=now_iso(),
                    ).model_dump(mode="json")
                )

            for condition in body.conditions:
                for repetition_index in range(body.repetitions_per_condition):
                    run_body = AuthoredRunRequest(
                        execution="live", llm_options=condition.run_overrides
                    )
                    try:
                        # The previous condition's worker thread releases
                        # live_lock a few instructions after it saves the
                        # "completed" run document, so a 409 immediately
                        # after our own completion poll is a brief, expected
                        # race rather than a real conflicting run.
                        response = None
                        for attempt in range(10):
                            try:
                                response = run_approved_draft(
                                    draft_id, run_body, request
                                )
                                break
                            except HTTPException as error:
                                if error.status_code != 409 or attempt == 9:
                                    raise
                                sleep(0.2)
                        assert response is not None
                    except HTTPException as error:
                        results.append(
                            ExperimentConditionResultV2(
                                condition_id=condition.condition_id,
                                repetition_index=repetition_index,
                                run_id="",
                                status="failed",
                                error=str(error.detail),
                            )
                        )
                        persist("running")
                        continue
                    started = (
                        json.loads(bytes(response.body))
                        if isinstance(response, Response)
                        else response
                    )
                    run_id = str(started["run_id"])
                    while True:
                        current_run = runs.get(run_id)
                        if current_run.get("status") in {"completed", "failed"}:
                            break
                        sleep(1.0)
                    if current_run.get("status") == "completed":
                        evidence = current_run.get("run_evidence_bundle")
                        run_scenario_digest = (
                            evidence.get("scenario_digest")
                            if isinstance(evidence, dict)
                            else None
                        )
                        if base_scenario_digest is None:
                            base_scenario_digest = (
                                str(run_scenario_digest)
                                if isinstance(run_scenario_digest, str)
                                else None
                            )
                        if (
                            base_scenario_digest is not None
                            and run_scenario_digest != base_scenario_digest
                        ):
                            results.append(
                                ExperimentConditionResultV2(
                                    condition_id=condition.condition_id,
                                    repetition_index=repetition_index,
                                    run_id=run_id,
                                    status="failed",
                                    error=(
                                        "run scenario_digest diverged from this "
                                        "experiment's base_scenario_digest"
                                    ),
                                )
                            )
                        else:
                            results.append(
                                ExperimentConditionResultV2(
                                    condition_id=condition.condition_id,
                                    repetition_index=repetition_index,
                                    run_id=run_id,
                                    run_evidence_bundle_digest=(
                                        evidence.get("record_digest")
                                        if isinstance(evidence, dict)
                                        else None
                                    ),
                                    status="completed",
                                )
                            )
                    else:
                        results.append(
                            ExperimentConditionResultV2(
                                condition_id=condition.condition_id,
                                repetition_index=repetition_index,
                                run_id=run_id,
                                status="failed",
                                error=str(current_run.get("error", "run failed")),
                            )
                        )
                    persist("running")
            persist("completed")

        Thread(
            target=execute_experiment,
            name=f"cybernetic-experiment-{experiment_id}",
            daemon=True,
        ).start()
        return JSONResponse(
            status_code=202,
            content={"experiment_id": experiment_id, "job_id": experiment_id},
        )

    @app.get("/api/experiments/{experiment_id}")
    def get_experiment(experiment_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            return experiments.get(experiment_id)
        except InvalidExperimentIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ExperimentNotFoundError as error:
            raise HTTPException(
                status_code=404, detail="experiment not found"
            ) from error

    @app.get("/api/scenarios/{scenario}/preview")
    def scenario_preview(
        scenario: Literal[
            "service_desk",
            "physical_access",
            "purchase_payment",
            "coordination_decision",
            "regional_outbreak",
        ],
        arm_id: str,
        cognition_profile: str = "position_context",
    ) -> dict[str, object]:
        """Return a read-only initial projection for the map before Play."""
        try:
            return _scenario_preview(scenario, arm_id, cognition_profile)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/runs/{run_id}")
    def retained_run(
        run_id: str,
        request: Request,
        through_event_id: str | None = None,
    ) -> dict[str, object]:
        _require_access(request)
        try:
            document = runs.get(run_id)
            validate_retained_narration(document)
            try:
                validate_retained_boundary_activities(document)
            except ValueError as error:
                raise HTTPException(
                    status_code=409,
                    detail="retained boundary evidence is corrupt",
                ) from error
            if through_event_id is not None:
                raw_events = document.get("events", [])
                if not isinstance(raw_events, list):
                    raise ValueError("retained events are malformed")
                selected_event = next(
                    (
                        item
                        for item in raw_events
                        if isinstance(item, dict)
                        and item.get("event_id") == through_event_id
                    ),
                    None,
                )
                if not isinstance(selected_event, dict):
                    raise ValueError("selected event is not retained by this run")
                through_sequence = selected_event.get("sequence")
                if not isinstance(through_sequence, int) or isinstance(
                    through_sequence, bool
                ):
                    raise ValueError("selected event sequence is malformed")
                document = deepcopy(document)
                raw_boundaries = document.get("boundaries", [])
                if not isinstance(raw_boundaries, list):
                    raise ValueError("retained boundaries are malformed")
                for raw_boundary in raw_boundaries:
                    if not isinstance(raw_boundary, dict):
                        raise ValueError("retained boundary is malformed")
                    raw_activity = raw_boundary.get("activity")
                    if raw_activity is None:
                        continue
                    raw_event_index = raw_boundary.get("activity_event_index")
                    if not isinstance(raw_event_index, list):
                        raise ValueError("retained boundary event index is malformed")
                    raw_boundary["activity"] = clip_boundary_activity_projection(
                        BoundaryActivityProjection.model_validate(raw_activity),
                        [
                            cast(dict[str, object], item)
                            for item in raw_events
                            if isinstance(item, dict)
                        ],
                        [
                            cast(dict[str, object], item)
                            for item in raw_event_index
                            if isinstance(item, dict)
                        ],
                        through_sequence=through_sequence,
                    ).model_dump(mode="json")
                    raw_boundary["activity_event_index"] = [
                        item
                        for item in raw_event_index
                        if isinstance(item, dict)
                        and isinstance(item.get("sequence"), int)
                        and not isinstance(item.get("sequence"), bool)
                        and cast(int, item["sequence"]) <= through_sequence
                    ]
                return {
                    "run_id": run_id,
                    "through_event_id": through_event_id,
                    "boundaries": raw_boundaries,
                }
            if (
                document.get("scenario")
                in {"coordination_decision", "coordination_decision_v1"}
                and document.get("execution") == "scripted"
            ):
                # Narration is a derived read model. Reproject it from retained
                # exact evidence so older saved proofs gain the current readable
                # presentation without rewriting their authoritative record.
                document = deepcopy(document)
                document["narration"] = _coordination_reference_narration(document)
            else:
                document = deepcopy(document)
            document["coordination_measurement_readout"] = (
                coordination_measurement_readout(document).model_dump(mode="json")
            )
            raw_theory = document.get("theory_analysis")
            projected_theory = (
                raw_theory
                if isinstance(raw_theory, dict)
                and raw_theory.get("framework")
                == "Waltzman-informed diagnostic projection"
                else project_retained_theory_analysis(raw_theory)
            )
            if projected_theory is not None:
                document["theory_analysis"] = projected_theory
            return document
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except RunCorruptError as error:
            raise HTTPException(status_code=409, detail="retained run is corrupt") from error
        except ValueError as error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "retained boundary evidence is corrupt"
                    if through_event_id is not None
                    else "retained narration evidence context is corrupt"
                ),
            ) from error

    def _analysis_isolation_state(document: dict[str, object]) -> dict[str, object]:
        general = document.get("general_simulation")
        final_revision = None
        if isinstance(general, dict):
            final_state = general.get("final_state")
            if isinstance(final_state, dict):
                final_revision = final_state.get("revision")
        evidence = document.get("run_evidence_bundle")
        evidence_digest = evidence.get("record_digest") if isinstance(evidence, dict) else None
        return {
            "model_calls": document.get("model_calls"),
            "world_revision": final_revision,
            "run_evidence_digest": evidence_digest,
        }

    def _analysis_attachment_payload(document: dict[str, object]) -> dict[str, object]:
        return {
            "run_id": document["run_id"],
            "analysis_specs": document.get("analysis_specs", []),
            "analysis_results": document.get("analysis_results", []),
            "analysis_isolation_receipts": document.get(
                "analysis_isolation_receipts", []
            ),
        }

    def _dict_items(document: dict[str, object], key: str) -> list[dict[str, object]]:
        value = document.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"retained run field {key!r} must be a list")
        return [item for item in value if isinstance(item, dict)]

    @app.post("/api/runs/{run_id}/analyses")
    def attach_run_analysis(
        run_id: str,
        body: RunAnalysisAttachmentRequest,
        request: Request,
    ) -> dict[str, object]:
        """Analyze retained evidence without invoking or mutating the simulation."""
        _require_access(request)
        try:
            document = runs.get(run_id)
            if document.get("status") != "completed":
                raise HTTPException(status_code=409, detail="analysis requires a completed run")
            raw_evidence = document.get("run_evidence_bundle")
            if not isinstance(raw_evidence, dict):
                raise HTTPException(status_code=422, detail="run has no V2 evidence bundle")
            evidence = RunEvidenceBundleV2.model_validate(raw_evidence)
            before = _analysis_isolation_state(document)
            result = analyze_run_evidence_v2(evidence, body.analysis_spec)
            retained_specs = _dict_items(document, "analysis_specs")
            retained_results = _dict_items(document, "analysis_results")
            existing_specs = [
                item
                for item in retained_specs
                if item.get("analysis_id") == body.analysis_spec.analysis_id
            ]
            replaced_digests = {
                AnalysisSpecV2.model_validate(item).digest for item in existing_specs
            }
            specs = [
                item
                for item in retained_specs
                if item.get("analysis_id") != body.analysis_spec.analysis_id
            ]
            results = [
                item
                for item in retained_results
                if item.get("analysis_spec_digest") not in replaced_digests
            ]
            updated = {
                **document,
                "analysis_specs": [
                    *specs, body.analysis_spec.model_dump(mode="json")
                ],
                "analysis_results": [*results, result.model_dump(mode="json")],
            }
            after = _analysis_isolation_state(updated)
            receipt = {
                "receipt_id": f"analysis_attach_{uuid4().hex[:12]}",
                "action": "attached",
                "analysis_id": body.analysis_spec.analysis_id,
                "before": before,
                "after": after,
                "simulation_unchanged": before == after,
                "recorded_at": now_iso(),
            }
            updated["analysis_isolation_receipts"] = [
                *[
                    item
                    for item in _dict_items(document, "analysis_isolation_receipts")
                ],
                receipt,
            ]
            retained = runs.save(updated)
            return _analysis_attachment_payload(retained)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except (RunCorruptError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.delete("/api/runs/{run_id}/analyses/{analysis_id}")
    def remove_run_analysis(
        run_id: str,
        analysis_id: str,
        request: Request,
    ) -> dict[str, object]:
        """Remove one interpretation while preserving the retained execution."""
        _require_access(request)
        try:
            document = runs.get(run_id)
            retained_specs = _dict_items(document, "analysis_specs")
            retained_results = _dict_items(document, "analysis_results")
            specs = [
                item for item in retained_specs if item.get("analysis_id") == analysis_id
            ]
            if not specs:
                raise HTTPException(status_code=404, detail="analysis attachment not found")
            removed_digest = AnalysisSpecV2.model_validate(specs[0]).digest
            before = _analysis_isolation_state(document)
            updated = {
                **document,
                "analysis_specs": [
                    item
                    for item in retained_specs
                    if item.get("analysis_id") != analysis_id
                ],
                "analysis_results": [
                    item
                    for item in retained_results
                    if item.get("analysis_spec_digest") != removed_digest
                ],
            }
            after = _analysis_isolation_state(updated)
            receipt = {
                "receipt_id": f"analysis_remove_{uuid4().hex[:12]}",
                "action": "removed",
                "analysis_id": analysis_id,
                "before": before,
                "after": after,
                "simulation_unchanged": before == after,
                "recorded_at": now_iso(),
            }
            updated["analysis_isolation_receipts"] = [
                *[
                    item
                    for item in _dict_items(document, "analysis_isolation_receipts")
                ],
                receipt,
            ]
            retained = runs.save(updated)
            return _analysis_attachment_payload(retained)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except (RunCorruptError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.get("/api/runs/{run_id}/progress")
    def retained_progress(
        run_id: str,
        request: Request,
        after_sequence: int = 0,
        include_projection: bool = True,
    ) -> dict[str, object]:
        """Return only analyst-safe live updates after one retained sequence."""
        _require_access(request)
        if after_sequence < 0:
            raise HTTPException(status_code=422, detail="after_sequence must be nonnegative")
        try:
            document = runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except RunCorruptError as error:
            raise HTTPException(status_code=409, detail="retained run is corrupt") from error
        records = document.get("live_progress", [])
        if not isinstance(records, list):
            raise HTTPException(status_code=409, detail="retained live progress is malformed")
        typed = [item for item in records if isinstance(item, dict)]
        if len(typed) != len(records):
            raise HTTPException(status_code=409, detail="retained live progress is malformed")
        newer = [
            item
            for item in typed
            if isinstance(item.get("sequence"), int)
            and not isinstance(item.get("sequence"), bool)
            and int(item["sequence"]) > after_sequence
        ]
        latest = typed[-1] if typed else None
        if not include_projection:
            newer = [
                {key: value for key, value in item.items() if key != "projection"}
                for item in newer
            ]
        story = document.get("story")
        if not isinstance(story, dict):
            story = {}
        return {
            "run_id": run_id,
            "status": document.get("status"),
            "latest_sequence": document.get("progress_sequence", 0),
            "records": newer,
            "projection": (
                latest.get("projection")
                if include_projection and latest is not None
                else None
            ),
            "model_calls": document.get("model_calls", 0),
            "cost": document.get("cost", 0.0),
            "completion": document.get("completion"),
            "coordination_measurement_status": document.get(
                "coordination_measurement_status"
            ),
            "outcome": document.get("outcome"),
            "headline": story.get("headline"),
            "summary": story.get("summary"),
            "error": document.get("error"),
        }

    @app.get("/api/runs/{run_id}/summary")
    def retained_run_summary(
        run_id: str,
        request: Request,
    ) -> dict[str, object]:
        """Return a compact readable result without the multi-megabyte evidence."""
        _require_access(request)
        try:
            document = runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except RunCorruptError as error:
            raise HTTPException(status_code=409, detail="retained run is corrupt") from error
        authoring_metadata = document.get("authoring")
        if isinstance(authoring_metadata, dict) and not isinstance(
            authoring_metadata.get("people"), list
        ):
            draft_id = authoring_metadata.get("draft_id")
            if isinstance(draft_id, str):
                try:
                    draft = drafts.get(draft_id)
                except DraftNotFoundError:
                    draft = None
                except ValueError as error:
                    raise HTTPException(
                        status_code=409,
                        detail="retained authoring draft is corrupt",
                    ) from error
                if isinstance(draft, dict) and isinstance(
                    draft.get("proposal"), dict
                ):
                    proposal = cast(dict[str, object], draft["proposal"])
                    people = proposal.get("people")
                    if isinstance(people, list):
                        document = deepcopy(document)
                        document_authoring = document.get("authoring")
                        if isinstance(document_authoring, dict):
                            document_authoring["people"] = [
                                {
                                    "entity_id": person.get("entity_id"),
                                    "label": person.get("label"),
                                    "position": person.get("position"),
                                }
                                for person in people
                                if isinstance(person, dict)
                            ]
        return _compact_run_result(document)

    @app.delete("/api/runs/{run_id}")
    def delete_run(run_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            runs.trash(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        return {"run_id": run_id, "status": "trashed", "recoverable": True}

    @app.post("/api/runs/{run_id}/pause")
    def pause_run(run_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            document = runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        with pause_lock:
            pause = pause_requests.get(run_id)
        if (
            document.get("scenario")
            not in {"service_desk", "coordination_decision"}
            or document.get("execution") not in {"scripted", "live"}
            or pause is None
        ):
            raise HTTPException(status_code=409, detail="this run cannot be paused")
        if document.get("status") not in {"running", "pause_requested"}:
            raise HTTPException(status_code=409, detail="run is not active")
        pause.set()
        # Serialize the operator transition with progress persistence so a
        # just-committed checkpoint cannot overwrite the requested pause.
        with progress_lock:
            current = runs.get(run_id)
            current["status"] = "pause_requested"
            current["pause_message"] = (
                "Pause will take effect after the current causal step."
            )
            runs.save(current)
        return {"run_id": run_id, "status": "pause_requested"}

    @app.post("/api/runs/{run_id}/stop")
    def stop_run(run_id: str, request: Request) -> dict[str, object]:
        """Request irreversible completion at the next retained causal boundary."""
        _require_access(request)
        try:
            document = runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        with pause_lock:
            stop = stop_requests.get(run_id)
        authoring = document.get("authoring")
        authored_template = (
            authoring.get("template_id") if isinstance(authoring, dict) else None
        )
        if (
            document.get("scenario")
            not in {
                "service_desk",
                "coordination_decision",
                "coordination_decision_v1",
            }
            and authored_template != "influence_network_v1"
        ) or stop is None:
            raise HTTPException(status_code=409, detail="this run cannot be stopped")
        if document.get("status") == "stop_requested":
            return {"run_id": run_id, "status": "stop_requested"}
        if document.get("status") not in {"running", "pause_requested"}:
            raise HTTPException(status_code=409, detail="run is not active")
        stop.set()
        with progress_lock:
            current = runs.get(run_id)
            current["status"] = "stop_requested"
            current["stop_message"] = (
                "Stop will take effect after the current causal step."
            )
            runs.save(current)
        return {"run_id": run_id, "status": "stop_requested"}

    @app.post("/api/runs/{run_id}/resume", response_model=None)
    def resume_run(run_id: str, request: Request) -> dict[str, object] | Response:
        _require_access(request)
        worker_execution = bool(
            getattr(resume_live_worker_context, "active", False)
        )
        try:
            paused = runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        narration = paused.get("narration")
        narration_resume = paused.get("narration_resume")
        if (
            paused.get("status") == "completed"
            and isinstance(narration, dict)
            and narration.get("status") == "completed"
            and isinstance(narration_resume, dict)
            and narration_resume.get("status") == "completed"
        ):
            return paused
        failure_boundary = (
            narration.get("failure_boundary")
            if isinstance(narration, dict)
            else None
        )
        narration_only_resume = (
            paused.get("status") == "completed"
            and paused.get("scenario")
            in {"coordination_decision", "coordination_decision_v1"}
            and paused.get("execution") == "live"
            and isinstance(narration, dict)
            and narration.get("status") == "unavailable"
            and _nonnegative_int(narration.get("model_calls")) == 0
            and isinstance(failure_boundary, dict)
            and failure_boundary.get("kind") == "call_limit_preflight"
        )
        if narration_only_resume:
            effective_narrator = retained_live_configuration(
                paused,
                description="completed live run",
            )
            if not live_lock.acquire(blocking=False):
                raise HTTPException(
                    status_code=409,
                    detail="another live run is already active",
                )
            try:
                raw_moments = paused.get("moments")
                if not isinstance(raw_moments, list) or not all(
                    isinstance(item, dict) for item in raw_moments
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="retained causal moments are invalid",
                    )
                coalesced = coalesce_retained_exact_work_moments(
                    cast(list[dict[str, object]], raw_moments)
                )
                if len(coalesced) > effective_narrator.maximum_narrator_calls:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "retained causal moments still exceed the original "
                            "narrator call limit after coordination coalescing"
                        ),
                    )
                pending = {
                    **paused,
                    "status": "narrating",
                    "moments": coalesced,
                    "narration": {
                        "status": "running",
                        "reason": (
                            "The completed world run is unchanged; its missing "
                            "causal-moment narrative is now being generated."
                        ),
                        "model_calls": 0,
                        "cost": 0.0,
                        "moments": [],
                        "calls": [],
                    },
                    "narration_resume": {
                        "status": "running",
                        "started_at": now_iso(),
                        "world_replayed": False,
                        "previous_failure_boundary": deepcopy(
                            failure_boundary
                        ),
                    },
                }
                pending = runs.save(pending)
            except Exception:
                live_lock.release()
                raise

            def execute_narration_resume_worker() -> None:
                try:
                    current = runs.get(run_id)
                    narrated = _attach_narration(
                        current,
                        live=True,
                        run_id=run_id,
                        effective_llm=effective_narrator,
                    )
                    resumed_narration = narrated.get("narration")
                    completed = (
                        isinstance(resumed_narration, dict)
                        and resumed_narration.get("status") == "completed"
                    )
                    runs.save(
                        {
                            **narrated,
                            "status": "completed",
                            "narration_resume": {
                                **cast(
                                    dict[str, object],
                                    current["narration_resume"],
                                ),
                                "status": "completed" if completed else "failed",
                                "completed_at": now_iso(),
                                "world_replayed": False,
                            },
                        }
                    )
                except Exception as error:
                    latest = runs.get(run_id)
                    runs.save(
                        {
                            **latest,
                            "status": "completed",
                            "cost_fully_observable": False,
                            "narration": {
                                "status": "unavailable",
                                "reason": (
                                    "The narration-only resume failed; the "
                                    "completed world run remains available."
                                ),
                                "failure_boundary": {
                                    "kind": "narration_resume_error",
                                    "error_type": type(error).__name__,
                                    "error_message": str(error),
                                },
                                "model_calls": 0,
                                "cost": 0.0,
                                "moments": [],
                                "calls": [],
                            },
                            "narration_resume": {
                                **cast(
                                    dict[str, object],
                                    latest["narration_resume"],
                                ),
                                "status": "failed",
                                "completed_at": now_iso(),
                                "world_replayed": False,
                            },
                        }
                    )
                finally:
                    live_lock.release()

            Thread(
                target=execute_narration_resume_worker,
                name=f"cybernetic-narration-resume-{run_id}",
                daemon=True,
            ).start()
            return JSONResponse(status_code=202, content=pending)
        scenario = paused.get("scenario")
        if (
            (
                not worker_execution
                and paused.get("status") not in {"paused", "failed"}
            )
            or scenario not in {"service_desk", "coordination_decision"}
            or paused.get("execution") not in {"scripted", "live"}
        ):
            raise HTTPException(status_code=409, detail="this run cannot be resumed")
        continuation = paused.get("continuation")
        if not isinstance(continuation, dict):
            raise HTTPException(status_code=422, detail="run has no continuation")
        try:
            checkpoint = ActiveRuntimeCheckpoint.model_validate(continuation["checkpoint"])
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail="retained checkpoint is invalid") from error
        arm = next(
            (
                item
                for item in service_desk_arm_configurations()
                if item.arm_id == paused.get("arm")
            ),
            None,
        )
        coordination_contract: CoordinationDecisionFixture | None = None
        if scenario == "service_desk" and arm is None:
            raise HTTPException(
                status_code=422,
                detail="retained run has an unknown scenario arm",
            )
        if scenario == "coordination_decision":
            try:
                coordination_contract = _coordination_contract(str(paused.get("arm")))
            except ValueError as error:
                raise HTTPException(
                    status_code=422,
                    detail="retained run has an unknown scenario arm",
                ) from error
        profile = paused.get("profile")
        if scenario == "service_desk" and profile not in {
            "position_context",
            "procedural_control",
        }:
            raise HTTPException(
                status_code=422,
                detail="retained run has an invalid cognition profile",
            )
        live = paused.get("execution") == "live"
        effective_llm: EffectiveRunLlmConfiguration | None = None
        if live:
            effective_llm = retained_live_configuration(
                paused,
                description="paused live run",
            )
            if not worker_execution and not live_lock.acquire(blocking=False):
                raise HTTPException(status_code=409, detail="another live run is already active")
        if live and not worker_execution:
            resume_document = {
                **paused,
                "status": "running",
                "pause_message": None,
            }
            runs.save(resume_document)
            pause = Event()
            stop = Event()
            with pause_lock:
                pause_requests[run_id] = pause
                stop_requests[run_id] = stop

            def execute_resume_worker() -> None:
                resume_live_worker_context.active = True
                try:
                    resume_run(run_id, request)
                except Exception as error:
                    try:
                        latest = runs.get(run_id)
                        runs.save(
                            {
                                **latest,
                                "status": "failed",
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                    finally:
                        with pause_lock:
                            pause_requests.pop(run_id, None)
                            stop_requests.pop(run_id, None)
                        if live_lock.locked():
                            live_lock.release()
                finally:
                    del resume_live_worker_context.active

            Thread(
                target=execute_resume_worker,
                name=f"cybernetic-live-resume-{run_id}",
                daemon=True,
            ).start()
            return JSONResponse(status_code=202, content=resume_document)

        if live:
            with pause_lock:
                resumed_pause = pause_requests.get(run_id)
                resumed_stop = stop_requests.get(run_id)
            if resumed_pause is None or resumed_stop is None:
                raise RuntimeError("resumed live worker lost its control handles")
            pause = resumed_pause
            stop = resumed_stop
        else:
            pause = Event()
            stop = Event()

        latest_resumed_checkpoint = checkpoint.model_copy(deep=True)

        def retain_checkpoint(checkpoint: ActiveRuntimeCheckpoint) -> None:
            nonlocal latest_resumed_checkpoint
            candidate = checkpoint.model_copy(deep=True)
            if _checkpoint_order(candidate) >= _checkpoint_order(
                latest_resumed_checkpoint
            ):
                latest_resumed_checkpoint = candidate
            with progress_lock:
                prior = runs.get(run_id)
                progress = prior.get("live_progress", [])
                if not isinstance(progress, list):
                    raise RuntimeError("retained live progress is malformed")
                runs.save(
                    {
                        **paused,
                        **_checkpoint_progress_projection(
                            latest_resumed_checkpoint
                        ),
                        "status": (
                            "stop_requested"
                            if stop.is_set()
                            else "pause_requested" if pause.is_set() else "running"
                        ),
                        "continuation": _checkpoint_continuation(
                            latest_resumed_checkpoint,
                            lifecycle="paused" if pause.is_set() else "running",
                        ),
                        "live_progress": progress,
                        "progress_sequence": len(progress),
                    }
                )

        run_control: ResolvedRunControlPlan | None = None
        if scenario == "service_desk":
            try:
                run_control = (
                    ResolvedRunControlPlan.model_validate(paused["run_control"])
                    if paused.get("run_control") is not None
                    else resolve_run_control(service_desk_run_control_options(), None)
                )
            except (TypeError, ValueError) as error:
                raise HTTPException(
                    status_code=422,
                    detail="retained run has an invalid run-control plan",
                ) from error
        try:
            if scenario == "service_desk":
                if arm is None or run_control is None:  # pragma: no cover - guarded
                    raise AssertionError("validated service-desk resume lacks inputs")
                service_profile = cast(ServiceDeskCognitionProfile, profile)
                fixture = service_desk_fixture(
                    arm,
                    cognition_profile=service_profile,
                    model=(
                        effective_llm.model if effective_llm else SERVICE_DESK_MODEL
                    ),
                    reasoning_effort=(
                        effective_llm.agent_reasoning_effort
                        if effective_llm
                        else SERVICE_DESK_SCAFFOLD_REASONING_EFFORT
                    ),
                )
                bindings = (
                    service_desk_native_bindings(
                        fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm
                    else service_desk_scripted_bindings(fixture)
                )
                resumed = run_event_driven_service_desk(
                    fixture,
                    bindings,
                    run_id=run_id,
                    checkpoint=checkpoint,
                    run_control=run_control,
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=lambda update, item: retain_progress(
                        run_id, update, item
                    ),
                    pause_requested=pause.is_set,
                    stop_requested=stop.is_set,
                )
                readout = event_driven_service_desk_outcome(resumed)
                document = build_service_desk_analyst_document(
                    fixture=fixture,
                    result=resumed,
                    readout=readout,
                    profile=service_profile,
                    arm_id=arm.arm_id,
                    execution="live" if live else "scripted",
                    created_at=str(paused["created_at"]),
                )
                document["run_control"] = run_control.model_dump(mode="json")
            else:
                if coordination_contract is None:  # pragma: no cover - guarded
                    raise AssertionError("validated coordination resume lacks contract")
                coordination_fixture = coordination_runtime_fixture(
                    coordination_contract,
                    model=(effective_llm.model if effective_llm else None),
                    reasoning_effort=(
                        effective_llm.agent_reasoning_effort
                        if effective_llm
                        else None
                    ),
                )
                coordination_bindings = (
                    coordination_native_bindings(
                        coordination_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm
                    else coordination_scripted_bindings(coordination_fixture)
                )
                resumed = run_coordination(
                    coordination_fixture,
                    coordination_bindings,
                    run_id=run_id,
                    checkpoint=checkpoint,
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=(
                        (
                            lambda update, item: retain_progress(
                                run_id,
                                update,
                                item,
                                initial_state=(
                                    coordination_fixture.scenario.initial_state
                                ),
                                analytical_boundaries=(
                                    coordination_fixture.scenario.analytical_boundaries
                                ),
                            )
                        )
                        if live
                        else (lambda _update, item: retain_checkpoint(item))
                    ),
                    pause_requested=pause.is_set,
                    stop_requested=stop.is_set,
                )
                outcome, headline, summary = _coordination_outcome(resumed)
                document = build_analyst_document(
                    initial_state=coordination_fixture.scenario.initial_state,
                    analytical_boundaries=(
                        coordination_fixture.scenario.analytical_boundaries
                    ),
                    result=resumed,
                    scenario="coordination_decision",
                    profile=str(profile),
                    arm_id=coordination_contract.condition.condition,
                    execution="live" if live else "scripted",
                    created_at=str(paused["created_at"]),
                    outcome=outcome,
                    headline=headline,
                    summary=summary,
                    include_boundary_activity=True,
                )
                document["run_control"] = coordination_run_control_plan(
                    coordination_fixture
                ).model_dump(mode="json")
            document["llm_configuration"] = paused.get("llm_configuration")
            document["completion"] = (
                resumed.completion.model_dump(mode="json")
                if resumed.completion is not None
                else None
            )
            document["continuation"] = {
                "schema_version": 1,
                "phase": "causal",
                "lifecycle": "completed_from_checkpoint",
                "checkpoint_digest": checkpoint.record_digest,
            }
            narrated = _attach_narration(
                document,
                live=live,
                run_id=run_id,
                effective_llm=effective_llm,
            )
            if scenario == "coordination_decision" and not live:
                narrated["narration"] = _coordination_reference_narration(narrated)
            narrated = retain_progress_history(narrated, run_id)
            if scenario == "coordination_decision" and live:
                if effective_llm is None:  # pragma: no cover - validated above
                    raise AssertionError("live coordination resume lacks LLM config")
                return retain_live_coordination_measurement(
                    narrated,
                    resumed,
                    effective_llm,
                )
            return runs.save(narrated)
        except (RuntimePaused, CoordinationRuntimePaused) as paused_error:
            paused_document = {
                **paused,
                "status": "paused",
                "pause_message": "Paused after a completed causal step.",
                **_checkpoint_progress_projection(paused_error.checkpoint),
                "continuation": _checkpoint_continuation(
                    paused_error.checkpoint, lifecycle="paused"
                ),
            }
            return runs.save(retain_progress_history(paused_document, run_id))
        except Exception as error:
            latest = runs.get(run_id)
            failed = {
                **latest,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            retained = runs.save(retain_progress_history(failed, run_id))
            if worker_execution:
                return retained
            raise
        finally:
            if live:
                with pause_lock:
                    pause_requests.pop(run_id, None)
                    stop_requests.pop(run_id, None)
            if live and worker_execution:
                live_lock.release()

    @app.post("/api/runs", response_model=None)
    def run(request_body: RunRequest, request: Request) -> dict[str, object] | Response:
        _require_access(request)
        if (
            request_body.scenario != "regional_outbreak"
            and request_body.regional_outbreak_configuration is not None
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "regional_outbreak_configuration applies only to the "
                    "regional_outbreak scenario"
                ),
            )
        service_arm = None
        physical_arm = None
        purchase_arm = None
        coordination_contract = None
        coordination_fixture: CoordinationRuntimeFixture | None = None
        coordination_experiment_condition: LiveCoordinationProbeCondition | None = None
        outbreak_condition: OutbreakCondition | None = None
        outbreak_runtime: OutbreakFixture | None = None
        resolved_run_control: ResolvedRunControlPlan | None = None
        selected_profile: str = request_body.cognition_profile
        if request_body.scenario == "service_desk":
            service_arm = next(
                (
                    item
                    for item in service_desk_arm_configurations()
                    if item.arm_id == request_body.arm_id
                ),
                None,
            )
            if service_arm is None:
                raise HTTPException(
                    status_code=422,
                    detail="unknown service-desk intervention arm",
                )
            try:
                resolved_run_control = resolve_run_control(
                    service_desk_run_control_options(), request_body.run_control
                )
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        elif request_body.scenario == "physical_access":
            physical_arm = next(
                (
                    item
                    for item in physical_access_arm_configurations()
                    if item.arm_id == request_body.arm_id
                ),
                None,
            )
            if physical_arm is None:
                raise HTTPException(
                    status_code=422,
                    detail="unknown physical-access intervention arm",
                )
            selected_profile = "position_context"
        elif request_body.scenario == "purchase_payment":
            purchase_arm = next(
                (
                    item
                    for item in purchase_payment_arm_configurations()
                    if item.arm_id == request_body.arm_id
                ),
                None,
            )
            if purchase_arm is None:
                raise HTTPException(
                    status_code=422,
                    detail="unknown purchase-payment intervention arm",
                )
            selected_profile = "position_context"
        elif request_body.scenario == "coordination_decision":
            try:
                coordination_contract = _coordination_contract(request_body.arm_id)
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            coordination_fixture = coordination_runtime_fixture(coordination_contract)
            if request_body.arm_id in LIVE_COORDINATION_PROBE_CONDITIONS:
                coordination_experiment_condition = request_body.arm_id
            resolved_run_control = coordination_run_control_plan(
                coordination_fixture
            )
            selected_profile = "position_context"
        else:
            if request_body.arm_id not in {
                "baseline",
                "responsive_exercise_injects",
                "capacity_inject_replay_with_stabilization",
                "adaptive_cso_stabilization",
                "threshold_managed_evasion",
            }:
                raise HTTPException(
                    status_code=422,
                    detail="unknown regional-outbreak condition",
                )
            outbreak_condition = cast(OutbreakCondition, request_body.arm_id)
            outbreak_runtime = regional_outbreak_fixture(
                outbreak_condition,
                configuration=request_body.regional_outbreak_configuration,
            )
            selected_profile = "position_context"
        if request_body.scenario != "service_desk" and request_body.run_control is not None:
            raise HTTPException(
                status_code=422,
                detail="run_control is not available for this scenario",
            )
        live = request_body.execution == "live"
        if (
            request_body.scenario in {"coordination_decision", "regional_outbreak"}
            and not live
            and not allow_internal_scripted_coordination
        ):
            raise HTTPException(
                status_code=422,
                detail=(
                    "coordination scenarios require live agent execution; "
                    "scripted people are internal verification fixtures"
                ),
            )
        if not live and request_body.llm_options is not None:
            raise HTTPException(
                status_code=422,
                detail="llm_options apply only to live execution",
            )
        if live and os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        effective_llm: EffectiveRunLlmConfiguration | None = None
        if live:
            try:
                effective_llm = resolve_live_configuration(
                    request_body.llm_options
                )
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            if (
                request_body.scenario in {"coordination_decision", "regional_outbreak"}
                and effective_llm.model not in coordination_live_model_ids()
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "the selected model is not currently certified for all "
                        "coordination participant schemas"
                    ),
                )
        run_id = request_body.run_id or f"run_{uuid4().hex[:12]}"
        worker_execution = live and bool(
            getattr(live_worker_context, "active", False)
        )
        if not worker_execution:
            try:
                runs.get(run_id)
            except RunNotFoundError:
                pass
            except InvalidRunIdError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
            else:
                raise HTTPException(status_code=409, detail="run ID already exists")
        lock_acquired = (
            True
            if worker_execution
            else live and live_lock.acquire(blocking=False)
        )
        if live and not lock_acquired:
            raise HTTPException(
                status_code=409,
                detail="another live run is already active",
            )

        if worker_execution:
            try:
                initial = runs.get(run_id)
            except (InvalidRunIdError, RunNotFoundError, RunCorruptError) as error:
                raise RuntimeError("live worker could not reopen its retained run") from error
            created_at = str(initial["created_at"])
            with pause_lock:
                pause = pause_requests.get(run_id)
                stop = stop_requests.get(run_id)
            if pause is None or stop is None:
                raise RuntimeError("live worker lost its control handles")
        else:
            created_at = now_iso()
            initial = {
                "run_id": run_id,
                "created_at": created_at,
                "status": "running",
                "scenario": request_body.scenario,
                "profile": selected_profile,
                "arm": request_body.arm_id,
                "execution": request_body.execution,
                "model_calls": 0,
                "cost": 0.0,
                "llm_configuration": (
                    effective_llm.model_dump(mode="json")
                    if effective_llm is not None
                    else None
                ),
                "run_control": (
                    resolved_run_control.model_dump(mode="json")
                    if resolved_run_control is not None
                    else None
                ),
                "regional_outbreak_configuration": (
                    request_body.regional_outbreak_configuration.model_dump(mode="json")
                    if request_body.regional_outbreak_configuration is not None
                    else default_outbreak_configuration().model_dump(mode="json")
                    if request_body.scenario == "regional_outbreak"
                    else None
                ),
                "live_progress": [],
                "progress_sequence": 0,
            }
            runs.save(initial)
            pause = Event()
            stop = Event()
            with pause_lock:
                pause_requests[run_id] = pause
                stop_requests[run_id] = stop
        latest_checkpoint: ActiveRuntimeCheckpoint | None = None

        def retain_checkpoint(checkpoint: ActiveRuntimeCheckpoint) -> None:
            nonlocal latest_checkpoint
            candidate = checkpoint.model_copy(deep=True)
            if latest_checkpoint is None or _checkpoint_order(
                candidate
            ) >= _checkpoint_order(latest_checkpoint):
                latest_checkpoint = candidate
            with progress_lock:
                prior = runs.get(run_id)
                progress = prior.get("live_progress", [])
                if not isinstance(progress, list):
                    raise RuntimeError("retained live progress is malformed")
                runs.save(
                    {
                        **initial,
                        **_checkpoint_progress_projection(latest_checkpoint),
                        "continuation": _checkpoint_continuation(
                            latest_checkpoint,
                            lifecycle="paused" if pause.is_set() else "running",
                        ),
                        "status": (
                            "stop_requested"
                            if stop.is_set()
                            else "pause_requested" if pause.is_set() else "running"
                        ),
                        "live_progress": progress,
                        "progress_sequence": len(progress),
                    }
                )

        if live and not worker_execution:
            worker_body = request_body.model_copy(update={"run_id": run_id})

            def execute_live_worker() -> None:
                live_worker_context.active = True
                try:
                    run(worker_body, request)
                except Exception as error:
                    # Normal execution records its own failures.  This guard
                    # covers only setup failures before that contract begins.
                    try:
                        runs.save(
                            {
                                **initial,
                                "status": "failed",
                                "error": f"{type(error).__name__}: {error}",
                            }
                        )
                    finally:
                        with pause_lock:
                            pause_requests.pop(run_id, None)
                            stop_requests.pop(run_id, None)
                        if live_lock.locked():
                            live_lock.release()
                finally:
                    del live_worker_context.active

            Thread(
                target=execute_live_worker,
                name=f"cybernetic-live-{run_id}",
                daemon=True,
            ).start()
            return JSONResponse(status_code=202, content=initial)

        try:
            if service_arm is not None:
                assert resolved_run_control is not None
                service_fixture = service_desk_fixture(
                    service_arm,
                    cognition_profile=request_body.cognition_profile,
                    model=(
                        effective_llm.model
                        if effective_llm is not None
                        else PHYSICAL_ACCESS_MODEL
                    ),
                    reasoning_effort=(
                        effective_llm.agent_reasoning_effort
                        if effective_llm is not None
                        else PHYSICAL_ACCESS_REASONING_EFFORT
                    ),
                )
                service_bindings = (
                    service_desk_native_bindings(
                        service_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm is not None
                    else service_desk_scripted_bindings(service_fixture)
                )
                result = run_event_driven_service_desk(
                    service_fixture,
                    service_bindings,
                    run_id=run_id,
                    runtime_config=(
                        service_desk_runtime_config(
                            per_run_budget=effective_llm.max_total_cost
                        )
                        if effective_llm is not None
                        else None
                    ),
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id, update, checkpoint
                    ),
                    pause_requested=pause.is_set,
                    stop_requested=stop.is_set,
                    run_control=resolved_run_control,
                )
                readout = event_driven_service_desk_outcome(result)
                document = build_service_desk_analyst_document(
                    fixture=service_fixture,
                    result=result,
                    readout=readout,
                    profile=request_body.cognition_profile,
                    arm_id=service_arm.arm_id,
                    execution=request_body.execution,
                    created_at=created_at,
                )
                document["run_control"] = resolved_run_control.model_dump(mode="json")
                document["completion"] = (
                    result.completion.model_dump(mode="json")
                    if result.completion is not None
                    else None
                )
            elif physical_arm is not None:
                physical_fixture = physical_access_fixture(
                    physical_arm,
                    model=(
                        effective_llm.model
                        if effective_llm is not None
                        else PURCHASE_PAYMENT_MODEL
                    ),
                    reasoning_effort=(
                        effective_llm.agent_reasoning_effort
                        if effective_llm is not None
                        else PURCHASE_PAYMENT_REASONING_EFFORT
                    ),
                )
                physical_bindings = (
                    physical_access_native_bindings(
                        physical_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm is not None
                    else physical_access_scripted_bindings(physical_fixture)
                )
                result = run_physical_access(
                    physical_fixture,
                    physical_bindings,
                    run_id=run_id,
                    runtime_config=(
                        physical_access_runtime_config(
                            per_run_budget=effective_llm.max_total_cost
                        )
                        if effective_llm is not None
                        else None
                    ),
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id, update, checkpoint
                    ),
                )
                physical_readout = build_physical_access_readout(result)
                headline, summary = physical_access_summary(physical_readout)
                document = build_analyst_document(
                    initial_state=physical_fixture.scenario.initial_state,
                    analytical_boundaries=(
                        physical_fixture.scenario.analytical_boundaries
                    ),
                    result=result,
                    scenario="physical_access",
                    profile=selected_profile,
                    arm_id=physical_arm.arm_id,
                    execution=request_body.execution,
                    created_at=created_at,
                    outcome=physical_readout.model_dump(mode="json"),
                    headline=headline,
                    summary=summary,
                )
            elif purchase_arm is not None:
                purchase_fixture = purchase_payment_fixture(
                    purchase_arm,
                    model=(
                        effective_llm.model
                        if effective_llm is not None
                        else SERVICE_DESK_MODEL
                    ),
                    reasoning_effort=(
                        effective_llm.agent_reasoning_effort
                        if effective_llm is not None
                        else SERVICE_DESK_SCAFFOLD_REASONING_EFFORT
                    ),
                )
                purchase_bindings = (
                    purchase_payment_native_bindings(
                        purchase_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm is not None
                    else purchase_payment_scripted_bindings(purchase_fixture)
                )
                result = run_purchase_payment(
                    purchase_fixture,
                    purchase_bindings,
                    run_id=run_id,
                    runtime_config=(
                        purchase_payment_runtime_config(
                            per_run_budget=effective_llm.max_total_cost
                        )
                        if effective_llm is not None
                        else None
                    ),
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id, update, checkpoint
                    ),
                )
                purchase_readout = build_purchase_payment_readout(result)
                headline, summary = purchase_payment_summary(
                    purchase_readout
                )
                document = build_analyst_document(
                    initial_state=purchase_fixture.scenario.initial_state,
                    analytical_boundaries=(
                        purchase_fixture.scenario.analytical_boundaries
                    ),
                    result=result,
                    scenario="purchase_payment",
                    profile=selected_profile,
                    arm_id=purchase_arm.arm_id,
                    execution=request_body.execution,
                    created_at=created_at,
                    outcome=purchase_readout.model_dump(mode="json"),
                    headline=headline,
                    summary=summary,
                )
            elif outbreak_runtime is not None:
                if effective_llm is None:  # pragma: no cover - live-only validation
                    raise AssertionError("regional outbreak run lacks LLM config")
                outbreak_runtime = regional_outbreak_fixture(
                    cast(OutbreakCondition, outbreak_condition),
                    model=effective_llm.model,
                    reasoning_effort=effective_llm.agent_reasoning_effort,
                    configuration=request_body.regional_outbreak_configuration,
                )
                result = run_outbreak(
                    outbreak_runtime,
                    outbreak_bindings(
                        outbreak_runtime,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    ),
                    run_id=run_id,
                    runtime_config=outbreak_runtime_config(
                        per_call_budget=effective_llm.participant_per_call_ceiling,
                        per_run_budget=effective_llm.max_total_cost,
                    ),
                    checkpoint_observer=retain_checkpoint,
                    progress_observer=lambda update, checkpoint: retain_progress(
                        run_id,
                        update,
                        checkpoint,
                        initial_state=outbreak_runtime.scenario.initial_state,
                        analytical_boundaries=(
                            outbreak_runtime.scenario.analytical_boundaries
                        ),
                    ),
                )
                outbreak_outcome, headline, summary = outbreak_readout(result)
                document = build_analyst_document(
                    initial_state=outbreak_runtime.scenario.initial_state,
                    analytical_boundaries=(
                        outbreak_runtime.scenario.analytical_boundaries
                    ),
                    result=result,
                    scenario="regional_outbreak",
                    profile=selected_profile,
                    arm_id=cast(str, outbreak_condition),
                    execution=request_body.execution,
                    created_at=created_at,
                    outcome=outbreak_outcome,
                    headline=headline,
                    summary=summary,
                    include_boundary_activity=True,
                )
                document["completion"] = (
                    result.completion.model_dump(mode="json")
                    if result.completion is not None
                    else None
                )
                document["regional_outbreak_configuration"] = (
                    outbreak_runtime.configuration.model_dump(mode="json")
                )
            elif coordination_fixture is not None:
                live_experiment_fixture: CoordinationExperimentRuntimeFixture | None = None
                if (
                    effective_llm is not None
                    and coordination_experiment_condition is not None
                ):
                    live_experiment_fixture = coordination_live_probe_fixture(
                        coordination_experiment_condition,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    coordination_fixture = live_experiment_fixture.runtime
                elif effective_llm is not None:
                    coordination_fixture = coordination_runtime_fixture(
                        coordination_fixture.contract,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                coordination_bindings = (
                    coordination_live_probe_bindings(
                        live_experiment_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if (
                        effective_llm is not None
                        and live_experiment_fixture is not None
                    )
                    else coordination_native_bindings(
                        coordination_fixture,
                        trace_id_prefix=run_id,
                        model=effective_llm.model,
                        reasoning_effort=effective_llm.agent_reasoning_effort,
                    )
                    if effective_llm is not None
                    else coordination_scripted_bindings(coordination_fixture)
                )
                result = run_coordination(
                    coordination_fixture,
                    coordination_bindings,
                    run_id=run_id,
                    runtime_config=(
                        coordination_runtime_config(
                            per_call_budget=(
                                effective_llm.participant_per_call_ceiling
                            ),
                            per_run_budget=effective_llm.max_total_cost
                        )
                        if effective_llm is not None
                        else None
                    ),
                    checkpoint_observer=retain_checkpoint,
                    pause_requested=pause.is_set,
                    stop_requested=stop.is_set,
                    progress_observer=(
                        (
                            lambda update, checkpoint: retain_progress(
                                run_id,
                                update,
                                checkpoint,
                                initial_state=(
                                    coordination_fixture.scenario.initial_state
                                ),
                                analytical_boundaries=(
                                    coordination_fixture.scenario.analytical_boundaries
                                ),
                            )
                        )
                        if live
                        else (
                            lambda _update, checkpoint: retain_checkpoint(checkpoint)
                        )
                    ),
                )
                coordination_outcome, headline, summary = _coordination_outcome(
                    result
                )
                document = build_analyst_document(
                    initial_state=coordination_fixture.scenario.initial_state,
                    analytical_boundaries=(
                        coordination_fixture.scenario.analytical_boundaries
                    ),
                    result=result,
                    scenario="coordination_decision",
                    profile=selected_profile,
                    arm_id=(
                        coordination_experiment_condition
                        or coordination_fixture.contract.condition.condition
                    ),
                    execution=request_body.execution,
                    created_at=created_at,
                    outcome=coordination_outcome,
                    headline=headline,
                    summary=summary,
                    include_boundary_activity=True,
                )
                document["run_control"] = coordination_run_control_plan(
                    coordination_fixture
                ).model_dump(mode="json")
                document["completion"] = (
                    result.completion.model_dump(mode="json")
                    if result.completion is not None
                    else None
                )
            else:
                raise RuntimeError("validated request has no scenario arm")
            narrated = _attach_narration(
                document,
                live=live and outbreak_runtime is None,
                run_id=run_id,
                effective_llm=effective_llm,
            )
            if coordination_fixture is not None and not live:
                narrated["narration"] = _coordination_reference_narration(
                    narrated
                )
            narrated = retain_progress_history(narrated, run_id)
            narrated["llm_configuration"] = initial["llm_configuration"]
            narrated["model_call_summaries"] = _result_call_summaries(result)
            if coordination_fixture is not None and live:
                if effective_llm is None:  # pragma: no cover - validated above
                    raise AssertionError("live coordination run lacks LLM config")
                return retain_live_coordination_measurement(
                    narrated,
                    result,
                    effective_llm,
                )
            return runs.save(narrated)
        except (RuntimePaused, CoordinationRuntimePaused) as paused_error:
            paused_document = {**initial, "status": "paused", "pause_message": "Paused after a completed causal step.", **_checkpoint_progress_projection(paused_error.checkpoint), "continuation": _checkpoint_continuation(paused_error.checkpoint, lifecycle="paused")}
            return runs.save(retain_progress_history(paused_document, run_id))
        except Exception as error:
            # Keep terminal status and lock availability coherent for a
            # polling operator: once failure is visible, another worker may
            # start. The finally block observes the cleared ownership.
            if worker_execution and lock_acquired:
                live_lock.release()
                lock_acquired = False
            retained_before_failure = runs.get(run_id)
            retained_continuation = retained_before_failure.get("continuation")
            failure_candidates = (
                [latest_checkpoint] if latest_checkpoint is not None else []
            )
            if isinstance(retained_continuation, dict) and isinstance(
                retained_continuation.get("checkpoint"), dict
            ):
                failure_candidates.append(
                    ActiveRuntimeCheckpoint.model_validate(
                        retained_continuation["checkpoint"]
                    )
                )
            failure_checkpoint = (
                max(
                    failure_candidates,
                    key=lambda item: (
                        item.next_attempt_index,
                        item.next_commit_index,
                    ),
                )
                if failure_candidates
                else None
            )
            failed = {
                **initial,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
                **_checkpoint_failure_projection(failure_checkpoint),
                **(
                    {
                        "continuation": _checkpoint_continuation(
                            failure_checkpoint,
                            lifecycle="interrupted",
                        )
                    }
                    if failure_checkpoint is not None
                    else {}
                ),
            }
            retained_failed = runs.save(retain_progress_history(failed, run_id))
            if worker_execution:
                return retained_failed
            raise HTTPException(
                status_code=500,
                detail="simulation failed; retained for inspection",
            ) from error
        finally:
            with pause_lock:
                pause_requests.pop(run_id, None)
                stop_requests.pop(run_id, None)
            if lock_acquired:
                live_lock.release()

    app.mount("/assets", StaticFiles(directory=root), name="assets")

    @app.get("/review")
    def review_dossier() -> FileResponse:
        return FileResponse(root / "review.html")

    @app.get("/review/trace")
    def review_trace() -> FileResponse:
        return FileResponse(root / "simulation-trace.md", media_type="text/markdown")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(root / "index.html")

    return app


def _allowed_tailscale_users() -> set[str]:
    configured = os.getenv("CYBERNETIC_INFLUENCE_ALLOWED_TAILSCALE_USERS", "")
    return {item.strip().lower() for item in configured.split(",") if item.strip()}


def _require_access(request: Request) -> None:
    allowed = _allowed_tailscale_users()
    if not allowed:
        return
    identity = request.headers.get("Tailscale-User-Login", "").strip().lower()
    if identity not in allowed:
        raise HTTPException(status_code=403, detail="operator identity is not authorized")


app = create_app()


def _attach_narration(
    document: dict[str, object],
    *,
    live: bool,
    run_id: str,
    effective_llm: EffectiveRunLlmConfiguration | None,
) -> dict[str, object]:
    """Add costed causal-moment narration without changing causal evidence."""
    narrated = dict(document)
    narration = (
        narrate_live_moments(
            narrated,
            model=effective_llm.model,
            trace_id_prefix=run_id,
            max_total_cost=max(
                0.0,
                effective_llm.max_total_cost
                - _nonnegative_float(narrated.get("cost")),
            ),
            max_calls=effective_llm.maximum_narrator_calls,
            reasoning_effort=effective_llm.narrator_reasoning_effort,
        )
        if live and effective_llm is not None
        else reference_narration()
    )
    agent_calls = _nonnegative_int(
        narrated.get("agent_model_calls", narrated.get("model_calls"))
    )
    agent_cost = _nonnegative_float(
        narrated.get("agent_cost", narrated.get("cost"))
    )
    narration_calls = _nonnegative_int(narration.get("model_calls"))
    narration_cost = _nonnegative_float(narration.get("cost"))
    narrated["agent_model_calls"] = agent_calls
    narrated["narration_model_calls"] = narration_calls
    narrated["model_calls"] = agent_calls + narration_calls
    narrated["agent_cost"] = agent_cost
    narrated["narration_cost"] = narration_cost
    narrated["cost"] = agent_cost + narration_cost
    narrated["cost_fully_observable"] = bool(
        narrated.get("cost_fully_observable", True)
    ) and bool(narration.get("cost_fully_observable", True))
    narrated["narration"] = narration
    return narrated


def _result_call_summaries(result: object) -> list[dict[str, object]]:
    attempts = getattr(result, "attempts", ())
    return _attempt_call_summaries(attempts)


def _error_call_summaries(error: Exception) -> list[dict[str, object]]:
    """Project directly attached provider evidence from a failed activation."""

    summaries: list[dict[str, object]] = []
    for call in getattr(error, "call_evidence", ()):
        summaries.append(
            {
                "status": getattr(call, "status", "failed"),
                "trace_id": getattr(call, "trace_id", ""),
                "model": getattr(call, "model", ""),
                "task": getattr(call, "task", ""),
                "reasoning_effort": getattr(call, "reasoning_effort", None),
                "cost": getattr(call, "cost", None),
                "cost_source": getattr(call, "cost_source", "unavailable"),
                "error_type": getattr(call, "error_type", None),
                "error_message": getattr(call, "error_message", None),
            }
        )
    return summaries


def _attempt_call_summaries(attempts: object) -> list[dict[str, object]]:
    summaries: list[dict[str, object]] = []
    if not isinstance(attempts, (list, tuple)):
        return summaries
    for attempt in attempts:
        for participant in getattr(attempt, "participants", ()):
            for call in getattr(participant, "call_evidence", ()):
                summaries.append(
                    {
                        key: value
                        for key, value in {
                            "status": call.status,
                            "trace_id": call.trace_id,
                            "model": call.model,
                            "task": call.task,
                            "reasoning_effort": call.reasoning_effort,
                            "cost": call.cost,
                            "cost_source": call.cost_source,
                            "cost_covers_all_attempts": (
                                call.cost_covers_all_attempts
                            ),
                            "error_type": call.error_type,
                            "error_message": call.error_message,
                        }.items()
                        if value is not None
                    }
                )
    return summaries


def _checkpoint_failure_projection(
    checkpoint: ActiveRuntimeCheckpoint | None,
) -> dict[str, object]:
    if checkpoint is None:
        return {
            "model_call_summaries": [],
            "failure_boundary": {"kind": "before_first_checkpoint"},
        }
    return {
        "model_calls": sum(
            len(participant.call_evidence)
            for attempt in checkpoint.attempts
            for participant in attempt.participants
        ),
        "cost": checkpoint.total_observed_cost,
        "cost_fully_observable": checkpoint.cost_fully_observable,
        "model_call_summaries": _attempt_call_summaries(checkpoint.attempts),
        "progress": {
            "completed_attempts": sum(
                attempt.status == "committed" for attempt in checkpoint.attempts
            ),
            "failed_attempts": sum(
                attempt.status == "failed" for attempt in checkpoint.attempts
            ),
            "logical_time": checkpoint.core_checkpoint.state.logical_time,
        },
        "failure_boundary": {
            "kind": "active_runtime",
            "attempt_index": checkpoint.next_attempt_index,
            "logical_time": checkpoint.core_checkpoint.state.logical_time,
        },
    }


def _checkpoint_order(checkpoint: ActiveRuntimeCheckpoint) -> tuple[int, int]:
    """Order retained prefixes without allowing a stale observer to regress one."""
    return checkpoint.next_attempt_index, checkpoint.next_commit_index


def _checkpoint_progress_projection(
    checkpoint: ActiveRuntimeCheckpoint,
) -> dict[str, object]:
    """Persist priced provider progress without manufacturing a partial world."""
    return {
        "model_calls": sum(
            len(participant.call_evidence)
            for attempt in checkpoint.attempts
            for participant in attempt.participants
        ),
        "cost": checkpoint.total_observed_cost,
        "cost_fully_observable": checkpoint.cost_fully_observable,
        "model_call_summaries": _attempt_call_summaries(checkpoint.attempts),
        "progress": {
            "completed_attempts": sum(
                attempt.status == "committed"
                for attempt in checkpoint.attempts
            ),
            "failed_attempts": sum(
                attempt.status == "failed"
                for attempt in checkpoint.attempts
            ),
            "logical_time": checkpoint.core_checkpoint.state.logical_time,
        },
    }


def _checkpoint_continuation(
    checkpoint: ActiveRuntimeCheckpoint,
    *,
    lifecycle: Literal["running", "paused", "interrupted"],
) -> dict[str, object]:
    """Persist the complete validated causal prefix, not only its summary.

    This is deliberately private run evidence.  It makes an interrupted prefix
    recoverable by the future controller while the analyst surface continues to
    receive only its redacted progress projection.
    """
    validated = ActiveRuntimeCheckpoint.model_validate(
        checkpoint.model_dump(mode="json")
    )
    return {
        "schema_version": 1,
        "phase": "causal",
        "lifecycle": lifecycle,
        "checkpoint": validated.model_dump(mode="json"),
        "checkpoint_digest": validated.record_digest,
    }


def _scenario_explanation(scenario: str) -> dict[str, object]:
    explanations: dict[str, dict[str, object]] = {
        "service_desk": {
            "help": "Inspect how information routes and exact gates shape one incident workflow.",
            "representation_summary": (
                "A customer cannot log in after resetting a password. The "
                "triager routes the report to a specialist, the system clears "
                "the stale login session, and the incident closes only after "
                "the customer confirms that access works."
            ),
            "assumptions": [
                "People act only from retained memory and delivered observations.",
                "Authentication, authorization, remediation, and closure are exact mechanisms.",
                "Process ticks order authored internal updates; they are not elapsed real-world seconds.",
            ],
            "known_omissions": [
                "The authored topology covers only the service-operations center and remote customer site; it does not model travel, building interiors, or network infrastructure in detail.",
                "The customer and broader organization are not active participants.",
                "The stipulated remediation abstracts away the underlying software stack.",
            ],
            "fidelity_questions": [
                "Did missing information cause a request or reroute rather than invented access?",
                "Did unsafe closure attempts fail at the exact mechanism?",
                "Do the narratives remain grounded in retained events?",
            ],
        },
        "physical_access": {
            "help": "Inspect proof, authorization, physical capability, crossing, and feedback separately.",
            "representation_summary": (
                "A person, credential proof, copied policy, access controller, "
                "physical latch, boundary, and observed crossing."
            ),
            "assumptions": [
                "Credential proof, policy authorization, latch operation, and movement are distinct.",
                "The technician acts only from retained or delivered information.",
            ],
            "known_omissions": [
                "No adversarial credential attack or tailgating is modeled.",
                "The building topology is intentionally small.",
            ],
            "fidelity_questions": [
                "Did location change only after the boundary opened?",
                "Did authorization remain distinct from physical capability?",
            ],
        },
        "purchase_payment": {
            "help": "Inspect human decisions, exact internal control, and a coarse external subsystem without conflating them.",
            "representation_summary": (
                "A purchase request moving through people, copied records, an "
                "exact internal control, and a deliberately coarse processor."
            ),
            "assumptions": [
                "People act from their positions, dispositions, memory, and delivered records.",
                "The internal approval control is exact; the external processor is coarse.",
            ],
            "known_omissions": [
                "The processor's internal organization and infrastructure are not modeled.",
                "No market, supplier, or accounting-period dynamics are included.",
            ],
            "fidelity_questions": [
                "Did policy evidence remain distinct from the exact control?",
                "Did the coarse processor avoid invented internal explanations?",
            ],
        },
        "coordination_decision": {
            "help": (
                "Inspect what enters and leaves a partnership boundary and how "
                "several people and exact mechanisms produce one decision path."
            ),
            "representation_summary": (
                "A five-person international team must decide whether to deploy a "
                "new public-health monitoring system. Each person is responsible for "
                "a different concern: technical reliability, government oversight, "
                "local safety, partner support, or keeping the decision on schedule."
            ),
            "assumptions": [
                "People act from retained dispositions, memories, delivered observations, and owned interfaces.",
                "Meetings occur daily on modeled days 0 through 3; unresolved decisions reach a day-4 fallback deadline.",
                "The partnership and pressure-source ensemble are analytical views, not additional actors.",
            ],
            "known_omissions": [
                "The live LLM people are synthetic roles, not validated models of particular people or institutions.",
                "The scenario represents one bounded decision and does not model broader institutions or geopolitics.",
            ],
            "fidelity_questions": [
                "Which outside information crossed into the partnership?",
                "Which people and exact mechanisms contributed before an output crossed back out?",
                "Was external acceptance retained separately from the partnership's attempted output?",
            ],
        },
        "regional_outbreak": {
            "help": (
                "Compare whether a multinational coalition preserves joint action "
                "when bounded autonomous sources introduce heterogeneous external signals."
            ),
            "representation_summary": (
                "Twenty-six autonomous synthetic roles across four countries and a regional "
                "institution make three successive compact decisions."
            ),
            "assumptions": [
                "Participant roles receive identical initial conditions across arms.",
                "Four source agents can emit only bounded external signals, not commands or participant stances.",
                "The exact decision rule requires thirteen executable-now support positions, twenty support or conditional positions, and at most two oppositions after round three.",
            ],
            "known_omissions": [
                "The synthetic roles are not validated models of real people or governments.",
                "A small synthetic replication set cannot establish a general causal effect.",
                "Epidemic transmission, media, and response implementation are outside this slice.",
            ],
            "fidelity_questions": [
                "Did participants remain autonomous while source agents changed only external information?",
                "Which risk and request patterns changed between rounds and conditions?",
                "Does the observed contrast warrant replicated runs or a larger coalition?",
            ],
        },
    }
    return explanations[scenario]


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _nonnegative_float(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else 0.0
