"""The single approved ``resource_request_v1`` executable template.

This module is deliberately concrete.  It compiles an equipment-style request
into the existing exact causal runtime; it is not an interpreter for arbitrary
world-transition code.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from cybernetic_influence.active_runtime import (
    ActivationCause,
    ActiveProposal,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    ActionIntent,
    ScriptedActiveSystem,
)
from cybernetic_influence.authoring.models import (
    ResourceRequestWorkflowDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.live import bind_authored_people
from cybernetic_influence.causal_core.engine import (
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
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


_FORBID = ConfigDict(extra="forbid", strict=True)
_REQUEST_ENCODING = "application/vnd.cybernetic.resource-request+json"
_POLICY_ENCODING = "application/vnd.cybernetic.resource-policy+json"
_RESULT_ENCODING = "application/vnd.cybernetic.resource-result+json"


class _StrictModel(BaseModel):
    model_config = _FORBID


class _Request(_StrictModel):
    request_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    requester_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    resource_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")


class _Policy(_StrictModel):
    eligible_requester_ids: list[str] = Field(min_length=1)


class _Result(_StrictModel):
    request_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    resource_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    status: str = Field(pattern=r"^(reserved|denied_ineligible|denied_unavailable)$")


@dataclass(frozen=True)
class ResourceRequestFixture:
    proposal: ScenarioDraftProposal
    scenario: CausalScenario
    exact_bindings: dict[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]


def resource_request_fixture(proposal: ScenarioDraftProposal) -> ResourceRequestFixture:
    """Build the known resource-request topology from an already valid draft."""

    people = {item.entity_id: item for item in proposal.people}
    objects = {item.entity_id: item for item in proposal.objects}
    information = {item.information_id: item for item in proposal.information}
    workflow = proposal.workflow
    if not isinstance(workflow, ResourceRequestWorkflowDraft):
        raise ValueError("resource request fixture requires its matching workflow")
    requester = people[workflow.requester_id]
    reviewer = people[workflow.reviewer_id]
    resource = objects[workflow.resource_id]
    policy = information[workflow.policy_information_id]
    state = CausalState(
        entities=_entities(proposal),
        places={
            item.place_id: PlaceState(
                place_id=item.place_id,
                place_kind="authored_place",
                description=f"{item.label}: {item.description}",
            )
            for item in proposal.places
        },
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
        ports=_ports(workflow.requester_id, workflow.reviewer_id),
        connections=_connections(proposal),
        mechanisms=_mechanisms(
            workflow.requester_id,
            workflow.reviewer_id,
            workflow.resource_id,
            workflow.request_id,
            workflow.policy_information_id,
        ),
        carriers=_carriers(workflow.requester_id, workflow.policy_information_id),
        representations={
            "request_copy": _token(
                "request_copy",
                "requester_request_carrier",
                _REQUEST_ENCODING,
                _Request(
                    request_id=workflow.request_id,
                    requester_id=workflow.requester_id,
                    resource_id=workflow.resource_id,
                ),
                workflow.requester_id,
            ),
            "policy_copy": _token(
                "policy_copy",
                "policy_carrier",
                _POLICY_ENCODING,
                _Policy(eligible_requester_ids=workflow.eligible_requester_ids),
                workflow.policy_information_id,
            ),
        },
    )
    scenario = CausalScenario(
        scenario_id=proposal.scenario_id,
        description=proposal.description,
        time_unit="minute",
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
    return ResourceRequestFixture(
        proposal=proposal,
        scenario=scenario,
        exact_bindings=_exact_bindings(),
        active_specs=_active_specs(requester, reviewer, policy.content),
    )


def resource_request_scripted_bindings(
    fixture: ResourceRequestFixture,
) -> dict[str, ActiveSystemBinding]:
    """Return the zero-cost reference policies for the approved template."""

    handlers: dict[str, Callable[[ActiveSystemInput], ActiveStepResult]] = {
        "requester": _scripted_requester,
        "reviewer": _scripted_reviewer,
    }
    bindings: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        handler = handlers[spec.active_system_id]

        def bound(
            active_input: ActiveSystemInput,
            *,
            selected_handler: Callable[[ActiveSystemInput], ActiveStepResult] = handler,
            implementation_id: str = spec.implementation_id,
        ) -> ActiveStepResult:
            result = selected_handler(active_input)
            return result.model_copy(
                update={
                    "proposal": result.proposal.model_copy(
                        update={"implementation_id": implementation_id}
                    )
                }
            )

        bindings[spec.active_system_id] = ActiveSystemBinding(
            spec.implementation_id,
            ScriptedActiveSystem(spec.implementation_id, bound),
        )
    return bindings


def resource_request_native_fixture_and_bindings(
    fixture: ResourceRequestFixture,
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str,
    structured_call: Any = None,
) -> tuple[ResourceRequestFixture, dict[str, ActiveSystemBinding]]:
    """Bind reviewed requester and reviewer profiles to native LLM policies."""

    workflow = fixture.proposal.workflow
    if not isinstance(workflow, ResourceRequestWorkflowDraft):
        raise ValueError("resource request live binding requires its matching workflow")
    people = {person.entity_id: person for person in fixture.proposal.people}
    policy = next(
        item
        for item in fixture.proposal.information
        if item.information_id == workflow.policy_information_id
    )
    specs, bindings = bind_authored_people(
        fixture.active_specs,
        {
            "requester": people[workflow.requester_id],
            "reviewer": people[workflow.reviewer_id],
        },
        trace_id_prefix=trace_id_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
        retained_context={
            "requester": (
                (
                    "retained_request",
                    fixture.scenario.initial_state.representations[
                        "request_copy"
                    ].content,
                ),
            ),
            "reviewer": (("written_policy", policy.content),),
        },
        structured_call=structured_call,
    )
    return replace(fixture, active_specs=specs), bindings


def run_resource_request(
    fixture: ResourceRequestFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
    runtime_config: ActiveRuntimeConfig | None = None,
) -> ActiveRuntimeResult:
    """Run the known template event by event, without a provider call."""

    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id=run_id,
        config=runtime_config
        or ActiveRuntimeConfig(
            per_call_budget=0.01,
            per_run_budget=0.02,
            max_actions_per_system=1,
            max_observations_per_system=8,
            max_private_state_bytes=8_192,
        ),
    )
    session.activate(
        ["requester"],
        logical_time=0,
        activation_causes={
            "requester": [
                ActivationCause(
                    kind="scenario_start",
                    scheduled_for=0,
                    description="The requester retained the authored request at scenario start.",
                )
            ]
        },
    )
    while (due := session.next_due_activation()) is not None:
        if len(session.attempts) >= 8:
            raise RuntimeError("resource-request scheduler exceeded its causal-moment bound")
        session.activate(
            due.active_system_ids,
            logical_time=due.logical_time,
            activation_causes=due.causes,
        )
    return session.complete()


def _entities(proposal: ScenarioDraftProposal) -> dict[str, EntityState]:
    workflow = proposal.workflow
    if not isinstance(workflow, ResourceRequestWorkflowDraft):
        raise ValueError("resource request entities require their matching workflow")
    result: dict[str, EntityState] = {
        item.entity_id: EntityState(
            entity_id=item.entity_id,
            entity_kind="person",
            description=(
                f"{item.label}, positioned as {item.position}. "
                f"Disposition: {item.disposition}"
            ),
        )
        for item in proposal.people
    }
    result.update(
        {
            item.entity_id: EntityState(
                entity_id=item.entity_id,
                entity_kind=item.entity_kind,
                description=f"{item.label}: {item.description}",
                attributes=(
                    {"availability": FactState(value=(
                        "available" if workflow.resource_available else "unavailable"
                    ))}
                    if item.entity_id == workflow.resource_id
                    else {}
                ),
            )
            for item in proposal.objects
        }
    )
    result[workflow.request_id] = EntityState(
        entity_id=workflow.request_id,
        entity_kind="resource_request",
        description="The authored request record; it is not an active system.",
        attributes={"status": FactState(value="open")},
    )
    result.update(
        {
            item.information_id: EntityState(
                entity_id=item.information_id,
                entity_kind="information_document",
                description=f"{item.label}: {item.content}",
            )
            for item in proposal.information
        }
    )
    return result


def _ports(requester_id: str, reviewer_id: str) -> dict[str, PortState]:
    return {
        "requester_submit_out": PortState(
            port_id="requester_submit_out", owner_ref=requester_id, direction="output",
            effect_type="resource_request",
            description=(
                "Submit the selected retained request representation to the "
                "configured route. Payload must be empty {}."
            ),
        ),
        "reviewer_request_in": PortState(
            port_id="reviewer_request_in", owner_ref="exact_request_delivery", direction="input",
            effect_type="resource_request", description="Receive a request for reviewer-visible delivery.",
        ),
        "reviewer_decision_out": PortState(
            port_id="reviewer_decision_out", owner_ref=reviewer_id, direction="output",
            effect_type="review_decision",
            description=(
                "Submit the delivered request to the exact reservation gate. "
                'Payload must be {"approve": true} to request reservation or '
                '{"approve": false} to request denial.'
            ),
        ),
        "reservation_gate_in": PortState(
            port_id="reservation_gate_in", owner_ref="exact_reservation_gate", direction="input",
            effect_type="review_decision", description="Receive a review decision for exact eligibility and availability checking.",
        ),
        "reservation_result_out": PortState(
            port_id="reservation_result_out", owner_ref="exact_reservation_gate", direction="output",
            effect_type="resource_result", description="Publish the exact reservation result.",
        ),
        "requester_result_in": PortState(
            port_id="requester_result_in", owner_ref="exact_requester_result_delivery", direction="input",
            effect_type="resource_result", description="Receive the result at the requester interface.",
        ),
    }


def _connections(proposal: ScenarioDraftProposal) -> dict[str, ConnectionState]:
    workflow = proposal.workflow
    if not isinstance(workflow, ResourceRequestWorkflowDraft):
        raise ValueError("resource request connections require their matching workflow")
    return {
        "request_route": ConnectionState(
            connection_id="request_route", source_port_id="requester_submit_out",
            target_port_id="reviewer_request_in", delay=workflow.request_delivery_minutes,
            description="The configured request route; spatial adjacency does not create this route.",
        ),
        "decision_route": ConnectionState(
            connection_id="decision_route", source_port_id="reviewer_decision_out",
            target_port_id="reservation_gate_in", delay=workflow.decision_delivery_minutes,
            description="The configured route from a reviewer attempt to the exact reservation gate.",
        ),
        "requester_result_route": ConnectionState(
            connection_id="requester_result_route", source_port_id="reservation_result_out",
            target_port_id="requester_result_in", delay=workflow.result_delivery_minutes,
            description="The configured result route to the requester.",
        ),
    }


def _mechanisms(
    requester_id: str,
    reviewer_id: str,
    resource_id: str,
    request_id: str,
    policy_information_id: str,
) -> dict[str, MechanismSpec]:
    delivery_fidelity = FidelityNote(
        abstraction="A declared point-to-point copy and observation delivery.",
        assumptions=["The configured route can carry the one retained representation."],
        known_omissions=["Network, hallway travel, and platform internals are omitted."],
        validation_basis=["Typed ports, carrier lineage, and exact input binding."],
    )
    gate_fidelity = FidelityNote(
        abstraction="An exact reservation gate over stated eligibility and availability.",
        assumptions=["The copied policy and resource availability are authoritative for this bounded request."],
        known_omissions=["Inventory synchronization and real identity proof are omitted."],
        validation_basis=["Exact handler plus independent invariant checker."],
    )
    return {
        "exact_request_delivery": MechanismSpec(
            mechanism_id="exact_request_delivery", mechanism_kind="representation_delivery",
            implementation_id="exact_resource_delivery_v1", description="Copy the request to the reviewer-visible interface.",
            input_port_ids=["reviewer_request_in"], write_carrier_ids=["reviewer_request_buffer"],
            observation_target_ids=[reviewer_id], substrate_refs=[reviewer_id, "reviewer_request_buffer"],
            invariant_ids=["delivery_valid"], fidelity=delivery_fidelity,
        ),
        "exact_reservation_gate": MechanismSpec(
            mechanism_id="exact_reservation_gate", mechanism_kind="reservation_gate",
            implementation_id="exact_resource_reservation_v1", description="Check a requested reservation against copied eligibility and exact availability.",
            input_port_ids=["reservation_gate_in"], output_port_ids=["reservation_result_out"],
            read_fact_ids=[f"{resource_id}.availability", f"{request_id}.status"], read_representation_ids=["policy_copy"],
            write_fact_ids=[f"{resource_id}.availability", f"{request_id}.status"], write_carrier_ids=["reservation_result_buffer"],
            substrate_refs=[resource_id, request_id, policy_information_id, "reservation_result_buffer"],
            invariant_ids=["reservation_valid"], fidelity=gate_fidelity,
        ),
        "exact_requester_result_delivery": MechanismSpec(
            mechanism_id="exact_requester_result_delivery", mechanism_kind="representation_delivery",
            implementation_id="exact_resource_delivery_v1", description="Copy the reservation result to the requester-visible interface.",
            input_port_ids=["requester_result_in"], write_carrier_ids=["requester_result_buffer"],
            observation_target_ids=[requester_id], substrate_refs=[requester_id, "requester_result_buffer"],
            invariant_ids=["delivery_valid"], fidelity=delivery_fidelity,
        ),
    }


def _carriers(requester_id: str, policy_information_id: str) -> dict[str, CarrierState]:
    owners = {
        "requester_request_carrier": requester_id, "policy_carrier": policy_information_id,
        "reviewer_request_buffer": "exact_request_delivery",
        "reservation_result_buffer": "exact_reservation_gate",
        "requester_result_buffer": "exact_requester_result_delivery",
    }
    return {
        carrier_id: CarrierState(
            carrier_id=carrier_id, owner_ref=owner, medium="resource_request_record",
            locator=f"resource_request/{carrier_id}",
            visibility="mechanism" if carrier_id == "policy_carrier" else "public",
        )
        for carrier_id, owner in owners.items()
    }


def _active_specs(requester: object, reviewer: object, policy_text: str) -> tuple[ActiveSystemSpec, ...]:
    # Kept descriptive: positions and memories are context, not imperative scripts.
    requester_item = requester
    reviewer_item = reviewer
    return (
        ActiveSystemSpec(
            active_system_id="requester", entity_id=getattr(requester_item, "entity_id"),
            implementation_id="scripted_resource_request_requester_v1",
            description="A bounded person process for the authored requester.",
            output_port_ids=["requester_submit_out"],
            output_port_initial_representation_ids={"requester_submit_out": ["request_copy"]},
            initial_representation_ids=["request_copy"],
            initial_private_state={"memory": list(getattr(requester_item, "memories")) + [getattr(requester_item, "position"), getattr(requester_item, "disposition")]},
        ),
        ActiveSystemSpec(
            active_system_id="reviewer", entity_id=getattr(reviewer_item, "entity_id"),
            implementation_id="scripted_resource_request_reviewer_v1",
            description="A bounded person process for the authored reviewer.",
            observation_port_ids=["reviewer_request_in"], output_port_ids=["reviewer_decision_out"],
            output_port_representation_sources={"reviewer_decision_out": ["reviewer_request_in"]},
            initial_private_state={"memory": list(getattr(reviewer_item, "memories")) + [getattr(reviewer_item, "position"), getattr(reviewer_item, "disposition"), policy_text]},
        ),
    )


def _exact_bindings() -> dict[str, ExactMechanismBinding]:
    return {
        "exact_request_delivery": ExactMechanismBinding("exact_resource_delivery_v1", _deliver, {"delivery_valid": _delivery_valid}),
        "exact_reservation_gate": ExactMechanismBinding("exact_resource_reservation_v1", _reserve, {"reservation_valid": _reservation_valid}),
        "exact_requester_result_delivery": ExactMechanismBinding("exact_resource_delivery_v1", _deliver, {"delivery_valid": _delivery_valid}),
    }


def _deliver(context: MechanismContext) -> MechanismOutcome:
    if context.effect.payload:
        raise ValueError("resource delivery payload must be empty")
    source = _source(context)
    carrier_id = {
        "exact_request_delivery": "reviewer_request_buffer",
        "exact_requester_result_delivery": "requester_result_buffer",
    }[context.mechanism.mechanism_id]
    target_id = context.mechanism.observation_target_ids[0]
    representation_id = f"delivered_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="delivered",
        representations=[RepresentationDraft(
            representation_id=representation_id, carrier_id=carrier_id, encoding=source.encoding,
            content=source.content, actual_source_ref=source.actual_source_ref,
            parent_representation_ids=[source.representation_id],
        )],
        observations=[ObservationDraft(
            target_entity_id=target_id, via_port_id=context.target_port.port_id,
            apparent_content=source.content, apparent_source_ref=source.actual_source_ref,
            representation_id=representation_id,
        )],
    )


def _reserve(context: MechanismContext) -> MechanismOutcome:
    request = _Request.model_validate_json(_source(context).content)
    policy = _Policy.model_validate_json(context.read_representation("policy_copy").content)
    approve_value = context.effect.payload.get("approve")
    if not isinstance(approve_value, bool):
        raise ValueError("review decision approve must be a boolean")
    approved = approve_value
    available = context.read(f"{request.resource_id}.availability") == "available"
    eligible = request.requester_id in policy.eligible_requester_ids
    status = "reserved" if approved and available and eligible else (
        "denied_unavailable" if not available else "denied_ineligible"
    )
    result = _Result(request_id=request.request_id, resource_id=request.resource_id, status=status)
    representation_id = f"reservation_result_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            *(
                [
                    FactUpdate(
                        fact_id=f"{request.resource_id}.availability",
                        value="reserved",
                    )
                ]
                if status == "reserved"
                else []
            ),
            FactUpdate(fact_id=f"{request.request_id}.status", value=status),
        ],
        representations=[RepresentationDraft(
            representation_id=representation_id, carrier_id="reservation_result_buffer", encoding=_RESULT_ENCODING,
            content=_render(result), actual_source_ref="exact_reservation_gate",
            parent_representation_ids=[_source(context).representation_id, "policy_copy"],
        )],
        effects=[EffectDraft(output_port_id="reservation_result_out", effect_type="resource_result", representation_id=representation_id)],
    )


def _delivery_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    return outcome.outcome_code == "delivered" and len(outcome.representations) == 1 and len(outcome.observations) == 1


def _reservation_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    request = _Request.model_validate_json(_source(context).content)
    policy = _Policy.model_validate_json(context.read_representation("policy_copy").content)
    approve_value = context.effect.payload.get("approve")
    if not isinstance(approve_value, bool):
        return False
    expected = "reserved" if (
        approve_value is True
        and context.read(f"{request.resource_id}.availability") == "available"
        and request.requester_id in policy.eligible_requester_ids
    ) else ("denied_unavailable" if context.read(f"{request.resource_id}.availability") != "available" else "denied_ineligible")
    return outcome.outcome_code == expected


def _scripted_requester(item: ActiveSystemInput) -> ActiveStepResult:
    return ActiveStepResult(proposal=ActiveProposal(
        active_system_id="requester", implementation_id="scripted_resource_request_requester_v1",
        private_state=item.private_state,
        actions=[ActionIntent(output_port_id="requester_submit_out", representation_id="request_copy", public_summary="Requester submitted the retained resource request.")],
    ))


def _scripted_reviewer(item: ActiveSystemInput) -> ActiveStepResult:
    observation = next((entry for entry in item.observations if entry.via_port_id == "reviewer_request_in"), None)
    actions = [] if observation is None else [ActionIntent(
        output_port_id="reviewer_decision_out", representation_id=observation.representation_id,
        payload={"approve": True}, public_summary="Reviewer requested approval of the delivered resource request.",
    )]
    return ActiveStepResult(proposal=ActiveProposal(
        active_system_id="reviewer", implementation_id="scripted_resource_request_reviewer_v1",
        private_state=item.private_state, actions=actions,
    ))


def _source(context: MechanismContext) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("resource-request mechanism requires a representation")
    return context.representation


def _token(representation_id: str, carrier_id: str, encoding: str, model: BaseModel, source_ref: str) -> RepresentationToken:
    content = _render(model)
    return RepresentationToken(
        representation_id=representation_id, carrier_id=carrier_id, carrier_revision=0,
        encoding=encoding, content=content, content_hash=representation_digest(content), actual_source_ref=source_ref,
    )


def _render(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
