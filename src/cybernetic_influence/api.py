"""Small operator-first API for the first complete simulator slice."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

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


class RunRequest(BaseModel):
    """One deliberately small service-desk run request."""

    model_config = ConfigDict(extra="forbid")

    cognition_profile: ServiceDeskCognitionProfile = "position_context"
    arm_id: ServiceDeskArmId = "baseline"
    execution: Literal["scripted", "live"] = "scripted"


def create_app(web_root: Path | None = None) -> FastAPI:
    """Create the API without importing any legacy workbench."""
    app = FastAPI(title="Cybernetic Influence Simulator", version="0.1.0")
    root = web_root or Path(__file__).resolve().parents[2] / "web"

    @app.get("/api/config")
    def config() -> dict[str, object]:
        return {
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
        fixture = service_desk_fixture(
            arm,
            cognition_profile=request.cognition_profile,
            reasoning_effort=SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
        )
        run_id = f"run_{uuid4().hex[:12]}"
        bindings = (
            service_desk_native_bindings(fixture, trace_id_prefix=run_id)
            if request.execution == "live"
            else service_desk_scripted_bindings(fixture)
        )
        result = run_service_desk(fixture, bindings, run_id=run_id)
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

        return {
            "run_id": run_id,
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
                "steps": [
                    event.summary
                    for event in result.core_result.events
                    if event.event_kind in {"action_attempted", "mechanism_decided", "state_changed"}
                ],
            },
            "outcome": readout.model_dump(mode="json"),
            "nodes": nodes,
            "edges": edges,
            "events": [
                event.model_dump(mode="json") for event in result.core_result.events
            ],
            "traces": traces,
        }

    app.mount("/assets", StaticFiles(directory=root), name="assets")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(root / "index.html")

    return app


app = create_app()
