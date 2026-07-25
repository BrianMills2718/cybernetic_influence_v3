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

from cybernetic_influence.active_runtime import ActiveRuntimeResult
from cybernetic_influence.authoring.models import ScenarioDraftProposal
from cybernetic_influence.authoring.resource_request import (
    ResourceRequestFixture,
    resource_request_fixture,
    resource_request_scripted_bindings,
    run_resource_request,
)
from cybernetic_influence.causal_core.engine import ExactMechanismBinding
from cybernetic_influence.causal_core.models import CausalScenario


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


@dataclass(frozen=True)
class CompiledScenario:
    """The executable result of one reviewed template-bound draft."""

    proposal: ScenarioDraftProposal
    proposal_digest: str
    fixture: ResourceRequestFixture

    @property
    def scenario(self) -> CausalScenario:
        return self.fixture.scenario

    @property
    def exact_bindings(self) -> dict[str, ExactMechanismBinding]:
        return self.fixture.exact_bindings

    def run_scripted(self, *, run_id: str) -> ActiveRuntimeResult:
        return run_resource_request(
            self.fixture,
            resource_request_scripted_bindings(self.fixture),
            run_id=run_id,
        )


def compile_resource_request(proposal: ScenarioDraftProposal) -> CompiledScenario:
    """Compile only ``resource_request_v1`` after semantic validation."""

    selected = ScenarioDraftProposal.model_validate(proposal.model_dump(mode="json"))
    _validate_resource_request(selected)
    return CompiledScenario(
        proposal=selected,
        proposal_digest=_proposal_digest(selected),
        fixture=resource_request_fixture(selected),
    )


def _validate_resource_request(proposal: ScenarioDraftProposal) -> None:
    people = {item.entity_id for item in proposal.people}
    objects = {item.entity_id for item in proposal.objects}
    information = {item.information_id for item in proposal.information}
    places = {item.place_id for item in proposal.places}
    all_entities = people | objects | information | {proposal.workflow.request_id}
    workflow = proposal.workflow
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
