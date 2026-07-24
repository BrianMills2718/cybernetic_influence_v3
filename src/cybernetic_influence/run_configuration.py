"""Typed operator configuration projected from shared LLM policy."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReasoningEffort = Literal["none", "low", "medium", "high"]
DEFAULT_MODEL = "openrouter/openai/gpt-5.6-terra"
DEFAULT_REASONING_EFFORT: ReasoningEffort = "medium"
NARRATOR_REASONING_EFFORT: Literal["low"] = "low"
PARTICIPANT_PER_CALL_CEILING = 0.05
NARRATOR_PER_CALL_CEILING = 0.02
SERVER_MAX_TOTAL_COST = 0.74
DEFAULT_MAX_TOTAL_COST = 0.74
MAXIMUM_PARTICIPANT_CALLS = 48
MAXIMUM_NARRATOR_CALLS = 12
CERTIFICATION_MAX_AGE = timedelta(days=7)

class _RouteAdvertisement(TypedDict):
    """Simulator-owned policy layered over shared-client capabilities."""

    label: str
    certification_env: str
    narrator_reasoning_effort: ReasoningEffort
    agent_reasoning_efforts: NotRequired[tuple[ReasoningEffort, ...]]


# This is a simulator-owned advertisement set, not a provider capability matrix.
# A route enters this set only after the exact participant and narrator schemas
# have been exercised in the deployment environment.
_ADVERTISEMENT: dict[str, _RouteAdvertisement] = {
    "openrouter/openai/gpt-5.6-terra": {
        "label": "OpenAI GPT-5.6 Terra",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_TERRA",
        "narrator_reasoning_effort": "low",
    },
    "openrouter/deepseek/deepseek-v4-flash": {
        "label": "DeepSeek V4 Flash",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH",
        # This route's exact simulator schemas have only been evidenced with
        # reasoning disabled.  Do not turn registry support for another effort
        # into an advertised simulator promise.
        "agent_reasoning_efforts": ("none",),
        "narrator_reasoning_effort": "none",
    },
}


class RunLlmOptions(BaseModel):
    """Strict operator-selected LLM policy for one live run."""

    model_config = ConfigDict(extra="forbid", strict=True)

    model: str = Field(min_length=1)
    agent_reasoning_effort: ReasoningEffort
    max_total_cost: float = Field(gt=0.0, le=SERVER_MAX_TOTAL_COST)

    @field_validator("model")
    @classmethod
    def canonical_nonblank_model(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("model must be a canonical identifier without whitespace")
        return value

    @field_validator("max_total_cost")
    @classmethod
    def finite_cost(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("max_total_cost must be finite")
        return value


class EffectiveRunLlmConfiguration(BaseModel):
    """Server-resolved execution policy retained before provider dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    agent_reasoning_effort: ReasoningEffort
    narrator_reasoning_effort: ReasoningEffort
    max_total_cost: float
    participant_per_call_ceiling: float = PARTICIPANT_PER_CALL_CEILING
    narrator_per_call_ceiling: float = NARRATOR_PER_CALL_CEILING
    maximum_participant_calls: int = MAXIMUM_PARTICIPANT_CALLS
    maximum_narrator_calls: int = MAXIMUM_NARRATOR_CALLS
    selection_basis: Literal["server_default", "operator_selected"]
    llm_client_revision: str


