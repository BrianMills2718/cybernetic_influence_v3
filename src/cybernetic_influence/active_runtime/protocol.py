"""Replaceable, stateless active-system implementation protocol."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from cybernetic_influence.active_runtime.models import (
    ActiveStepResult,
    ActiveSystemInput,
    ModelCallEvidence,
)


class ActiveSystemImplementation(Protocol):
    """One implementation technology behind the bounded active-system API."""

    @property
    def implementation_id(self) -> str:
        """Return the immutable code/config identity bound by the scenario."""
        ...

    def step(self, active_input: ActiveSystemInput) -> object:
        """Return one proposal from only the supplied bounded input."""
        ...


class ActiveSystemExecutionError(RuntimeError):
    """A provider-bound implementation failed with retainable call evidence."""

    def __init__(
        self,
        message: str,
        *,
        call_evidence: tuple[ModelCallEvidence, ...] = (),
    ) -> None:
        super().__init__(message)
        self.call_evidence = call_evidence


@dataclass(frozen=True)
class ActiveSystemBinding:
    """Trusted registry binding between a spec identity and implementation."""

    implementation_id: str
    implementation: ActiveSystemImplementation

    def __post_init__(self) -> None:
        """Reject a wrapper whose declared identity differs from its policy."""
        if self.implementation_id != self.implementation.implementation_id:
            raise ValueError("active-system binding implementation id mismatch")


Controller = Callable[[ActiveSystemInput], ActiveStepResult]


@dataclass(frozen=True)
class ScriptedActiveSystem:
    """Stateless non-LLM controller used as a valid policy and test instrument."""

    implementation_id: str
    controller: Controller

    def step(self, active_input: ActiveSystemInput) -> object:
        """Validate the controller result at the same boundary as other policies."""
        raw = self.controller(active_input.model_copy(deep=True))
        return ActiveStepResult.model_validate(raw.model_dump(mode="json"))
