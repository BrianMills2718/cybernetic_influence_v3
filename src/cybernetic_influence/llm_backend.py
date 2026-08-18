"""Project-owned execution settings for shared ``llm_client`` backends."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

CODEX_LUNA_MODEL: Final = "codex/gpt-5.6-luna"
CODEX_TERRA_MODEL: Final = "codex/gpt-5.6-terra"
OPENROUTER_TERRA_MODEL: Final = "openrouter/openai/gpt-5.6-terra"
OPENROUTER_SOL_MODEL: Final = "openrouter/openai/gpt-5.6-sol"
CODEX_SUBSCRIPTION_MODELS: Final[frozenset[str]] = frozenset(
    {CODEX_LUNA_MODEL, CODEX_TERRA_MODEL}
)
_CODEX_LOGIN_MARKER = "Logged in using ChatGPT"


def is_codex_subscription_model(model: str) -> bool:
    """Return whether this exact route uses local ChatGPT Codex authentication."""
    return model in CODEX_SUBSCRIPTION_MODELS


def codex_subscription_available() -> bool:
    """Verify the local CLI exists and is currently authenticated by ChatGPT."""
    executable = shutil.which("codex")
    if executable is None:
        return False
    try:
        result = subprocess.run(
            [executable, "login", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    output = f"{result.stdout}\n{result.stderr}"
    return result.returncode == 0 and _CODEX_LOGIN_MARKER in output


@contextmanager
def structured_backend_options(model: str) -> Iterator[dict[str, object]]:
    """Yield isolated transport options for one structured shared-client call."""
    if not is_codex_subscription_model(model):
        yield {}
        return
    with tempfile.TemporaryDirectory(prefix="cybernetic-influence-codex-") as root:
        yield {
            "execution_mode": "workspace_agent",
            "codex_transport": "cli",
            "working_directory": root,
            "sandbox_mode": "read-only",
            "approval_policy": "never",
            "skip_git_repo_check": True,
            "mcp_servers": {},
            "model_policy": "enforce_allowlist",
        }