def model_catalog() -> list[dict[str, object]]:
    """Project only deployment-advertised, shared-policy-eligible live routes."""
    try:
        from llm_client import (
            ALLOWED_EXECUTION_MODELS,
            evaluate_model_execution_policy,
            list_models,
        )
        from llm_client.core.errors import LLMConfigurationError
    except ImportError:
        return []

    registry = {
        str(item["litellm_id"]): item
        for item in list_models(available_only=False)
    }
    choices: list[dict[str, object]] = []
    for model, advertisement in _ADVERTISEMENT.items():
        info = registry.get(model)
        configured_certification = os.getenv(
            str(advertisement["certification_env"]), ""
        ).strip()
        certification_basis = _validated_certification_basis(
            model,
            configured_certification,
        )
        if (
            model not in ALLOWED_EXECUTION_MODELS
            or info is None
            or info.get("structured_output") is not True
            or info.get("available") is not True
            or not certification_basis
        ):
            continue
        justification = _model_justification(model)
        candidate_efforts = advertisement.get(
            "agent_reasoning_efforts", ("none", "low", "medium", "high")
        )
        supported_efforts = []
        for effort in candidate_efforts:
            try:
                evaluate_model_execution_policy(
                    [model],
                    justification=justification,
                    reasoning_effort=effort,
                )
            except LLMConfigurationError:
                continue
            supported_efforts.append(effort)
        narrator_effort = advertisement["narrator_reasoning_effort"]
        try:
            evaluate_model_execution_policy(
                [model],
                justification=justification,
                reasoning_effort=narrator_effort,
            )
        except LLMConfigurationError:
            continue
        if not supported_efforts:
            continue
        choices.append(
            {
                "model": model,
                "label": advertisement["label"],
                "default": model == DEFAULT_MODEL,
                "agent_reasoning_efforts": supported_efforts,
                "default_agent_reasoning_effort": (
                    DEFAULT_REASONING_EFFORT
                    if DEFAULT_REASONING_EFFORT in supported_efforts
                    else supported_efforts[0]
                ),
                "narrator_reasoning_effort": narrator_effort,
                "structured_output": True,
                "availability_basis": (
                    f"configured credential: {info['api_key_env']}"
                ),
                "certification_basis": certification_basis,
            }
        )
    return choices


def _model_justification(model: str) -> str | None:
    if model.endswith("deepseek-v4-flash"):
        return None
    return "Operator selected an advertised simulator route."


def _validated_certification_basis(
    model: str,
    configured: str,
) -> str | None:
    """Replay two exact route observations before projecting a selectable model."""
    observation_ids = {
        item.strip() for item in configured.split(",") if item.strip()
    }
    if len(observation_ids) != 2:
        return None
    try:
        from llm_client.route_certification import RouteCertificationStore
    except ImportError:
        return None
    root = Path(
        os.getenv(
            "LLM_ROUTE_CERTIFICATION_ROOT",
            "~/projects/data/llm_route_certification",
        )
    ).expanduser()
    try:
        observations = {
            item.observation_id: item
            for item in RouteCertificationStore(root / "observations").observations()
        }
    except (OSError, ValueError):
        return None
    selected = [observations.get(item) for item in sorted(observation_ids)]
    if any(item is None for item in selected):
        return None
    now = datetime.now(timezone.utc)
    required_schemas = {"LlmDecision", "CausalMomentNarration"}
    expected_schema_digests = _current_schema_digests()
    revision = llm_client_revision()
    typed = [item for item in selected if item is not None]
    if (
        {item.schema_class.rsplit(".", maxsplit=1)[-1] for item in typed}
        != required_schemas
        or expected_schema_digests is None
        or any(
            item.requested_model != model
            or not item.transport_certifies
            or item.schema_sha256
            != expected_schema_digests[
                item.schema_class.rsplit(".", maxsplit=1)[-1]
            ]
            or item.llm_client_revision != revision
            or item.observed_at > now
            or now - item.observed_at > CERTIFICATION_MAX_AGE
            for item in typed
        )
    ):
        return None
    return ",".join(sorted(observation_ids))


def _current_schema_digests() -> dict[str, str] | None:
    """Reproduce the shared runtime's exact OpenRouter provider schemas."""
    try:
        from llm_client import (
            openrouter_native_provider_schema,
            route_schema_sha256,
        )
        from cybernetic_influence.active_runtime.llm import LlmDecision
        from cybernetic_influence.narration import CausalMomentNarration
    except ImportError:
        return None
    schemas = {
        "LlmDecision": LlmDecision,
        "CausalMomentNarration": CausalMomentNarration,
    }
    return {
        name: route_schema_sha256(
            openrouter_native_provider_schema(schema)
        )
        for name, schema in schemas.items()
    }


