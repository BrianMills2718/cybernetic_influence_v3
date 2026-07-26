"""Typed, scenario-compiled stopping controls for active simulator runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from cybernetic_influence.causal_core.models import CausalState


_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class _StrictModel(BaseModel):
    model_config = _FORBID


class ExactFactTerminalCondition(_StrictModel):
    kind: Literal["fact_equals"] = "fact_equals"
    condition_id: str = Field(pattern=_ID_PATTERN)
    fact_id: str = Field(min_length=1)
    expected_value: JsonValue
    public_description: str = Field(min_length=1)


class ModeledTimeHorizon(_StrictModel):
    kind: Literal["modeled_time_horizon"] = "modeled_time_horizon"
    logical_time: int = Field(ge=0)
    public_description: str = Field(min_length=1)


class RunControlOptions(_StrictModel):
    available_terminal_conditions: list[ExactFactTerminalCondition] = Field(min_length=1)
    default_terminal_condition_ids: list[str] = Field(min_length=1)
    allowed_terminal_modes: list[Literal["any", "all"]] = Field(min_length=1)
    minimum_horizon: int | None = Field(default=None, ge=0)
    default_horizon: int | None = Field(default=None, ge=0)
    maximum_horizon: int | None = Field(default=None, ge=0)
    max_causal_moments_cap: int = Field(ge=1)
    max_participant_calls_cap: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_options(self) -> "RunControlOptions":
        ids = [item.condition_id for item in self.available_terminal_conditions]
        if len(ids) != len(set(ids)):
            raise ValueError("terminal condition ids must be unique")
        if not set(self.default_terminal_condition_ids) <= set(ids):
            raise ValueError("default terminal condition is not available")
        if len(self.default_terminal_condition_ids) != len(set(self.default_terminal_condition_ids)):
            raise ValueError("default terminal condition ids must be unique")
        bounds = (self.minimum_horizon, self.default_horizon, self.maximum_horizon)
        if any(value is not None for value in bounds) and any(value is None for value in bounds):
            raise ValueError("horizon bounds require minimum, default, and maximum")
        if self.minimum_horizon is not None:
            assert self.default_horizon is not None
            assert self.maximum_horizon is not None
            if not self.minimum_horizon <= self.default_horizon <= self.maximum_horizon:
                raise ValueError("horizon bounds are not ordered")
        return self


class RunControlSelection(_StrictModel):
    terminal_condition_ids: list[str] = Field(default_factory=list)
    terminal_mode: Literal["any", "all"] = "any"
    modeled_time_horizon: int | None = Field(default=None, ge=0)
    max_causal_moments: int | None = Field(default=None, ge=1)
    max_participant_calls: int | None = Field(default=None, ge=0)


class ResolvedRunControlPlan(_StrictModel):
    terminal_conditions: list[ExactFactTerminalCondition] = Field(min_length=1)
    terminal_mode: Literal["any", "all"]
    modeled_time_horizon: ModeledTimeHorizon | None = None
    stop_on_quiescence: Literal[True] = True
    max_causal_moments: int = Field(ge=1)
    max_participant_calls: int = Field(ge=0)


class CompletionRecord(_StrictModel):
    reason: Literal[
        "terminal_condition_met",
        "modeled_time_horizon",
        "quiescent_before_terminal",
        "operator_stopped",
        "safety_limit",
    ]
    condition_ids: list[str] = Field(default_factory=list)
    causal_time: int = Field(ge=0)
    logical_time: int = Field(ge=0)
    public_summary: str = Field(min_length=1)
    evidence_event_ids: list[str] = Field(default_factory=list)


def resolve_run_control(
    options: RunControlOptions,
    selection: RunControlSelection | None,
) -> ResolvedRunControlPlan:
    """Resolve operator choices without exposing arbitrary state predicates."""
    selected = selection or RunControlSelection()
    condition_ids = selected.terminal_condition_ids or options.default_terminal_condition_ids
    if len(condition_ids) != len(set(condition_ids)):
        raise ValueError("selected terminal condition ids must be unique")
    available = {item.condition_id: item for item in options.available_terminal_conditions}
    unknown = set(condition_ids) - set(available)
    if unknown:
        raise ValueError(f"unknown terminal condition ids: {sorted(unknown)!r}")
    if selected.terminal_mode not in options.allowed_terminal_modes:
        raise ValueError("selected terminal mode is not allowed")
    horizon = selected.modeled_time_horizon
    if horizon is None:
        horizon = options.default_horizon
    if options.minimum_horizon is not None:
        assert horizon is not None
        assert options.maximum_horizon is not None
        if not options.minimum_horizon <= horizon <= options.maximum_horizon:
            raise ValueError("selected modeled horizon is outside scenario bounds")
    max_causal_moments = (
        selected.max_causal_moments
        if selected.max_causal_moments is not None
        else options.max_causal_moments_cap
    )
    max_participant_calls = (
        selected.max_participant_calls
        if selected.max_participant_calls is not None
        else options.max_participant_calls_cap
    )
    if max_causal_moments > options.max_causal_moments_cap:
        raise ValueError("selected causal-moment limit exceeds scenario cap")
    if max_participant_calls > options.max_participant_calls_cap:
        raise ValueError("selected participant-call limit exceeds scenario cap")
    return ResolvedRunControlPlan(
        terminal_conditions=[available[item] for item in condition_ids],
        terminal_mode=selected.terminal_mode,
        modeled_time_horizon=(
            ModeledTimeHorizon(
                logical_time=horizon,
                public_description=f"Stop at modeled time {horizon} if no terminal condition has been met.",
            )
            if horizon is not None
            else None
        ),
        max_causal_moments=max_causal_moments,
        max_participant_calls=max_participant_calls,
    )


def terminal_condition_ids(
    plan: ResolvedRunControlPlan,
    state: CausalState,
) -> list[str]:
    """Return satisfied compiled conditions; a missing fact fails loudly."""
    matched = [
        item.condition_id
        for item in plan.terminal_conditions
        if state.fact(item.fact_id).value == item.expected_value
    ]
    if plan.terminal_mode == "all":
        return [item.condition_id for item in plan.terminal_conditions] if len(matched) == len(plan.terminal_conditions) else []
    return matched
