"""Reusable authored influence network over the canonical causal runtime."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, cast

from cybernetic_influence.active_runtime import (
    ActionIntent,
    ActiveProposal,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    ActivationCause,
    RuntimeProgressObserver,
    ScriptedActiveSystem,
)
from cybernetic_influence.active_runtime.run_control import CompletionRecord
from cybernetic_influence.authoring.live import bind_authored_people
from cybernetic_influence.authoring.models import (
    InfluenceNetworkWorkflowDraft,
    InfluenceStance,
    ScenarioDraftProposal,
)
from cybernetic_influence.causal_core.engine import (
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
    ActionAttempt,
    AnalyticalBoundary,
    CarrierState,
    CausalScenario,
    CausalState,
    ConnectionState,
    EffectDraft,
    EntityState,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PlacementState,
    PlaceState,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    SpatialLinkState,
    representation_digest,
)

_ENCODING = "application/vnd.cybernetic.influence-message+json"
_ROUND_ENCODING = "application/vnd.cybernetic.decision-round+json"
_STANCES = frozenset({"support", "conditional", "defer", "oppose"})


@dataclass(frozen=True)
class InfluenceNetworkFixture:
    proposal: ScenarioDraftProposal
    scenario: CausalScenario
    exact_bindings: dict[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]


def validate_influence_network_proposal(proposal: ScenarioDraftProposal) -> None:
    workflow = proposal.workflow
    if not isinstance(workflow, InfluenceNetworkWorkflowDraft):
        raise ValueError("proposal is not an influence_network_v1 workflow")
    people = {item.entity_id for item in proposal.people}
    objects = {item.entity_id for item in proposal.objects}
    information = {item.information_id for item in proposal.information}
    places = {item.place_id for item in proposal.places}
    if not 3 <= len(people) <= 12:
        raise ValueError("influence_network_v1 requires three to twelve people")
    if workflow.round_minutes[0] < 3:
        raise ValueError("the first influence-network round must be at minute 3 or later")
    if workflow.decision_rule.minimum_support > len(people):
        raise ValueError("minimum support exceeds the number of people")
    if workflow.decision_rule.minimum_support_or_conditional > len(people):
        raise ValueError("support-or-conditional threshold exceeds the number of people")
    if workflow.decision_rule.maximum_oppose > len(people):
        raise ValueError("maximum opposition exceeds the number of people")
    for delivery in workflow.deliveries:
        if delivery.delivery_minutes > workflow.round_minutes[-1]:
            raise ValueError(
                f"delivery {delivery.delivery_id!r} occurs after the final decision round"
            )
        if delivery.source_id not in objects:
            raise ValueError(
                f"delivery {delivery.delivery_id!r} source is not a declared object"
            )
        if delivery.information_id not in information:
            raise ValueError(
                f"delivery {delivery.delivery_id!r} information is not declared"
            )
        unknown = set(delivery.recipient_ids) - people
        if unknown:
            raise ValueError(
                f"delivery {delivery.delivery_id!r} has unknown recipients "
                f"{sorted(unknown)!r}"
            )
    placeable = people | objects
    if unknown_placements := set(proposal.placements) - placeable:
        raise ValueError(
            f"placements contain unknown entities {sorted(unknown_placements)!r}"
        )
    if missing_placements := placeable - set(proposal.placements):
        raise ValueError(
            f"people and source objects require placements {sorted(missing_placements)!r}"
        )
    if unknown_places := set(proposal.placements.values()) - places:
        raise ValueError(f"placements refer to unknown places {sorted(unknown_places)!r}")
    declared_refs = people | objects | information
    for boundary in proposal.analytical_boundaries:
        unknown = set(boundary.member_refs) - declared_refs
        if unknown:
            raise ValueError(
                f"analytical boundary {boundary.boundary_id!r} has unknown members "
                f"{sorted(unknown)!r}"
            )


def influence_network_fixture(proposal: ScenarioDraftProposal) -> InfluenceNetworkFixture:
    """Compile arbitrary people and message recipient sets into reviewed machinery."""

    validate_influence_network_proposal(proposal)
    workflow = proposal.workflow
    assert isinstance(workflow, InfluenceNetworkWorkflowDraft)
    people = {item.entity_id: item for item in proposal.people}
    objects = {item.entity_id: item for item in proposal.objects}
    information = {item.information_id: item for item in proposal.information}

    entities = {
        person.entity_id: EntityState(
            entity_id=person.entity_id,
            entity_kind="person",
            description=person.position,
            attributes={
                "label": FactState(value=person.label),
            },
        )
        for person in proposal.people
    }
    entities.update(
        {
            item.entity_id: EntityState(
                entity_id=item.entity_id,
                entity_kind=item.entity_kind,
                description=item.description,
                attributes={"label": FactState(value=item.label)},
            )
            for item in proposal.objects
        }
    )
    entities.update(
        {
            item.information_id: EntityState(
                entity_id=item.information_id,
                entity_kind="information_document",
                description=item.content,
                attributes={"label": FactState(value=item.label)},
            )
            for item in proposal.information
        }
    )
    entities["network_clock"] = EntityState(
        entity_id="network_clock",
        entity_kind="process",
        description="Exact source-injection, round, and decision-evaluation controller.",
    )
    entities["decision_register"] = EntityState(
        entity_id="decision_register",
        entity_kind="decision_record",
        description="Exact public record of current stances and the collective result.",
        attributes={
            "question": FactState(value=workflow.collective_question),
            "participant_ids": FactState(value=cast(Any, sorted(people))),
            "positions": FactState(value=[]),
            "decision_rule": FactState(value=workflow.decision_rule.model_dump(mode="json")),
            "outcome": FactState(value=None),
            "counts": FactState(value={}),
        },
    )

    ports: dict[str, PortState] = {}
    connections: dict[str, ConnectionState] = {}
    mechanisms: dict[str, MechanismSpec] = {}
    carriers: dict[str, CarrierState] = {
        "round_snapshot_carrier": CarrierState(
            carrier_id="round_snapshot_carrier",
            owner_ref="round_snapshot_builder",
            medium="decision_round_snapshot",
            locator="influence_network/round_snapshots",
        )
    }
    representations: dict[str, RepresentationToken] = {}

    def add_port(
        port_id: str,
        owner_ref: str,
        direction: str,
        effect_type: str,
        description: str,
    ) -> None:
        ports[port_id] = PortState(
            port_id=port_id,
            owner_ref=owner_ref,
            direction=cast(Any, direction),
            effect_type=effect_type,
            description=description,
        )

    add_port(
        "round_wake_out",
        "network_clock",
        "output",
        "decision_round_wake",
        "Trigger one exact decision-round snapshot. Payload requires round_index.",
    )
    add_port(
        "round_wake_in",
        "round_snapshot_builder",
        "input",
        "decision_round_wake",
        "Build a public snapshot from the current exact decision register.",
    )
    add_port(
        "round_snapshot_out",
        "round_snapshot_builder",
        "output",
        "decision_round_snapshot",
        "Fan out one exact public decision-round snapshot.",
    )
    connections["round_wake_route"] = _connection(
        "round_wake_route", "round_wake_out", "round_wake_in"
    )
    mechanisms["round_snapshot_builder"] = _mechanism(
        "round_snapshot_builder",
        ["round_wake_in"],
        output_ports=["round_snapshot_out"],
        read_facts=["decision_register.question", "decision_register.positions"],
        write_carriers=["round_snapshot_carrier"],
    )

    for person_id in sorted(people):
        round_input = f"round_snapshot_{person_id}_in"
        delivery_mechanism = f"round_snapshot_delivery_{person_id}"
        add_port(
            round_input,
            delivery_mechanism,
            "input",
            "decision_round_snapshot",
            f"Deliver the public round snapshot to {person_id}.",
        )
        connections[f"round_snapshot_{person_id}_route"] = _connection(
            f"round_snapshot_{person_id}_route", "round_snapshot_out", round_input
        )
        mechanisms[delivery_mechanism] = _mechanism(
            delivery_mechanism,
            [round_input],
            observation_targets=[person_id],
        )
        stance_output = f"stance_{person_id}_out"
        add_port(
            stance_output,
            person_id,
            "output",
            "decision_stance",
            (
                "Record your current stance. Payload must contain person_id equal to "
                f"{person_id!r}, stance equal to support, conditional, defer, or oppose, "
                "and a concise reason string grounded in your memories and delivered "
                "observations. This records a decision; it does not force anyone else."
            ),
        )
        connections[f"stance_{person_id}_route"] = _connection(
            f"stance_{person_id}_route", stance_output, "stance_record_in"
        )

    add_port(
        "stance_record_in",
        "stance_recorder",
        "input",
        "decision_stance",
        "Record one person's latest stated decision stance.",
    )
    mechanisms["stance_recorder"] = _mechanism(
        "stance_recorder",
        ["stance_record_in"],
        read_facts=["decision_register.positions"],
        write_facts=["decision_register.positions"],
    )
    add_port(
        "decision_evaluate_out",
        "network_clock",
        "output",
        "evaluate_collective_decision",
        "Apply the authored exact decision rule to the latest recorded stances.",
    )
    add_port(
        "decision_evaluate_in",
        "decision_gate",
        "input",
        "evaluate_collective_decision",
        "Evaluate the final exact decision gate.",
    )
    connections["decision_evaluate_route"] = _connection(
        "decision_evaluate_route", "decision_evaluate_out", "decision_evaluate_in"
    )
    mechanisms["decision_gate"] = _mechanism(
        "decision_gate",
        ["decision_evaluate_in"],
        read_facts=[
            "decision_register.participant_ids",
            "decision_register.positions",
            "decision_register.decision_rule",
        ],
        write_facts=["decision_register.outcome", "decision_register.counts"],
    )

    observation_ports: dict[str, list[str]] = {person_id: [] for person_id in people}
    for delivery in workflow.deliveries:
        source_port = f"{delivery.delivery_id}_source_out"
        representation_id = f"{delivery.delivery_id}_representation"
        carrier_id = f"{delivery.delivery_id}_carrier"
        source = objects[delivery.source_id]
        item = information[delivery.information_id]
        content = json.dumps(
            {
                "document_kind": "influence_message",
                "delivery_id": delivery.delivery_id,
                "topic": item.label,
                "content": item.content,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        carriers[carrier_id] = CarrierState(
            carrier_id=carrier_id,
            owner_ref=delivery.source_id,
            medium="authored_influence_message",
            locator=f"influence_network/{delivery.delivery_id}",
        )
        representations[representation_id] = RepresentationToken(
            representation_id=representation_id,
            carrier_id=carrier_id,
            carrier_revision=0,
            encoding=_ENCODING,
            content=content,
            content_hash=representation_digest(content),
            actual_source_ref=delivery.source_id,
        )
        add_port(
            source_port,
            delivery.source_id,
            "output",
            "influence_message",
            f"Inject {item.label} from {source.label} through explicit routes.",
        )
        for recipient_id in delivery.recipient_ids:
            input_port = f"{delivery.delivery_id}_{recipient_id}_in"
            mechanism_id = f"{delivery.delivery_id}_{recipient_id}_delivery"
            add_port(
                input_port,
                mechanism_id,
                "input",
                "influence_message",
                f"Deliver {delivery.delivery_id} to {recipient_id}.",
            )
            connections[f"{delivery.delivery_id}_{recipient_id}_route"] = _connection(
                f"{delivery.delivery_id}_{recipient_id}_route",
                source_port,
                input_port,
            )
            mechanisms[mechanism_id] = _mechanism(
                mechanism_id,
                [input_port],
                observation_targets=[recipient_id],
            )
            observation_ports[recipient_id].append(input_port)

    specs = tuple(
        ActiveSystemSpec(
            active_system_id=person_id,
            entity_id=person_id,
            implementation_id=f"scripted_influence_person_{person_id}_v1",
            description=people[person_id].position,
            observation_port_ids=[
                *sorted(observation_ports[person_id]),
                f"round_snapshot_{person_id}_in",
            ],
            output_port_ids=[f"stance_{person_id}_out"],
            initial_private_state={
                "memory": cast(Any, people[person_id].memories)
            },
        )
        for person_id in sorted(people)
    )
    places = {
        item.place_id: PlaceState(
            place_id=item.place_id,
            place_kind="authored_place",
            description=f"{item.label}: {item.description}",
        )
        for item in proposal.places
    }
    state = CausalState(
        entities=entities,
        places=places,
        placements={
            entity_id: PlacementState(entity_id=entity_id, place_id=place_id)
            for entity_id, place_id in proposal.placements.items()
        },
        spatial_links={
            item.spatial_link_id: SpatialLinkState(
                spatial_link_id=item.spatial_link_id,
                endpoint_a_place_id=item.endpoint_a_place_id,
                endpoint_b_place_id=item.endpoint_b_place_id,
                link_kind="authored_pathway",
                description=item.description,
            )
            for item in proposal.spatial_links
        },
        ports=ports,
        connections=connections,
        mechanisms=mechanisms,
        carriers=carriers,
        representations=representations,
    )
    scenario = CausalScenario(
        scenario_id=proposal.scenario_id,
        description=proposal.description,
        time_unit="scenario_minute",
        timing_contract="positive_duration",
        minimum_world_duration=1,
        initial_state=state,
        analytical_boundaries=[
            AnalyticalBoundary(
                boundary_id=item.boundary_id,
                label=item.label,
                description=item.description,
                member_refs=item.member_refs,
            )
            for item in proposal.analytical_boundaries
        ],
        fidelity_questions=proposal.fidelity_questions,
    )
    return InfluenceNetworkFixture(
        proposal=proposal,
        scenario=scenario,
        exact_bindings=_exact_bindings(mechanisms),
        active_specs=specs,
    )


def influence_network_scripted_bindings(
    fixture: InfluenceNetworkFixture,
) -> dict[str, ActiveSystemBinding]:
    result: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        person_id = spec.active_system_id
        implementation_id = spec.implementation_id

        def step(
            item: ActiveSystemInput,
            *,
            bound_person_id: str = person_id,
            bound_implementation_id: str = implementation_id,
        ) -> ActiveStepResult:
            return ActiveStepResult(
                proposal=ActiveProposal(
                    active_system_id=bound_person_id,
                    implementation_id=bound_implementation_id,
                    private_state=item.private_state,
                    actions=[
                        ActionIntent(
                            output_port_id=f"stance_{bound_person_id}_out",
                            payload={
                                "person_id": bound_person_id,
                                "stance": "support",
                                "reason": "The scripted integration fixture supports the proposal.",
                            },
                            public_summary=f"{bound_person_id} recorded support.",
                        )
                    ],
                )
            )

        result[person_id] = ActiveSystemBinding(
            implementation_id,
            ScriptedActiveSystem(implementation_id, step),
        )
    return result


def influence_network_native_fixture_and_bindings(
    fixture: InfluenceNetworkFixture,
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str,
    structured_call: Any = None,
) -> tuple[InfluenceNetworkFixture, dict[str, ActiveSystemBinding]]:
    people = {person.entity_id: person for person in fixture.proposal.people}
    specs, bindings = bind_authored_people(
        fixture.active_specs,
        people,
        trace_id_prefix=trace_id_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
        structured_call=structured_call,
    )
    return replace(fixture, active_specs=specs), bindings


def run_influence_network(
    fixture: InfluenceNetworkFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
    runtime_config: ActiveRuntimeConfig,
    progress_observer: RuntimeProgressObserver | None = None,
    stop_requested: Callable[[], bool] | None = None,
    participant_concurrency: int = 1,
) -> ActiveRuntimeResult:
    workflow = fixture.proposal.workflow
    assert isinstance(workflow, InfluenceNetworkWorkflowDraft)
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id=run_id,
        config=runtime_config,
        progress_observer=progress_observer,
        participant_concurrency=participant_concurrency,
    )
    actions: list[ActionAttempt] = []
    for delivery in workflow.deliveries:
        actions.append(
            ActionAttempt(
                action_id=f"inject_{delivery.delivery_id}",
                actor_entity_id=delivery.source_id,
                output_port_id=f"{delivery.delivery_id}_source_out",
                representation_id=f"{delivery.delivery_id}_representation",
                logical_time=delivery.delivery_minutes - 1,
                public_summary=(
                    f"The configured source injected {delivery.delivery_id} toward "
                    f"{len(delivery.recipient_ids)} explicit recipient(s)."
                ),
            )
        )
    for index, minute in enumerate(workflow.round_minutes):
        actions.append(
            ActionAttempt(
                action_id=f"start_decision_round_{index + 1}",
                actor_entity_id="network_clock",
                output_port_id="round_wake_out",
                payload={"round_index": index + 1},
                logical_time=minute - 1,
                public_summary=f"The exact clock opened decision round {index + 1}.",
            )
        )
    evaluation_time = workflow.round_minutes[-1] + 4
    actions.append(
        ActionAttempt(
            action_id="evaluate_collective_decision",
            actor_entity_id="network_clock",
            output_port_id="decision_evaluate_out",
            logical_time=evaluation_time,
            public_summary="The exact gate evaluated the latest recorded stances.",
        )
    )
    actions.sort(key=lambda item: (item.logical_time, item.action_id))

    def drain_participants(*, through: int | None = None) -> bool:
        while (due := session.next_due_activation(through=through)) is not None:
            if stop_requested is not None and stop_requested():
                return False
            session.activate(
                due.active_system_ids,
                logical_time=due.logical_time,
                activation_causes=due.causes,
            )
        return True

    for action in actions:
        if stop_requested is not None and stop_requested():
            return session.complete(
                completion=CompletionRecord(
                    reason="operator_stopped",
                    causal_time=len(actions),
                    logical_time=session.core_state.logical_time,
                    public_summary="The operator stopped the simulation after a retained step.",
                ),
                discard_pending_effects=True,
            )
        # A participant response to an earlier scheduled event may itself
        # advance exact causal time beyond the next authored minute. Preserve
        # the authored event order without pretending that time can regress.
        effective_action = action.model_copy(
            update={
                "logical_time": max(
                    action.logical_time,
                    session.core_state.logical_time,
                )
            }
        )
        session.apply_external_action(effective_action)
        if not drain_participants():
            return session.complete(
                completion=CompletionRecord(
                    reason="operator_stopped",
                    causal_time=len(actions),
                    logical_time=session.core_state.logical_time,
                    public_summary="The operator stopped the simulation after a retained step.",
                ),
                discard_pending_effects=True,
            )
    if not drain_participants():
        return session.complete(
            completion=CompletionRecord(
                reason="operator_stopped",
                causal_time=len(actions),
                logical_time=session.core_state.logical_time,
                public_summary="The operator stopped the simulation after a retained step.",
            ),
            discard_pending_effects=True,
        )
    outcome = session.core_state.entities["decision_register"].attributes[
        "outcome"
    ].value
    if outcome not in {"approved", "not_approved"}:
        raise RuntimeError("influence-network decision gate did not record an outcome")
    return session.complete(
        completion=CompletionRecord(
            reason="terminal_condition_met",
            condition_ids=[f"influence_network_{outcome}"],
            causal_time=len(actions),
            logical_time=session.core_state.logical_time,
            public_summary=(
                "The collective decision gate approved the proposal."
                if outcome == "approved"
                else "The collective decision gate did not approve the proposal."
            ),
        )
    )


def _retained_int(values: Mapping[str, object], key: str) -> int:
    value = values.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"retained influence-network gate evidence has invalid {key!r}"
        )
    return value


def influence_network_outcome(
    result: ActiveRuntimeResult,
) -> tuple[dict[str, object], str, str]:
    register = result.core_result.final_state.entities["decision_register"]
    outcome = register.attributes["outcome"].value
    counts = register.attributes["counts"].value
    rule = register.attributes["decision_rule"].value
    if not isinstance(counts, dict) or not isinstance(rule, dict):
        raise ValueError("retained influence-network gate evidence is malformed")
    support = _retained_int(counts, "support")
    conditional = _retained_int(counts, "conditional")
    oppose = _retained_int(counts, "oppose")
    minimum_support = _retained_int(rule, "minimum_support")
    minimum_combined = _retained_int(rule, "minimum_support_or_conditional")
    maximum_oppose = _retained_int(rule, "maximum_oppose")
    gate_checks = {
        "support": {
            "actual": support,
            "required": minimum_support,
            "passed": support >= minimum_support,
        },
        "support_or_conditional": {
            "actual": support + conditional,
            "required": minimum_combined,
            "passed": support + conditional >= minimum_combined,
        },
        "opposition": {
            "actual": oppose,
            "maximum": maximum_oppose,
            "passed": oppose <= maximum_oppose,
        },
    }
    headline = (
        "The group approved the proposal"
        if outcome == "approved"
        else "The group did not approve the proposal"
    )
    failed = [label for label, check in gate_checks.items() if not check["passed"]]
    summary = (
        "Every configured decision threshold passed."
        if outcome == "approved"
        else (
            "The decision was not approved because the "
            + ", ".join(item.replace("_", " ") for item in failed)
            + " threshold failed."
        )
    )
    return (
        {
            "final_status": outcome,
            "counts": counts,
            "decision_rule": rule,
            "gate_checks": gate_checks,
            "model_calls": result.model_calls,
            "participant_activation_count": sum(
                len(attempt.participants) for attempt in result.attempts
            ),
            "causal_moment_count": len(result.attempts) + len(result.exact_work),
            "known_cost": result.total_observed_cost,
            "cost_fully_observable": result.cost_fully_observable,
        },
        headline,
        summary,
    )


def _connection(connection_id: str, source: str, target: str) -> ConnectionState:
    return ConnectionState(
        connection_id=connection_id,
        source_port_id=source,
        target_port_id=target,
        delay=1,
        description=f"Explicit directed route from {source} to {target}.",
    )


def _mechanism(
    mechanism_id: str,
    input_ports: list[str],
    *,
    output_ports: list[str] | None = None,
    read_facts: list[str] | None = None,
    write_facts: list[str] | None = None,
    write_carriers: list[str] | None = None,
    observation_targets: list[str] | None = None,
) -> MechanismSpec:
    return MechanismSpec(
        mechanism_id=mechanism_id,
        mechanism_kind="exact_transition",
        implementation_id=f"{mechanism_id}_v1",
        description=f"Reviewed reusable influence-network transition for {mechanism_id}.",
        input_port_ids=input_ports,
        output_port_ids=output_ports or [],
        read_fact_ids=read_facts or [],
        write_fact_ids=write_facts or [],
        write_carrier_ids=write_carriers or [],
        observation_target_ids=observation_targets or [],
        substrate_refs=["decision_register"],
        invariant_ids=[f"{mechanism_id}_contract"],
        fidelity=FidelityNote(
            abstraction="Exact information delivery or collective-decision bookkeeping.",
            assumptions=["Configured routes and decision thresholds are stipulated."],
            known_omissions=["No unconfigured physical or institutional effects are inferred."],
            validation_basis=["Typed routes, declared authority, and exact invariant checks."],
        ),
    )


def _exact_bindings(
    mechanisms: Mapping[str, MechanismSpec],
) -> dict[str, ExactMechanismBinding]:
    bindings: dict[str, ExactMechanismBinding] = {}
    for mechanism_id, mechanism in mechanisms.items():
        if mechanism_id == "round_snapshot_builder":
            handler = _build_round_snapshot
        elif mechanism_id == "stance_recorder":
            handler = _record_stance
        elif mechanism_id == "decision_gate":
            handler = _evaluate_decision
        else:
            handler = _deliver_observation
        invariant_id = mechanism.invariant_ids[0]
        bindings[mechanism_id] = ExactMechanismBinding(
            mechanism.implementation_id,
            handler,
            {invariant_id: lambda _context, _outcome: True},
        )
    return bindings


def _deliver_observation(context: MechanismContext) -> MechanismOutcome:
    if context.representation is None:
        raise ValueError("information delivery requires a retained representation")
    source = context.representation
    target = context.mechanism.observation_target_ids[0]
    return MechanismOutcome(
        outcome_code="information_delivered",
        observations=[
            ObservationDraft(
                target_entity_id=target,
                via_port_id=context.target_port.port_id,
                apparent_content=source.content,
                apparent_source_ref=source.actual_source_ref,
                representation_id=source.representation_id,
            )
        ],
    )


def _build_round_snapshot(context: MechanismContext) -> MechanismOutcome:
    round_index = context.effect.payload.get("round_index")
    if not isinstance(round_index, int) or isinstance(round_index, bool) or round_index < 1:
        raise ValueError("decision round requires a positive integer round_index")
    content = json.dumps(
        {
            "document_kind": "decision_round_snapshot",
            "round_index": round_index,
            "collective_question": context.read("decision_register.question"),
            "current_public_positions": context.read("decision_register.positions"),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    representation_id = f"round_snapshot_{round_index}_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="round_snapshot_created",
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="round_snapshot_carrier",
                encoding=_ROUND_ENCODING,
                content=content,
                actual_source_ref="network_clock",
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="round_snapshot_out",
                effect_type="decision_round_snapshot",
                representation_id=representation_id,
            )
        ],
    )


def _record_stance(context: MechanismContext) -> MechanismOutcome:
    person_id = context.effect.payload.get("person_id")
    stance_value = context.effect.payload.get("stance")
    reason = context.effect.payload.get("reason")
    if not isinstance(person_id, str):
        raise ValueError("decision stance requires person_id")
    expected_person_id = context.effect.source_port_id.removeprefix("stance_").removesuffix("_out")
    if person_id != expected_person_id:
        raise ValueError("decision stance person_id does not match the owned interface")
    if not isinstance(stance_value, str) or stance_value not in _STANCES:
        raise ValueError("decision stance must be support, conditional, defer, or oppose")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("decision stance requires a concise reason")
    positions = context.read("decision_register.positions")
    if not isinstance(positions, list):
        raise ValueError("decision register positions are malformed")
    retained = [
        item
        for item in positions
        if isinstance(item, dict) and item.get("person_id") != person_id
    ]
    retained.append(
        {
            "person_id": person_id,
            "stance": cast(InfluenceStance, stance_value),
            "reason": reason.strip(),
            "logical_time": context.effect.logical_time,
        }
    )
    retained.sort(key=lambda item: str(item.get("person_id")))
    return MechanismOutcome(
        outcome_code="stance_recorded",
        updates=[
            FactUpdate(
                fact_id="decision_register.positions",
                value=cast(Any, retained),
            )
        ],
    )


def _evaluate_decision(context: MechanismContext) -> MechanismOutcome:
    participant_ids = context.read("decision_register.participant_ids")
    positions = context.read("decision_register.positions")
    rule = context.read("decision_register.decision_rule")
    if (
        not isinstance(participant_ids, list)
        or not all(isinstance(item, str) for item in participant_ids)
        or not isinstance(positions, list)
        or not isinstance(rule, dict)
    ):
        raise ValueError("decision gate inputs are malformed")
    counts = {stance: 0 for stance in sorted(_STANCES)}
    observed_people: set[str] = set()
    for item in positions:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("person_id"), str)
            or item.get("person_id") not in participant_ids
            or item.get("person_id") in observed_people
            or item.get("stance") not in _STANCES
        ):
            raise ValueError("decision gate encountered an invalid recorded stance")
        observed_people.add(str(item["person_id"]))
        counts[str(item["stance"])] += 1
    counts["defer"] += len(participant_ids) - len(observed_people)
    minimum_support = rule.get("minimum_support")
    minimum_combined = rule.get("minimum_support_or_conditional")
    maximum_oppose = rule.get("maximum_oppose")
    if not all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in (minimum_support, minimum_combined, maximum_oppose)
    ):
        raise ValueError("decision rule is malformed")
    approved = (
        counts["support"] >= cast(int, minimum_support)
        and counts["support"] + counts["conditional"] >= cast(int, minimum_combined)
        and counts["oppose"] <= cast(int, maximum_oppose)
    )
    return MechanismOutcome(
        outcome_code="collective_decision_evaluated",
        updates=[
            FactUpdate(
                fact_id="decision_register.outcome",
                value="approved" if approved else "not_approved",
            ),
            FactUpdate(
                fact_id="decision_register.counts",
                value=cast(Any, counts),
            ),
        ],
    )
