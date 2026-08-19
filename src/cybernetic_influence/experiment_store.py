"""Durable store and typed contracts for RunSpec-level Experimentation.

See docs/plans/030-unified-frontend-experimentation-and-levin-analysis.md,
Design A. An experiment selects RunLlmOptions per condition and re-executes
an already-approved draft's scenario unchanged; it never edits the scenario,
proposal, or draft (ADR-014's Experiment/Scenario authority separation).
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from cybernetic_influence.run_configuration import RunLlmOptions

EXPERIMENT_ID_PATTERN = re.compile(r"experiment_[0-9a-f]{12}")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class InvalidExperimentIdError(ValueError):
    """Raised when an external experiment ID is not in the closed format."""


class ExperimentNotFoundError(FileNotFoundError):
    """Raised when a valid experiment ID has no retained document."""


class ExperimentConditionV2(BaseModel):
    """One controlled RunLlmOptions variation over an already-approved scenario."""

    model_config = ConfigDict(extra="forbid", strict=True)

    condition_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    run_overrides: RunLlmOptions


class ExperimentRequestV2(BaseModel):
    """POST /api/authoring/drafts/{draft_id}/experiments request body."""

    model_config = ConfigDict(extra="forbid", strict=True)

    conditions: list[ExperimentConditionV2] = Field(min_length=1)
    repetitions_per_condition: int = Field(default=1, ge=1, le=5)

    @field_validator("conditions")
    @classmethod
    def unique_condition_ids(
        cls, value: list[ExperimentConditionV2]
    ) -> list[ExperimentConditionV2]:
        ids = [item.condition_id for item in value]
        if len(set(ids)) != len(ids):
            raise ValueError("condition_id must be unique within one experiment")
        return value


class ExperimentConditionResultV2(BaseModel):
    """One completed or failed condition x repetition run."""

    model_config = ConfigDict(extra="forbid")

    condition_id: str
    repetition_index: int
    run_id: str
    run_evidence_bundle_digest: str | None = None
    status: Literal["completed", "failed"]
    error: str | None = None


class ExperimentResultV2(BaseModel):
    """The retained, poll-able record of one experiment's execution."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    draft_id: str
    base_scenario_digest: str | None = None
    status: Literal["running", "completed"]
    conditions: list[ExperimentConditionResultV2] = Field(default_factory=list)
    created_at: str
    updated_at: str


class ExperimentStore:
    """Persist one complete JSON document per experiment, atomically."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        for path in self.root.glob("experiment_*.json"):
            path.chmod(0o600)

    def _validate(self, experiment_id: str) -> None:
        if not EXPERIMENT_ID_PATTERN.fullmatch(experiment_id):
            raise InvalidExperimentIdError(experiment_id)

    def _path(self, experiment_id: str) -> Path:
        self._validate(experiment_id)
        return self.root / f"{experiment_id}.json"

    def new_id(self) -> str:
        return f"experiment_{uuid4().hex[:12]}"

    def save(self, document: Mapping[str, object]) -> dict[str, object]:
        experiment_id = document.get("experiment_id")
        if not isinstance(experiment_id, str):
            raise InvalidExperimentIdError("experiment document requires a string experiment_id")
        destination = self._path(experiment_id)
        temporary = self.root / f".{experiment_id}.{uuid4().hex}.tmp"
        stored = dict(document)
        stored["updated_at"] = now_iso()
        encoded = json.dumps(stored, ensure_ascii=False, indent=2, sort_keys=True)
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                temporary.chmod(0o600)
                handle.write(encoded)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return stored

    def get(self, experiment_id: str) -> dict[str, object]:
        path = self._path(experiment_id)
        if not path.is_file():
            raise ExperimentNotFoundError(experiment_id)
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
        if not isinstance(document, dict):
            raise ValueError(f"retained experiment {experiment_id} is not a JSON object")
        return document
