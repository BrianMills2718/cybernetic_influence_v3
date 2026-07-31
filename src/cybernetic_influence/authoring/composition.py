"""Reviewed component inventory and retained composition receipts.

The registry deliberately describes only capabilities already executable through
the causal runtime.  It is not a plugin loader and never accepts user-supplied
code.  Slice 25 uses it as the observable seam before authoring is allowed to
compose reviewed component families directly.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from cybernetic_influence.causal_core.models import CausalScenario, CausalState


_FORBID = ConfigDict(extra="forbid", strict=True)
_ID_PATTERN = r"^[a-z][a-z0-9_]*$"


class _StrictModel(BaseModel):
    model_config = _FORBID


class RegisteredComponentV1(_StrictModel):
    """One reviewed component family that the compiler may report or select."""

    component_kind: str = Field(pattern=_ID_PATTERN)
    version: Literal[1] = 1
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    runtime_surface: Literal[
        "participant", "object", "information", "place", "connection", "mechanism", "boundary"
    ]


class ResolvedComponentV1(_StrictModel):
    """One concrete reviewed component resolved by a compiled scenario."""

    component_id: str = Field(pattern=_ID_PATTERN)
    component_kind: str = Field(pattern=_ID_PATTERN)
    version: Literal[1] = 1
    runtime_refs: list[str] = Field(min_length=1)
    description: str = Field(min_length=1)


class CompositionDiagnosticV1(_StrictModel):
    """A deterministic compiler decision retained beside the composition."""

    severity: Literal["info", "error"]
    code: str = Field(pattern=_ID_PATTERN)
    path: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ComponentSelectionV1(_StrictModel):
    """A future authoring selection of one reviewed component version.

    This intentionally has no implementation, prompt, or executable field.
    The compiler resolves it only through :func:`reviewed_component_registry`.
    """

    component_id: str = Field(pattern=_ID_PATTERN)
    component_kind: str = Field(pattern=_ID_PATTERN)
    version: int = Field(ge=1)


class CompositionReceiptV1(_StrictModel):
    """Inspectable record of reviewed components resolved into one runtime graph."""

    schema_version: Literal[1] = 1
    registry_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    scenario_id: str = Field(pattern=_ID_PATTERN)
    workflow_template_id: str = Field(pattern=_ID_PATTERN)
    selected_components: list[ResolvedComponentV1] = Field(min_length=1)
    diagnostics: list[CompositionDiagnosticV1] = Field(min_length=1)

    @property
    def digest(self) -> str:
        """Stable receipt identity excluding no runtime-derived hidden state."""

        payload = self.model_dump(mode="json")
        return sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


_REGISTRY: tuple[RegisteredComponentV1, ...] = (
    RegisteredComponentV1(
        component_kind="person_participant",
        label="Person participant",
        description="A concrete person with retained state and owned interfaces.",
        runtime_surface="participant",
    ),
    RegisteredComponentV1(
        component_kind="stateful_object",
        label="Stateful object",
        description="A concrete non-person entity retaining world state.",
        runtime_surface="object",
    ),
    RegisteredComponentV1(
        component_kind="information_carrier",
        label="Information carrier",
        description="A carrier retaining an encoded representation at a revision.",
        runtime_surface="information",
    ),
    RegisteredComponentV1(
        component_kind="place",
        label="Place",
        description="An authored spatial locus; placement does not grant capability.",
        runtime_surface="place",
    ),
    RegisteredComponentV1(
        component_kind="directed_connection",
        label="Directed connection",
        description="A configured compatible route between owned interfaces.",
        runtime_surface="connection",
    ),
    RegisteredComponentV1(
        component_kind="exact_mechanism",
        label="Exact mechanism",
        description="A reviewed deterministic transition with explicit read/write authority.",
        runtime_surface="mechanism",
    ),
    RegisteredComponentV1(
        component_kind="analytical_boundary",
        label="Analytical boundary",
        description="An execution-inert grouping used only for analysis and inspection.",
        runtime_surface="boundary",
    ),
)


def reviewed_component_registry() -> tuple[RegisteredComponentV1, ...]:
    """Return the fixed reviewed registry in deterministic presentation order."""

    return _REGISTRY


def reviewed_component_registry_digest() -> str:
    """Identify the registry revision used to compile a receipt."""

    payload = [item.model_dump(mode="json") for item in reviewed_component_registry()]
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def resolve_component_selections(
    selections: list[ComponentSelectionV1],
) -> tuple[RegisteredComponentV1, ...]:
    """Resolve only known reviewed component versions; fail before execution."""

    component_ids = [item.component_id for item in selections]
    if len(component_ids) != len(set(component_ids)):
        raise ValueError("composition has duplicate component_id values")
    registry: dict[tuple[str, int], RegisteredComponentV1] = {
        (item.component_kind, item.version): item
        for item in reviewed_component_registry()
    }
    resolved: list[RegisteredComponentV1] = []
    for selection in selections:
        component = registry.get((selection.component_kind, selection.version))
        if component is None:
            raise ValueError(
                "composition selects unknown reviewed component "
                f"{selection.component_kind!r} version {selection.version}"
            )
        resolved.append(component)
    return tuple(resolved)


def composition_receipt(
    scenario: CausalScenario, *, workflow_template_id: str
) -> CompositionReceiptV1:
    """Resolve every configured runtime surface through the reviewed registry."""

    state = scenario.initial_state
    components = _resolved_components(state, scenario)
    return CompositionReceiptV1(
        registry_digest=reviewed_component_registry_digest(),
        scenario_id=scenario.scenario_id,
        workflow_template_id=workflow_template_id,
        selected_components=components,
        diagnostics=[
            CompositionDiagnosticV1(
                severity="info",
                code="runtime_surfaces_resolved",
                path="scenario.initial_state",
                message=(
                    f"Resolved {len(components)} reviewed components into the existing "
                    "causal runtime; no executable implementation was supplied by authoring."
                ),
            )
        ],
    )


def _resolved_components(
    state: CausalState, scenario: CausalScenario
) -> list[ResolvedComponentV1]:
    components: list[ResolvedComponentV1] = []
    for entity in state.entities.values():
        kind = "person_participant" if entity.entity_kind == "person" else "stateful_object"
        components.append(
            ResolvedComponentV1(
                component_id=f"{kind}_{entity.entity_id}",
                component_kind=kind,
                runtime_refs=[entity.entity_id],
                description=entity.description,
            )
        )
    for carrier in state.carriers.values():
        components.append(
            ResolvedComponentV1(
                component_id=f"information_carrier_{carrier.carrier_id}",
                component_kind="information_carrier",
                runtime_refs=[carrier.carrier_id, carrier.owner_ref],
                description=f"{carrier.medium} at {carrier.locator}.",
            )
        )
    for place in state.places.values():
        components.append(
            ResolvedComponentV1(
                component_id=f"place_{place.place_id}",
                component_kind="place",
                runtime_refs=[place.place_id],
                description=place.description,
            )
        )
    for connection in state.connections.values():
        components.append(
            ResolvedComponentV1(
                component_id=f"directed_connection_{connection.connection_id}",
                component_kind="directed_connection",
                runtime_refs=[
                    connection.connection_id,
                    connection.source_port_id,
                    connection.target_port_id,
                ],
                description=connection.description,
            )
        )
    for mechanism in state.mechanisms.values():
        components.append(
            ResolvedComponentV1(
                component_id=f"exact_mechanism_{mechanism.mechanism_id}",
                component_kind="exact_mechanism",
                runtime_refs=[mechanism.mechanism_id, mechanism.implementation_id],
                description=mechanism.description,
            )
        )
    for boundary in scenario.analytical_boundaries:
        components.append(
            ResolvedComponentV1(
                component_id=f"analytical_boundary_{boundary.boundary_id}",
                component_kind="analytical_boundary",
                runtime_refs=[boundary.boundary_id, *boundary.member_refs],
                description=boundary.description,
            )
        )
    return sorted(components, key=lambda item: item.component_id)
