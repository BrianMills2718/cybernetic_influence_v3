"""Provider-neutral native ``llm_client`` active-system implementation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import functools
from hashlib import sha256
from importlib import resources
import json
import re
from typing import Any, Final, Literal, cast

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, Json, field_validator, model_validator
import yaml

from cybernetic_influence.active_runtime.models import (
    ActionIntent,
    ActiveProposal,
    ActiveStepResult,
    ActiveSystemInput,
    ModelCallEvidence,
)
from cybernetic_influence.active_runtime.protocol import (
    ActiveSystemExecutionError,
)
from cybernetic_influence.causal_core.models import canonical_record_digest

_FORBID = ConfigDict(extra="forbid", strict=True)
_UNPRICED_COST_SOURCES = frozenset({"unavailable", "unspecified"})
_UNRECONCILED_RECOVERY_CODES = frozenset({"LLMC_WARN_RETRY", "LLMC_WARN_FALLBACK"})
NATIVE_LLM_CONFIGURATION_CONTRACT = "native-llm-configuration.v1"
DECISION_WIRE_CONTRACT_V1: Final[Literal["native-decision-wire.v1"]] = (
    "native-decision-wire.v1"
)
DECISION_WIRE_CONTRACT_V2: Final[Literal["openai-json-payload-wire.v2"]] = (
    "openai-json-payload-wire.v2"
)
DecisionWireContract = Literal[
    "native-decision-wire.v1", "openai-json-payload-wire.v2"
]
_IMPLEMENTATION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class LlmMemoryEntry(BaseModel):
    """One private memory item committed only with a successful activation."""

    model_config = _FORBID

    logical_time: int = Field(ge=0)
    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)


class LlmPrivateState(BaseModel):
    """Small native-LLM memory schema stored through the generic private state."""

    model_config = _FORBID

    memory: list[LlmMemoryEntry] = Field(default_factory=list)


class LlmActionDecision(BaseModel):
    """Provider-compatible flat action schema translated to a generic intent."""

    model_config = _FORBID

    output_port_id: str = Field(
        min_length=1,
        description="Exactly one output_port_id from the supplied interfaces.",
    )
    representation_id: str | None = Field(
        default=None,
        description="One permitted representation ID from that interface, or null.",
    )
    payload: Json[dict[str, str | int | float | bool | None]] = Field(
        default_factory=lambda: "{}",
        validate_default=True,
        description=(
            "JSON-encoded flat scalar payload required by the selected interface."
        ),
    )
    public_summary: str = Field(
        min_length=1,
        description="Concise public description of the attempted action.",
    )

    @field_validator("payload", mode="before")
    @classmethod
    def normalize_payload(cls, value: object) -> object:
        """Accept typed test inputs while exposing a strict-schema-safe wire string."""
        if isinstance(value, Mapping):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        return value


class LegacyLlmActionDecision(BaseModel):
    """Original object-payload action wire retained for durable evidence."""

    model_config = _FORBID

    output_port_id: str = Field(
        min_length=1,
        description="Exactly one output_port_id from the supplied interfaces.",
    )
    representation_id: str | None = Field(
        default=None,
        description="One permitted representation ID from that interface, or null.",
    )
    payload: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Flat scalar payload required by the selected interface.",
    )
    public_summary: str = Field(
        min_length=1,
        description="Concise public description of the attempted action.",
    )


class LlmDecision(BaseModel):
    """Scenario-neutral structured cognition without engine-assigned identity."""

    model_config = _FORBID

    orientation: str = Field(
        min_length=1,
        description="Your concise read of the bounded situation and rationale.",
    )
    memory_update: str = Field(
        description="What you want to retain privately after a successful step."
    )
    actions: list[LlmActionDecision] = Field(
        description=(
            "Zero or more actions through only the supplied output interfaces; "
            "never invent actor, action, event, or time identifiers."
        )
    )
    silence_reason: str | None = Field(
        default=None,
        description=(
            "Required when actions is empty and null when at least one action is "
            "proposed."
        ),
    )

    @model_validator(mode="after")
    def validate_silence(self) -> "LlmDecision":
        """Require explicit silence without contradictory action testimony."""
        if not self.actions and not (
            self.silence_reason and self.silence_reason.strip()
        ):
            raise ValueError("empty actions require a nonempty silence reason")
        if self.actions and self.silence_reason is not None:
            raise ValueError("actions require a null silence reason")
        return self


class LegacyLlmDecision(LlmDecision):
    """Original response schema, kept only to inspect and replay v1 evidence."""

    actions: list[LegacyLlmActionDecision] = Field(  # type: ignore[assignment]
        description=(
            "Zero or more actions through only the supplied output interfaces; "
            "never invent actor, action, event, or time identifiers."
        )
    )


StructuredCall = Callable[..., tuple[Any, Any]]


def _decision_model_for_wire_contract(
    contract: DecisionWireContract,
) -> type[BaseModel]:
    _validate_wire_contract(contract)
    return LegacyLlmDecision if contract == DECISION_WIRE_CONTRACT_V1 else LlmDecision


def _validate_wire_contract(contract: DecisionWireContract) -> None:
    if contract not in {DECISION_WIRE_CONTRACT_V1, DECISION_WIRE_CONTRACT_V2}:
        raise ValueError("unknown native decision wire contract")


def _prompt_resource_name(contract: DecisionWireContract) -> str:
    _validate_wire_contract(contract)
    return (
        "active_step_v1.yaml"
        if contract == DECISION_WIRE_CONTRACT_V1
        else "active_step.yaml"
    )


def _decision_schema(
    decision_model: type[BaseModel], *, wire_contract: DecisionWireContract
) -> dict[str, object]:
    """Return the exact wire schema, not merely the runtime normalization model."""
    _validate_wire_contract(wire_contract)
    if wire_contract == DECISION_WIRE_CONTRACT_V2:
        return cast(dict[str, object], decision_model.model_json_schema())
    # v1 predates the OpenAI-compatible JSON-string payload.  Preserve its
    # exact historical schema identity rather than deriving an equivalent new
    # Pydantic class (which would change definition names and invalidate IDs).
    schema = cast(dict[str, object], LlmDecision.model_json_schema())
    definitions = cast(dict[str, object], schema["$defs"])
    action = cast(dict[str, object], definitions["LlmActionDecision"])
    properties = cast(dict[str, object], action["properties"])
    properties["payload"] = {
        "additionalProperties": {
            "anyOf": [{"type": "string"}, {"type": "integer"}, {"type": "number"}, {"type": "boolean"}, {"type": "null"}]
        },
        "description": "Flat scalar payload required by the selected interface.",
        "title": "Payload",
        "type": "object",
    }
    return schema


def native_llm_configuration_digest(
    *,
    implementation_family_id: str,
    persona: str,
    model: str,
    task: str,
    reasoning_effort: str | None = None,
    max_memory_entries: int = 32,
    max_output_tokens: int = 2048,
    decision_model: type[BaseModel] | None = None,
    decision_wire_contract: DecisionWireContract = DECISION_WIRE_CONTRACT_V2,
) -> str:
    """Digest every non-secret field that can change native policy behavior."""
    if not _IMPLEMENTATION_ID_PATTERN.fullmatch(implementation_family_id):
        raise ValueError("implementation_family_id must be a canonical id")
    for label, value in (("persona", persona), ("model", model), ("task", task)):
        if not value.strip():
            raise ValueError(f"{label} must be nonempty")
    if reasoning_effort is not None and not reasoning_effort.strip():
        raise ValueError("reasoning_effort must be nonempty when provided")
    if max_memory_entries < 1:
        raise ValueError("max_memory_entries must be positive")
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    selected_model = decision_model or _decision_model_for_wire_contract(
        decision_wire_contract
    )
    if not isinstance(selected_model, type) or not issubclass(
        selected_model, BaseModel
    ):
        raise ValueError("decision_model must be a Pydantic model class")
    prompt_bytes = resources.files(__package__).joinpath(
        f"prompts/{_prompt_resource_name(decision_wire_contract)}"
    ).read_bytes()
    configuration: dict[str, object] = {
        "configuration_contract": NATIVE_LLM_CONFIGURATION_CONTRACT,
        "implementation_family_id": implementation_family_id,
        "persona_sha256": sha256(persona.encode("utf-8")).hexdigest(),
        "model": model,
        "task": task,
        "max_memory_entries": max_memory_entries,
        "max_output_tokens": max_output_tokens,
        "decision_schema_digest": canonical_record_digest(
            _decision_schema(
                selected_model, wire_contract=decision_wire_contract
            )
        ),
        "prompt_template_sha256": sha256(prompt_bytes).hexdigest(),
    }
    if reasoning_effort is not None:
        configuration["reasoning_effort"] = reasoning_effort
    return canonical_record_digest(configuration)


def bound_native_llm_implementation_id(
    *,
    implementation_family_id: str,
    persona: str,
    model: str,
    task: str,
    reasoning_effort: str | None = None,
    max_memory_entries: int = 32,
    max_output_tokens: int = 2048,
    decision_model: type[BaseModel] | None = None,
    decision_wire_contract: DecisionWireContract = DECISION_WIRE_CONTRACT_V2,
) -> str:
    """Bind one manually versioned implementation family to exact config."""
    digest = native_llm_configuration_digest(
        implementation_family_id=implementation_family_id,
        persona=persona,
        model=model,
        task=task,
        reasoning_effort=reasoning_effort,
        max_memory_entries=max_memory_entries,
        max_output_tokens=max_output_tokens,
        decision_model=decision_model,
        decision_wire_contract=decision_wire_contract,
    )
    return f"{implementation_family_id}_cfg_{digest}"


@dataclass(frozen=True)
class NativeLlmActiveSystem:
    """One stateless structured LLM policy behind the active-system protocol."""

    implementation_id: str
    persona: str
    model: str
    task: str
    trace_id_prefix: str
    reasoning_effort: str | None = None
    max_memory_entries: int = 32
    max_output_tokens: int = 2048
    structured_call: StructuredCall | None = None
    decision_model: type[BaseModel] = LlmDecision
    implementation_family_id: str | None = None
    decision_wire_contract: DecisionWireContract = DECISION_WIRE_CONTRACT_V2

    @property
    def provider_bound(self) -> bool:
        return True

    def __post_init__(self) -> None:
        """Reject blank configuration and nonsensical memory bounds early."""
        for label, value in (
            ("implementation_id", self.implementation_id),
            ("persona", self.persona),
            ("model", self.model),
            ("task", self.task),
            ("trace_id_prefix", self.trace_id_prefix),
        ):
            if not value.strip():
                raise ValueError(f"{label} must be nonempty")
        if self.max_memory_entries < 1:
            raise ValueError("max_memory_entries must be positive")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if self.reasoning_effort is not None and not self.reasoning_effort.strip():
            raise ValueError("reasoning_effort must be nonempty when provided")
        if (
            not isinstance(self.decision_model, type)
            or not issubclass(self.decision_model, BaseModel)
            or set(self.decision_model.model_fields) != set(LlmDecision.model_fields)
        ):
            raise ValueError(
                "decision_model must expose the canonical LlmDecision fields"
            )
        if self.implementation_family_id is not None:
            expected = bound_native_llm_implementation_id(
                implementation_family_id=self.implementation_family_id,
                persona=self.persona,
                model=self.model,
                task=self.task,
                reasoning_effort=self.reasoning_effort,
                max_memory_entries=self.max_memory_entries,
                max_output_tokens=self.max_output_tokens,
                decision_model=self.decision_model,
                decision_wire_contract=self.decision_wire_contract,
            )
            if self.implementation_id != expected:
                raise ValueError(
                    "native LLM implementation id does not bind its configuration"
                )

    @classmethod
    def from_bound_configuration(
        cls,
        *,
        implementation_family_id: str,
        persona: str,
        model: str,
        task: str,
        trace_id_prefix: str,
        reasoning_effort: str | None = None,
        max_memory_entries: int = 32,
        max_output_tokens: int = 2048,
        structured_call: StructuredCall | None = None,
        decision_model: type[BaseModel] | None = None,
        decision_wire_contract: DecisionWireContract = DECISION_WIRE_CONTRACT_V2,
    ) -> NativeLlmActiveSystem:
        """Construct a native policy whose persisted ID binds its behavior."""
        selected_model = decision_model or _decision_model_for_wire_contract(
            decision_wire_contract
        )
        implementation_id = bound_native_llm_implementation_id(
            implementation_family_id=implementation_family_id,
            persona=persona,
            model=model,
            task=task,
            reasoning_effort=reasoning_effort,
            max_memory_entries=max_memory_entries,
            max_output_tokens=max_output_tokens,
            decision_model=selected_model,
            decision_wire_contract=decision_wire_contract,
        )
        return cls(
            implementation_id=implementation_id,
            persona=persona,
            model=model,
            task=task,
            trace_id_prefix=trace_id_prefix,
            reasoning_effort=reasoning_effort,
            max_memory_entries=max_memory_entries,
            max_output_tokens=max_output_tokens,
            structured_call=structured_call,
            decision_model=selected_model,
            implementation_family_id=implementation_family_id,
            decision_wire_contract=decision_wire_contract,
        )

    def step(self, active_input: ActiveSystemInput) -> object:
        """Make one structured call and propose state/actions without core IDs."""
        validated_input = ActiveSystemInput.model_validate(
            active_input.model_dump(mode="json")
        )
        prior = LlmPrivateState.model_validate(validated_input.private_state)
        system, user = render_llm_prompts(
            validated_input,
            persona=self.persona,
            memory=prior,
            decision_wire_contract=self.decision_wire_contract,
        )
        trace_id = (
            f"{self.trace_id_prefix}/{validated_input.active_system_id}/"
            f"activation/{validated_input.activation_id}"
        )
        call = self.structured_call or _resolve_structured_call()
        try:
            call_kwargs: dict[str, object] = {
                "response_model": self.decision_model,
                "task": self.task,
                "trace_id": trace_id,
                "max_budget": validated_input.budget.max_call_cost,
                "max_tokens": self.max_output_tokens,
                "model_justification": (
                    "Use the model bound into this native active-system "
                    "implementation as an explicit simulation condition."
                ),
            }
            if self.reasoning_effort is not None:
                call_kwargs["reasoning_effort"] = self.reasoning_effort
            parsed, meta = call(
                self.model,
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                **call_kwargs,
            )
        except Exception as error:
            evidence = ModelCallEvidence(
                status="failed",
                trace_id=trace_id,
                model=self.model,
                task=self.task,
                reasoning_effort=self.reasoning_effort,
                system_prompt=system,
                user_prompt=user,
                cost=None,
                cost_source="unavailable",
                error_type=type(error).__name__,
                error_message=str(error),
            )
            raise ActiveSystemExecutionError(
                f"native LLM step failed for {validated_input.active_system_id!r}",
                call_evidence=(evidence,),
            ) from error

        try:
            decision_input = (
                parsed.model_dump(mode="json")
                if isinstance(parsed, BaseModel)
                else parsed
            )
            decision = cast(Any, self.decision_model.model_validate(decision_input))
        except Exception as error:
            cost, cost_source = _observed_cost(meta)
            evidence = ModelCallEvidence(
                status="failed",
                trace_id=trace_id,
                model=self.model,
                task=self.task,
                reasoning_effort=self.reasoning_effort,
                system_prompt=system,
                user_prompt=user,
                cost=cost,
                cost_source=cost_source,
                error_type=type(error).__name__,
                error_message=str(error),
            )
            raise ActiveSystemExecutionError(
                f"native LLM decode failed for {validated_input.active_system_id!r}",
                call_evidence=(evidence,),
            ) from error

        cost, cost_source = _observed_cost(meta)
        evidence = ModelCallEvidence(
            status="completed",
            trace_id=trace_id,
            model=self.model,
            task=self.task,
            reasoning_effort=self.reasoning_effort,
            system_prompt=system,
            user_prompt=user,
            structured_output=decision.model_dump(mode="json"),
            cost=cost,
            cost_source=cost_source,
        )
        memory = [entry.model_copy(deep=True) for entry in prior.memory]
        memory.extend(
            LlmMemoryEntry(
                logical_time=validated_input.logical_time,
                kind="observation",
                content=observation.apparent_content,
            )
            for observation in validated_input.observations
        )
        memory.append(
            LlmMemoryEntry(
                logical_time=validated_input.logical_time,
                kind="orientation",
                content=decision.orientation,
            )
        )
        if decision.memory_update.strip():
            memory.append(
                LlmMemoryEntry(
                    logical_time=validated_input.logical_time,
                    kind="memory_update",
                    content=decision.memory_update,
                )
            )
        action_intents = [
            ActionIntent(
                output_port_id=action.output_port_id,
                representation_id=action.representation_id,
                payload=cast(
                    dict[str, Any],
                    (
                        action.payload.model_dump(mode="json")
                        if isinstance(action.payload, BaseModel)
                        else dict(action.payload)
                    ),
                ),
                public_summary=action.public_summary,
            )
            for action in decision.actions
        ]
        for action in action_intents:
            memory.append(
                LlmMemoryEntry(
                    logical_time=validated_input.logical_time,
                    kind="own_action",
                    content=action.public_summary,
                )
            )
        if not decision.actions and decision.silence_reason is not None:
            memory.append(
                LlmMemoryEntry(
                    logical_time=validated_input.logical_time,
                    kind="silence",
                    content=decision.silence_reason,
                )
            )
        next_state = LlmPrivateState(memory=memory[-self.max_memory_entries :])
        return ActiveStepResult(
            proposal=ActiveProposal(
                active_system_id=validated_input.active_system_id,
                implementation_id=self.implementation_id,
                private_state=next_state.model_dump(mode="json"),
                actions=action_intents,
            ),
            call_evidence=[evidence],
        )


def render_llm_prompts(
    active_input: ActiveSystemInput,
    *,
    persona: str,
    memory: LlmPrivateState | None = None,
    decision_wire_contract: DecisionWireContract = DECISION_WIRE_CONTRACT_V2,
) -> tuple[str, str]:
    """Render only the native policy's bounded protocol input and persona."""
    validated = ActiveSystemInput.model_validate(active_input.model_dump(mode="json"))
    private_memory = memory or LlmPrivateState.model_validate(validated.private_state)
    prompt = _load_prompt(decision_wire_contract)
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    )
    context = {
        "active_system_id": validated.active_system_id,
        "entity_id": validated.entity_id,
        "logical_time": validated.logical_time,
        "time_unit": validated.time_unit,
        "activation_causes": [
            item.model_dump(mode="json")
            for item in validated.activation_causes
        ],
        "next_update_at": validated.next_update_at,
        "persona": persona,
        "memory": [item.model_dump(mode="json") for item in private_memory.memory],
        "observations": [
            item.model_dump(mode="json") for item in validated.observations
        ],
        "action_interfaces": [
            item.model_dump(mode="json") for item in validated.action_interfaces
        ],
        "max_actions": validated.budget.max_actions,
    }
    return (
        environment.from_string(prompt["system"]).render(context),
        environment.from_string(prompt["user"]).render(context),
    )


