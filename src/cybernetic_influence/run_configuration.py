"""Typed operator configuration projected from shared LLM policy."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ReasoningEffort = Literal["low", "medium", "high"]
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

# This is a simulator-owned advertisement set, not a provider capability matrix.
# A route enters this set only after the exact participant and narrator schemas
# have been exercised in the deployment environment.
_ADVERTISEMENT = {
    "openrouter/openai/gpt-5.6-terra": {
        "label": "OpenAI GPT-5.6 Terra",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_TERRA",
    },
    "openrouter/deepseek/deepseek-v4-flash": {
        "label": "DeepSeek V4 Flash",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH",
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
    narrator_reasoning_effort: Literal["low"] = NARRATOR_REASONING_EFFORT
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
        justification = None if model.endswith("deepseek-v4-flash") else (
            "Operator selected an advertised simulator route."
        )
        evaluate_model_execution_policy(
            [model],
            justification=justification,
        )
        choices.append(
            {
                "model": model,
                "label": advertisement["label"],
                "default": model == DEFAULT_MODEL,
                "structured_output": True,
                "availability_basis": (
                    f"configured credential: {info['api_key_env']}"
                ),
                "certification_basis": certification_basis,
            }
        )
    return choices


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
    revision = llm_client_revision()
    typed = [item for item in selected if item is not None]
    if (
        {item.schema_class.rsplit(".", maxsplit=1)[-1] for item in typed}
        != required_schemas
        or any(
            item.requested_model != model
            or not item.transport_certifies
            or item.llm_client_revision != revision
            or item.observed_at > now
            or now - item.observed_at > CERTIFICATION_MAX_AGE
            for item in typed
        )
    ):
        return None
    return ",".join(sorted(observation_ids))


def resolve_live_configuration(
    options: RunLlmOptions | None,
) -> EffectiveRunLlmConfiguration:
    """Validate one request against the currently advertised catalog."""
    selected = options or RunLlmOptions(
        model=DEFAULT_MODEL,
        agent_reasoning_effort=DEFAULT_REASONING_EFFORT,
        max_total_cost=DEFAULT_MAX_TOTAL_COST,
    )
    advertised = {str(choice["model"]) for choice in model_catalog()}
    if selected.model not in advertised:
        raise ValueError("model is not currently advertised for simulator execution")
    return EffectiveRunLlmConfiguration(
        model=selected.model,
        agent_reasoning_effort=selected.agent_reasoning_effort,
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
