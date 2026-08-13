"""Private, revisioned persistence for reviewable authored scenario drafts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from uuid import uuid4

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


_DRAFT_ID = re.compile(r"draft_[0-9a-f]{12}")


class DraftNotFoundError(FileNotFoundError):
    """A valid draft id has no retained document."""


class DraftConflictError(ValueError):
    """A mutation did not name the draft revision it intended to replace."""


class _DraftDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    draft_id: str = Field(pattern=r"^draft_[0-9a-f]{12}$")
    target_kind: Literal["legacy_templates_v1", "general_world_v1"] = (
        "legacy_templates_v1"
    )
    revision: int = Field(ge=0)
    status: Literal["draft", "repairing", "needs_input", "ready_for_review", "approved"]
    messages: list["_DraftMessage"] = Field(default_factory=list)
    attempts: list["_DraftAttempt"] = Field(default_factory=list)
    authoring_summary: str = "Describe a bounded situation to begin."
    proposal: dict[str, object] | None = None
    coverage: dict[str, object] | None = None
    diagnostics: list[dict[str, str]] = Field(default_factory=list)
    approval: dict[str, object] | None = None
    created_at: str
    updated_at: str


class _DraftMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    message_id: str
    content: str
    source: Literal[
        "conversation",
        "direct_person_edit",
        "direct_coordination_edit",
        "direct_component_composition_edit",
        "direct_proposal_edit",
        "direct_general_proposal_edit",
    ] = "conversation"
    edit_digest: str | None = None
    model: str | None = None
    reasoning_effort: str | None = None
    assistant_summary: str | None = None
    result_status: str | None = None
    trace_ids: list[str] = Field(default_factory=list)


class _DraftAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    attempt: int = Field(ge=1)
    trace_id: str
    status: Literal["accepted", "repair", "needs_input", "provider_error"]
    message: str
    observed_cost: float | None = Field(default=None, ge=0)


class AuthoringDraftStore:
    """Atomic JSON persistence with optimistic revision replacement."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        root.chmod(0o700)

    def create(
        self,
        *,
        now: str,
        target_kind: Literal["legacy_templates_v1", "general_world_v1"] = (
            "legacy_templates_v1"
        ),
    ) -> dict[str, object]:
        document = _DraftDocument(
            draft_id=f"draft_{uuid4().hex[:12]}",
            target_kind=target_kind,
            revision=0,
            status="draft",
            created_at=now, updated_at=now,
        )
        return self._write(document)

    def get(self, draft_id: str) -> dict[str, object]:
        path = self._path(draft_id)
        if not path.is_file():
            raise DraftNotFoundError(draft_id)
        try:
            document = _DraftDocument.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("retained authoring draft is corrupt") from error
        return document.model_dump(mode="json")

    def replace(
        self, draft_id: str, *, expected_revision: int, document: dict[str, object]
    ) -> dict[str, object]:
        current = self.get(draft_id)
        if current["revision"] != expected_revision:
            raise DraftConflictError("draft revision has changed; reload before editing")
        candidate = _DraftDocument.model_validate(document)
        if candidate.draft_id != draft_id or candidate.revision != expected_revision + 1:
            raise DraftConflictError("replacement does not advance this draft by one revision")
        return self._write(candidate)

    def _write(self, document: _DraftDocument) -> dict[str, object]:
        destination = self._path(document.draft_id)
        temporary = self.root / f".{document.draft_id}.{uuid4().hex}.tmp"
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                temporary.chmod(0o600)
                handle.write(document.model_dump_json(indent=2))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
            descriptor = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            temporary.unlink(missing_ok=True)
        return document.model_dump(mode="json")

    def _path(self, draft_id: str) -> Path:
        if _DRAFT_ID.fullmatch(draft_id) is None:
            raise ValueError("invalid draft ID")
        return self.root / f"{draft_id}.json"
