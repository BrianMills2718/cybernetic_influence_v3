"""Known executable template for one traceable information campaign pathway."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict

from cybernetic_influence.active_runtime import (
    ActivationCause, ActiveProposal, ActiveRuntimeConfig, ActiveRuntimeResult,
    RuntimeProgressObserver,
    ActiveRuntimeSession, ActiveStepResult, ActiveSystemBinding, ActiveSystemInput,
    ActiveSystemSpec, ActionIntent, ScriptedActiveSystem,
)
from cybernetic_influence.authoring.models import (
    InformationCampaignWorkflowDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.live import bind_authored_people
from cybernetic_influence.causal_core.engine import ExactMechanismBinding, MechanismContext
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary, CarrierState, CausalScenario, CausalState, ConnectionState,
    EntityState, FactState, FactUpdate, FidelityNote, MechanismOutcome,
    MechanismSpec, ObservationDraft, PlacementState, PlaceState, PortState,
    RepresentationDraft, RepresentationToken, SpatialLinkState, representation_digest,
)

_ENCODING = "application/vnd.cybernetic.information-claim+json"
_ASSESSMENT_ENCODING = "application/vnd.cybernetic.claim-assessment+json"
AssessmentDisposition = Literal["accepted", "contested", "uncertain", "deferred"]
_ASSESSMENT_DISPOSITIONS = frozenset(
    {"accepted", "contested", "uncertain", "deferred"}
)


class _Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    campaign_id: str
    claim_information_id: str
    content: str


class _Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    campaign_id: str
    disposition: AssessmentDisposition


@dataclass(frozen=True)
class InformationCampaignFixture:
    proposal: ScenarioDraftProposal
    scenario: CausalScenario
    exact_bindings: dict[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]


def information_campaign_fixture(proposal: ScenarioDraftProposal) -> InformationCampaignFixture:
    workflow = proposal.workflow
    if workflow.template_id != "information_campaign_v1":
        raise ValueError("information campaign fixture requires its matching workflow")
    people = {item.entity_id: item for item in proposal.people}
    claim = next(item for item in proposal.information if item.information_id == workflow.claim_information_id)
    entities = {
        item.entity_id: EntityState(
            entity_id=item.entity_id, entity_kind="person",
            description=f"{item.label}, positioned as {item.position}. Disposition: {item.disposition}",
        ) for item in proposal.people
    }
    entities.update({
        item.entity_id: EntityState(
            entity_id=item.entity_id, entity_kind=item.entity_kind,
            description=f"{item.label}: {item.description}",
        ) for item in proposal.objects
    })
    entities.update({
        item.information_id: EntityState(
            entity_id=item.information_id, entity_kind="information_document",
            description=f"{item.label}: {item.content}",
        ) for item in proposal.information
    })
    entities[workflow.campaign_id] = EntityState(
        entity_id=workflow.campaign_id, entity_kind="information_campaign_record",
        description="A retained campaign record; it is not an actor.",
        attributes={"status": FactState(value="drafted")},
    )
    claim_token = _Claim(
        campaign_id=workflow.campaign_id,
        claim_information_id=workflow.claim_information_id,
        content=claim.content,
    )
    state = CausalState(
        entities=entities,
        places={item.place_id: PlaceState(
            place_id=item.place_id, place_kind="authored_place",
            description=f"{item.label}: {item.description}",
        ) for item in proposal.places},
        placements={entity_id: PlacementState(entity_id=entity_id, place_id=place_id)
                    for entity_id, place_id in proposal.placements.items()},
        spatial_links={item.spatial_link_id: SpatialLinkState(
            spatial_link_id=item.spatial_link_id,
            endpoint_a_place_id=item.endpoint_a_place_id,
            endpoint_b_place_id=item.endpoint_b_place_id,
            link_kind="authored_pathway", description=item.description,
        ) for item in proposal.spatial_links},
        ports={
            "source_publish_out": PortState(
                port_id="source_publish_out",
                owner_ref=workflow.source_id,
                direction="output",
                effect_type="publish_claim",
                description=(
                    "Attempt publication of the selected retained claim "
                    "representation. Payload must be empty {}."
                ),
            ),
            "publication_in": PortState(port_id="publication_in", owner_ref="exact_publication_delivery", direction="input", effect_type="publish_claim", description="Receive a publication attempt."),
            "recipient_assess_out": PortState(
                port_id="recipient_assess_out",
                owner_ref=workflow.recipient_id,
                direction="output",
                effect_type="record_assessment",
                description=(
                    "Record an assessment of the delivered claim. Payload must "
                    'contain one field named "disposition", equal to accepted, '
                    "contested, uncertain, or deferred. Put explanatory detail "
                    "in orientation and public_summary, not in the disposition."
                ),
            ),
            "assessment_in": PortState(port_id="assessment_in", owner_ref="exact_assessment_recording", direction="input", effect_type="record_assessment", description="Receive an assessment for exact recording."),
        },
        connections={
            "publication_route": ConnectionState(connection_id="publication_route", source_port_id="source_publish_out", target_port_id="publication_in", enabled=workflow.publication_enabled, delay=workflow.publication_delivery_minutes, description="Configured claim-publication pathway; physical adjacency does not create it."),
            "assessment_route": ConnectionState(connection_id="assessment_route", source_port_id="recipient_assess_out", target_port_id="assessment_in", delay=workflow.assessment_recording_minutes, description="Configured pathway for recording the recipient's assessment."),
        },
        mechanisms={
            "exact_publication_delivery": MechanismSpec(
                mechanism_id="exact_publication_delivery", mechanism_kind="representation_delivery",
                implementation_id="exact_information_publication_v1", description="Copy the retained claim to the recipient when publication is enabled.",
                input_port_ids=["publication_in"], write_carrier_ids=["recipient_claim_buffer"],
                observation_target_ids=[workflow.recipient_id], substrate_refs=[workflow.channel_object_id, workflow.recipient_id, "recipient_claim_buffer"],
                invariant_ids=["publication_valid"], fidelity=_delivery_fidelity(),
            ),
            "exact_assessment_recording": MechanismSpec(
                mechanism_id="exact_assessment_recording", mechanism_kind="assessment_recording",
                implementation_id="exact_claim_assessment_v1", description="Record that the delivered claim was assessed; it does not infer persuasion or truth.",
                input_port_ids=["assessment_in"], read_fact_ids=[f"{workflow.campaign_id}.status"],
                write_fact_ids=[f"{workflow.campaign_id}.status"], write_carrier_ids=["assessment_record"],
                substrate_refs=[workflow.campaign_id, workflow.recipient_id, "assessment_record"],
                invariant_ids=["assessment_valid"], fidelity=_assessment_fidelity(),
            ),
        },
        carriers={
            "source_claim_carrier": CarrierState(carrier_id="source_claim_carrier", owner_ref=workflow.source_id, medium="authored_claim", locator="information_campaign/source_claim", visibility="public"),
            "recipient_claim_buffer": CarrierState(carrier_id="recipient_claim_buffer", owner_ref="exact_publication_delivery", medium="delivered_claim", locator="information_campaign/recipient_claim", visibility="public"),
            "assessment_record": CarrierState(carrier_id="assessment_record", owner_ref="exact_assessment_recording", medium="assessment_record", locator="information_campaign/assessment", visibility="public"),
        },
        representations={
            "claim_copy": RepresentationToken(
                representation_id="claim_copy", carrier_id="source_claim_carrier",
                carrier_revision=0,
                encoding=_ENCODING, content=claim_token.model_dump_json(),
                content_hash=representation_digest(claim_token.model_dump_json()),
                actual_source_ref=workflow.source_id,
            )
        },
    )
    scenario = CausalScenario(
        scenario_id=proposal.scenario_id, description=proposal.description,
        time_unit="minute", timing_contract="positive_duration", minimum_world_duration=1,
        initial_state=state,
        analytical_boundaries=[AnalyticalBoundary(
            boundary_id=item.boundary_id, label=item.label,
            description=item.description, member_refs=item.member_refs,
        ) for item in proposal.analytical_boundaries],
        fidelity_questions=proposal.fidelity_questions,
    )
    source = people[workflow.source_id]
    recipient = people[workflow.recipient_id]
    specs = (
        ActiveSystemSpec(
            active_system_id="campaign_source", entity_id=workflow.source_id,
            implementation_id="scripted_information_source_v1",
            description="The authored source person, not an organization executor.",
            output_port_ids=["source_publish_out"],
            output_port_initial_representation_ids={"source_publish_out": ["claim_copy"]},
            initial_representation_ids=["claim_copy"],
            initial_private_state={"memory": [*source.memories, source.position, source.disposition]},
        ),
        ActiveSystemSpec(
            active_system_id="campaign_recipient", entity_id=workflow.recipient_id,
            implementation_id="scripted_information_recipient_v1",
            description="The authored recipient person assessing only delivered information.",
            observation_port_ids=["publication_in"], output_port_ids=["recipient_assess_out"],
            output_port_representation_sources={"recipient_assess_out": ["publication_in"]},
            initial_private_state={"memory": [*recipient.memories, recipient.position, recipient.disposition]},
        ),
    )
    return InformationCampaignFixture(proposal, scenario, _exact_bindings(), specs)


def information_campaign_scripted_bindings(fixture: InformationCampaignFixture) -> dict[str, ActiveSystemBinding]:
    handlers: dict[str, Callable[[ActiveSystemInput], ActiveStepResult]] = {
        "campaign_source": _source_step, "campaign_recipient": _recipient_step,
    }
    result: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        handler = handlers[spec.active_system_id]
        result[spec.active_system_id] = ActiveSystemBinding(
            spec.implementation_id, ScriptedActiveSystem(spec.implementation_id, handler)
        )
    return result


def information_campaign_native_fixture_and_bindings(
    fixture: InformationCampaignFixture,
    *,
    trace_id_prefix: str,
    model: str,
    reasoning_effort: str,
    structured_call: Any = None,
) -> tuple[InformationCampaignFixture, dict[str, ActiveSystemBinding]]:
    """Bind reviewed source and recipient profiles to native LLM policies."""

    workflow = fixture.proposal.workflow
    if not isinstance(workflow, InformationCampaignWorkflowDraft):
        raise ValueError("information campaign live binding requires its matching workflow")
    people = {person.entity_id: person for person in fixture.proposal.people}
    specs, bindings = bind_authored_people(
        fixture.active_specs,
        {
            "campaign_source": people[workflow.source_id],
            "campaign_recipient": people[workflow.recipient_id],
        },
        trace_id_prefix=trace_id_prefix,
        model=model,
        reasoning_effort=reasoning_effort,
        retained_context={
            "campaign_source": (
                (
                    "retained_claim",
                    fixture.scenario.initial_state.representations[
                        "claim_copy"
                    ].content,
                ),
            ),
        },
        structured_call=structured_call,
    )
    return replace(fixture, active_specs=specs), bindings


def run_information_campaign(
    fixture: InformationCampaignFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
    runtime_config: ActiveRuntimeConfig | None = None,
    progress_observer: RuntimeProgressObserver | None = None,
) -> ActiveRuntimeResult:
    session = ActiveRuntimeSession(
        fixture.scenario, fixture.exact_bindings, fixture.active_specs, bindings,
        run_id=run_id,
        config=runtime_config
        or ActiveRuntimeConfig(
            per_call_budget=0.01,
            per_run_budget=0.02,
            max_actions_per_system=1,
            max_observations_per_system=8,
            max_private_state_bytes=8192,
        ),
        progress_observer=progress_observer,
    )
    session.activate(["campaign_source"], logical_time=0, activation_causes={
        "campaign_source": [ActivationCause(kind="scenario_start", scheduled_for=0, description="The source retained the authored claim at scenario start.")]
    })
    while (due := session.next_due_activation()) is not None:
        if len(session.attempts) >= 6:
            raise RuntimeError("information-campaign scheduler exceeded its bound")
        session.activate(due.active_system_ids, logical_time=due.logical_time, activation_causes=due.causes)
    return session.complete()


def _source_step(item: ActiveSystemInput) -> ActiveStepResult:
    return ActiveStepResult(proposal=ActiveProposal(
        active_system_id="campaign_source", implementation_id="scripted_information_source_v1",
        private_state=item.private_state,
        actions=[ActionIntent(output_port_id="source_publish_out", representation_id="claim_copy", public_summary="The source attempted to publish the retained claim.")],
    ))


def _recipient_step(item: ActiveSystemInput) -> ActiveStepResult:
    observation = next((value for value in item.observations if value.via_port_id == "publication_in"), None)
    actions = [] if observation is None else [ActionIntent(
        output_port_id="recipient_assess_out", representation_id=observation.representation_id,
        payload={"disposition": "contested"},
        public_summary="The recipient recorded a contested assessment of the delivered claim.",
    )]
    return ActiveStepResult(proposal=ActiveProposal(
        active_system_id="campaign_recipient", implementation_id="scripted_information_recipient_v1",
        private_state=item.private_state, actions=actions,
    ))


def _exact_bindings() -> dict[str, ExactMechanismBinding]:
    return {
        "exact_publication_delivery": ExactMechanismBinding("exact_information_publication_v1", _deliver, {"publication_valid": lambda _c, o: len(o.observations) == 1}),
        "exact_assessment_recording": ExactMechanismBinding("exact_claim_assessment_v1", _record_assessment, {"assessment_valid": lambda _c, o: o.outcome_code == "assessment_recorded"}),
    }


def _deliver(context: MechanismContext) -> MechanismOutcome:
    if context.effect.payload:
        raise ValueError("claim publication payload must be empty")
    source = _source_representation(context)
    representation_id = f"delivered_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="delivered",
        representations=[RepresentationDraft(
            representation_id=representation_id, carrier_id="recipient_claim_buffer",
            encoding=source.encoding, content=source.content,
            actual_source_ref=source.actual_source_ref,
            parent_representation_ids=[source.representation_id],
        )],
        observations=[ObservationDraft(
            target_entity_id=context.mechanism.observation_target_ids[0],
            via_port_id=context.target_port.port_id, apparent_content=source.content,
            apparent_source_ref=source.actual_source_ref, representation_id=representation_id,
        )],
    )


def _record_assessment(context: MechanismContext) -> MechanismOutcome:
    claim = _Claim.model_validate_json(_source_representation(context).content)
    disposition_value = context.effect.payload.get("disposition")
    if (
        not isinstance(disposition_value, str)
        or disposition_value not in _ASSESSMENT_DISPOSITIONS
    ):
        raise ValueError(
            "assessment disposition must be accepted, contested, uncertain, or deferred"
        )
    disposition = cast(AssessmentDisposition, disposition_value)
    assessment = _Assessment(campaign_id=claim.campaign_id, disposition=disposition)
    return MechanismOutcome(
        outcome_code="assessment_recorded",
        updates=[FactUpdate(fact_id=f"{claim.campaign_id}.status", value=f"assessed_{disposition}")],
        representations=[RepresentationDraft(
            representation_id=f"assessment_{context.route_event_id}", carrier_id="assessment_record",
            encoding=_ASSESSMENT_ENCODING, content=assessment.model_dump_json(),
            actual_source_ref=context.mechanism.substrate_refs[1],
            parent_representation_ids=[_source_representation(context).representation_id],
        )],
    )


def _source_representation(context: MechanismContext) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("information-campaign mechanism requires a representation")
    return context.representation


def _delivery_fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction="One exact configured claim delivery.",
        assumptions=["The configured publication route carries the retained claim."],
        known_omissions=["Ranking, virality, persuasion, and platform internals are not modeled."],
        validation_basis=["Typed carrier lineage and exact observation delivery."],
    )


def _assessment_fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction="A recipient records an assessment after receiving the claim.",
        assumptions=["The reference recipient contests the delivered claim."],
        known_omissions=["Belief change, diplomatic effects, population response, and truth adjudication are not inferred."],
        validation_basis=["Assessment requires a delivered representation and exact state update."],
    )
