#!/usr/bin/env python3
"""Exercise and retain the exact simulator schemas through a Codex route."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import cast

import httpx
from llm_client import (
    call_llm_structured,
    compile_codex_structured_success,
)
from llm_client.route_certification_runtime import (
    observe_openrouter_native_success_from_runtime,
    openrouter_native_provider_schema,
)
from llm_client.route_certification import RouteCertificationStore
from pydantic import BaseModel

from cybernetic_influence.active_runtime.llm import LlmDecision
from cybernetic_influence.analysis.coordination_measurement import CoderOutput
from cybernetic_influence.experiments.coordination_experiment import (
    PRESSURE_SOURCE_DECISION_MODELS,
)
from cybernetic_influence.general_simulation.authoring_models import (
    DependencyCompletenessReviewV1,
)
from cybernetic_influence.general_simulation.study_models import (
    AuthoredSimulationProposalEnvelopeV2,
)
from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    CODEX_TERRA_MODEL,
    OPENROUTER_SOL_MODEL,
    OPENROUTER_TERRA_MODEL,
    is_codex_subscription_model,
    structured_backend_options,
)
from cybernetic_influence.narration import CausalMomentNarration
from cybernetic_influence.run_configuration import llm_client_revision
from cybernetic_influence.scenarios.coordination_decision import (
    COORDINATION_PERSON_DECISION_MODELS,
)


def _messages(schema: type[BaseModel]) -> list[dict[str, str]]:
    if schema is AuthoredSimulationProposalEnvelopeV2:
        request = (
            "Create a compact valid simulation of one person receiving a message "
            "and recording it. Do not add an analyst question or analysis."
        )
    elif schema is DependencyCompletenessReviewV1:
        request = (
            "Return status complete, a concise schema-certification summary, and "
            "no missing dependencies."
        )
    elif schema is CausalMomentNarration:
        request = (
            "Return a concise account and one detailed paragraph stating that "
            "this schema-certification probe retained no scenario claim."
        )
    elif schema is CoderOutput:
        request = (
            "Classify conditional_trust_episode, "
            "precautionary_hedging_episode, and relevance_classification as "
            "unclear. Give each a concise explanation that this is only a "
            "schema-certification probe with no scenario evidence."
        )
    else:
        request = (
            "Return a valid decision with a concise orientation, a blank memory "
            "update, no actions, and a nonempty silence reason. This is only a "
            "schema-certification probe and contains no scenario evidence."
        )
    return [
        {
            "role": "system",
            "content": "Produce only the requested structured result.",
        },
        {"role": "user", "content": request},
    ]


# The free Codex subscription routes bill nothing, so this ceiling only ever
# binds on a metered route -- and it was set below what the metered route
# actually costs. Certifying the 8000-token proposal envelope over Sol came to
# $0.1608 on 2026-08-26 and raised LLMBudgetExceededError against the $0.10
# limit, which means the paid fallback in refresh_authoring_certification.py had
# never once completed: the "a demo going dark costs more than a fraction of a
# dollar" path was unrunnable from the day it was written, and nothing would
# have discovered that except the free route failing during a demo.
# Sized to roughly twice the observed cost of the larger schema.
_METERED_BUDGET_BY_SCHEMA = {"AuthoredSimulationProposalEnvelopeV2": 0.35}
_DEFAULT_CERTIFICATION_BUDGET = 0.10


def _certification_budget(schema: type[BaseModel], model: str) -> float:
    if is_codex_subscription_model(model):
        return _DEFAULT_CERTIFICATION_BUDGET
    return _METERED_BUDGET_BY_SCHEMA.get(
        schema.__name__, _DEFAULT_CERTIFICATION_BUDGET
    )


def _observability_db() -> Path:
    """Where llm_client actually writes the call records, per its own contract.

    This used to be built as LLM_CLIENT_DATA_ROOT / "llm_observability.db",
    which is two different mistakes at once: LLM_CLIENT_DATA_ROOT is the root of
    the *JSONL* logs (and llm_client namespaces a project directory underneath
    it), while the SQLite mirror these evidence refs point into is addressed by
    LLM_CLIENT_DB_PATH, a separate variable with a separate default. On the
    deployment the two resolve to different files, and the one being referenced
    was 0 bytes -- so 102 of 220 retained certifications named an evidence store
    that had never been written. The evidence itself was always fine, in the
    321MB database the other variable names.

    Env var and default are llm_client/io_log.py's documented interface; the
    resolver itself (_db_path) is private, so this mirrors the contract rather
    than importing it.
    """
    return Path(
        os.environ.get(
            "LLM_CLIENT_DB_PATH", "~/projects/data/llm_observability.db"
        )
    ).expanduser()


def _certify(
    schema: type[BaseModel],
    *,
    model: str,
    trace_id: str,
    store: RouteCertificationStore,
    evidence_root: Path,
    llm_client_revision_value: str,
) -> str:
    with structured_backend_options(model) as backend_options:
        parsed, result = call_llm_structured(
            model,
            _messages(schema),
            response_model=schema,
            task="cybernetic_influence_route_certification",
            trace_id=trace_id,
            max_budget=_certification_budget(schema, model),
            max_tokens=(
                8000 if schema is AuthoredSimulationProposalEnvelopeV2 else 1000
            ),
            reasoning_effort="medium",
            model_justification=(
                "Certify the exact simulator schema through the selected "
                "subscription-backed Codex route."
            ),
            **backend_options,
        )
    schema.model_validate(
        parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
    )
    logical_call_id = result.logical_call_id
    if not logical_call_id:
        raise RuntimeError(f"{schema.__name__} call retained no logical_call_id")
    if is_codex_subscription_model(model):
        observation = compile_codex_structured_success(
            result=result,
            response_model=schema,
            trace_id=trace_id,
            llm_client_revision=llm_client_revision_value,
            evidence_ref=(
                f"sqlite://{evidence_root.resolve()}#logical_call_id={logical_call_id}"
            ),
        )
        store.append(observation)
    else:
        for metadata_attempt in range(3):
            try:
                observation = observe_openrouter_native_success_from_runtime(
                    result=result,
                    provider_schema=openrouter_native_provider_schema(schema),
                    schema_class=schema.__name__,
                )
                break
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 404 or metadata_attempt == 2:
                    raise
                time.sleep(8 * (metadata_attempt + 1))
    return cast(str, observation.observation_id)


def main() -> None:
    route = sys.argv[1] if len(sys.argv) > 1 else "luna"
    authoring_routes = {
        "luna-authoring": (CODEX_LUNA_MODEL, "CYBERNETIC_INFLUENCE_CERT_AUTHORING_CODEX_LUNA"),
        "openrouter-terra-authoring": (
            OPENROUTER_TERRA_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_AUTHORING_TERRA",
        ),
        "sol-authoring": (
            OPENROUTER_SOL_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL",
        ),
    }
    execution_only_routes = {
        "sol-execution": (OPENROUTER_SOL_MODEL, "CYBERNETIC_INFLUENCE_CERT_SOL"),
    }
    if route in execution_only_routes:
        model, execution_env = execution_only_routes[route]
        revision = llm_client_revision()
        certification_root = Path(
            os.environ.get(
                "LLM_ROUTE_CERTIFICATION_ROOT",
                "~/projects/data/llm_route_certification",
            )
        ).expanduser()
        store = RouteCertificationStore(certification_root / "observations")
        observability_db = _observability_db()
        ids = [
            _certify(
                schema,
                model=model,
                trace_id=(
                    f"cybernetic-influence/certification/{route}/"
                    f"{schema.__name__}"
                ),
                store=store,
                evidence_root=observability_db,
                llm_client_revision_value=revision,
            )
            for schema in (LlmDecision, CausalMomentNarration)
        ]
        print(f"{execution_env}=" + ",".join(ids))
        return
    if route in authoring_routes:
        model, authoring_env = authoring_routes[route]
        revision = llm_client_revision()
        certification_root = Path(
            os.environ.get(
                "LLM_ROUTE_CERTIFICATION_ROOT",
                "~/projects/data/llm_route_certification",
            )
        ).expanduser()
        store = RouteCertificationStore(certification_root / "observations")
        observability_db = _observability_db()
        ids = [
            _certify(
                schema,
                model=model,
                trace_id=(
                    f"cybernetic-influence/certification/{route}/"
                    f"{schema.__name__}"
                ),
                store=store,
                evidence_root=observability_db,
                llm_client_revision_value=revision,
            )
            for schema in (
                AuthoredSimulationProposalEnvelopeV2,
                DependencyCompletenessReviewV1,
            )
        ]
        print(f"{authoring_env}=" + ",".join(ids))
        return
    routes = {
        "luna": (
            CODEX_LUNA_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA",
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_LUNA",
        ),
        "terra": (
            CODEX_TERRA_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_CODEX_TERRA",
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_TERRA",
        ),
        "openrouter-terra": (
            OPENROUTER_TERRA_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_TERRA",
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA",
        ),
        "sol": (
            OPENROUTER_SOL_MODEL,
            "CYBERNETIC_INFLUENCE_CERT_SOL",
            "CYBERNETIC_INFLUENCE_CERT_COORDINATION_SOL",
        ),
    }
    try:
        model, global_env, coordination_env = routes[route]
    except KeyError as error:
        raise SystemExit(
            "usage: certify_codex_luna.py "
            "[luna|luna-authoring|terra|openrouter-terra|"
            "openrouter-terra-authoring|sol|sol-authoring|sol-execution]"
        ) from error
    revision = llm_client_revision()
    certification_root = Path(
        os.environ.get(
            "LLM_ROUTE_CERTIFICATION_ROOT",
            "~/projects/data/llm_route_certification",
        )
    ).expanduser()
    store = RouteCertificationStore(certification_root / "observations")
    observability_db = _observability_db()
    global_ids = [
        _certify(
            schema,
            model=model,
            trace_id=f"cybernetic-influence/certification/{route}/{schema.__name__}",
            store=store,
            evidence_root=observability_db,
            llm_client_revision_value=revision,
        )
        for schema in (LlmDecision, CausalMomentNarration)
    ]
    coordination_schemas: tuple[type[BaseModel], ...] = (
        *COORDINATION_PERSON_DECISION_MODELS.values(),
        *PRESSURE_SOURCE_DECISION_MODELS.values(),
        CoderOutput,
    )
    coordination_ids = [
        _certify(
            schema,
            model=model,
            trace_id=(
                f"cybernetic-influence/certification/{route}/coordination/"
                f"{schema.__name__}"
            ),
            store=store,
            evidence_root=observability_db,
            llm_client_revision_value=revision,
        )
        for schema in coordination_schemas
    ]
    print(f"{global_env}={','.join(global_ids)}")
    print(f"{coordination_env}={','.join(coordination_ids)}")


if __name__ == "__main__":
    main()