@functools.lru_cache(maxsize=2)
def _load_prompt(decision_wire_contract: DecisionWireContract) -> dict[str, str]:
    """Load and validate the scenario-neutral native active-system prompt."""
    prompt_path = resources.files(__package__).joinpath(
        f"prompts/{_prompt_resource_name(decision_wire_contract)}"
    )
    payload = yaml.safe_load(prompt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("active-system prompt must be a mapping")
    required = {"name", "description", "system", "user"}
    if set(payload) != required or not all(
        isinstance(payload[key], str) and payload[key].strip() for key in required
    ):
        raise ValueError("active-system prompt has an invalid contract")
    return cast(dict[str, str], payload)


def _observed_cost(meta: Any) -> tuple[float | None, str]:
    """Extract priced metadata without turning unavailable spend into zero."""
    warning_records = getattr(meta, "warning_records", None)
    cost_covers_all_attempts = getattr(
        meta,
        "cost_covers_all_attempts",
        False,
    )
    if (
        isinstance(warning_records, list)
        and any(
            isinstance(record, dict)
            and record.get("code") in _UNRECONCILED_RECOVERY_CODES
            for record in warning_records
        )
        and cost_covers_all_attempts is not True
    ):
        return None, "unreconciled_provider_attempts"
    try:
        raw_cost = meta.cost
        cost_source = str(meta.cost_source)
    except AttributeError:
        return None, "unavailable"
    if raw_cost is None or cost_source in _UNPRICED_COST_SOURCES:
        return None, cost_source
    try:
        cost = float(raw_cost)
    except (TypeError, ValueError):
        return None, f"invalid_{cost_source}"
    if cost < 0.0:
        return None, f"invalid_{cost_source}"
    return cost, cost_source


def _resolve_structured_call() -> StructuredCall:
    """Resolve the shared provider-neutral structured-call boundary lazily."""
    try:
        from llm_client import call_llm_structured
    except ImportError as error:
        raise RuntimeError(
            "llm_client is required for native active systems: install the shared "
            "llm_client project in this environment"
        ) from error
    return cast(StructuredCall, call_llm_structured)