def resolve_live_configuration(
    options: RunLlmOptions | None,
) -> EffectiveRunLlmConfiguration:
    """Validate one request against the currently advertised catalog."""
    selected = options or RunLlmOptions(
        model=DEFAULT_MODEL,
        agent_reasoning_effort=DEFAULT_REASONING_EFFORT,
        max_total_cost=DEFAULT_MAX_TOTAL_COST,
    )
    advertised = {
        str(choice["model"]): choice
        for choice in model_catalog()
    }
    choice = advertised.get(selected.model)
    if choice is None:
        raise ValueError("model is not currently advertised for simulator execution")
    supported_efforts = {
        str(effort)
        for effort in cast(list[object], choice["agent_reasoning_efforts"])
    }
    if selected.agent_reasoning_effort not in supported_efforts:
        raise ValueError(
            f"{selected.model} does not support agent reasoning effort "
            f"{selected.agent_reasoning_effort!r}; choose one of "
            f"{', '.join(sorted(supported_efforts))}"
        )
    return EffectiveRunLlmConfiguration(
        model=selected.model,
        agent_reasoning_effort=selected.agent_reasoning_effort,
        narrator_reasoning_effort=cast(
            ReasoningEffort,
            choice["narrator_reasoning_effort"],
        ),
        max_total_cost=selected.max_total_cost,
        selection_basis=(
            "server_default" if options is None else "operator_selected"
        ),
        llm_client_revision=llm_client_revision(),
    )


def llm_client_revision() -> str:
    """Return the deployment binding without inventing a source revision."""
    bound = os.getenv("LLM_CLIENT_REVISION", "").strip()
    if bound:
        return bound
    try:
        return version("llm-client")
    except PackageNotFoundError:
        return "unknown-development"


def live_options_contract() -> dict[str, object]:
    """Return UI-safe defaults, limits, call ceilings, and help."""
    return {
        "models": model_catalog(),
        "defaults": {
            "model": DEFAULT_MODEL,
            "agent_reasoning_effort": DEFAULT_REASONING_EFFORT,
            "max_total_cost": DEFAULT_MAX_TOTAL_COST,
        },
        "limits": {
            "server_max_total_cost": SERVER_MAX_TOTAL_COST,
            "participant_per_call_ceiling": PARTICIPANT_PER_CALL_CEILING,
            "narrator_per_call_ceiling": NARRATOR_PER_CALL_CEILING,
            "maximum_participant_calls": MAXIMUM_PARTICIPANT_CALLS,
            "maximum_narrator_calls": MAXIMUM_NARRATOR_CALLS,
        },
        "help": {
            "model": "The shared client route used by every LLM-modeled person and by the narrator. Exact mechanisms make no model call.",
            "agent_reasoning_effort": "How much reasoning effort each modeled person may use. It does not change their position, dispositions, memory, or observations.",
            "max_total_cost": "The maximum authorized provider spend across people and narration. A new call starts only when its full per-call ceiling still fits.",
            "scenario_condition": "A concrete change to world state or a mechanism—not an instruction inserted into a person's mind.",
            "live_execution": "Live mode lets LLM-modeled people orient and act. Reference mode uses fixed zero-cost policies.",
            "map_projection": "Spatial and causal layouts are two projections of the same retained world and trace.",
            "analytical_scale": "A coarse boundary summarizes exact members but never becomes another executor.",
            "causal_moment": "Everyone due at the same simulated time acts from the same frozen pre-moment state.",
            "narrative": "An LLM account of each retained causal moment, constrained to cite that moment's exact evidence.",
            "exact_evidence": "The retained events, state revisions, observations, actions, and provider-call receipts beneath the account.",
        },
    }
