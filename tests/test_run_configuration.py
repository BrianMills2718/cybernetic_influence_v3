"""Gates for evidence-derived live model advertisement."""

from __future__ import annotations

import plistlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from llm_client import installed_llm_client_revision
from llm_client.route_certification import (
    RouteCertificationObservation,
    RouteCertificationStore,
)
from pytest import MonkeyPatch

from cybernetic_influence.run_configuration import (
    RunLlmOptions,
    _current_authoring_schema_digests,
    _current_coordination_schema_digests,
    _current_schema_digests,
    authoring_model_ids,
    coordination_live_model_ids,
    live_options_contract,
    llm_client_revision,
    model_catalog,
    resolve_live_configuration,
)

MODEL = "openrouter/openai/gpt-5.6-terra"
SOL_MODEL = "openrouter/openai/gpt-5.6-sol"
CODEX_MODEL = "codex/gpt-5.6-terra"
CODEX_LUNA_MODEL = "codex/gpt-5.6-luna"
ROOT = Path(__file__).resolve().parents[1]
CLIENT_REVISION = installed_llm_client_revision()


def test_launch_agent_binds_global_and_coordination_certification_groups() -> None:
    with (ROOT / "deploy" / "com.cybernetic-influence.v3.plist").open("rb") as stream:
        launch_agent = plistlib.load(stream)

    environment = launch_agent["EnvironmentVariables"]
    assert environment["CYBERNETIC_INFLUENCE_CERT_TERRA"] == "__CERT_TERRA__"
    assert environment["CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA"] == (
        "__CERT_CODEX_LUNA__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA"] == (
        "__CERT_AUTHORING_CODEX_LUNA__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_CODEX_TERRA"] == (
        "__CERT_CODEX_TERRA__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH"] == (
        "__CERT_DEEPSEEK_V4_FLASH__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA"] == (
        "__CERT_COORDINATION_TERRA__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_LUNA"] == (
        "__CERT_COORDINATION_CODEX_LUNA__"
    )
    assert environment["CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_TERRA"] == (
        "__CERT_COORDINATION_CODEX_TERRA__"
    )
    assert environment["LLM_CLIENT_AGENT_BILLING_MODE"] == "subscription"
    assert environment["LLM_CLIENT_OPENROUTER_ROUTING"] == "off"
    assert environment[
        "CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH"
    ] == "__CERT_COORDINATION_DEEPSEEK_V4_FLASH__"

    launcher = (ROOT / "deploy" / "run-with-provider-secret.sh").read_text()
    assert "validated_llm_client_revision" in launcher


def test_local_revision_uses_validated_shared_client(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.validated_llm_client_revision",
        lambda: "installed-revision",
    )

    assert llm_client_revision() == "installed-revision"


def test_local_revision_rejects_a_false_deployment_binding(
    monkeypatch: MonkeyPatch,
) -> None:
    def reject() -> str:
        raise ValueError("configured llm_client revision does not match installed code")

    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.validated_llm_client_revision",
        reject,
    )

    with pytest.raises(ValueError, match="does not match installed code"):
        llm_client_revision()


def _observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_schema_digests(MODEL)
    assert schema_digests is not None
    return RouteCertificationObservation.build(
        requested_model=MODEL,
        resolved_model=MODEL,
        upstream_provider_name="test provider",
        upstream_provider_endpoint="test-endpoint",
        execution_mode="native_json_schema",
        schema_class=schema_class,
        schema_sha256=schema_digests[schema_class],
        outcome="parseable",
        failure_stage="none",
        logical_call_id=f"logical-{schema_class}",
        trace_id=f"trace-{schema_class}",
        observed_at=observed_at,
        llm_client_revision=CLIENT_REVISION,
        selected_attempt_receipt_digest="b" * 64,
        evidence_ref=f"/test/{schema_class}.json",
    )


def _coordination_observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_coordination_schema_digests(MODEL)
    assert schema_digests is not None
    return RouteCertificationObservation.build(
        requested_model=MODEL,
        resolved_model=MODEL,
        upstream_provider_name="test provider",
        upstream_provider_endpoint="test-endpoint",
        execution_mode="native_json_schema",
        schema_class=schema_class,
        schema_sha256=schema_digests[schema_class],
        outcome="parseable",
        failure_stage="none",
        logical_call_id=f"logical-{schema_class}",
        trace_id=f"trace-{schema_class}",
        observed_at=observed_at,
        llm_client_revision=CLIENT_REVISION,
        selected_attempt_receipt_digest="c" * 64,
        evidence_ref=f"/test/{schema_class}.json",
    )


