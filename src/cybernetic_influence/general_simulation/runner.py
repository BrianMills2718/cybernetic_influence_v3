"""General group execution on stock Concordia's simultaneous engine."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
from concordia.agents import entity_agent
from concordia.associative_memory import basic_associative_memory
from concordia.components.game_master import next_acting as concordia_next_acting
from concordia.environment.engines import simultaneous
from concordia.language_model import language_model, no_language_model
from concordia.prefabs.simulation import generic
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component, prefab
from pydantic import TypeAdapter

from .authoring_models import GeneralPersonDraft, GeneralSimulationProposalV1
from .compiler import CompiledGeneralSimulationV1
from .concordia_runtime import (
    ACTOR_CONTEXT_COMPONENT,
    CONCORDIA_REVISION,
    INBOX_COMPONENT,
    WORLD_COMPONENT,
    ActorContextComponent,
    InboxComponent,
    MemoryViewComponent,
    StructuredCall,
    _call_model,
    _structured_call,
)
from .models import (
    ActorContext,
    ActorDecision,
    AdoptionReceipt,
    GeneralGroupSimulationResult,
    GeneralMomentEvidence,
    ModelCallReceipt,
    ObjectiveAssessment,
    SemanticActionIntent,
    TypedTarget,
    WorldTransaction,
)
from .world import CanonicalWorld


ProgressObserver = Callable[[dict[str, Any], dict[str, Any]], None]


def _normalize_existing_target(
    target: TypedTarget,
    world: CanonicalWorld,
    *,
    correction_context: str,
    corrections: list[str],
) -> TypedTarget:
    containers: dict[str, Mapping[str, object]] = {
        "record": world.state.records,
        "place": world.state.places,
        "placement": world.state.placements,
        "route": world.state.routes,
        "representation": world.state.representations,
        "resource": world.state.resources,
    }
    if target.record_id in containers[target.record_type]:
        return target
    matching_types = [
        record_type
        for record_type, records in containers.items()
        if target.record_id in records
    ]
    if len(matching_types) != 1:
        return target
    corrected_type = matching_types[0]
    corrections.append(
        f"{correction_context} target {target.record_id} normalized from "
        f"{target.record_type} to {corrected_type}"
    )
    return target.model_copy(update={"record_type": corrected_type})


def _normalize_transaction_targets(
    transaction: WorldTransaction,
    world: CanonicalWorld,
    corrections: list[str],
) -> WorldTransaction:
    operations = [
        operation
        if operation.operation == "create"
        else operation.model_copy(
            update={
                "target": _normalize_existing_target(
                    operation.target,
                    world,
                    correction_context="operation",
                    corrections=corrections,
                )
            }
        )
        for operation in transaction.operations
    ]
    preconditions = [
        precondition.model_copy(
            update={
                "target": _normalize_existing_target(
                    precondition.target,
                    world,
                    correction_context="precondition",
                    corrections=corrections,
                )
            }
        )
        for precondition in transaction.preconditions
    ]
    return transaction.model_copy(
        update={"operations": operations, "preconditions": preconditions}
    )


def _normalized_memory(value: str) -> str:
    return " ".join(value.lower().split())


def _memory_reference_is_grounded(reference: str, memories: set[str]) -> bool:
    """Accept one unambiguous retained-memory citation.

    Natural-language models sometimes cite the relevant leading sentence(s) of
    a retained memory instead of copying a later, unrelated sentence.  Treat a
    unique sentence-boundary prefix as a reference to that retained string,
    while continuing to reject paraphrases, fragments, and ambiguous prefixes.
    """
    normalized = _normalized_memory(reference)
    if not normalized:
        return False
    exact_matches = {memory for memory in memories if memory == normalized}
    if exact_matches:
        return True
    if len(normalized) < 24 or normalized[-1] not in ".?!":
        return False
    prefix_matches = {
        memory
        for memory in memories
        if memory.startswith(normalized) and len(memory) > len(normalized)
    }
    return len(prefix_matches) == 1


def _checkpoint_hash(checkpoint: Mapping[str, Any]) -> str:
    encoded = json.dumps(checkpoint, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _strict_general_checkpoint(
    checkpoint: Mapping[str, Any],
    compiled: CompiledGeneralSimulationV1,
) -> dict[str, Any]:
    """Validate a persisted Concordia checkpoint before loading it.

    Stock Concordia deliberately tolerates missing names while restoring.  A
    resumable experiment cannot: silently omitting one actor, its memory, or
    the canonical world would create a different execution prefix.
    """
    try:
        retained = json.loads(json.dumps(dict(checkpoint)))
        expected_actors = {person.entity_id for person in compiled.proposal.people}
        entities = retained["entities"]
        game_masters = retained["game_masters"]
        if set(entities) != expected_actors:
            raise ValueError("checkpoint actor set differs from the approved proposal")
        if set(game_masters) != {"general_world_game_master"}:
            raise ValueError("checkpoint game-master set is incomplete")
        for actor_id in expected_actors:
            context = entities[actor_id]["components"]["context_components"]
            if set(context) != {ACTOR_CONTEXT_COMPONENT, "__memory__"}:
                raise ValueError(f"checkpoint components are incomplete for {actor_id}")
            entities[actor_id]["components"]["act_component"]["receipts"]
        gm_components = game_masters["general_world_game_master"]["components"]
        gm_components["act_component"]["moments"]
        gm_context = gm_components["context_components"]
        if set(gm_context) != {
            WORLD_COMPONENT,
            INBOX_COMPONENT,
            concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
        }:
            raise ValueError("checkpoint game-master components are incomplete")
        world_state = gm_context[WORLD_COMPONENT]
        restored_world = CanonicalWorld(compiled.world_spec)
        restored_world.set_state(world_state)
        completed = len(gm_components["act_component"]["moments"])
        if completed > len(compiled.proposal.schedule):
            raise ValueError("checkpoint contains more moments than the approved schedule")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid or incomplete general-simulation checkpoint") from exc
    return cast(dict[str, Any], retained)


class GeneralActorActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(
        self,
        call: StructuredCall,
        *,
        person: GeneralPersonDraft,
        question: str,
        trace_prefix: str,
    ) -> None:
        self._call = call
        self._person = person.model_copy(deep=True)
        self._question = question
        self._trace_prefix = trace_prefix
        self.receipts: list[ModelCallReceipt] = []
        self.activation_count = 0

    def _validate_decision(
        self, decision: ActorDecision, actor_context: ActorContext
    ) -> None:
        if decision.intent.actor_id != actor_context.actor_id:
            raise ValueError(
                f"actor_id must be {actor_context.actor_id!r}; received "
                f"{decision.intent.actor_id!r}"
            )
        if decision.intent.base_revision != actor_context.base_revision:
            raise ValueError(
                f"base_revision must be {actor_context.base_revision}; received "
                f"{decision.intent.base_revision}"
            )
        available_observations = {
            item.observation_id for item in actor_context.observations
        }
        unknown_attention = (
            set(decision.assimilation.attended_observation_ids)
            - available_observations
        )
        if unknown_attention:
            raise ValueError(
                "attended_observation_ids contained unavailable IDs "
                f"{sorted(unknown_attention)}; allowed IDs are "
                f"{sorted(available_observations)}"
            )
        available_provenance = available_observations | {
            item.representation_id
            for item in actor_context.observations
            if item.representation_id is not None
        } | {item.record_id for item in actor_context.accessible_records} | {
            item.route_id for item in actor_context.accessible_routes
        }
        unknown_provenance = (
            set(decision.assimilation.provenance_links) - available_provenance
        )
        available_memories = {
            _normalized_memory(item)
            for item in [*self._person.memories, *actor_context.private_memory]
        }
        unknown_provenance = {
            item
            for item in unknown_provenance
            if not (
                item.startswith("private_memory:")
                and _memory_reference_is_grounded(
                    item.partition(":")[2], available_memories
                )
            )
        }
        if unknown_provenance:
            raise ValueError(
                "provenance_links contained unavailable references "
                f"{sorted(unknown_provenance)}; use exact supplied IDs or one "
                "unambiguous retained-memory citation"
            )
        for revision in decision.assimilation.memory_revisions:
            if revision.prior_memory not in actor_context.private_memory:
                raise ValueError(
                    "memory_revisions.prior_memory did not exactly match a supplied "
                    "private memory"
                )

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del action_spec
        actor_context = ActorContext.model_validate_json(context[ACTOR_CONTEXT_COMPONENT])
        self.activation_count += 1
        call_number = self.activation_count
        actor_user = json.dumps(
            {
                "research_question": self._question,
                "person": self._person.model_dump(mode="json"),
                "actor_context": actor_context.model_dump(mode="json"),
            },
            sort_keys=True,
        )
        parsed, receipt = _call_model(
            self._call,
            role="actor",
            response_model=ActorDecision,
            system=(
                "You are one synthetic person in an exploratory causal simulation. "
                "Use only the supplied authorized observations, accessible world records, "
                "private memory, and character. Delivery is not truth and an attempted action "
                "is not guaranteed to succeed. Return an assimilation record and one bounded, "
                "open-ended semantic action intent against the supplied world revision."
            ),
            user=actor_user,
            trace_id=f"{self._trace_prefix}/moment/{call_number}/actor/{self._person.entity_id}",
        )
        decision = ActorDecision.model_validate(parsed)
        try:
            self._validate_decision(decision, actor_context)
        except ValueError as validation_error:
            self.receipts.append(receipt)
            repaired, repair_receipt = _call_model(
                self._call,
                role="actor",
                response_model=ActorDecision,
                system=(
                    "Repair one rejected synthetic-person output. Preserve the actor's "
                    "substantive judgment, but make every typed identity, revision, "
                    "observation ID, provenance reference, and prior-memory reference "
                    "conform exactly to the supplied authorized context. Do not add new "
                    "evidence or change the world. Return only the corrected typed output."
                ),
                user=json.dumps(
                    {
                        "original_input": json.loads(actor_user),
                        "rejected_output": decision.model_dump(mode="json"),
                        "validation_error": str(validation_error),
                    },
                    sort_keys=True,
                ),
                trace_id=(
                    f"{self._trace_prefix}/moment/{call_number}/actor/"
                    f"{self._person.entity_id}/repair/1"
                ),
            )
            decision = ActorDecision.model_validate(repaired)
            receipt = repair_receipt
            self._validate_decision(decision, actor_context)
        context_component = self.get_entity().get_component(
            ACTOR_CONTEXT_COMPONENT, type_=ActorContextComponent
        )
        if context_component.context is not None:
            for revision in decision.assimilation.memory_revisions:
                index = context_component.context.private_memory.index(
                    revision.prior_memory
                )
                context_component.context.private_memory[index] = revision.revised_memory
            context_component.context.private_memory.extend(
                decision.assimilation.memory_additions
            )
        self.receipts.append(receipt)
        return decision.intent.model_dump_json()

    def get_state(self) -> entity_component.ComponentState:
        return {
            "receipts": [item.model_dump(mode="json") for item in self.receipts],
            "activation_count": self.activation_count,
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])
        self.activation_count = int(state.get("activation_count", len(self.receipts)))


class GeneralGameMasterActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(
        self,
        call: StructuredCall,
        *,
        proposal: GeneralSimulationProposalV1,
        authority_id: str,
        trace_prefix: str,
    ) -> None:
        self._call = call
        self._proposal = proposal.model_copy(deep=True)
        self._authority_id = authority_id
        self._trace_prefix = trace_prefix
        self.receipts: list[ModelCallReceipt] = []
        self.moments: list[GeneralMomentEvidence] = []
        self.lifecycle_events: list[str] = []

    def _world(self) -> CanonicalWorld:
        return cast(
            CanonicalWorld,
            self.get_entity().get_component(WORLD_COMPONENT, type_=CanonicalWorld),
        )

    def _moment(self) -> Any:
        if len(self.moments) >= len(self._proposal.schedule):
            return self._proposal.schedule[-1]
        return self._proposal.schedule[len(self.moments)]

    def _delivered_representations(self) -> set[str]:
        current_minute = self._moment().minute
        return {
            representation_id
            for moment in self._proposal.schedule
            if moment.minute <= current_minute
            for representation_id in moment.external_inject_representation_ids
        }

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del context
        output_type = action_spec.output_type
        self.lifecycle_events.append(output_type.value)
        actor_ids = [person.entity_id for person in self._proposal.people]
        if output_type == entity_lib.OutputType.TERMINATE:
            return "Yes" if len(self.moments) >= len(self._proposal.schedule) else "No"
        if output_type == entity_lib.OutputType.NEXT_ACTING:
            selector = self.get_entity().get_component(
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
                type_=concordia_next_acting.NextActingAllEntities,
            )
            return str(selector.pre_act(action_spec))
        if output_type == entity_lib.OutputType.NEXT_ACTION_SPEC:
            return "prompt: Propose one bounded action from your authorized context.;;type: free"
        if output_type == entity_lib.OutputType.MAKE_OBSERVATION:
            actor_id = next(
                (candidate for candidate in actor_ids if candidate in action_spec.call_to_action),
                None,
            )
            if actor_id is None:
                raise ValueError("Concordia observation request did not name a configured actor")
            self._world().drain_outbox(actor_id)
            moment = self._moment()
            return self._world().actor_context(
                actor_id,
                current_minute=moment.minute,
                delivered_representation_ids=self._delivered_representations(),
            ).model_dump_json()
        if output_type == entity_lib.OutputType.RESOLVE:
            inbox = self.get_entity().get_component(INBOX_COMPONENT, type_=InboxComponent)
            if inbox.putative_event is None:
                raise RuntimeError("joint resolution requested without actor intents")
            intents: list[SemanticActionIntent] = []
            for line in inbox.putative_event.splitlines():
                raw = line.removeprefix("[putative_event]").strip()
                actor_id, separator, payload = raw.partition(":")
                if not separator or actor_id.strip() not in actor_ids:
                    continue
                intents.append(SemanticActionIntent.model_validate_json(payload.strip()))
            if {item.actor_id for item in intents} != set(actor_ids):
                raise ValueError("joint resolution did not receive one intent from every actor")
            frozen_revisions = {item.base_revision for item in intents}
            world = self._world()
            if frozen_revisions != {world.state.revision}:
                raise ValueError("same-moment actors did not reason from one frozen revision")
            authority = next(
                item for item in world.spec.authorities if item.authority_id == self._authority_id
            )
            moment = self._moment()
            is_final_moment = len(self.moments) + 1 == len(self._proposal.schedule)
            parsed, receipt = _call_model(
                self._call,
                role="adjudicator",
                response_model=WorldTransaction,
                system=(
                    "You are a bounded joint transition authority in an exploratory simulation. "
                    "Reconcile the same-revision semantic intents into one transaction containing "
                    "only mutations allowed by the supplied patch grammar. You propose; canonical "
                    "validation determines whether the transaction commits. Do not put hidden world "
                    "facts into actor-visible consequences. On the final scheduled moment, also "
                    "assess the research objective as achieved, partially_achieved, failed, or "
                    "unresolved. Base that assessment only on canonical state, collected intents, "
                    "and the transaction you propose; cite exact supplied evidence identifiers. "
                    "Use unresolved when the evidence does not establish success or failure."
                ),
                user=json.dumps(
                    {
                        "research_question": self._proposal.question,
                        "moment": moment.model_dump(mode="json"),
                        "world": world.state.model_dump(mode="json"),
                        "intents": [item.model_dump(mode="json") for item in intents],
                        "authority": authority.model_dump(mode="json"),
                        "requirements": {
                            "authority_id": self._authority_id,
                            "base_revision": world.state.revision,
                            "intent_ids": [item.intent_id for item in intents],
                            "actor_visible_consequences_may_name": actor_ids,
                            "is_final_moment": is_final_moment,
                            "objective_assessment_required": is_final_moment,
                        },
                    },
                    sort_keys=True,
                ),
                trace_id=f"{self._trace_prefix}/moment/{len(self.moments) + 1}/adjudicator",
                timeout_s=180,
            )
            proposed_transaction = WorldTransaction.model_validate(parsed)
            expected_intents = {item.intent_id for item in intents}
            corrections: list[str] = []
            if proposed_transaction.authority_id != self._authority_id:
                corrections.append("authority_id restored from trusted runtime")
            if proposed_transaction.base_revision != world.state.revision:
                corrections.append("base_revision restored from trusted runtime")
            if set(proposed_transaction.intent_ids) != expected_intents:
                corrections.append("intent_ids restored from collected Concordia actions")
            transaction = proposed_transaction.model_copy(
                update={
                    "authority_id": self._authority_id,
                    "base_revision": world.state.revision,
                    "intent_ids": [item.intent_id for item in intents],
                }
            )
            if is_final_moment and transaction.objective_assessment is None:
                corrections.append(
                    "missing final objective assessment retained as unresolved"
                )
                transaction = transaction.model_copy(
                    update={
                        "objective_assessment": ObjectiveAssessment(
                            status="unresolved",
                            summary=(
                                "The final transition authority output did not establish "
                                "whether the configured objective was achieved or failed."
                            ),
                            evidence_refs=list(transaction.evidence_refs),
                            unresolved_requirements=[
                                "A grounded final objective assessment is still required."
                            ],
                        )
                    }
                )
            transaction = _normalize_transaction_targets(
                transaction, world, corrections
            )
            allowed_evidence_refs = (
                expected_intents
                | {moment.moment_id}
                | set(world.state.records)
                | set(world.state.places)
                | set(world.state.routes)
                | set(world.state.representations)
                | set(world.state.resources)
            )
            allowed_evidence_refs |= {
                f"{record_type}:{record_id}"
                for record_type, record_ids in (
                    ("record", world.state.records),
                    ("place", world.state.places),
                    ("route", world.state.routes),
                    ("representation", world.state.representations),
                    ("resource", world.state.resources),
                )
                for record_id in record_ids
            }
            if set(transaction.evidence_refs) - allowed_evidence_refs:
                raise ValueError("adjudicator cited unknown canonical evidence")
            assessment = transaction.objective_assessment
            if assessment is not None and set(assessment.evidence_refs) - (
                allowed_evidence_refs | {transaction.transaction_id}
            ):
                raise ValueError("objective assessment cited unknown canonical evidence")
            unknown_recipients = {
                item.recipient_id for item in transaction.consequences
            } - set(actor_ids)
            if unknown_recipients:
                raise ValueError("adjudicator consequence named an unknown actor")
            frozen_revision = world.state.revision
            validation = world.validate_and_commit(
                transaction, envelope_corrections=corrections
            )
            grammar_errors = [
                error
                for error in validation.errors
                if "outside authority grammar" in error
            ]
            if grammar_errors and len(grammar_errors) == len(validation.errors):
                self.receipts.append(receipt)
                repaired, repair_receipt = _call_model(
                    self._call,
                    role="adjudicator",
                    response_model=WorldTransaction,
                    system=(
                        "Repair one rejected transition-authority output. Preserve the "
                        "substantive judgment, but use only operations and target record "
                        "types in the supplied authority patch grammar. Actor-visible "
                        "communications belong in consequences; do not create, replace, "
                        "or rebind information representations unless the grammar explicitly "
                        "allows that target type. Do not evade a world invariant or invent "
                        "new evidence. Return only the corrected typed transaction."
                    ),
                    user=json.dumps(
                        {
                            "original_input": {
                                "research_question": self._proposal.question,
                                "moment": moment.model_dump(mode="json"),
                                "world": world.state.model_dump(mode="json"),
                                "intents": [item.model_dump(mode="json") for item in intents],
                                "authority": authority.model_dump(mode="json"),
                                "requirements": {
                                    "authority_id": self._authority_id,
                                    "base_revision": world.state.revision,
                                    "intent_ids": [item.intent_id for item in intents],
                                    "actor_visible_consequences_may_name": actor_ids,
                                },
                            },
                            "rejected_output": transaction.model_dump(mode="json"),
                            "validation_errors": validation.errors,
                        },
                        sort_keys=True,
                    ),
                    trace_id=(
                        f"{self._trace_prefix}/moment/{len(self.moments) + 1}/"
                        "adjudicator/repair/1"
                    ),
                    timeout_s=180,
                )
                repaired_transaction = WorldTransaction.model_validate(repaired).model_copy(
                    update={
                        "authority_id": self._authority_id,
                        "base_revision": world.state.revision,
                        "intent_ids": [item.intent_id for item in intents],
                    }
                )
                if is_final_moment and repaired_transaction.objective_assessment is None:
                    repaired_transaction = repaired_transaction.model_copy(
                        update={"objective_assessment": transaction.objective_assessment}
                    )
                repair_corrections: list[str] = []
                repaired_transaction = _normalize_transaction_targets(
                    repaired_transaction, world, repair_corrections
                )
                if set(repaired_transaction.evidence_refs) - allowed_evidence_refs:
                    raise ValueError("repaired adjudicator output cited unknown canonical evidence")
                repaired_assessment = repaired_transaction.objective_assessment
                if repaired_assessment is not None and set(
                    repaired_assessment.evidence_refs
                ) - (allowed_evidence_refs | {repaired_transaction.transaction_id}):
                    raise ValueError(
                        "repaired objective assessment cited unknown canonical evidence"
                    )
                repaired_unknown_recipients = {
                    item.recipient_id for item in repaired_transaction.consequences
                } - set(actor_ids)
                if repaired_unknown_recipients:
                    raise ValueError("repaired adjudicator consequence named an unknown actor")
                validation = world.validate_and_commit(
                    repaired_transaction,
                    envelope_corrections=[
                        "one bounded repair followed an authority-grammar rejection",
                        *repair_corrections,
                    ],
                )
                transaction = repaired_transaction
                receipt = repair_receipt
            self.receipts.append(receipt)
            self.moments.append(
                GeneralMomentEvidence(
                    moment_id=moment.moment_id,
                    minute=moment.minute,
                    description=moment.description,
                    frozen_revision=frozen_revision,
                    actor_ids=actor_ids,
                    intent_ids=[item.intent_id for item in intents],
                    resulting_revision=validation.resulting_revision,
                    checkpoint_hash="pending",
                )
            )
            return json.dumps(
                {
                    "moment_id": moment.moment_id,
                    "accepted": validation.accepted,
                    "resulting_revision": validation.resulting_revision,
                    "errors": validation.errors,
                }
            )
        raise NotImplementedError(f"unsupported Concordia action type {output_type}")

    def get_state(self) -> entity_component.ComponentState:
        return {
            "receipts": [item.model_dump(mode="json") for item in self.receipts],
            "moments": [item.model_dump(mode="json") for item in self.moments],
            "lifecycle_events": list(self.lifecycle_events),
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])
        self.moments = TypeAdapter(list[GeneralMomentEvidence]).validate_python(state["moments"])
        self.lifecycle_events = TypeAdapter(list[str]).validate_python(state["lifecycle_events"])


@dataclass
class GeneralPersonPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "One bounded authored person in a general simulation."
    call: StructuredCall = field(default_factory=_structured_call)
    person: GeneralPersonDraft | None = None
    question: str = ""
    trace_prefix: str = "general-simulation"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        if self.person is None:
            raise ValueError("person prefab requires an authored person")
        return entity_agent.EntityAgent(
            agent_name=self.person.entity_id,
            act_component=GeneralActorActingComponent(
                self.call,
                person=self.person,
                question=self.question,
                trace_prefix=self.trace_prefix,
            ),
            context_components={
                ACTOR_CONTEXT_COMPONENT: ActorContextComponent(),
                "__memory__": MemoryViewComponent(),
            },
        )


@dataclass
class GeneralWorldPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "Canonical world and joint transition authority."
    compiled: CompiledGeneralSimulationV1 | None = None
    call: StructuredCall = field(default_factory=_structured_call)
    trace_prefix: str = "general-simulation"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        if self.compiled is None:
            raise ValueError("world prefab requires a compiled simulation")
        semantic_authorities = [
            item for item in self.compiled.world_spec.authorities if item.implementation == "llm"
        ]
        if len(semantic_authorities) != 1:
            raise ValueError("this vertical requires exactly one joint LLM authority")
        world = CanonicalWorld(self.compiled.world_spec)
        for person in self.compiled.proposal.people:
            world.retain_memory(person.entity_id, person.memories)
        return entity_agent.EntityAgent(
            agent_name="general_world_game_master",
            act_component=GeneralGameMasterActingComponent(
                self.call,
                proposal=self.compiled.proposal,
                authority_id=semantic_authorities[0].authority_id,
                trace_prefix=self.trace_prefix,
            ),
            context_components={
                WORLD_COMPONENT: world,
                INBOX_COMPONENT: InboxComponent(),
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY: (
                    concordia_next_acting.NextActingAllEntities(
                        [person.entity_id for person in self.compiled.proposal.people]
                    )
                ),
            },
        )


def _build_simulation(
    compiled: CompiledGeneralSimulationV1,
    call: StructuredCall,
    trace_prefix: str,
) -> generic.Simulation:
    prefabs: dict[str, prefab.Prefab] = {
        f"person_{person.entity_id}": GeneralPersonPrefab(
            call=call,
            person=person,
            question=compiled.proposal.question,
            trace_prefix=trace_prefix,
        )
        for person in compiled.proposal.people
    }
    prefabs["world"] = GeneralWorldPrefab(
        compiled=compiled,
        call=call,
        trace_prefix=trace_prefix,
    )
    instances = [
        prefab.InstanceConfig(
            prefab=f"person_{person.entity_id}",
            role=prefab.Role.ENTITY,
            params={"name": person.entity_id},
        )
        for person in compiled.proposal.people
    ]
    instances.append(
        prefab.InstanceConfig(
            prefab="world",
            role=prefab.Role.GAME_MASTER,
            params={"name": "general_world_game_master"},
        )
    )
    return generic.Simulation(
        config=prefab.Config(
            prefabs=prefabs,
            instances=instances,
            default_max_steps=len(compiled.proposal.schedule),
        ),
        model=no_language_model.NoLanguageModel(),
        embedder=lambda _: np.zeros(4),
        engine=simultaneous.Simultaneous(),
    )


def run_general_simulation(
    compiled: CompiledGeneralSimulationV1,
    *,
    run_id: str,
    call: StructuredCall | None = None,
    progress_observer: ProgressObserver | None = None,
    checkpoint: Mapping[str, Any] | None = None,
    max_additional_moments: int | None = None,
) -> GeneralGroupSimulationResult:
    selected_call = call or _structured_call()
    trace_prefix = f"{run_id}/general"
    simulation = _build_simulation(compiled, selected_call, trace_prefix)
    restored_checkpoint: dict[str, Any] | None = None
    if checkpoint is not None:
        restored_checkpoint = _strict_general_checkpoint(checkpoint, compiled)
        simulation.load_from_checkpoint(restored_checkpoint)
    checkpoints: list[dict[str, Any]] = []

    def retain_checkpoint(checkpoint: dict[str, Any]) -> None:
        retained = json.loads(json.dumps(checkpoint))
        checkpoints.append(retained)
        if progress_observer is not None:
            progress_observer(
                {
                    "stage": "commit",
                    "completed_moments": len(checkpoints),
                    "total_moments": len(compiled.proposal.schedule),
                },
                retained,
            )

    game_master = simulation.get_game_masters()[0]
    assert isinstance(game_master, entity_agent.EntityAgent)
    gm_act = cast(GeneralGameMasterActingComponent, game_master.get_act_component())
    completed_before = len(gm_act.moments)
    remaining = len(compiled.proposal.schedule) - completed_before
    if max_additional_moments is not None:
        if max_additional_moments < 0:
            raise ValueError("max_additional_moments must be non-negative")
        remaining = min(remaining, max_additional_moments)
    if remaining:
        simulation.play(max_steps=remaining, get_state_callback=retain_checkpoint)
    world = cast(
        CanonicalWorld,
        game_master.get_component(WORLD_COMPONENT, type_=CanonicalWorld),
    )
    actor_receipts: list[ModelCallReceipt] = []
    for actor in simulation.get_entities():
        assert isinstance(actor, entity_agent.EntityAgent)
        actor_act = cast(GeneralActorActingComponent, actor.get_act_component())
        actor_receipts.extend(actor_act.receipts)
    if restored_checkpoint is not None and completed_before:
        gm_act.moments[completed_before - 1].checkpoint_hash = _checkpoint_hash(
            restored_checkpoint
        )
    for offset, retained_checkpoint in enumerate(checkpoints):
        gm_act.moments[completed_before + offset].checkpoint_hash = _checkpoint_hash(
            retained_checkpoint
        )
    return GeneralGroupSimulationResult(
        simulation_id=compiled.proposal.simulation_id,
        title=compiled.proposal.title,
        question=compiled.proposal.question,
        proposal_digest=compiled.proposal_digest,
        registry_digest=compiled.registry_digest,
        final_state=world.state,
        transition_evidence=world.evidence,
        model_calls=actor_receipts + gm_act.receipts,
        moments=gm_act.moments,
        checkpoints=checkpoints,
        adoption=AdoptionReceipt(
            simulation_class=f"{type(simulation).__module__}.{type(simulation).__name__}",
            engine_class=f"{type(simulation._engine).__module__}.{type(simulation._engine).__name__}",
            actor_selection_component=(
                "concordia.components.game_master.next_acting.NextActingAllEntities"
            ),
            concordia_revision=CONCORDIA_REVISION,
            actor_names=[item.name for item in simulation.get_entities()],
            game_master_names=[item.name for item in simulation.get_game_masters()],
            lifecycle_events=gm_act.lifecycle_events,
            forbidden_runtime_imports=[],
        ),
    )
