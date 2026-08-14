"""Stock-Concordia execution of one open semantic action vertical."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
from concordia.agents import entity_agent
from concordia.associative_memory import basic_associative_memory
from concordia.components.game_master import next_acting as concordia_next_acting
from concordia.environment.engines import sequential
from concordia.language_model import language_model
from concordia.language_model import no_language_model
from concordia.prefabs.simulation import generic
from concordia.typing import entity as entity_lib
from concordia.typing import entity_component, prefab
from pydantic import TypeAdapter, ValidationError

from cybernetic_influence.llm_backend import CODEX_LUNA_MODEL, structured_backend_options

from .models import (
    ActiveSystemSpec,
    ActorAccessSpec,
    ActorContext,
    ActorDecision,
    AdoptionReceipt,
    Consequence,
    GeneralSimulationResult,
    GeneralWorldSpec,
    GeneralWorldState,
    ModelCallReceipt,
    PatchGrammar,
    PatchOperation,
    Place,
    Placement,
    Precondition,
    Representation,
    ResourceStock,
    Route,
    SemanticActionIntent,
    TransitionAuthoritySpec,
    TypedTarget,
    WorldRecord,
    WorldTransaction,
)
from .world import CanonicalWorld, state_hash


StructuredCall = Callable[..., tuple[Any, Any]]
CONCORDIA_REVISION = "131ed0d2ea14754539a3feb9dfd3717d11e859df"
WORLD_COMPONENT = "canonical_world"
ACTOR_CONTEXT_COMPONENT = "bounded_context"
INBOX_COMPONENT = "putative_event_inbox"


class MemoryViewComponent(entity_component.ContextComponent):  # type: ignore[misc]
    """Minimal stock-Simulation memory reporting seam.

    Cognitive state remains in ``ActorContextComponent``; this adapter only
    satisfies Concordia's post-run log collector without becoming a second
    memory authority.
    """

    def get_all_memories_as_text(self) -> list[str]:
        actor_context = self.get_entity().get_component(
            ACTOR_CONTEXT_COMPONENT, type_=ActorContextComponent
        )
        return list(actor_context.context.private_memory) if actor_context.context else []

    def get_state(self) -> entity_component.ComponentState:
        return {}

    def set_state(self, state: entity_component.ComponentState) -> None:
        if state:
            raise ValueError("memory view has no independent checkpoint state")


def _structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as exc:
        raise RuntimeError("general simulation requires the shared llm_client") from exc
    return cast(StructuredCall, call_llm_structured)


def _call_model(
    call: StructuredCall,
    *,
    role: str,
    response_model: type[Any],
    system: str,
    user: str,
    trace_id: str,
    timeout_s: int = 100,
    model: str = CODEX_LUNA_MODEL,
    reasoning_effort: str = "medium",
) -> tuple[Any, ModelCallReceipt]:
    with structured_backend_options(model) as backend_options:
        parsed, meta = call(
            model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_model=response_model,
            task=f"cybernetic_influence_general_simulation_{role}",
            trace_id=trace_id,
            max_budget=0.10,
            max_tokens=4000,
            model_justification=(
                "Generate one bounded semantic action or one structured world transaction "
                "inside an analyst-authored causal simulation."
            ),
            reasoning_effort=reasoning_effort,
            timeout=timeout_s,
            **backend_options,
        )
    provider = str(getattr(meta, "provider", "codex"))
    return parsed, ModelCallReceipt(
        role=cast(Any, role),
        provider=provider,
        model=model,
        trace_id=trace_id,
        input_context=user,
        structured_output=parsed.model_dump(mode="json"),
        decoding={"reasoning_effort": reasoning_effort, "max_tokens": 4000},
        exact_replay_possible=False,
    )


class ActorContextComponent(entity_component.ContextComponent):  # type: ignore[misc]
    def __init__(self) -> None:
        self.context: ActorContext | None = None

    def pre_observe(self, observation: str) -> str:
        updated = ActorContext.model_validate_json(observation)
        if self.context is not None:
            updated.private_memory = list(
                dict.fromkeys(self.context.private_memory + updated.private_memory)
            )
        self.context = updated
        return ""

    def pre_act(self, action_spec: entity_lib.ActionSpec) -> str:
        del action_spec
        if self.context is None:
            raise RuntimeError("actor was asked to act before receiving authorized context")
        return self.context.model_dump_json()

    def get_state(self) -> entity_component.ComponentState:
        return {"context": self.context.model_dump(mode="json") if self.context else None}

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.context = (
            ActorContext.model_validate(state["context"])
            if state.get("context") is not None
            else None
        )


class ActorActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(self, call: StructuredCall, trace_id: str) -> None:
        self._call = call
        self._trace_id = trace_id
        self.receipts: list[ModelCallReceipt] = []

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del action_spec
        raw_context = context[ACTOR_CONTEXT_COMPONENT]
        actor_context = ActorContext.model_validate_json(raw_context)
        system = (
            "You are a bounded actor in a causal simulation. Distinguish observation from truth. "
            "First state which observations you attended to and what you retain in natural-language "
            "memory. Then propose one open-ended action attempt grounded only in supplied context. "
            "You do not determine whether it succeeds and must use the supplied base revision."
        )
        user = (
            "The objective is to bring the worker and fuel truck into the port. The original bridge "
            "is visibly unusable; inspect the current routes and propose a plausible bounded action.\n"
            + actor_context.model_dump_json(indent=2)
        )
        parsed, receipt = _call_model(
            self._call,
            role="actor",
            response_model=ActorDecision,
            system=system,
            user=user,
            trace_id=self._trace_id,
        )
        decision = ActorDecision.model_validate(parsed)
        if decision.intent.actor_id != actor_context.actor_id:
            raise ValueError("actor output changed actor identity")
        if decision.intent.base_revision != actor_context.base_revision:
            raise ValueError("actor intent did not use supplied world revision")
        available_observations = {
            item.observation_id for item in actor_context.observations
        }
        available_provenance = available_observations | {
            item.representation_id
            for item in actor_context.observations
            if item.representation_id is not None
        } | {item.record_id for item in actor_context.accessible_records} | {
            item.route_id for item in actor_context.accessible_routes
        }
        if set(decision.assimilation.attended_observation_ids) - available_observations:
            raise ValueError("actor attended an observation it did not receive")
        unknown_provenance = set(decision.assimilation.provenance_links) - available_provenance
        available_memories = {
            " ".join(item.lower().split()) for item in actor_context.private_memory
        }
        unknown_provenance = {
            item
            for item in unknown_provenance
            if not (
                item.startswith("private_memory:")
                and " ".join(item.partition(":")[2].lower().split())
                in available_memories
            )
        }
        if unknown_provenance:
            raise ValueError("actor cited observation provenance it did not receive")
        context_component = self.get_entity().get_component(
            ACTOR_CONTEXT_COMPONENT, type_=ActorContextComponent
        )
        # The actor retains its own strings; these are not canonical world truth.
        if context_component.context is not None:
            for revision in decision.assimilation.memory_revisions:
                try:
                    index = context_component.context.private_memory.index(
                        revision.prior_memory
                    )
                except ValueError as exc:
                    raise ValueError(
                        "actor attempted to revise memory it did not possess"
                    ) from exc
                context_component.context.private_memory[index] = revision.revised_memory
            context_component.context.private_memory.extend(
                decision.assimilation.memory_additions
            )
        self.receipts.append(receipt)
        return decision.intent.model_dump_json()

    def get_state(self) -> entity_component.ComponentState:
        return {"receipts": [item.model_dump(mode="json") for item in self.receipts]}

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])


class InboxComponent(entity_component.ContextComponent):  # type: ignore[misc]
    def __init__(self) -> None:
        self.putative_event: str | None = None

    def pre_observe(self, observation: str) -> str:
        if observation.startswith("[putative_event]"):
            self.putative_event = observation.removeprefix("[putative_event]").strip()
        return ""

    def get_state(self) -> entity_component.ComponentState:
        return {"putative_event": self.putative_event}

    def set_state(self, state: entity_component.ComponentState) -> None:
        value = state.get("putative_event")
        self.putative_event = str(value) if value is not None else None


class GameMasterActingComponent(entity_component.ActingComponent):  # type: ignore[misc]
    def __init__(self, call: StructuredCall, trace_id: str) -> None:
        self._call = call
        self._trace_id = trace_id
        self.receipts: list[ModelCallReceipt] = []
        self.resolved = False
        self.final_observation_delivered = False
        self.lifecycle_events: list[str] = []

    def _world(self) -> CanonicalWorld:
        return cast(
            CanonicalWorld,
            self.get_entity().get_component(WORLD_COMPONENT, type_=CanonicalWorld),
        )

    def get_action_attempt(
        self,
        context: entity_component.ComponentContextMapping,
        action_spec: entity_lib.ActionSpec,
    ) -> str:
        del context
        output_type = action_spec.output_type
        self.lifecycle_events.append(output_type.value)
        if output_type == entity_lib.OutputType.TERMINATE:
            return "Yes" if self.resolved and self.final_observation_delivered else "No"
        if output_type == entity_lib.OutputType.MAKE_OBSERVATION:
            actor_id = action_spec.call_to_action.split()[-1].rstrip("?.,")
            # The stable vertical has one actor; format wording changes must not
            # change information authorization.
            if actor_id != "worker":
                actor_id = "worker"
            self._world().drain_outbox(actor_id)
            if self.resolved:
                self.final_observation_delivered = True
            return self._world().actor_context(actor_id).model_dump_json()
        if output_type == entity_lib.OutputType.NEXT_ACTING:
            selector = self.get_entity().get_component(
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
                type_=concordia_next_acting.NextActingInFixedOrder,
            )
            return str(selector.pre_act(action_spec))
        if output_type == entity_lib.OutputType.NEXT_ACTION_SPEC:
            if self.resolved:
                return "type: __SKIP_THIS_STEP__"
            return "prompt: Propose one bounded action attempt grounded in your observations.;;type: free"
        if output_type == entity_lib.OutputType.RESOLVE:
            inbox = self.get_entity().get_component(INBOX_COMPONENT, type_=InboxComponent)
            if inbox.putative_event is None:
                raise RuntimeError("resolution requested without a putative event")
            raw = inbox.putative_event
            prefix = "worker:"
            if raw.startswith(prefix):
                raw = raw[len(prefix) :].strip()
            intent = SemanticActionIntent.model_validate_json(raw)
            world = self._world()
            authority_context = {
                "world": world.state.model_dump(mode="json"),
                "intent": intent.model_dump(mode="json"),
                "authority": "port_semantic_adjudicator",
                "requirements": [
                    "Only propose placement rebind operations for worker and fuel_truck.",
                    "The destination is port. The validator independently checks operational reachability.",
                    "Use the exact supplied base revision and authority id.",
                    "Include one actor-visible consequence for worker stating the committed arrival outcome.",
                    "Do not expose hidden route state in that consequence.",
                ],
            }
            parsed, receipt = _call_model(
                self._call,
                role="adjudicator",
                response_model=WorldTransaction,
                system=(
                    "You are a coarse semantic transition authority, not an omnipotent state editor. "
                    "Translate the supplied intent into only the operations allowed by the authority "
                    "requirements. You propose; the canonical validator decides and commits."
                ),
                user=json.dumps(authority_context, sort_keys=True),
                trace_id=self._trace_id,
            )
            proposed_transaction = WorldTransaction.model_validate(parsed)
            corrections: list[str] = []
            if proposed_transaction.authority_id != "port_semantic_adjudicator":
                corrections.append("authority_id restored from trusted runtime")
            if proposed_transaction.base_revision != world.state.revision:
                corrections.append("base_revision restored from trusted runtime")
            if proposed_transaction.intent_ids != [intent.intent_id]:
                corrections.append("intent_ids restored from collected Concordia action")
            transaction = proposed_transaction.model_copy(
                update={
                    "authority_id": "port_semantic_adjudicator",
                    "base_revision": world.state.revision,
                    "intent_ids": [intent.intent_id],
                }
            )
            allowed_evidence_refs = {
                intent.intent_id,
                *world.state.records,
                *world.state.places,
                *world.state.routes,
                *world.state.representations,
                *world.state.resources,
            }
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
            if not any(item.recipient_id == "worker" for item in transaction.consequences):
                raise ValueError("adjudicator omitted the required actor-visible consequence")
            validation = world.validate_and_commit(
                transaction, envelope_corrections=corrections
            )
            if not validation.accepted:
                raise ValueError(f"adjudicator transaction rejected: {validation.errors}")
            self.receipts.append(receipt)
            self.resolved = True
            return json.dumps(
                {"transaction_id": transaction.transaction_id, "revision": validation.resulting_revision}
            )
        raise NotImplementedError(f"unsupported Concordia action type {output_type}")

    def get_state(self) -> entity_component.ComponentState:
        return {
            "receipts": [item.model_dump(mode="json") for item in self.receipts],
            "resolved": self.resolved,
            "final_observation_delivered": self.final_observation_delivered,
            "lifecycle_events": list(self.lifecycle_events),
        }

    def set_state(self, state: entity_component.ComponentState) -> None:
        self.receipts = TypeAdapter(list[ModelCallReceipt]).validate_python(state["receipts"])
        self.resolved = bool(state["resolved"])
        self.final_observation_delivered = bool(state["final_observation_delivered"])
        self.lifecycle_events = TypeAdapter(list[str]).validate_python(state["lifecycle_events"])


@dataclass
class WorkerPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "Bounded worker driven by the shared structured LLM client."
    call: StructuredCall = field(default_factory=_structured_call)
    trace_id: str = "slice28/bridge-port/actor"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        name = self.params.get("name", "worker")
        return entity_agent.EntityAgent(
            agent_name=name,
            act_component=ActorActingComponent(self.call, self.trace_id),
            context_components={
                ACTOR_CONTEXT_COMPONENT: ActorContextComponent(),
                "__memory__": MemoryViewComponent(),
            },
        )


@dataclass
class WorldGameMasterPrefab(prefab.Prefab):  # type: ignore[misc]
    description = "Canonical-world transition authority hosted in a Concordia game master."
    spec: GeneralWorldSpec | None = None
    call: StructuredCall = field(default_factory=_structured_call)
    trace_id: str = "slice28/bridge-port/adjudicator"

    def build(
        self,
        model: language_model.LanguageModel,
        memory_bank: basic_associative_memory.AssociativeMemoryBank,
    ) -> entity_component.EntityWithComponents:
        del model, memory_bank
        if self.spec is None:
            raise ValueError("world game master requires a GeneralWorldSpec")
        return entity_agent.EntityAgent(
            agent_name=self.params.get("name", "world_game_master"),
            act_component=GameMasterActingComponent(self.call, self.trace_id),
            context_components={
                WORLD_COMPONENT: CanonicalWorld(self.spec),
                INBOX_COMPONENT: InboxComponent(),
                concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY: (
                    concordia_next_acting.NextActingInFixedOrder(sequence=["worker"])
                ),
            },
        )


def bridge_port_spec() -> GeneralWorldSpec:
    deterministic = TransitionAuthoritySpec(
        authority_id="port_deterministic_mechanics",
        implementation="deterministic",
        patch_grammar=PatchGrammar(
            allowed_operations=["create", "replace", "rebind"],
            allowed_record_types=[
                "place", "placement", "route", "representation", "resource"
            ],
        ),
        reads=["placements", "routes"],
        writes=["places", "placements", "routes", "representations"],
        deterministic=True,
        replayable_from_receipt=True,
        idempotent=True,
    )
    semantic = TransitionAuthoritySpec(
        authority_id="port_semantic_adjudicator",
        implementation="llm",
        patch_grammar=PatchGrammar(
            allowed_operations=["replace", "rebind"],
            allowed_record_types=["placement"],
        ),
        reads=["records", "places", "placements", "routes"],
        writes=["placements"],
        deterministic=False,
        replayable_from_receipt=True,
        assumptions=["ordinary movement is adjudicated coarsely"],
        invalid_questions=["fine-grained vehicle dynamics", "predictive port throughput"],
    )
    return GeneralWorldSpec(
        spec_id="bridge_port_v1",
        initial_state=GeneralWorldState(
            records={
                "worker": WorldRecord(record_id="worker", kind="person", label="Port worker"),
                "fuel_truck": WorldRecord(
                    record_id="fuel_truck", kind="vehicle", label="Fuel truck"
                ),
            },
            places={
                "outside_port": Place(place_id="outside_port", label="Outside port"),
                "port": Place(place_id="port", label="Port"),
            },
            placements={
                "worker": Placement(record_id="worker", place_id="outside_port"),
                "fuel_truck": Placement(record_id="fuel_truck", place_id="outside_port"),
            },
            routes={
                "main_bridge": Route(
                    route_id="main_bridge",
                    origin_id="outside_port",
                    destination_id="port",
                    operational=False,
                    public_state={"condition": "collapsed"},
                    hidden_state={"cause": "sabotage"},
                )
            },
            representations={
                "bridge_notice": Representation(
                    representation_id="bridge_notice",
                    content="The main bridge has collapsed and cannot be used.",
                    apparent_source="port operations notice",
                    recipient_ids=["worker"],
                    hidden_provenance={"actual_cause": "sabotage"},
                )
            },
            resources={
                "truck_fuel": ResourceStock(
                    resource_id="truck_fuel",
                    quantity=100.0,
                    custodian_id="worker",
                )
            },
        ),
        active_systems=[
            ActiveSystemSpec(
                system_id="worker",
                executor="actor",
                resolution="individual actor with bounded observation and natural-language memory",
            ),
            ActiveSystemSpec(
                system_id="port_world",
                executor="transition_authority",
                authority_id="port_semantic_adjudicator",
                resolution="coarse semantic movement",
            ),
        ],
        authorities=[deterministic, semantic],
        invariants=["reference integrity", "valid placement", "operational movement path"],
        fidelity_assumptions=["vehicle dynamics are outside analytical scope"],
        timing={"temporary_route_setup_minutes": 90},
        actor_access=[
            ActorAccessSpec(
                actor_id="worker",
                record_ids=["worker", "fuel_truck"],
                route_ids=["main_bridge", "outside_to_depot", "depot_to_port"],
                representation_ids=["bridge_notice"],
            )
        ],
    )


def _simulation(spec: GeneralWorldSpec, call: StructuredCall) -> generic.Simulation:
    config = prefab.Config(
        prefabs={
            "worker": WorkerPrefab(call=call),
            "world": WorldGameMasterPrefab(spec=spec, call=call),
        },
        instances=[
            prefab.InstanceConfig(prefab="worker", role=prefab.Role.ENTITY, params={"name": "worker"}),
            prefab.InstanceConfig(
                prefab="world", role=prefab.Role.GAME_MASTER, params={"name": "world_game_master"}
            ),
        ],
        default_max_steps=1,
    )
    return generic.Simulation(
        config=config,
        model=no_language_model.NoLanguageModel(),
        embedder=lambda _: np.zeros(4),
        engine=sequential.Sequential(),
    )


def _world(simulation: generic.Simulation) -> CanonicalWorld:
    gm = simulation.get_game_masters()[0]
    assert isinstance(gm, entity_component.EntityWithComponents)
    return cast(CanonicalWorld, gm.get_component(WORLD_COMPONENT, type_=CanonicalWorld))


def _strict_checkpoint(
    checkpoint: Mapping[str, Any], spec: GeneralWorldSpec
) -> tuple[dict[str, Any], str]:
    payload = copy.deepcopy(dict(checkpoint))
    try:
        if set(payload["entities"]) != {"worker"}:
            raise ValueError("checkpoint actor set differs from the vertical")
        if set(payload["game_masters"]) != {"world_game_master"}:
            raise ValueError("checkpoint game-master set differs from the vertical")
        entity_data = payload["entities"]["worker"]
        gm_data = payload["game_masters"]["world_game_master"]
        gm_context = gm_data["components"]["context_components"]
        if set(gm_context) != {
            WORLD_COMPONENT,
            INBOX_COMPONENT,
            concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY,
        }:
            raise ValueError("checkpoint game-master components are incomplete")
        ActorContextComponent().set_state(entity_data["components"]["context_components"][ACTOR_CONTEXT_COMPONENT])
        CanonicalWorld(spec).set_state(gm_context[WORLD_COMPONENT])
        InboxComponent().set_state(gm_context[INBOX_COMPONENT])
        concordia_next_acting.NextActingInFixedOrder(sequence=["worker"]).set_state(
            gm_context[concordia_next_acting.DEFAULT_NEXT_ACTING_COMPONENT_KEY]
        )
        ActorActingComponent(lambda *args, **kwargs: (None, None), "validation").set_state(
            entity_data["components"]["act_component"]
        )
        GameMasterActingComponent(lambda *args, **kwargs: (None, None), "validation").set_state(
            gm_data["components"]["act_component"]
        )
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        raise ValueError("invalid or incomplete Concordia checkpoint") from exc
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return payload, hashlib.sha256(serialized.encode()).hexdigest()


def _prepare_world(world: CanonicalWorld) -> None:
    blocked = WorldTransaction(
        transaction_id="blocked-main-bridge-attempt",
        base_revision=world.state.revision,
        authority_id="port_deterministic_mechanics",
        intent_ids=["scripted-blocked-attempt"],
        operations=[
            PatchOperation(
                operation="rebind",
                target=TypedTarget(record_type="placement", record_id="fuel_truck", field="place_id"),
                value="port",
            )
        ],
        preconditions=[
            Precondition(
                target=TypedTarget(record_type="route", record_id="main_bridge", field="operational"),
                expected=True,
            )
        ],
        consequences=[],
        evidence_refs=["scripted-blocked-attempt"],
        stated_rationale="Attempt to use the direct bridge route.",
    )
    rejected = world.validate_and_commit(blocked)
    if rejected.accepted:
        raise AssertionError("destroyed bridge attempt must be rejected")
    topology = WorldTransaction(
        transaction_id="establish-temporary-depot-and-route",
        base_revision=world.state.revision,
        authority_id="port_deterministic_mechanics",
        intent_ids=["port-contingency-plan"],
        operations=[
            PatchOperation(
                operation="create",
                target=TypedTarget(record_type="place", record_id="temporary_depot"),
                value={"place_id": "temporary_depot", "label": "Temporary depot"},
            ),
            PatchOperation(
                operation="create",
                target=TypedTarget(record_type="route", record_id="outside_to_depot"),
                value={
                    "route_id": "outside_to_depot",
                    "origin_id": "outside_port",
                    "destination_id": "temporary_depot",
                    "operational": True,
                    "public_state": {"kind": "temporary access road"},
                    "hidden_state": {},
                },
            ),
            PatchOperation(
                operation="create",
                target=TypedTarget(record_type="route", record_id="depot_to_port"),
                value={
                    "route_id": "depot_to_port",
                    "origin_id": "temporary_depot",
                    "destination_id": "port",
                    "operational": True,
                    "public_state": {"kind": "temporary service route"},
                    "hidden_state": {},
                },
            ),
        ],
        preconditions=[],
        consequences=[
            Consequence(
                consequence_id="temporary-route-open",
                recipient_id="worker",
                content="A temporary depot and connected service route to the port are operational.",
                apparent_source="port operations",
            )
        ],
        evidence_refs=["port-contingency-plan"],
        stated_rationale="Create a material alternative to the destroyed bridge.",
    )
    accepted = world.validate_and_commit(topology)
    if not accepted.accepted:
        raise AssertionError(accepted.errors)


def run_bridge_port_vertical(call: StructuredCall | None = None) -> GeneralSimulationResult:
    selected_call = call or _structured_call()
    spec = bridge_port_spec()
    before = _simulation(spec, selected_call)
    _prepare_world(_world(before))
    checkpoint, checkpoint_hash = _strict_checkpoint(before.make_checkpoint_data(), spec)
    # JSON round trip is an intentional persistence boundary.
    persisted = json.loads(json.dumps(checkpoint))
    restored_checkpoint, restored_hash = _strict_checkpoint(persisted, spec)
    after = _simulation(spec, selected_call)
    after.load_from_checkpoint(restored_checkpoint)
    if state_hash(_world(before).state) != state_hash(_world(after).state):
        raise AssertionError("restored canonical state differs from checkpoint source")
    actor_context_at_fork = _world(after).actor_context("worker")
    after.play(max_steps=2)
    final_world = _world(after)
    if final_world.state.placements["worker"].place_id != "port":
        raise AssertionError("worker did not reach port")
    if final_world.state.placements["fuel_truck"].place_id != "port":
        raise AssertionError("fuel truck did not reach port")
    actor = after.get_entities()[0]
    gm = after.get_game_masters()[0]
    assert isinstance(actor, entity_agent.EntityAgent)
    assert isinstance(gm, entity_agent.EntityAgent)
    actor_act = cast(ActorActingComponent, actor.get_act_component())
    gm_act = cast(GameMasterActingComponent, gm.get_act_component())
    actor_context_component = actor.get_component(
        ACTOR_CONTEXT_COMPONENT, type_=ActorContextComponent
    )
    if actor_context_component.context is None:
        raise AssertionError("actor did not retain its final authorized context")
    actor_context_after = actor_context_component.context.model_copy(deep=True)
    if not any(
        observation.observation_id.startswith("consequence:")
        and observation.observation_id != "consequence:temporary-route-open"
        for observation in actor_context_after.observations
    ):
        raise AssertionError("committed outcome was not delivered through an actor-safe observation")
    actor_payloads = [
        actor_context_at_fork.model_dump_json(),
        actor_context_after.model_dump_json(),
        *[receipt.input_context for receipt in actor_act.receipts],
    ]
    if any("sabotage" in payload.lower() for payload in actor_payloads):
        raise AssertionError("hidden bridge cause leaked into actor context")
    return GeneralSimulationResult(
        checkpoint_hash=checkpoint_hash,
        restored_checkpoint_hash=restored_hash,
        final_state=final_world.state,
        transition_evidence=final_world.evidence,
        model_calls=actor_act.receipts + gm_act.receipts,
        actor_contexts=[actor_context_at_fork, actor_context_after],
        adoption=AdoptionReceipt(
            simulation_class=f"{type(after).__module__}.{type(after).__name__}",
            engine_class=f"{type(after._engine).__module__}.{type(after._engine).__name__}",
            actor_selection_component=(
                "concordia.components.game_master.next_acting.NextActingInFixedOrder"
            ),
            concordia_revision=CONCORDIA_REVISION,
            actor_names=[item.name for item in after.get_entities()],
            game_master_names=[item.name for item in after.get_game_masters()],
            lifecycle_events=gm_act.lifecycle_events,
            forbidden_runtime_imports=[],
        ),
    )