def _codex_observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_schema_digests(CODEX_MODEL)
    assert schema_digests is not None
    return RouteCertificationObservation.build(
        requested_model=CODEX_MODEL,
        resolved_model=CODEX_MODEL,
        upstream_provider_name="OpenAI Codex subscription",
        upstream_provider_endpoint="codex_cli",
        execution_mode="workspace_agent",
        schema_class=schema_class,
        schema_sha256=schema_digests[schema_class],
        outcome="parseable",
        failure_stage="none",
        logical_call_id=f"logical-{schema_class}",
        trace_id=f"trace-{schema_class}",
        observed_at=observed_at,
        llm_client_revision=CLIENT_REVISION,
        selected_attempt_receipt_digest=None,
        evidence_ref=f"/test/{schema_class}.json",
    )


def _codex_authoring_observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_authoring_schema_digests(CODEX_LUNA_MODEL)
    assert schema_digests is not None
    return RouteCertificationObservation.build(
        requested_model=CODEX_LUNA_MODEL,
        resolved_model=CODEX_LUNA_MODEL,
        upstream_provider_name="OpenAI Codex subscription",
        upstream_provider_endpoint="codex_cli",
        execution_mode="workspace_agent",
        schema_class=schema_class,
        schema_sha256=schema_digests[schema_class],
        outcome="parseable",
        failure_stage="none",
        logical_call_id=f"logical-authoring-{schema_class}",
        trace_id=f"trace-authoring-{schema_class}",
        observed_at=observed_at,
        llm_client_revision=CLIENT_REVISION,
        selected_attempt_receipt_digest=None,
        evidence_ref=f"/test/authoring-{schema_class}.json",
    )


def test_authoring_catalog_requires_exact_proposal_and_review_certifications(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    store = RouteCertificationStore(tmp_path / "observations")
    observations = [
        _codex_authoring_observation(schema_class, observed_at=now)
        for schema_class in (_current_authoring_schema_digests(CODEX_LUNA_MODEL) or {})
    ]
    for observation in observations:
        store.append(observation)
    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.codex_subscription_available",
        lambda: True,
    )
    monkeypatch.setenv("LLM_CLIENT_REVISION", CLIENT_REVISION)
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA",
        ",".join(item.observation_id for item in observations),
    )

    assert authoring_model_ids() == [CODEX_LUNA_MODEL]

    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA",
        observations[0].observation_id,
    )
    assert authoring_model_ids() == []


def test_codex_catalog_requires_login_and_exact_schema_observations(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    store = RouteCertificationStore(tmp_path / "observations")
    participant = _codex_observation("LlmDecision", observed_at=now)
    narrator = _codex_observation("CausalMomentNarration", observed_at=now)
    store.append(participant)
    store.append(narrator)
    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.codex_subscription_available",
        lambda: True,
    )
    monkeypatch.setenv("LLM_CLIENT_REVISION", CLIENT_REVISION)
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_CODEX_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )

    catalog = model_catalog()

    assert [item["model"] for item in catalog] == [CODEX_MODEL]
    assert catalog[0]["agent_reasoning_efforts"] == ["medium"]
    assert catalog[0]["default_agent_reasoning_effort"] == "medium"
    assert catalog[0]["narrator_reasoning_effort"] == "medium"
    assert catalog[0]["availability_basis"] == (
        "verified local ChatGPT Codex login"
    )
    assert catalog[0]["billing_mode"] == "subscription_included"

    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.codex_subscription_available",
        lambda: False,
    )
    assert model_catalog() == []


