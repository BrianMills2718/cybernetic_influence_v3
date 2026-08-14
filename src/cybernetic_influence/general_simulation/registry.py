"""Trusted implementation registry for semantic behavior requests."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .authoring_models import ComponentRequestV1


class RegisteredComponentV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    component_kind: str
    version: int
    implementation_ref: str
    configuration_schema_ref: str
    read_scope_schema: list[str]
    patch_operations: list[Literal["create", "remove", "replace", "rebind"]]
    patch_record_types: list[
        Literal["record", "place", "placement", "route", "representation", "resource"]
    ]
    fidelity: Literal["exact", "coarse_llm", "descriptive"]
    assumptions: list[str]
    invalid_questions: list[str]
    causal_responsibility_tags: list[str]
    semantic_triggers: list[str]
    what_can_change: list[str]
    what_cannot_change: list[str]

    @property
    def ref(self) -> str:
        return f"{self.component_kind}@{self.version}"


def default_registry() -> tuple[RegisteredComponentV1, ...]:
    return (
        RegisteredComponentV1(
            component_kind="spatial_topology",
            version=1,
            implementation_ref="general_simulation.world:spatial_topology_v1",
            configuration_schema_ref="SpatialExtensionV1",
            read_scope_schema=["places", "placements", "routes"],
            patch_operations=["create", "remove", "replace", "rebind"],
            patch_record_types=["place", "placement", "route"],
            fidelity="exact",
            assumptions=["links are abstract traversable connections, not detailed physics"],
            invalid_questions=["vehicle dynamics", "continuous geometry"],
            causal_responsibility_tags=["location", "movement", "topology"],
            semantic_triggers=["move", "movement", "route", "placement", "transport", "travel"],
            what_can_change=["places", "placements", "route availability"],
            what_cannot_change=["continuous physical dynamics"],
        ),
        RegisteredComponentV1(
            component_kind="information_delivery",
            version=1,
            implementation_ref="general_simulation.world:information_delivery_v1",
            configuration_schema_ref="InformationExtensionV1",
            read_scope_schema=["representations", "recipients", "schedule"],
            patch_operations=["create"],
            patch_record_types=["representation"],
            fidelity="exact",
            assumptions=["delivery is exact only at the configured routing boundary"],
            invalid_questions=["unmodeled channel interpretation"],
            causal_responsibility_tags=["information", "delivery", "observation"],
            semantic_triggers=["message", "information", "deliver", "observation", "claim"],
            what_can_change=["delivered representations", "actor observations"],
            what_cannot_change=["actor belief automatically"],
        ),
        RegisteredComponentV1(
            component_kind="conserved_resources",
            version=1,
            implementation_ref="general_simulation.world:conserved_resources_v1",
            configuration_schema_ref="ResourceExtensionV1",
            read_scope_schema=["resources", "custody"],
            patch_operations=["create", "replace", "rebind"],
            patch_record_types=["resource"],
            fidelity="exact",
            assumptions=["declared stock quantities are the complete conserved boundary"],
            invalid_questions=["undeclared resource substitution"],
            causal_responsibility_tags=["resource", "custody", "conservation"],
            semantic_triggers=[
                "resource",
                "stock",
                "fuel",
                "battery",
                "charge",
                "consume",
                "consumption",
                "allocate",
                "conserve",
                "custody",
            ],
            what_can_change=["resource quantity", "resource custody"],
            what_cannot_change=["undeclared resources"],
        ),
        RegisteredComponentV1(
            component_kind="bounded_person_action",
            version=1,
            implementation_ref="general_simulation.actors:bounded_person_action_v1",
            configuration_schema_ref="PersonDraft+ActorContext",
            read_scope_schema=["authorized_actor_context", "private_memory"],
            patch_operations=[],
            patch_record_types=[],
            fidelity="coarse_llm",
            assumptions=["Luna role behavior is synthetic and not a calibrated human model"],
            invalid_questions=["prediction of a named real person"],
            causal_responsibility_tags=["interpretation", "choice", "intent"],
            semantic_triggers=[
                "assess",
                "choose",
                "decide",
                "interpret",
                "prioritize",
                "propose",
                "reason",
                "recommend",
                "open-ended action",
                "bounded action",
            ],
            what_can_change=["private memory", "semantic action intent"],
            what_cannot_change=["canonical world state directly"],
        ),
        RegisteredComponentV1(
            component_kind="joint_semantic_adjudication",
            version=1,
            implementation_ref="general_simulation.authorities:joint_semantic_adjudication_v1",
            configuration_schema_ref="TransitionAuthoritySpec",
            read_scope_schema=["declared_adjudicator_context", "semantic_intents"],
            patch_operations=["create", "remove", "replace", "rebind"],
            patch_record_types=["record", "placement", "route", "resource"],
            fidelity="coarse_llm",
            assumptions=["one bounded Luna authority adjudicates the same-moment intent batch"],
            invalid_questions=["stable transition probabilities", "unregistered exact physics"],
            causal_responsibility_tags=["joint_resolution", "adjudication", "coordination"],
            semantic_triggers=[
                "adjudicate",
                "apply",
                "attempt",
                "change",
                "coordinate",
                "decision",
                "enact",
                "execute",
                "recovery",
                "restore",
                "joint plan",
                "resolve competing",
                "agree",
            ],
            what_can_change=["registered canonical records through validated transactions"],
            what_cannot_change=["unregistered state", "actor private memory"],
        ),
    )


def registry_digest(registry: tuple[RegisteredComponentV1, ...]) -> str:
    payload = [item.model_dump(mode="json") for item in registry]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def resolve_request(
    request: ComponentRequestV1,
    registry: tuple[RegisteredComponentV1, ...],
    *,
    actor_ids: set[str] | None = None,
) -> tuple[RegisteredComponentV1 | None, list[str]]:
    description = request.behavior_description.lower()
    effects = " ".join(request.desired_effects).lower()
    description_tokens = set(re.findall(r"[a-z0-9_]+", description))
    effect_tokens = set(re.findall(r"[a-z0-9_]+", effects))
    scored: list[tuple[int, RegisteredComponentV1, list[str]]] = []
    for entry in registry:
        matches = []
        score = 0
        description_positions: list[int] = []
        for trigger in entry.semantic_triggers:
            normalized = trigger.replace("-", "_")
            in_description = trigger in description or normalized in description_tokens
            in_effects = trigger in effects or normalized in effect_tokens
            if not in_description and not in_effects:
                continue
            matches.append(trigger)
            score += 3 if in_description else 1
            if in_description:
                positions = [
                    position
                    for candidate in (trigger, normalized)
                    if (position := description.find(candidate)) >= 0
                ]
                if positions:
                    description_positions.append(min(positions))
        if matches:
            if description_positions:
                score += max(0, 6 - min(description_positions) // 12)
            scored.append((score, entry, matches))
    if not scored:
        return None, ["no registered semantic trigger matched the requested behavior"]
    scored.sort(key=lambda item: (-item[0], item[1].ref))
    best_score, best, matches = scored[0]
    tied_entries = [item[1] for item in scored if item[0] == best_score]
    tied = [item.ref for item in tied_entries]
    if len(tied) > 1:
        actor_subjects = set(request.subject_refs) & (actor_ids or set())
        person_entry = next(
            (item for item in tied_entries if item.component_kind == "bounded_person_action"),
            None,
        )
        joint_entry = next(
            (
                item
                for item in tied_entries
                if item.component_kind == "joint_semantic_adjudication"
            ),
            None,
        )
        if (
            person_entry is not None
            and len(actor_subjects) == 1
            and request.subject_refs[0] in actor_subjects
        ):
            return person_entry, [
                "resolved equal semantic scores to the one named actor's bounded action"
            ]
        if joint_entry is not None and len(actor_subjects) != 1:
            return joint_entry, [
                "resolved equal semantic scores to joint adjudication over multiple or "
                "non-person subjects"
            ]
        return None, [f"ambiguous registry match at score {best_score}: {', '.join(tied)}"]
    return best, [f"matched trusted registry triggers: {', '.join(sorted(matches))}"]
