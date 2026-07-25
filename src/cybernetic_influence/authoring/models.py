"""The constrained draft language for the first authored scenario template.

These records are intentionally human-reviewable.  They are not a general
mechanism language: ``resource_request_v1`` is the sole executable template in
this slice and the compiler owns all ports, carriers, exact mechanisms, and
runtime bindings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class _StrictModel(BaseModel):
    model_config = _FORBID


class PersonDraft(_StrictModel):
    entity_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    position: str = Field(min_length=1)
    disposition: str = Field(min_length=1)
    memories: list[str] = Field(min_length=1)


class ObjectDraft(_StrictModel):
    entity_id: str = Field(pattern=_ID_PATTERN)
    entity_kind: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class InformationDraft(_StrictModel):
    information_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    content: str = Field(min_length=1)


class PlaceDraft(_StrictModel):
    place_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)


class SpatialLinkDraft(_StrictModel):
    spatial_link_id: str = Field(pattern=_ID_PATTERN)
    endpoint_a_place_id: str = Field(pattern=_ID_PATTERN)
    endpoint_b_place_id: str = Field(pattern=_ID_PATTERN)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def distinct_endpoints(self) -> "SpatialLinkDraft":
        if self.endpoint_a_place_id == self.endpoint_b_place_id:
            raise ValueError("spatial link endpoints must be distinct")
        return self


class TimingAssumption(_StrictModel):
    name: str = Field(pattern=_ID_PATTERN)
    minutes: int = Field(ge=1)
    basis: str = Field(min_length=1)


class AnalyticalBoundaryDraft(_StrictModel):
    boundary_id: str = Field(pattern=_ID_PATTERN)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    member_refs: list[str] = Field(min_length=1)


class ResourceRequestWorkflowDraft(_StrictModel):
    template_id: Literal["resource_request_v1"] = "resource_request_v1"
    requester_id: str = Field(pattern=_ID_PATTERN)
    reviewer_id: str = Field(pattern=_ID_PATTERN)
    request_id: str = Field(pattern=_ID_PATTERN)
    resource_id: str = Field(pattern=_ID_PATTERN)
    policy_information_id: str = Field(pattern=_ID_PATTERN)
    eligible_requester_ids: list[str] = Field(min_length=1)
    resource_available: bool
    request_delivery_minutes: int = Field(ge=1)
    decision_delivery_minutes: int = Field(ge=1)
    result_delivery_minutes: int = Field(ge=1)


class ScenarioDraftProposal(_StrictModel):
    """One proposal that can be semantically validated before compilation."""

    proposal_version: Literal[1] = 1
    scenario_id: str = Field(pattern=_ID_PATTERN)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    people: list[PersonDraft] = Field(min_length=2)
    objects: list[ObjectDraft] = Field(min_length=1)
    information: list[InformationDraft] = Field(min_length=1)
    places: list[PlaceDraft] = Field(min_length=2)
    spatial_links: list[SpatialLinkDraft] = Field(min_length=1)
    placements: dict[str, str] = Field(min_length=2)
    timing_assumptions: list[TimingAssumption] = Field(min_length=1)
    workflow: ResourceRequestWorkflowDraft
    analytical_boundaries: list[AnalyticalBoundaryDraft] = Field(min_length=1)
    fidelity_questions: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_declared_ids(self) -> "ScenarioDraftProposal":
        for label, values in (
            ("people", [item.entity_id for item in self.people]),
            ("objects", [item.entity_id for item in self.objects]),
            ("information", [item.information_id for item in self.information]),
            ("places", [item.place_id for item in self.places]),
            ("spatial links", [item.spatial_link_id for item in self.spatial_links]),
            ("timing assumptions", [item.name for item in self.timing_assumptions]),
            ("analytical boundaries", [item.boundary_id for item in self.analytical_boundaries]),
        ):
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {label}")
        return self
