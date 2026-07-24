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
from cybernetic_influence.active_runtime import (
    ActiveRuntimeCheckpoint,
)
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
from cybernetic_influence.run_configuration import (
    EffectiveRunLlmConfiguration,
    RunLlmOptions,
    live_options_contract,
    resolve_live_configuration,
)
from cybernetic_influence.scenarios.service_desk import (
    SERVICE_DESK_MODEL,
    SERVICE_DESK_SCAFFOLD_REASONING_EFFORT,
    ServiceDeskCognitionProfile,
    run_event_driven_service_desk,
    service_desk_runtime_config,
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


class RunRequest(BaseModel):
    """One request from the closed PoC scenario catalog."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal[
        "service_desk",
        "physical_access",
        "purchase_payment",
    ] = "service_desk"
    cognition_profile: ServiceDeskCognitionProfile = "position_context"
    arm_id: str = "baseline"
    execution: Literal["scripted", "live"] = "scripted"
    llm_options: RunLlmOptions | None = None


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
        live_options = live_options_contract()
        return {
            "version": __version__,
            "build_commit": os.getenv("CYBERNETIC_INFLUENCE_BUILD_COMMIT", "development"),
            "scenario": "service_desk",
            "scenarios": {
                "service_desk": {
                    "label": "Service desk",
                    **_scenario_explanation("service_desk"),
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
            "live_options": live_options,
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
        purchase_arm = None
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
        else:
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
        live = request_body.execution == "live"
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
            "llm_configuration": (
                effective_llm.model_dump(mode="json")
                if effective_llm is not None
                else None
            ),
        }
        runs.save(initial)
        latest_checkpoint: ActiveRuntimeCheckpoint | None = None

        def retain_checkpoint(checkpoint: ActiveRuntimeCheckpoint) -> None:
            nonlocal latest_checkpoint
            latest_checkpoint = checkpoint.model_copy(deep=True)
            runs.save(
                {
                    **initial,
                    **_checkpoint_progress_projection(latest_checkpoint),
                }
            )

        try:
            if service_arm is not None:
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
            else:
                raise RuntimeError("validated request has no scenario arm")
            narrated = _attach_narration(
                document,
                live=live,
                run_id=run_id,
                effective_llm=effective_llm,
            )
            narrated["llm_configuration"] = initial["llm_configuration"]
            narrated["model_call_summaries"] = _result_call_summaries(result)
            return runs.save(narrated)
        except Exception as error:
            failed = {
                **initial,
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
                **_checkpoint_failure_projection(latest_checkpoint),
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
            reasoning_effort=effective_llm.narrator_reasoning_effort,
        )
        if live and effective_llm is not None
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


def _result_call_summaries(result: object) -> list[dict[str, object]]:
    attempts = getattr(result, "attempts", ())
    return _attempt_call_summaries(attempts)


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
        "failure_boundary": {
            "kind": "active_runtime",
            "attempt_index": checkpoint.next_attempt_index,
            "logical_time": checkpoint.core_checkpoint.state.logical_time,
        },
    }


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
                "Logical seconds express process cadence, not wall-clock duration.",
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
    }
    return explanations[scenario]


def _nonnegative_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _nonnegative_float(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else 0.0
