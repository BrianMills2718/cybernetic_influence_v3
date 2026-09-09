from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from pytest import CaptureFixture, MonkeyPatch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "certify_codex_luna.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("certify_codex_luna_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sol_execution_certifies_only_general_execution_schemas(
    tmp_path: Path, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    module = _load_script()
    calls: list[str] = []

    def fake_certify(schema: type[object], **_: object) -> str:
        calls.append(schema.__name__)
        return f"obs_{schema.__name__}"

    monkeypatch.setattr(module, "_certify", fake_certify)
    monkeypatch.setattr(module, "llm_client_revision", lambda: "test-revision")
    monkeypatch.setattr(module, "_observability_db", lambda: tmp_path / "observability.db")
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path / "certification"))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "sol-execution"])

    module.main()

    assert calls == ["LlmDecision", "CausalMomentNarration"]
    output = capsys.readouterr().out
    assert output == (
        "CYBERNETIC_INFLUENCE_CERT_SOL="
        "obs_LlmDecision,obs_CausalMomentNarration\n"
    )
