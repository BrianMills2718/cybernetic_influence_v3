"""Typed operator configuration projected from shared LLM policy."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from typing import Literal, NotRequired, TypedDict, cast

from llm_client import validated_llm_client_revision
from pydantic import BaseModel, ConfigDict, Field, field_validator

from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_TERRA_MODEL,
    codex_subscription_available,
    is_codex_subscription_model,
)
from cybernetic_influence.narration import NARRATOR_MAX_BUDGET
from cybernetic_influence.scenarios.coordination_decision import (
    MAX_CAUSAL_MOMENTS as COORDINATION_MAX_CAUSAL_MOMENTS,
    MAX_PARTICIPANT_CALLS as COORDINATION_MAX_PARTICIPANT_CALLS,
)

ReasoningEffort = Literal["none", "low", "medium", "high", "xhigh"]
DEFAULT_MODEL = OPENROUTER_TERRA_MODEL
PREFERRED_MODEL = CODEX_LUNA_MODEL
DEFAULT_REASONING_EFFORT: ReasoningEffort = "medium"
NARRATOR_REASONING_EFFORT: Literal["medium"] = "medium"
PARTICIPANT_PER_CALL_CEILING = 0.05
NARRATOR_PER_CALL_CEILING = NARRATOR_MAX_BUDGET
SERVER_MAX_TOTAL_COST = 0.74
DEFAULT_MAX_TOTAL_COST = 0.74
MAXIMUM_PARTICIPANT_CALLS = COORDINATION_MAX_PARTICIPANT_CALLS
# A Coordination trajectory may retain one activation moment for every allowed
# attempt plus one coalesced exact-work span before, between, or after those
# attempts. Preserve the preflight guard while admitting the scenario's full
# structural bound instead of a smaller service-desk-sized trace.
MAXIMUM_NARRATOR_CALLS = 2 * COORDINATION_MAX_CAUSAL_MOMENTS + 1
CERTIFICATION_MAX_AGE = timedelta(days=7)

class _RouteAdvertisement(TypedDict):
    """Simulator-owned policy layered over shared-client capabilities."""

    label: str
    certification_env: str
    coordination_certification_env: str
    authoring_certification_env: NotRequired[str]
    narrator_reasoning_effort: ReasoningEffort
    agent_reasoning_efforts: NotRequired[tuple[ReasoningEffort, ...]]
    experimental_agent_reasoning_efforts: NotRequired[tuple[ReasoningEffort, ...]]


def _preferred_catalog_choice(
    catalog: list[dict[str, object]],
) -> dict[str, object] | None:
    """Prefer Luna when eligible, while retaining a visible usable fallback."""
    by_model = {str(item["model"]): item for item in catalog}
    return (
        by_model.get(PREFERRED_MODEL)
        or by_model.get(DEFAULT_MODEL)
        or (catalog[0] if catalog else None)
    )


# This is a simulator-owned advertisement set, not a provider capability matrix.
# A route enters this set only after the exact participant and narrator schemas
# have been exercised in the deployment environment.
_ADVERTISEMENT: dict[str, _RouteAdvertisement] = {
    CODEX_TERRA_MODEL: {
        "label": "OpenAI GPT-5.6 Terra · Codex subscription",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_CODEX_TERRA",
        "coordination_certification_env": (
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_TERRA"
        ),
        "agent_reasoning_efforts": ("medium",),
        "narrator_reasoning_effort": "medium",
    },
    CODEX_LUNA_MODEL: {
        "label": "OpenAI GPT-5.6 Luna · Codex subscription",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA",
        "coordination_certification_env": (
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_LUNA"
        ),
        "authoring_certification_env": (
            "CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA"
        ),
        "agent_reasoning_efforts": ("medium",),
        "narrator_reasoning_effort": "medium",
    },
    OPENROUTER_TERRA_MODEL: {
        "label": "OpenAI GPT-5.6 Terra",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_TERRA",
        "coordination_certification_env": (
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA"
        ),
        "narrator_reasoning_effort": "low",
    },
    "openrouter/deepseek/deepseek-v4-flash": {
        "label": "DeepSeek V4 Flash",
        "certification_env": "CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH",
        "coordination_certification_env": (
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH"
        ),
        # `none` is the only certified simulator setting.  The shared client
        # also supports high and xhigh, which the operator explicitly asked to
        # make available for investigation.  They remain visibly experimental:
        # focused current-revision structured-output probes did not complete
        # reliably and are not treated as route certification.
        "agent_reasoning_efforts": ("none", "high", "xhigh"),
        "experimental_agent_reasoning_efforts": ("high", "xhigh"),
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
    billing_mode: Literal["subscription_included", "usage_based"] | None = None


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
        codex_available = (
            codex_subscription_available()
            if is_codex_subscription_model(model)
            else False
        )
        configured_certification = os.getenv(
            str(advertisement["certification_env"]), ""
        ).strip()
        certification_basis = _validated_certification_basis(
            model,
            configured_certification,
        )
        if (
            model not in ALLOWED_EXECUTION_MODELS
            or (
                is_codex_subscription_model(model)
                and not codex_available
            )
            or (
                not is_codex_subscription_model(model)
                and (
                    info is None
                    or info.get("structured_output") is not True
                    or info.get("available") is not True
                )
            )
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
        availability_basis: str
        billing_mode: str
        if is_codex_subscription_model(model):
            availability_basis = "verified local ChatGPT Codex login"
            billing_mode = "subscription_included"
        else:
            assert info is not None
            availability_basis = f"configured credential: {info['api_key_env']}"
            billing_mode = "usage_based"
        choices.append(
            {
                "model": model,
                "label": advertisement["label"],
                "default": False,
                "agent_reasoning_efforts": supported_efforts,
                "experimental_agent_reasoning_efforts": [
                    effort
                    for effort in advertisement.get(
                        "experimental_agent_reasoning_efforts", ()
                    )
                    if effort in supported_efforts
                ],
                "default_agent_reasoning_effort": (
                    DEFAULT_REASONING_EFFORT
                    if DEFAULT_REASONING_EFFORT in supported_efforts
                    else supported_efforts[0]
                ),
                "narrator_reasoning_effort": narrator_effort,
                "structured_output": True,
                "availability_basis": availability_basis,
                "billing_mode": billing_mode,
                "certification_basis": certification_basis,
            }
        )
    default_choice = _preferred_catalog_choice(choices)
    if default_choice is not None:
        default_choice["default"] = True
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
    expected_schema_digests = _current_schema_digests(model)
    return _validated_schema_group_basis(
        model,
        configured,
        expected_schema_digests,
    )


def _validated_coordination_certification_basis(
    model: str,
    configured: str,
) -> str | None:
    """Replay every exact participant and post-run schema used by coordination."""
    return _validated_schema_group_basis(
        model,
        configured,
        _current_coordination_schema_digests(model),
    )


def _validated_schema_group_basis(
    model: str,
    configured: str,
    expected_schema_digests: dict[str, str] | None,
) -> str | None:
    """Validate one complete current-revision schema observation group."""
    if expected_schema_digests is None:
        return None
    observation_ids = {
        item.strip() for item in configured.split(",") if item.strip()
    }
    if len(observation_ids) != len(expected_schema_digests):
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
    revision = llm_client_revision()
    typed = [item for item in selected if item is not None]
    if (
        {item.schema_class.rsplit(".", maxsplit=1)[-1] for item in typed}
        != set(expected_schema_digests)
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


def coordination_live_model_ids() -> list[str]:
    """Return globally advertised routes certified for all coordination people."""
    globally_advertised = {
        str(choice["model"])
        for choice in model_catalog()
    }
    supported: list[str] = []
    for model, advertisement in _ADVERTISEMENT.items():
        configured = os.getenv(
            advertisement["coordination_certification_env"], ""
        ).strip()
        if (
            model in globally_advertised
            and _validated_coordination_certification_basis(model, configured)
        ):
            supported.append(model)
    return supported


def authoring_model_ids() -> list[str]:
    """Return routes certified for the exact separated public authoring calls."""
    try:
        from llm_client import ALLOWED_EXECUTION_MODELS
    except ImportError:
        return []
    supported: list[str] = []
    for model, advertisement in _ADVERTISEMENT.items():
        certification_env = advertisement.get("authoring_certification_env")
        if not certification_env or model not in ALLOWED_EXECUTION_MODELS:
            continue
        if is_codex_subscription_model(model) and not codex_subscription_available():
            continue
        configured = os.getenv(certification_env, "").strip()
        if _validated_schema_group_basis(
            model,
            configured,
            _current_authoring_schema_digests(model),
        ):
            supported.append(model)
    return supported


def _current_schema_digests(model: str = DEFAULT_MODEL) -> dict[str, str] | None:
    """Reproduce the exact provider schema used by the selected route."""
    try:
        from llm_client import (
            codex_native_provider_schema,
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
    projector = (
        codex_native_provider_schema
        if is_codex_subscription_model(model)
        else openrouter_native_provider_schema
    )
    return {name: route_schema_sha256(projector(schema)) for name, schema in schemas.items()}


def _current_coordination_schema_digests(
    model: str = DEFAULT_MODEL,
) -> dict[str, str] | None:
    """Reproduce every provider schema used by coordination people."""
    try:
        from llm_client import (
            codex_native_provider_schema,
            openrouter_native_provider_schema,
            route_schema_sha256,
        )

        from cybernetic_influence.analysis.coordination_measurement import (
            CoderOutput,
        )
        from cybernetic_influence.experiments.coordination_experiment import (
            PRESSURE_SOURCE_DECISION_MODELS,
        )
        from cybernetic_influence.scenarios.coordination_decision import (
            COORDINATION_PERSON_DECISION_MODELS,
        )
    except ImportError:
        return None
    schemas = {
        schema.__name__: schema
        for schema in (
            *COORDINATION_PERSON_DECISION_MODELS.values(),
            *PRESSURE_SOURCE_DECISION_MODELS.values(),
        )
    }
    schemas[CoderOutput.__name__] = CoderOutput
    projector = (
        codex_native_provider_schema
        if is_codex_subscription_model(model)
        else openrouter_native_provider_schema
    )
    return {name: route_schema_sha256(projector(schema)) for name, schema in schemas.items()}


def _current_authoring_schema_digests(
    model: str = PREFERRED_MODEL,
) -> dict[str, str] | None:
    """Reproduce both provider schemas used by the public configure action."""
    try:
        from llm_client import (
            codex_native_provider_schema,
            openrouter_native_provider_schema,
            route_schema_sha256,
        )

        from cybernetic_influence.general_simulation.authoring_models import (
            DependencyCompletenessReviewV1,
        )
        from cybernetic_influence.general_simulation.study_models import (
            AuthoredSimulationProposalEnvelopeV2,
        )
    except ImportError:
        return None
    schemas = {
        AuthoredSimulationProposalEnvelopeV2.__name__: (
            AuthoredSimulationProposalEnvelopeV2
        ),
        DependencyCompletenessReviewV1.__name__: DependencyCompletenessReviewV1,
    }
    projector = (
        codex_native_provider_schema
        if is_codex_subscription_model(model)
        else openrouter_native_provider_schema
    )
    return {
        name: route_schema_sha256(projector(schema))
        for name, schema in schemas.items()
    }


def resolve_live_configuration(
    options: RunLlmOptions | None,
) -> EffectiveRunLlmConfiguration:
    """Validate one request against the currently advertised catalog."""
    catalog = model_catalog()
    default_choice = _preferred_catalog_choice(catalog)
    if options is None:
        if default_choice is None:
            raise ValueError("no model is currently advertised for simulator execution")
        selected = RunLlmOptions(
            model=str(default_choice["model"]),
            agent_reasoning_effort=cast(
                ReasoningEffort,
                default_choice["default_agent_reasoning_effort"],
            ),
            max_total_cost=DEFAULT_MAX_TOTAL_COST,
        )
    else:
        selected = options
    advertised = {
        str(choice["model"]): choice
        for choice in catalog
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
        billing_mode=cast(
            Literal["subscription_included", "usage_based"],
            choice["billing_mode"],
        ),
    )


def llm_client_revision() -> str:
    """Return the installed shared-client revision after validating any binding."""
    return cast(str, validated_llm_client_revision())


def live_options_contract() -> dict[str, object]:
    """Return UI-safe defaults, limits, call ceilings, and help."""
    catalog = model_catalog()
    default_choice = _preferred_catalog_choice(catalog)
    return {
        "models": catalog,
        "defaults": {
            "model": (
                default_choice["model"] if default_choice is not None else DEFAULT_MODEL
            ),
            "agent_reasoning_effort": (
                default_choice["default_agent_reasoning_effort"]
                if default_choice is not None
                else DEFAULT_REASONING_EFFORT
            ),
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
            "max_total_cost": "A planning amount retained with the run. A valid simulation is not terminated when known or partially known provider cost crosses it. Provider requests still carry per-call budgets, while call-count and causal-step limits bound runtime growth.",
            "scenario_condition": "A concrete change to world state or a mechanism—not an instruction inserted into a person's mind.",
            "live_execution": "Live mode lets LLM-modeled people orient and act. Reference mode uses fixed zero-cost policies.",
            "map_projection": "Spatial and causal layouts are two projections of the same retained world and trace.",
            "analytical_scale": "A coarse boundary summarizes exact members but never becomes another executor.",
            "causal_moment": "Everyone due at the same simulated time acts from the same frozen pre-moment state.",
            "narrative": "An LLM account of each retained causal moment, constrained to cite that moment's exact evidence.",
            "exact_evidence": "The retained events, state revisions, observations, actions, and provider-call receipts beneath the account.",
        },
    }
