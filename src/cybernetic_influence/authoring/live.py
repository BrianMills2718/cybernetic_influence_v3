"""Profile-derived native-LLM bindings for reviewed authored people."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from cybernetic_influence.active_runtime import (
    ActiveSystemBinding,
    ActiveSystemSpec,
    NativeLlmActiveSystem,
)
from cybernetic_influence.authoring.models import PersonDraft

AUTHORED_PERSON_TASK = "cybernetic_influence_v3_authored_person_step"

_PROFILE_LABELS = (
    ("values", "Values"),
    ("goals", "Goals"),
    ("beliefs", "Beliefs"),
    ("decision_tendencies", "Decision tendencies"),
    ("social_perceptions", "Perceived social conditions"),
    ("current_state", "Current state"),
    ("capabilities", "Described capabilities"),
    ("limitations", "Described limitations"),
)


def person_context(person: PersonDraft) -> str:
    """Render reviewed assumptions as declarative context, never commands."""

    lines = [
        f"Name: {person.label}.",
        f"Position: {person.label} is {person.position}.",
        f"Disposition: {person.disposition}",
    ]
    profile = person.behavioral_profile
    for field_name, label in _PROFILE_LABELS:
        statements = getattr(profile, field_name)
        if statements:
            lines.append(f"{label}:")
            lines.extend(f"- {statement}" for statement in statements)
    lines.append(
        "Described capabilities and limitations do not grant or remove an "
        "interface. Only the separately listed current interfaces determine "
        "what action can be attempted."
    )
    return "\n".join(lines)


def bind_authored_people(
    specs: Sequence[ActiveSystemSpec],
    people: Mapping[str, PersonDraft],
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str,
    retained_context: Mapping[str, Sequence[tuple[str, str]]] | None = None,
    structured_call: Any = None,
) -> tuple[tuple[ActiveSystemSpec, ...], dict[str, ActiveSystemBinding]]:
    """Replace scripted person identities with configuration-bound LLM policies."""

    extra_context = retained_context or {}
    live_specs: list[ActiveSystemSpec] = []
    bindings: dict[str, ActiveSystemBinding] = {}
    for spec in specs:
        person = people.get(spec.active_system_id)
        if person is None:
            raise ValueError(
                f"no reviewed person bound to active system {spec.active_system_id!r}"
            )
        implementation = NativeLlmActiveSystem.from_bound_configuration(
            implementation_family_id=f"native_authored_{spec.active_system_id}_v1",
            persona=person_context(person),
            model=model,
            task=AUTHORED_PERSON_TASK,
            trace_id_prefix=trace_id_prefix,
            reasoning_effort=reasoning_effort,
            max_memory_entries=32,
            max_output_tokens=384,
            structured_call=structured_call,
            decision_wire_contract="openai-json-payload-wire.v2",
        )
        memory = [
            {
                "logical_time": 0,
                "kind": "autobiographical_memory",
                "content": content,
            }
            for content in person.memories
        ]
        memory.extend(
            {
                "logical_time": 0,
                "kind": kind,
                "content": content,
            }
            for kind, content in extra_context.get(spec.active_system_id, ())
        )
        live_spec = spec.model_copy(
            deep=True,
            update={
                "implementation_id": implementation.implementation_id,
                "initial_private_state": {"memory": memory},
            },
        )
        live_specs.append(live_spec)
        bindings[spec.active_system_id] = ActiveSystemBinding(
            implementation.implementation_id,
            implementation,
        )
    return tuple(live_specs), bindings
