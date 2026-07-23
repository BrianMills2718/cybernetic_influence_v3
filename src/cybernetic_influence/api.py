"""Operator-first API for retained, temporally inspectable simulator runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from cybernetic_influence import __version__
from cybernetic_influence.scenarios.service_desk import (
    SERVICE_DESK_MODEL,
    SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
    ServiceDeskArmId,
    ServiceDeskCognitionProfile,
    run_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_native_bindings,
    service_desk_scripted_bindings,
)
from cybernetic_influence.scenarios.service_desk_fidelity import (
    build_service_desk_trial_readout,
)
from cybernetic_influence.run_store import (
    InvalidRunIdError,
    RunNotFoundError,
    RunStore,
    now_iso,
)


class RunRequest(BaseModel):
    """One deliberately small service-desk run request."""

    model_config = ConfigDict(extra="forbid")

    cognition_profile: ServiceDeskCognitionProfile = "position_context"
    arm_id: ServiceDeskArmId = "baseline"
    execution: Literal["scripted", "live"] = "scripted"


def create_app(web_root: Path | None = None, run_root: Path | None = None) -> FastAPI:
    """Create the API without importing any legacy workbench."""
    app = FastAPI(title="Cybernetic Influence Simulator", version="0.2.0")
    root = web_root or Path(__file__).resolve().parents[2] / "web"
    configured_run_root = os.getenv("CYBERNETIC_INFLUENCE_RUNS_DIR")
    runs = RunStore(
        run_root
        or (Path(configured_run_root) if configured_run_root else root.parent / "artifacts" / "runs")
    )
    runs.mark_incomplete_interrupted()

    @app.get("/api/config")
    def config() -> dict[str, object]:
        return {
            "version": __version__,
            "build_commit": os.getenv("CYBERNETIC_INFLUENCE_BUILD_COMMIT", "development"),
            "scenario": "service_desk",
            "profiles": ["position_context", "procedural_control"],
            "arms": [arm.arm_id for arm in service_desk_arm_configurations()],
            "model": SERVICE_DESK_MODEL,
            "reasoning_effort": SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
            "live_authorized": os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1",
            "scripted_cost": 0.0,
            "maximum_live_calls": 9,
            "maximum_live_cost": 0.45,
        }

    @app.get("/api/runs")
    def history() -> dict[str, object]:
        retained, corrupt = runs.list_runs()
        return {"runs": retained, "corrupt_files": corrupt}

    @app.get("/api/runs/{run_id}")
    def retained_run(run_id: str) -> dict[str, object]:
        try:
            return runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error

    @app.delete("/api/runs/{run_id}")
    def delete_run(run_id: str) -> dict[str, object]:
        try:
            runs.trash(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        return {"run_id": run_id, "status": "trashed", "recoverable": True}

    @app.post("/api/runs")
    def run(request: RunRequest) -> dict[str, object]:
        arm = next(
            (item for item in service_desk_arm_configurations() if item.arm_id == request.arm_id),
            None,
        )
        if arm is None:
            raise HTTPException(status_code=422, detail="unknown intervention arm")
        if request.execution == "live" and os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        run_id = f"run_{uuid4().hex[:12]}"
        created_at = now_iso()
        initial: dict[str, object] = {
            "run_id": run_id,
            "created_at": created_at,
            "status": "running",
            "scenario": "service_desk",
            "profile": request.cognition_profile,
            "arm": request.arm_id,
            "execution": request.execution,
            "model_calls": 0,
            "cost": 0.0,
        }
        runs.save(initial)
        try:
            fixture = service_desk_fixture(
                arm,
                cognition_profile=request.cognition_profile,
                reasoning_effort=SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
            )
            bindings = (
                service_desk_native_bindings(fixture, trace_id_prefix=run_id)
                if request.execution == "live"
                else service_desk_scripted_bindings(fixture)
            )
            result = run_service_desk(fixture, bindings, run_id=run_id)
        except Exception as error:
            failed = {
                **initial,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            runs.save(failed)
            raise HTTPException(status_code=500, detail="simulation failed; retained for inspection") from error

        readout = build_service_desk_trial_readout(request.arm_id, 0, result)
        state = result.core_result.final_state

        nodes: list[dict[str, object]] = []
        for entity in state.entities.values():
            nodes.append(
                {
                    "id": entity.entity_id,
                    "kind": entity.entity_kind,
                    "label": entity.entity_id.replace("_", " ").title(),
                    "description": entity.description,
                    "state": entity.model_dump(mode="json")["attributes"],
                }
            )
        for representation in state.representations.values():
            nodes.append(
                {
                    "id": representation.representation_id,
                    "kind": "information",
                    "label": representation.representation_id.replace("_", " ").title(),
                    "description": representation.encoding,
                    "state": representation.model_dump(mode="json"),
                }
            )
        for mechanism in state.mechanisms.values():
            nodes.append(
                {
                    "id": mechanism.mechanism_id,
                    "kind": "mechanism",
                    "label": mechanism.mechanism_id.replace("_", " ").title(),
                    "description": mechanism.description,
                    "state": mechanism.model_dump(mode="json"),
                }
            )

        edges: list[dict[str, object]] = []
        for connection in state.connections.values():
            source = state.ports[connection.source_port_id].owner_ref
            target = state.ports[connection.target_port_id].owner_ref
            edges.append(
                {
                    "id": connection.connection_id,
                    "source": source,
                    "target": target,
                    "enabled": connection.enabled,
                    "description": connection.description,
                }
            )

        traces: list[dict[str, object]] = []
        for attempt in result.attempts:
            for participant in attempt.participants:
                traces.append(
                    {
                        "activation": attempt.activation_id,
                        "logical_time": attempt.logical_time,
                        "person": participant.requested_active_system_id,
                        "status": attempt.status,
                        "orientation": (
                            (
                                participant.call_evidence[-1].structured_output
                                or {}
                            ).get("orientation")
                            if participant.call_evidence
                            else "Scripted zero-cost reference action."
                        ),
                        "actions": [
                            action.model_dump(mode="json")
                            for action in (participant.proposal.actions if participant.proposal else [])
                        ],
                        "observations": [
                            observation.model_dump(mode="json")
                            for observation in participant.input.observations
                        ],
                    }
                )

        node_ids = {str(node["id"]) for node in nodes}
        timeline: list[dict[str, object]] = []
        for event in result.core_result.events:
            exact = event.model_dump(mode="json")
            focus_ids: set[str] = set()
            focus_edges: set[str] = set()
            for field in ("actor_entity_id", "mechanism_id", "representation_id"):
                value = exact.get(field)
                if isinstance(value, str) and value in node_ids:
                    focus_ids.add(value)
            connection_id = exact.get("connection_id")
            if isinstance(connection_id, str):
                focus_edges.add(connection_id)
                focused_connection = state.connections.get(connection_id)
                if focused_connection is not None:
                    focus_ids.add(state.ports[focused_connection.source_port_id].owner_ref)
                    focus_ids.add(state.ports[focused_connection.target_port_id].owner_ref)
            for field in ("source_port_id", "target_port_id"):
                port_id = exact.get(field)
                if isinstance(port_id, str) and port_id in state.ports:
                    focus_ids.add(state.ports[port_id].owner_ref)
            patch = exact.get("patch")
            if isinstance(patch, dict):
                for change in patch.get("fact_changes", []):
                    if isinstance(change, dict):
                        fact_id = change.get("fact_id")
                        if isinstance(fact_id, str) and fact_id.partition(".")[0] in node_ids:
                            focus_ids.add(fact_id.partition(".")[0])
                for observation in patch.get("observations_added", []):
                    if isinstance(observation, dict):
                        observation_target = observation.get("target_entity_id")
                        if isinstance(observation_target, str) and observation_target in node_ids:
                            focus_ids.add(observation_target)
            actor = exact.get("actor_entity_id")
            event_person = (
                actor
                if isinstance(actor, str)
                and actor in {"triager", "specialist", "supervisor"}
                else None
            )
            if event_person is None:
                people = focus_ids.intersection({"triager", "specialist", "supervisor"})
                event_person = sorted(people)[0] if len(people) == 1 else None
            timeline.append(
                {
                    "event_id": exact["event_id"],
                    "sequence": exact["sequence"],
                    "logical_time": exact["logical_time"],
                    "kind": exact["event_kind"],
                    "summary": exact["summary"],
                    "person": event_person,
                    "focus_ids": sorted(focus_ids),
                    "focus_edges": sorted(focus_edges),
                }
            )

        if request.arm_id == "no_direct_path":
            summary = (
                "The direct report path was unavailable. The specialist requested the missing "
                "details, the triager recorded them in the ticket, and remediation and confirmed "
                "closure happened later through that alternate route."
            )
        elif request.arm_id == "speed_priority":
            summary = (
                "Speed pressure led the supervisor to attempt closure early. The exact closure "
                "mechanism denied that attempt, then accepted closure after customer confirmation."
            )
        else:
            summary = (
                "The triager assigned the incident and delivered the customer report to the "
                "specialist. After remediation and recorded customer feedback, the supervisor "
                "closed the incident safely."
            )

        # The concise account stays at the human-action level; the adjacent
        # timeline exposes every route, exact decision, commit, and observation.
        story_kinds = {"action_attempted"}
        story_steps = [event for event in timeline if event["kind"] in story_kinds]
        document: dict[str, object] = {
            "run_id": run_id,
            "created_at": created_at,
            "status": result.status,
            "scenario": "service_desk",
            "profile": request.cognition_profile,
            "arm": request.arm_id,
            "execution": request.execution,
            "model_calls": result.model_calls,
            "cost": result.total_observed_cost,
            "cost_fully_observable": result.cost_fully_observable,
            "story": {
                "headline": readout.target_outcome.replace("_", " ").title(),
                "summary": summary,
                "steps": story_steps,
            },
            "outcome": readout.model_dump(mode="json"),
            "nodes": nodes,
            "edges": edges,
            "timeline": timeline,
            "events": [
                event.model_dump(mode="json") for event in result.core_result.events
            ],
            "traces": traces,
        }
        return runs.save(document)

    app.mount("/assets", StaticFiles(directory=root), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(root / "index.html")

    return app


app = create_app()
