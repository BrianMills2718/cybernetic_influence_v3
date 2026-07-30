#!/usr/bin/env python3
"""Exercise and retain the exact simulator schemas through Codex Luna."""

from __future__ import annotations

import os
from pathlib import Path

from llm_client import (
    call_llm_structured,
    codex_native_provider_schema,
    compile_codex_structured_success,
)
from llm_client.route_certification import RouteCertificationStore
from pydantic import BaseModel

from cybernetic_influence.active_runtime.llm import LlmDecision
from cybernetic_influence.llm_backend import (
    CODEX_LUNA_MODEL,
    structured_backend_options,
)
from cybernetic_influence.narration import CausalMomentNarration
from cybernetic_influence.run_configuration import llm_client_revision
from cybernetic_influence.scenarios.coordination_decision import (
    COORDINATION_PERSON_DECISION_MODELS,
)


def _messages(schema: type[BaseModel]) -> list[dict[str, str]]:
    if schema is CausalMomentNarration:
        request = (
            "Return a concise account and one detailed paragraph stating that "
            "this schema-certification probe retained no scenario claim."
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


def _certify(
    schema: type[BaseModel],
    *,
    trace_id: str,
    store: RouteCertificationStore,
    evidence_root: Path,
) -> str:
    with structured_backend_options(CODEX_LUNA_MODEL) as backend_options:
        parsed, result = call_llm_structured(
            CODEX_LUNA_MODEL,
            _messages(schema),
            response_model=schema,
            task="cybernetic_influence_route_certification",
            trace_id=trace_id,
            max_budget=0.10,
            max_tokens=1000,
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
    observation = compile_codex_structured_success(
        result=result,
        provider_schema=codex_native_provider_schema(schema),
        schema_class=schema.__name__,
        trace_id=trace_id,
        llm_client_revision=llm_client_revision(),
        evidence_ref=(
            f"sqlite://{evidence_root.resolve()}#logical_call_id={logical_call_id}"
        ),
    )
    store.append(observation)
    return observation.observation_id


def main() -> None:
    data_root = Path(
        os.environ.get("LLM_CLIENT_DATA_ROOT", "~/projects/data")
    ).expanduser()
    certification_root = Path(
        os.environ.get(
            "LLM_ROUTE_CERTIFICATION_ROOT",
            "~/projects/data/llm_route_certification",
        )
    ).expanduser()
    store = RouteCertificationStore(certification_root / "observations")
    observability_db = data_root / "llm_observability.db"
    global_ids = [
        _certify(
            schema,
            trace_id=f"cybernetic-influence/certification/luna/{schema.__name__}",
            store=store,
            evidence_root=observability_db,
        )
        for schema in (LlmDecision, CausalMomentNarration)
    ]
    coordination_ids = [
        _certify(
            schema,
            trace_id=(
                "cybernetic-influence/certification/luna/coordination/"
                f"{schema.__name__}"
            ),
            store=store,
            evidence_root=observability_db,
        )
        for schema in COORDINATION_PERSON_DECISION_MODELS.values()
    ]
    print(f"CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA={','.join(global_ids)}")
    print(
        "CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_LUNA="
        f"{','.join(coordination_ids)}"
    )


if __name__ == "__main__":
    main()
