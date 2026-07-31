"""Validate and compile the one approved authoring template.

The compiler is the security and ontology boundary.  A draft may name people,
objects, places, information, timing assumptions, and a known workflow.  It
never supplies arbitrary code or lets a draft turn an analytical boundary into
an executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from cybernetic_influence.active_runtime import (
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    RuntimeProgressObserver,
)
from cybernetic_influence.authoring.models import (
    CoordinationDecisionWorkflowDraft,
    InformationCampaignWorkflowDraft,
    ResourceRequestWorkflowDraft,
    ScenarioDraftProposal,
)
from cybernetic_influence.authoring.coordination_decision import (
    authored_coordination_fixture,
    validate_coordination_proposal,
)
from cybernetic_influence.authoring.information_campaign import (
    InformationCampaignFixture,
    information_campaign_fixture,
    information_campaign_native_fixture_and_bindings,
    information_campaign_scripted_bindings,
    run_information_campaign,
)
from cybernetic_influence.authoring.resource_request import (
    ResourceRequestFixture,
    resource_request_fixture,
    resource_request_native_fixture_and_bindings,
    resource_request_scripted_bindings,
    run_resource_request,
)
from cybernetic_influence.causal_core.engine import ExactMechanismBinding
from cybernetic_influence.causal_core.models import CausalScenario
from cybernetic_influence.scenarios.coordination_decision import (
    CoordinationRuntimeFixture,
    coordination_native_bindings,
    coordination_runtime_config,
    coordination_runtime_fixture,
    run_coordination,
    run_scripted_coordination,
)


class AuthoringCompilationError(ValueError):
    """A typed draft cannot be compiled by the approved template."""


_RESOURCE_REQUEST_RUNTIME_IDS = frozenset(
    {
        "exact_request_delivery",
        "exact_reservation_gate",
        "exact_requester_result_delivery",
        "requester_submit_out",
        "reviewer_request_in",
        "reviewer_decision_out",
        "reservation_gate_in",
        "reservation_result_out",
        "requester_result_in",
        "requester_request_carrier",
        "policy_carrier",
        "reviewer_request_buffer",
        "reservation_result_buffer",
        "requester_result_buffer",
        "request_copy",
        "policy_copy",
    }
)

_INFORMATION_CAMPAIGN_RUNTIME_IDS = frozenset(
    {
        "exact_publication_delivery",
        "exact_assessment_recording",
        "source_publish_out",
        "publication_in",
        "recipient_assess_out",
        "assessment_in",
        "publication_route",
        "assessment_route",
        "source_claim_carrier",
        "recipient_claim_buffer",
        "assessment_record",
        "claim_copy",
        "campaign_source",
        "campaign_recipient",
    }
)


@dataclass(frozen=True)
class CompiledScenario:
    """The executable result of one reviewed template-bound draft."""

    proposal: ScenarioDraftProposal
    proposal_digest: str
    fixture: (
        ResourceRequestFixture
        | InformationCampaignFixture
        | CoordinationRuntimeFixture
    )

    @property
    def scenario(self) -> CausalScenario:
        return self.fixture.scenario

    @property
    def exact_bindings(self) -> dict[str, ExactMechanismBinding]:
        return dict(self.fixture.exact_bindings)

    def run_scripted(
        self, *, run_id: str, progress_observer: RuntimeProgressObserver | None = None
    ) -> ActiveRuntimeResult:
        if isinstance(self.fixture, CoordinationRuntimeFixture):
            return run_scripted_coordination(
                self.fixture,
                run_id=run_id,
                progress_observer=progress_observer,
            )
        if isinstance(self.fixture, InformationCampaignFixture):
            return run_information_campaign(
                self.fixture,
                information_campaign_scripted_bindings(self.fixture),
                run_id=run_id,
                progress_observer=progress_observer,
            )
        return run_resource_request(
            self.fixture,
            resource_request_scripted_bindings(self.fixture),
            run_id=run_id,
            progress_observer=progress_observer,
        )

    def run_live(
        self,
        *,
        run_id: str,
        model: str,
        reasoning_effort: str,
        per_call_budget: float,
        per_run_budget: float,
        structured_call: Any = None,
        progress_observer: RuntimeProgressObserver | None = None,
    ) -> ActiveRuntimeResult:
        """Run reviewed people through native LLM policies and exact mechanisms."""

        runtime_config = ActiveRuntimeConfig(
            per_call_budget=per_call_budget,
            per_run_budget=per_run_budget,
            max_actions_per_system=1,
            max_observations_per_system=8,
            max_private_state_bytes=16_384,
        )
        if isinstance(self.fixture, CoordinationRuntimeFixture):
            live_fixture = coordination_runtime_fixture(
                self.fixture.contract,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            bindings = coordination_native_bindings(
                live_fixture,
                trace_id_prefix=run_id,
                model=model,
                reasoning_effort=reasoning_effort,
            )
            return run_coordination(
                live_fixture,
                bindings,
                run_id=run_id,
                runtime_config=coordination_runtime_config(
                    per_call_budget=per_call_budget,
                    per_run_budget=per_run_budget,
                ),
                progress_observer=progress_observer,
            )
        if isinstance(self.fixture, InformationCampaignFixture):
            campaign_fixture, campaign_bindings = (
                information_campaign_native_fixture_and_bindings(
                    self.fixture,
                    trace_id_prefix=run_id,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    structured_call=structured_call,
                )
            )
            return run_information_campaign(
                campaign_fixture,
                campaign_bindings,
                run_id=run_id,
                runtime_config=runtime_config,
                progress_observer=progress_observer,
            )
        request_fixture, request_bindings = (
            resource_request_native_fixture_and_bindings(
                self.fixture,
                trace_id_prefix=run_id,
                model=model,
                reasoning_effort=reasoning_effort,
                structured_call=structured_call,
            )
        )
        return run_resource_request(
            request_fixture,
            request_bindings,
            run_id=run_id,
            runtime_config=runtime_config,
            progress_observer=progress_observer,
        )


def compile_resource_request(proposal: ScenarioDraftProposal) -> CompiledScenario:
    """Compile only ``resource_request_v1`` after semantic validation."""

    selected = ScenarioDraftProposal.model_validate(proposal.model_dump(mode="json"))
    if selected.workflow.template_id != "resource_request_v1":
        raise AuthoringCompilationError("proposal is not a resource_request_v1 workflow")
    _validate_resource_request(selected)
    return CompiledScenario(
        proposal=selected,
        proposal_digest=_proposal_digest(selected),
        fixture=resource_request_fixture(selected),
    )


def compile_scenario(proposal: ScenarioDraftProposal) -> CompiledScenario:
    """Dispatch one typed proposal to a known, reviewed executable template."""

    if proposal.workflow.template_id == "resource_request_v1":
        return compile_resource_request(proposal)
    if proposal.workflow.template_id == "information_campaign_v1":
        selected = ScenarioDraftProposal.model_validate(proposal.model_dump(mode="json"))
        _validate_information_campaign(selected)
        return CompiledScenario(
            proposal=selected,
            proposal_digest=_proposal_digest(selected),
            fixture=information_campaign_fixture(selected),
        )
    if proposal.workflow.template_id == "coordination_decision_v1":
        return compile_coordination_decision(proposal)
    raise AuthoringCompilationError("unknown authored scenario template")


def compile_coordination_decision(
    proposal: ScenarioDraftProposal,
) -> CompiledScenario:
    """Compile reviewed coordination values onto existing exact mechanisms."""

    selected = ScenarioDraftProposal.model_validate(proposal.model_dump(mode="json"))
    if not isinstance(selected.workflow, CoordinationDecisionWorkflowDraft):
        raise AuthoringCompilationError(
            "proposal is not a coordination_decision_v1 workflow"
        )
    try:
        validate_coordination_proposal(selected)
        contract = authored_coordination_fixture(selected)
    except ValueError as error:
        raise AuthoringCompilationError(str(error)) from error
    return CompiledScenario(
        proposal=selected,
        proposal_digest=_proposal_digest(selected),
        fixture=coordination_runtime_fixture(contract),
    )


def _validate_information_campaign(proposal: ScenarioDraftProposal) -> None:
    workflow = proposal.workflow
    if not isinstance(workflow, InformationCampaignWorkflowDraft):
        raise AuthoringCompilationError("proposal is not an information_campaign_v1 workflow")
    people = {item.entity_id for item in proposal.people}
    objects = {item.entity_id for item in proposal.objects}
    information = {item.information_id for item in proposal.information}
    places = {item.place_id for item in proposal.places}
    for label, value, allowed in (
        ("source_id", workflow.source_id, people),
        ("recipient_id", workflow.recipient_id, people),
        ("claim_information_id", workflow.claim_information_id, information),
        ("channel_object_id", workflow.channel_object_id, objects),
    ):
        if value not in allowed:
            raise AuthoringCompilationError(f"{label} does not name a declared referent: {value}")
    if workflow.source_id == workflow.recipient_id:
        raise AuthoringCompilationError("information_campaign_v1 requires distinct source and recipient")
    authored_campaign_records = sorted(
        item.entity_id for item in proposal.objects if item.entity_kind == "campaign_record"
    )
    if authored_campaign_records:
        raise AuthoringCompilationError(
            "information_campaign_v1 creates its campaign record from workflow.campaign_id; "
            "remove separately declared campaign_record objects and reference campaign_id "
            f"from analytical boundaries instead: {authored_campaign_records!r}"
        )
    declared_ids = [
        *(item.entity_id for item in proposal.people),
        *(item.entity_id for item in proposal.objects),
        *(item.information_id for item in proposal.information),
        workflow.campaign_id,
    ]
    declared = set(declared_ids)
    if len(declared) != len(declared_ids):
        duplicates = sorted(
            entity_id for entity_id in declared if declared_ids.count(entity_id) > 1
        )
        raise AuthoringCompilationError(
            "campaign, people, objects, and information need distinct ids; "
            f"duplicate ids: {duplicates!r}"
        )
    if reserved := declared & _INFORMATION_CAMPAIGN_RUNTIME_IDS:
        raise AuthoringCompilationError(
            "draft entity ids collide with information_campaign_v1 runtime ids: "
            f"{sorted(reserved)!r}"
        )
    required_placements = {workflow.source_id, workflow.recipient_id, workflow.channel_object_id}
    if unknown := set(proposal.placements) - (people | objects):
        raise AuthoringCompilationError(f"placements has unknown entities: {sorted(unknown)!r}")
    if missing := required_placements - set(proposal.placements):
        raise AuthoringCompilationError(f"placements missing required entities: {sorted(missing)!r}")
    if unknown := set(proposal.placements.values()) - places:
        raise AuthoringCompilationError(f"placements names unknown places: {sorted(unknown)!r}")
    for link in proposal.spatial_links:
        if {link.endpoint_a_place_id, link.endpoint_b_place_id} - places:
            raise AuthoringCompilationError(f"spatial link {link.spatial_link_id} names an unknown place")
    timing = {item.name: item.minutes for item in proposal.timing_assumptions}
    expected = {
        "publication_delivery": workflow.publication_delivery_minutes,
        "assessment_recording": workflow.assessment_recording_minutes,
    }
    for name, minutes in expected.items():
        if timing.get(name) != minutes:
            raise AuthoringCompilationError(f"timing assumption {name!r} must equal workflow duration {minutes}")
    for boundary in proposal.analytical_boundaries:
        if unknown := set(boundary.member_refs) - declared:
            raise AuthoringCompilationError(
                f"boundary {boundary.boundary_id} has unknown members: {sorted(unknown)!r}"
            )


def _validate_resource_request(proposal: ScenarioDraftProposal) -> None:
    workflow = proposal.workflow
    if not isinstance(workflow, ResourceRequestWorkflowDraft):
        raise AuthoringCompilationError("proposal is not a resource_request_v1 workflow")
    people = {item.entity_id for item in proposal.people}
    objects = {item.entity_id for item in proposal.objects}
    information = {item.information_id for item in proposal.information}
    places = {item.place_id for item in proposal.places}
    all_entities = people | objects | information | {workflow.request_id}
    declared_entity_ids = [
        *(item.entity_id for item in proposal.people),
        *(item.entity_id for item in proposal.objects),
        *(item.information_id for item in proposal.information),
        workflow.request_id,
    ]
    if len(declared_entity_ids) != len(set(declared_entity_ids)):
        raise AuthoringCompilationError(
            "people, objects, information, and request must have distinct entity ids"
        )
    reserved = set(declared_entity_ids) & _RESOURCE_REQUEST_RUNTIME_IDS
    if reserved:
        raise AuthoringCompilationError(
            f"draft entity ids collide with resource_request_v1 runtime ids: {sorted(reserved)!r}"
        )
    for label, value, allowed in (
        ("requester_id", workflow.requester_id, people),
        ("reviewer_id", workflow.reviewer_id, people),
        ("resource_id", workflow.resource_id, objects),
        ("policy_information_id", workflow.policy_information_id, information),
    ):
        if value not in allowed:
            raise AuthoringCompilationError(f"{label} does not name a declared referent: {value}")
    if workflow.requester_id == workflow.reviewer_id:
        raise AuthoringCompilationError("resource_request_v1 requires distinct requester and reviewer")
    if workflow.requester_id not in workflow.eligible_requester_ids:
        raise AuthoringCompilationError("eligible_requester_ids must include the requester")
    unknown_eligible = set(workflow.eligible_requester_ids) - people
    if unknown_eligible:
        raise AuthoringCompilationError(f"eligible_requester_ids has unknown people: {sorted(unknown_eligible)!r}")
    unknown_placements = set(proposal.placements) - (people | objects)
    if unknown_placements:
        raise AuthoringCompilationError(f"placements has unknown entities: {sorted(unknown_placements)!r}")
    required_placements = {workflow.requester_id, workflow.reviewer_id, workflow.resource_id}
    absent = required_placements - set(proposal.placements)
    if absent:
        raise AuthoringCompilationError(f"placements missing required entities: {sorted(absent)!r}")
    unknown_places = set(proposal.placements.values()) - places
    if unknown_places:
        raise AuthoringCompilationError(f"placements names unknown places: {sorted(unknown_places)!r}")
    for link in proposal.spatial_links:
        if {link.endpoint_a_place_id, link.endpoint_b_place_id} - places:
            raise AuthoringCompilationError(f"spatial link {link.spatial_link_id} names an unknown place")
    timing = {item.name: item.minutes for item in proposal.timing_assumptions}
    expected_timing = {
        "request_delivery": workflow.request_delivery_minutes,
        "decision_delivery": workflow.decision_delivery_minutes,
        "result_delivery": workflow.result_delivery_minutes,
    }
    for name, minutes in expected_timing.items():
        if timing.get(name) != minutes:
            raise AuthoringCompilationError(
                f"timing assumption {name!r} must equal the workflow duration {minutes}"
            )
    for boundary in proposal.analytical_boundaries:
        unknown_members = set(boundary.member_refs) - all_entities
        if unknown_members:
            raise AuthoringCompilationError(
                f"boundary {boundary.boundary_id} has unknown members: {sorted(unknown_members)!r}"
            )


def _proposal_digest(proposal: ScenarioDraftProposal) -> str:
    encoded = json.dumps(
        proposal.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()
