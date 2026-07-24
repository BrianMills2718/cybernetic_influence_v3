"""Gates for evidence-derived live model advertisement."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from llm_client.route_certification import (
    RouteCertificationObservation,
    RouteCertificationStore,
)
from pytest import MonkeyPatch

from cybernetic_influence.run_configuration import (
    _current_schema_digests,
    model_catalog,
)


MODEL = "openrouter/openai/gpt-5.6-terra"


def _observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_schema_digests()
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
        llm_client_revision="test-revision",
        selected_attempt_receipt_digest="b" * 64,
        evidence_ref=f"/test/{schema_class}.json",
    )


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
    monkeypatch.setenv("LLM_CLIENT_REVISION", "test-revision")
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )

    catalog = model_catalog()
    assert [item["model"] for item in catalog] == [MODEL]
    assert catalog[0]["agent_reasoning_efforts"] == ["low", "medium", "high"]
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
    monkeypatch.setenv("LLM_CLIENT_REVISION", "test-revision")
    monkeypatch.setenv("LLM_ROUTE_CERTIFICATION_ROOT", str(tmp_path))
    monkeypatch.setenv(
        "CYBERNETIC_INFLUENCE_CERT_TERRA",
        f"{participant.observation_id},{narrator.observation_id}",
    )

    assert model_catalog() == []
