"""Shared, theory-neutral projection and connectivity audit for authored worlds."""

from __future__ import annotations

from collections import deque

from .authoring_models import GeneralSimulationProposalV1
from .contracts_v2 import ScenarioSpecV2


def project_configuration_graph(
    proposal: GeneralSimulationProposalV1 | ScenarioSpecV2,
) -> dict[str, object]:
    nodes: dict[str, dict[str, object]] = {}
    edges: list[dict[str, object]] = []

    def node(node_id: str, node_type: str, label: str, **extra: object) -> None:
        nodes.setdefault(
            node_id,
            {"id": node_id, "type": node_type, "kind": node_type, "label": label, **extra},
        )

    def edge(source: str, target: str, kind: str, label: str, edge_id: str) -> None:
        edges.append(
            {
                "id": edge_id,
                "type": kind,
                "kind": kind,
                "source": source,
                "target": target,
                "label": label,
                "directed": True,
            }
        )

    for person in proposal.people:
        node(person.entity_id, "person", person.label, description=person.position)
    for record in proposal.world_records:
        node(record.record_id, "record", record.label, semantic_kind=record.kind)
        for actor_id in record.visible_to_actor_ids:
            edge(record.record_id, actor_id, "authorized_access", "may observe", f"access:{record.record_id}:{actor_id}")
    for system in proposal.active_systems:
        node(system.system_id, "active_system", system.system_id.replace("_", " ").title(), description=system.behavior_summary)
        for ref in system.subject_refs:
            edge(ref, system.system_id, "causal_responsibility", "modeled by", f"system:{system.system_id}:{ref}")

    if proposal.spatial_extension:
        for place in proposal.spatial_extension.places:
            node(place.place_id, "place", place.label)
        for placement in proposal.spatial_extension.placements:
            edge(placement.record_id, placement.place_id, "placement", "located at", f"placement:{placement.record_id}")
        for link in proposal.spatial_extension.links:
            node(link.link_id, "route", link.link_id.replace("_", " ").title())
            edge(link.origin_place_id, link.link_id, "route_origin", "origin", f"route-origin:{link.link_id}")
            edge(link.link_id, link.destination_place_id, "route_destination", "destination", f"route-destination:{link.link_id}")

    if proposal.information_extension:
        known = set(nodes)
        for representation in proposal.information_extension.representations:
            node(representation.representation_id, "representation", representation.representation_id.replace("_", " ").title(), content=representation.content)
            source_id = representation.apparent_source
            if source_id not in known:
                node(source_id, "external_source", source_id.replace("_", " ").title())
            edge(source_id, representation.representation_id, "apparent_source", "appears to originate from", f"source:{representation.representation_id}")
            for actor_id in representation.recipient_ids:
                edge(representation.representation_id, actor_id, "information_delivery", "delivered to", f"delivery:{representation.representation_id}:{actor_id}")

    if proposal.resource_extension:
        for stock in proposal.resource_extension.stocks:
            node(stock.resource_id, "resource", stock.resource_id.replace("_", " ").title(), quantity=stock.quantity)
            edge(stock.resource_id, stock.custodian_id, "custody", "held by", f"custody:{stock.resource_id}")

    if proposal.relationship_extension:
        for relationship in proposal.relationship_extension.relationships:
            node(relationship.relationship_id, "relationship", relationship.relationship_id.replace("_", " ").title(), description=relationship.description)
            for ref in relationship.participant_refs:
                edge(ref, relationship.relationship_id, "relationship_participant", "participates in", f"relationship:{relationship.relationship_id}:{ref}")

    for rule in proposal.sensing_rules:
        node(rule.rule_id, "mechanism", rule.rule_id.replace("_", " ").title(), mechanism_kind="sensing")
        edge(rule.subject_ref, rule.rule_id, "mechanism_read", "reads hidden state", f"sense-read:{rule.rule_id}")
        edge(rule.rule_id, rule.output_record_id, "mechanism_write", "writes finding", f"sense-write:{rule.rule_id}")
        for actor_id in rule.observer_ids:
            edge(actor_id, rule.rule_id, "capability", "may attempt", f"sense-actor:{rule.rule_id}:{actor_id}")
        for actor_id in rule.result_recipient_ids:
            edge(rule.rule_id, actor_id, "result_recipient", "may inform", f"sense-result:{rule.rule_id}:{actor_id}")

    for transformation in proposal.resource_transformations:
        mechanism_id = transformation.transformation_id
        node(mechanism_id, "mechanism", mechanism_id.replace("_", " ").title(), mechanism_kind="resource_transformation")
        for actor_id in transformation.operator_ids:
            edge(actor_id, mechanism_id, "capability", "may attempt", f"transform-actor:{mechanism_id}:{actor_id}")
        for requirement in transformation.input_resource_quantities:
            edge(requirement.resource_id, mechanism_id, "resource_input", "consumed by", f"transform-input:{mechanism_id}:{requirement.resource_id}")
        edge(mechanism_id, transformation.output_resource_id, "resource_output", "produces", f"transform-output:{mechanism_id}")
        edge(mechanism_id, transformation.public_inventory_record_id, "mechanism_write", "updates inventory", f"transform-record:{mechanism_id}")

    for transport in proposal.resource_transports:
        mechanism_id = transport.transport_id
        node(mechanism_id, "mechanism", mechanism_id.replace("_", " ").title(), mechanism_kind="resource_transport")
        for actor_id in transport.operator_ids:
            edge(actor_id, mechanism_id, "capability", "may attempt", f"transport-actor:{mechanism_id}:{actor_id}")
        edge(transport.source_resource_id, mechanism_id, "resource_input", "moved by", f"transport-source:{mechanism_id}")
        edge(mechanism_id, transport.destination_resource_id, "resource_output", "moves into", f"transport-destination:{mechanism_id}")
        edge(mechanism_id, transport.arrival_record_id, "mechanism_write", "records arrival", f"transport-arrival:{mechanism_id}")
        for route_id in transport.allowed_route_ids:
            edge(route_id, mechanism_id, "permitted_route", "may carry", f"transport-route:{mechanism_id}:{route_id}")

    adjacency = {node_id: set() for node_id in nodes}
    degree = {node_id: 0 for node_id in nodes}
    for item in edges:
        source, target = str(item["source"]), str(item["target"])
        if source in adjacency and target in adjacency:
            adjacency[source].add(target)
            adjacency[target].add(source)
            degree[source] += 1
            degree[target] += 1
    isolated = sorted(
        node_id
        for node_id, count in degree.items()
        if count == 0 and nodes[node_id]["type"] != "external_source"
    )
    components: list[list[str]] = []
    remaining = {node_id for node_id in nodes if nodes[node_id]["type"] != "external_source"}
    while remaining:
        root = min(remaining)
        queue = deque([root])
        component: set[str] = set()
        while queue:
            current = queue.popleft()
            if current in component:
                continue
            component.add(current)
            queue.extend(adjacency[current] - component)
        remaining -= component
        components.append(sorted(component))
    diagnostics = [
        {
            "severity": "error",
            "code": "isolated_configured_node",
            "node_id": node_id,
            "message": f"{nodes[node_id]['label']} has no configured path for information, action, resources, space, or causal execution.",
        }
        for node_id in isolated
    ]
    if len(components) > 1 and not isolated:
        diagnostics.append(
            {
                "severity": "warning",
                "code": "disconnected_configured_components",
                "message": f"The configured world contains {len(components)} disconnected components; verify that this separation is intentional.",
                "components": components,
            }
        )
    return {
        "contract": "general-configuration-graph.v1",
        "nodes": list(nodes.values()),
        "edges": edges,
        "diagnostics": diagnostics,
        "isolated_node_ids": isolated,
        "component_count": len(components),
        "components": components,
    }
