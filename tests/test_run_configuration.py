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
    RunLlmOptions,
    _current_coordination_schema_digests,
    _current_schema_digests,
    coordination_live_model_ids,
    llm_client_revision,
    model_catalog,
    resolve_live_configuration,
)


MODEL = "openrouter/openai/gpt-5.6-terra"


def test_local_package_revision_matches_shared_client_observation_format(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("LLM_CLIENT_REVISION", raising=False)
    monkeypatch.setattr("cybernetic_influence.run_configuration.version", lambda _: "0.7.0")

    assert llm_client_revision() == "package:0.7.0"


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


def _coordination_observation(
    schema_class: str,
    *,
    observed_at: datetime,
) -> RouteCertificationObservation:
    schema_digests = _current_coordination_schema_digests()
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
        selected_attempt_receipt_digest="c" * 64,
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
    assert catalog[0]["agent_reasoning_efforts"] == ["none", "low", "medium", "high"]
    assert catalog[0]["experimental_agent_reasoning_efforts"] == []
    assert catalog[0]["default_agent_reasoning_effort"] == "none"
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


def test_coordination_requires_every_current_person_schema_observation(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    store = RouteCertificationStore(tmp_path / "observations")
    participant = _observation("LlmDecision", observed_at=now)
    narrator = _observation("CausalMomentNarration", observed_at=now)
    coordination = [
        _coordination_observation(schema_class, observed_at=now)
        for schema_class in (_current_coordination_schema_digests() or {})
    ]
    for observation in [participant, narrator, *coordination]:
        store.append(observation)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_CLIENT_REVISION", "test-revision")
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
