"""First mixed reviewed-component composition over the existing runtime."""

from __future__ import annotations

from cybernetic_influence.authoring.composition import (
    ComponentSelectionV1,
    resolve_component_selections,
)
from cybernetic_influence.authoring.information_campaign import (
    InformationCampaignFixture,
    information_campaign_fixture,
)
from cybernetic_influence.authoring.models import (
    ComponentCompositionWorkflowDraft,
    ComponentCompositionConfigurationReview,
    ScenarioDraftProposal,
)


def component_composition_fixture(
    proposal: ScenarioDraftProposal,
) -> InformationCampaignFixture:
    """Compile reviewed delivery, recording, and route components into one fixture.

    The mapping deliberately reuses the existing reviewed exact delivery and
    assessment-recording mechanisms.  The author supplies typed component
    selections and bindings; this adapter supplies no user-authored behavior.
    """

    workflow = proposal.workflow
    if not isinstance(workflow, ComponentCompositionWorkflowDraft):
        raise ValueError("component composition fixture requires its matching workflow")
    _validate(proposal, workflow)
    projected = proposal.model_dump(mode="json")
    projected["workflow"] = {
        "template_id": "information_campaign_v1",
        "source_id": workflow.source_id,
        "recipient_id": workflow.recipient_id,
        "campaign_id": workflow.record_id,
        "claim_information_id": workflow.information_id,
        "channel_object_id": workflow.channel_object_id,
        "publication_enabled": workflow.delivery_enabled,
        "publication_delivery_minutes": workflow.delivery_minutes,
        "assessment_recording_minutes": workflow.recording_minutes,
    }
    return information_campaign_fixture(ScenarioDraftProposal.model_validate(projected))


def _validate(
    proposal: ScenarioDraftProposal, workflow: ComponentCompositionWorkflowDraft
) -> None:
    resolve_component_selections(workflow.components)
    people = {item.entity_id for item in proposal.people}
    objects = {item.entity_id for item in proposal.objects}
    information = {item.information_id for item in proposal.information}
    for label, value, allowed in (
        ("source_id", workflow.source_id, people),
        ("recipient_id", workflow.recipient_id, people),
        ("channel_object_id", workflow.channel_object_id, objects),
        ("information_id", workflow.information_id, information),
    ):
        if value not in allowed:
            raise ValueError(f"{label} does not name a declared composition referent")
    if workflow.source_id == workflow.recipient_id:
        raise ValueError("composition requires distinct source and recipient")
    expected = {
        (workflow.source_id, "person_participant"),
        (workflow.recipient_id, "person_participant"),
        (workflow.channel_object_id, "stateful_object"),
        (workflow.information_id, "information_carrier"),
        ("publication_route", "directed_connection"),
        ("assessment_route", "directed_connection"),
        ("publication_delivery", "exact_mechanism"),
        ("assessment_recording", "exact_mechanism"),
    }
    selected = {(item.component_id, item.component_kind) for item in workflow.components}
    if selected != expected:
        raise ValueError(
            "composition must select exactly the reviewed source, recipient, channel, "
            "information, two routes, and two exact mechanisms"
        )


def component_configuration_from_proposal(
    proposal: ScenarioDraftProposal,
) -> ComponentCompositionConfigurationReview:
    """Project only semantic fields that a human may revise directly."""

    workflow = proposal.workflow
    if not isinstance(workflow, ComponentCompositionWorkflowDraft):
        raise ValueError("proposal is not a component composition")
    return ComponentCompositionConfigurationReview(
        title=proposal.title,
        description=proposal.description,
        source_id=workflow.source_id,
        recipient_id=workflow.recipient_id,
        information_id=workflow.information_id,
        channel_object_id=workflow.channel_object_id,
        delivery_enabled=workflow.delivery_enabled,
        delivery_minutes=workflow.delivery_minutes,
        recording_minutes=workflow.recording_minutes,
    )


def apply_component_configuration(
    proposal: ScenarioDraftProposal,
    configuration: ComponentCompositionConfigurationReview,
) -> ScenarioDraftProposal:
    """Apply editable semantics while rebuilding compiler-owned selections."""

    workflow = proposal.workflow
    if not isinstance(workflow, ComponentCompositionWorkflowDraft):
        raise ValueError("proposal is not a component composition")
    payload = proposal.model_dump(mode="json")
    payload["title"] = configuration.title
    payload["description"] = configuration.description
    payload["workflow"] = {
        **workflow.model_dump(mode="json"),
        "components": _reviewed_components(configuration),
        "source_id": configuration.source_id,
        "recipient_id": configuration.recipient_id,
        "information_id": configuration.information_id,
        "channel_object_id": configuration.channel_object_id,
        "delivery_enabled": configuration.delivery_enabled,
        "delivery_minutes": configuration.delivery_minutes,
        "recording_minutes": configuration.recording_minutes,
    }
    return ScenarioDraftProposal.model_validate(payload)


def _reviewed_components(
    configuration: ComponentCompositionConfigurationReview,
) -> list[dict[str, object]]:
    """Keep the initial composition's executable seams compiler-owned."""

    return [
        ComponentSelectionV1(
            component_id=configuration.source_id,
            component_kind="person_participant",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id=configuration.recipient_id,
            component_kind="person_participant",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id=configuration.channel_object_id,
            component_kind="stateful_object",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id=configuration.information_id,
            component_kind="information_carrier",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id="publication_route",
            component_kind="directed_connection",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id="assessment_route",
            component_kind="directed_connection",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id="publication_delivery",
            component_kind="exact_mechanism",
        ).model_dump(mode="json"),
        ComponentSelectionV1(
            component_id="assessment_recording",
            component_kind="exact_mechanism",
        ).model_dump(mode="json"),
    ]