def test_model_catalog_requires_two_current_replayed_schema_observations(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    store = RouteCertificationStore(tmp_path / "observations")
    participant = _observation("LlmDecision", observed_at=now)
    narrator = _observation("CausalMomentNarration", observed_at=now)
    store.append(participant)
    store.append(narrator)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CLIENT_REVISION", CLIENT_REVISION)
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )

    catalog = model_catalog()
    assert [item["model"] for item in catalog] == [MODEL]
    assert catalog[0]["agent_reasoning_efforts"] == ["none", "low", "medium", "high"]
    assert catalog[0]["experimental_agent_reasoning_efforts"] == []
    assert catalog[0]["default_agent_reasoning_effort"] == "medium"
    assert catalog[0]["narrator_reasoning_effort"] == "low"

    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        participant.observation_id,
    )
    assert model_catalog() == []


def test_stale_route_observations_do_not_advertise(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    stale = datetime.now(timezone.utc) - timedelta(days=8)
    store = RouteCertificationStore(tmp_path / "observations")
    participant = _observation("LlmDecision", observed_at=stale)
    narrator = _observation("CausalMomentNarration", observed_at=stale)
    store.append(participant)
    store.append(narrator)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CLIENT_REVISION", CLIENT_REVISION)
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )

    assert model_catalog() == []


def test_coordination_requires_every_current_execution_and_analysis_schema(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    store = RouteCertificationStore(tmp_path / "observations")
    participant = _observation("LlmDecision", observed_at=now)
    narrator = _observation("CausalMomentNarration", observed_at=now)
    coordination = [
        _coordination_observation(schema_class, observed_at=now)
        for schema_class in (_current_coordination_schema_digests(MODEL) or {})
    ]
    assert "CoderOutput" in {
        item.schema_class.rsplit(".", maxsplit=1)[-1] for item in coordination
    }
    assert {
        "TechnicalPressureSourceDecision",
        "PolicyPressureSourceDecision",
        "LocalPressureSourceDecision",
    }.issubset({item.schema_class for item in coordination})
    for observation in [participant, narrator, *coordination]:
        store.append(observation)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CLIENT_REVISION", CLIENT_REVISION)
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA",
        ",".join(item.observation_id for item in coordination),
    )

    assert coordination_live_model_ids() == [MODEL]

    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA",
        ",".join(item.observation_id for item in coordination[:-1]),
    )
    assert coordination_live_model_ids() == []


def test_experimental_deepseek_effort_is_resolved_without_claiming_certification(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.model_catalog",
        lambda: [
            {
                "model": "openrouter/deepseek/deepseek-v4-flash",
                "agent_reasoning_efforts": ["none", "high", "xhigh"],
                "experimental_agent_reasoning_efforts": ["high", "xhigh"],
                "narrator_reasoning_effort": "none",
                "billing_mode": "usage_based",
            }
        ],
    )

    resolved = resolve_live_configuration(
        RunLlmOptions(
            model="openrouter/deepseek/deepseek-v4-flash",
            agent_reasoning_effort="xhigh",
            max_total_cost=0.20,
        )
    )

    assert resolved.agent_reasoning_effort == "xhigh"
    assert resolved.narrator_reasoning_effort == "none"


def test_server_default_prefers_sol_and_falls_back_when_unavailable(
    monkeypatch: MonkeyPatch,
) -> None:
    """PREFERRED_MODEL is Sol while Luna's Codex subscription quota is
    exhausted (see run_configuration.py); falls back to whatever remains in
    the catalog when Sol itself is unavailable."""

    def choice(model: str, billing_mode: str) -> dict[str, object]:
        return {
            "model": model,
            "agent_reasoning_efforts": ["medium"],
            "default_agent_reasoning_effort": "medium",
            "narrator_reasoning_effort": "medium",
            "billing_mode": billing_mode,
        }

    luna = choice("codex/gpt-5.6-luna", "subscription_included")
    sol = choice(SOL_MODEL, "usage_based")
    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.model_catalog",
        lambda: [luna, sol],
    )
    assert resolve_live_configuration(None).model == SOL_MODEL
    assert live_options_contract()["defaults"]["model"] == SOL_MODEL  # type: ignore[index]

    monkeypatch.setattr(
        "cybernetic_influence.run_configuration.model_catalog",
        lambda: [luna],
    )
    assert resolve_live_configuration(None).model == "codex/gpt-5.6-luna"
    assert live_options_contract()["defaults"]["model"] == "codex/gpt-5.6-luna"  # type: ignore[index]
