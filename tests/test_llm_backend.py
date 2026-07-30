"""Focused contracts for subscription-backed Codex execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    codex_subscription_available,
    structured_backend_options,
)


def test_codex_availability_requires_chatgpt_login(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("cybernetic_influence.llm_backend.shutil.which", lambda _: "/bin/codex")
    monkeypatch.setattr(
        "cybernetic_influence.llm_backend.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 0, "Logged in using ChatGPT\n", ""
        ),
    )

    assert codex_subscription_available() is True


def test_codex_availability_rejects_api_key_or_missing_cli(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("cybernetic_influence.llm_backend.shutil.which", lambda _: None)
    assert codex_subscription_available() is False


def test_codex_structured_backend_is_isolated_and_has_no_fallback() -> None:
    retained_root: Path | None = None
    with structured_backend_options(CODEX_LUNA_MODEL) as options:
        retained_root = Path(str(options["working_directory"]))
        assert retained_root.is_dir()
        assert options == {
            "execution_mode": "workspace_agent",
            "codex_transport": "cli",
            "working_directory": str(retained_root),
            "sandbox_mode": "read-only",
            "approval_policy": "never",
            "skip_git_repo_check": True,
            "mcp_servers": {},
            "model_policy": "enforce_allowlist",
        }
        assert "fallback_models" not in options
    assert retained_root is not None
    assert not retained_root.exists()


def test_non_codex_routes_retain_the_shared_client_defaults() -> None:
    with structured_backend_options("openrouter/openai/gpt-5.6-terra") as options:
        assert options == {}
