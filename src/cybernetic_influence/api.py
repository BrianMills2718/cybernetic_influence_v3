"""Operator-first API for retained, temporally inspectable simulator runs."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from cybernetic_influence import __version__
from cybernetic_influence.presentation import (
    build_analyst_document,
    build_service_desk_analyst_document,
    event_driven_service_desk_outcome,
)
from cybernetic_influence.narration import (
    narrate_live_moments,
    reference_narration,
)
from cybernetic_influence.run_store import (
    InvalidRunIdError,
    RunCorruptError,
    RunNotFoundError,
    RunStore,
    now_iso,
)
from cybernetic_influence.scenarios.service_desk import (
    SERVICE_DESK_MODEL,
    SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
    ServiceDeskCognitionProfile,
    run_event_driven_service_desk,
    service_desk_arm_configurations,
    service_desk_fixture,
    service_desk_native_bindings,
    service_desk_scripted_bindings,
)
from cybernetic_influence.scenarios.physical_access import (
    build_physical_access_readout,
    physical_access_arm_configurations,
    physical_access_fixture,
    physical_access_native_bindings,
    physical_access_scripted_bindings,
    physical_access_summary,
    run_physical_access,
)


class RunRequest(BaseModel):
    """One request from the closed PoC scenario catalog."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal["service_desk", "physical_access"] = "service_desk"
    cognition_profile: ServiceDeskCognitionProfile = "position_context"
    arm_id: str = "baseline"
    execution: Literal["scripted", "live"] = "scripted"


def create_app(web_root: Path | None = None, run_root: Path | None = None) -> FastAPI:
    """Create the visibility-safe API without any legacy workbench."""
    app = FastAPI(title="Cybernetic Influence Simulator", version=__version__)
    root = web_root or Path(__file__).resolve().parents[2] / "web"
    configured_run_root = os.getenv("CYBERNETIC_INFLUENCE_RUNS_DIR")
    runs = RunStore(
        run_root
        or (Path(configured_run_root) if configured_run_root else root.parent / "artifacts" / "runs")
    )
    runs.mark_incomplete_interrupted()
    live_lock = Lock()

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
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
        return {
            "version": __version__,
            "build_commit": os.getenv("CYBERNETIC_INFLUENCE_BUILD_COMMIT", "development"),
            "scenario": "service_desk",
            "scenarios": {
                "service_desk": {
                    "label": "Service desk",
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
            },
            "profiles": ["position_context", "procedural_control"],
            "arms": [arm.arm_id for arm in service_desk_arm_configurations()],
            "model": SERVICE_DESK_MODEL,
            "reasoning_effort": SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
            "live_authorized": os.getenv("CYBERNETIC_INFLUENCE_LIVE") == "1",
            "access_restricted": bool(_allowed_tailscale_users()),
            "scripted_cost": 0.0,
            "maximum_live_calls": 48,
            "maximum_live_cost": 0.74,
        }

    @app.get("/api/runs")
    def history(request: Request) -> dict[str, object]:
        _require_access(request)
        retained, corrupt = runs.list_runs()
        return {"runs": retained, "corrupt_files": corrupt}

    @app.get("/api/runs/{run_id}")
    def retained_run(run_id: str, request: Request) -> dict[str, object]:
        _require_access(request)
        try:
            return runs.get(run_id)
        except InvalidRunIdError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RunNotFoundError as error:
            raise HTTPException(status_code=404, detail="run not found") from error
        except RunCorruptError as error:
            raise HTTPException(status_code=409, detail="retained run is corrupt") from error

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

    @app.post("/api/runs")
    def run(request_body: RunRequest, request: Request) -> dict[str, object]:
        _require_access(request)
        service_arm = None
        physical_arm = None
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
        else:
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
        live = request_body.execution == "live"
        if live and os.getenv("CYBERNETIC_INFLUENCE_LIVE") != "1":
            raise HTTPException(
                status_code=403,
                detail="live execution requires CYBERNETIC_INFLUENCE_LIVE=1",
            )
        lock_acquired = live and live_lock.acquire(blocking=False)
        if live and not lock_acquired:
            raise HTTPException(
                status_code=409,
                detail="another live run is already active",
            )

        run_id = f"run_{uuid4().hex[:12]}"
        created_at = now_iso()
        initial: dict[str, object] = {
            "run_id": run_id,
            "created_at": created_at,
            "status": "running",
            "scenario": request_body.scenario,
            "profile": selected_profile,
            "arm": request_body.arm_id,
            "execution": request_body.execution,
            "model_calls": 0,
            "cost": 0.0,
        }
        runs.save(initial)
        try:
            if service_arm is not None:
                service_fixture = service_desk_fixture(
                    service_arm,
                    cognition_profile=request_body.cognition_profile,
                    reasoning_effort=SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
                )
                service_bindings = (
                    service_desk_native_bindings(
                        service_fixture,
                        trace_id_prefix=run_id,
                    )
                    if live
                    else service_desk_scripted_bindings(service_fixture)
                )
                result = run_event_driven_service_desk(
                    service_fixture,
                    service_bindings,
                    run_id=run_id,
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
            elif physical_arm is not None:
                physical_fixture = physical_access_fixture(physical_arm)
                physical_bindings = (
                    physical_access_native_bindings(
                        physical_fixture,
                        trace_id_prefix=run_id,
                    )
                    if live
                    else physical_access_scripted_bindings(physical_fixture)
                )
                result = run_physical_access(
                    physical_fixture,
                    physical_bindings,
                    run_id=run_id,
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
            else:
                raise RuntimeError("validated request has no scenario arm")
            narrated = _attach_narration(
                document,
                live=live,
                run_id=run_id,
            )
            return runs.save(narrated)
        except Exception as error:
            failed = {
                **initial,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
            runs.save(failed)
            raise HTTPException(
                status_code=500,
                detail="simulation failed; retained for inspection",
            ) from error
        finally:
            if lock_acquired:
                live_lock.release()

    app.mount("/assets", StaticFiles(directory=root), name="assets")

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
    document: dict[str, object], *, live: bool, run_id: str
) -> dict[str, object]:
    """Add costed causal-moment narration without changing causal evidence."""
    narrated = dict(document)
    narration = (
        narrate_live_moments(
            narrated,
            model=SERVICE_DESK_MODEL,
            trace_id_prefix=run_id,
        )
        if live
        else reference_narration()
    )
    agent_calls = _nonnegative_int(narrated.get("model_calls"))
    agent_cost = _nonnegative_float(narrated.get("cost"))
    narration_calls = _nonnegative_int(narration.get("model_calls"))
    narration_cost = _nonnegative_float(narration.get("cost"))
    narrated["agent_model_calls"] = agent_calls
    narrated["narration_model_calls"] = narration_calls
    narrated["model_calls"] = agent_calls + narration_calls
    narrated["agent_cost"] = agent_cost
    narrated["narration_cost"] = narration_cost
    narrated["cost"] = agent_cost + narration_cost
    narrated["narration"] = narration
    return narrated


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _nonnegative_float(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else 0.0
