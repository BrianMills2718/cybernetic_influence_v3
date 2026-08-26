import { useEffect, useMemo, useState } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import dagre from '@dagrejs/dagre'
import ReactFlow, {
  Background,
  BackgroundVariant,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  getBezierPath,
  MarkerType,
  MiniMap,
  ReactFlowProvider,
  type Edge,
  type EdgeProps,
  type Node,
  useEdgesState,
  useNodesInitialized,
  useNodesState,
  useReactFlow,
} from 'reactflow'
import 'reactflow/dist/style.css'
import './styles.css'

interface AnalystNode {
  id: string
  kind: string
  label: string
  description: string
  state: unknown
}

interface AnalystEdge {
  id: string
  kind: string
  source: string
  target: string
  enabled: boolean
  description: string
  routeIds: string[]
  substrateEntityIds?: string[]
}

interface GraphDiagnostics {
  contract: 'configured-graph-diagnostics.v1'
  counts: Record<string, number>
  nodeClassification: Record<string, string>
  warnings: Array<{
    code: string
    nodeId: string
    message: string
  }>
}

interface PlaceView {
  id: string
  kind: string
  label: string
  description: string
  parentPlaceId: string | null
}

interface PlacementView {
  entityId: string
  placeId: string
}

interface WorldView {
  places: PlaceView[]
  links: AnalystEdge[]
  placements: PlacementView[]
  unplacedEntityIds: string[]
}

interface BoundaryView {
  id: string
  label: string
  description: string
  executor: false
  memberIds: string[]
  hiddenFacts: number
  hiddenInformation: number
  internalRoutes: number
}

interface EventView {
  event_id: string
  state_revision: number
  focus_ids: string[]
  focus_edges: string[]
  spatial_focus_ids?: string[]
  spatial_link_ids?: string[]
  boundary_ids?: string[]
}

interface TrajectoryNode {
  id: string
  kind: string
  label: string
  logical_time: number
  causal_timestamp?: string | null
  timing?: {
    starts_at: number
    duration: number
    minimum_duration: number
    serialization_delay: number
    source_kind: string
    source_ref: string
  } | null
}

interface TrajectoryEdge {
  id: string
  source: string
  target: string
}

interface TrajectoryView {
  nodes: TrajectoryNode[]
  edges: TrajectoryEdge[]
}

interface CanvasOptions {
  nodes: AnalystNode[]
  edges: AnalystEdge[]
  event: EventView | null
  initialRevision?: number | null
  boundary: BoundaryView | null
  world: WorldView | null
  trajectory: TrajectoryView | null
  graphDiagnostics?: GraphDiagnostics | null
  viewMode: 'world' | 'causal' | 'trajectory'
  collapsedBoundaryId: string | null
  selectedNodeId: string | null
  selectedEdgeId: string | null
  title?: string
  subtitle?: string
  showLegend?: boolean
  showMiniMap?: boolean
  legendNodes?: AnalystNode[]
  legendEdges?: AnalystEdge[]
  activity?: {
    participantIds: string[]
    cue: CanvasAnimationCue | null
  } | null
  onSelectNode: (nodeId: string) => void
  onSelectEdge: (edge: AnalystEdge) => void
}

interface CanvasNodeData {
  raw: AnalystNode
  active: boolean
  connectivityClass?: string
  aggregateMode?: 'expanded' | 'collapsed'
  memberCount?: number
  placeMode?: 'root' | 'place'
}

interface CanvasEdgeData {
  raw: AnalystEdge
  cue?: CanvasAnimationCue | null
}

interface CanvasAnimationCue {
  kind: 'action_attempt' | 'information_transfer' | 'mechanism_accepted' | 'mechanism_denied' | 'state_changed' | 'observation_delivered' | 'effect_dissipated'
  label: string
  source_id: string | null
  target_id: string | null
  edge_ids: string[]
}

const NODE_WIDTH = 194
const NODE_HEIGHT = 92
const WORLD_NODE_WIDTH = 152
const WORLD_NODE_HEIGHT = 78
const roots = new WeakMap<Element, Root>()

function relationLabel(kind: string): string {
  return {
    connection: 'route',
    issued_information: 'issued',
    delivered_to: 'delivered to',
    contributed_to_decision: 'contributed',
    mechanism_binding: 'input',
    mechanism_read: 'reads',
    mechanism_write: 'updates',
    mechanism_substrate: 'uses',
    observation_target: 'notifies',
    information_location: 'carried',
    information_lineage: 'derived',
    spatial_link: 'adjacent via',
    apparent_source: 'appears from',
    authorized_access: 'may inspect',
    capability: 'may attempt',
    causal_responsibility: 'governs',
    custody: 'held by',
    information_delivery: 'may be delivered to',
    placement: 'located at',
    relationship_participant: 'participates in',
    resource_input: 'input to',
    resource_output: 'produces',
    result_recipient: 'reports result to',
    route_origin: 'starts at',
    route_destination: 'ends at',
    permitted_route: 'available route for',
    scheduled_after: 'scheduled before',
  }[kind] ?? kind.replaceAll('_', ' ')
}

function relationColor(kind: string): string {
  return {
    connection: '#5aa9e6',
    issued_information: '#f2a65a',
    delivered_to: '#ef79b7',
    contributed_to_decision: '#79c7ff',
    mechanism_binding: '#e8a84d',
    mechanism_read: '#97a9bd',
    mechanism_write: '#d7b46a',
    mechanism_substrate: '#70b7aa',
    observation_target: '#88aee8',
    information_location: '#ef79b7',
    information_lineage: '#c36fa1',
    spatial_link: '#83d6c0',
    apparent_source: '#f2a65a',
    authorized_access: '#97a9bd',
    capability: '#58a6ff',
    causal_responsibility: '#e8a84d',
    custody: '#81c784',
    information_delivery: '#ef79b7',
    placement: '#83d6c0',
    relationship_participant: '#b891ff',
    resource_input: '#81c784',
    resource_output: '#57b49d',
    result_recipient: '#88aee8',
    route_origin: '#5aa9e6',
    route_destination: '#5aa9e6',
    permitted_route: '#70b7aa',
    scheduled_after: '#f6c667',
  }[kind] ?? '#71849a'
}

function nodeColor(node: Node<CanvasNodeData>): string {
  return {
    person: '#58a6ff',
    source: '#f2a65a',
    information_source: '#f2a65a',
    thing: '#57b49d',
    information: '#ef79b7',
    information_document: '#c36fa1',
    representation: '#ef79b7',
    record: '#57b49d',
    resource: '#81c784',
    route: '#5aa9e6',
    relationship: '#b891ff',
    active_system: '#e8a84d',
    external_source: '#f2a65a',
    mechanism: '#e8a84d',
    process: '#f6c667',
    decision_record: '#b891ff',
    analytical_boundary: '#b891ff',
    place: '#83d6c0',
    run_started: '#8fa0b5',
    action_attempted: '#58a6ff',
    effect_emitted: '#c08cff',
    effect_routed: '#79c7ff',
    mechanism_executed: '#e8a84d',
    state_committed: '#81c784',
    observation_delivered: '#ef79b7',
    run_completed: '#57b49d',
  }[node.data.raw.kind] ?? '#57b49d'
}

function nodeGlyph(kind: string): string {
  return {
    person: '●',
    source: '◆',
    information_source: '◆',
    thing: '◆',
    information: '▤',
    information_document: '▧',
    representation: '▤',
    record: '▦',
    resource: '■',
    route: '⇢',
    relationship: '⬚',
    active_system: '⚙',
    external_source: '◆',
    place: '⌂',
    mechanism: '⚙',
    process: '◷',
    decision_record: '▦',
    analytical_boundary: '⬚',
    run_started: '▶',
    action_attempted: '●',
    effect_emitted: '◇',
    effect_routed: '→',
    mechanism_executed: '⚙',
    state_committed: '✓',
    observation_delivered: '▤',
    run_completed: '■',
  }[kind] ?? '◇'
}

function nodeTypeLabel(kind: string): string {
  return {
    person: 'person',
    source: 'source',
    information_source: 'information source',
    thing: 'thing / object',
    information: 'representation',
    information_document: 'information document',
    representation: 'information representation',
    record: 'canonical state record',
    resource: 'resource',
    route: 'directed route',
    relationship: 'relationship record',
    active_system: 'coarse transition system',
    external_source: 'external information source',
    place: 'place',
    mechanism: 'transition mechanism',
    process: 'scheduled process',
    decision_record: 'decision state record',
    analytical_boundary: 'group / boundary',
    run_started: 'run started event',
    action_attempted: 'action attempted event',
    effect_emitted: 'effect emitted event',
    effect_routed: 'effect routed event',
    mechanism_executed: 'mechanism executed event',
    state_committed: 'state committed event',
    observation_delivered: 'observation delivered event',
    run_completed: 'run completed event',
  }[kind] ?? kind.replaceAll('_', ' ')
}

function edgeDash(kind: string): string | undefined {
  return {
    spatial_link: '10 5',
    mechanism_binding: '6 4',
    information_lineage: '3 4',
    issued_information: '7 4',
    contributed_to_decision: '2 4',
  }[kind]
}

function toCanvasNode(
  item: AnalystNode,
  active: boolean,
  selected: boolean,
  connectivityClass?: string,
): Node<CanvasNodeData> {
  const collapsed = item.kind === 'analytical_boundary'
  return {
    id: item.id,
    position: { x: 0, y: 0 },
    data: {
      raw: item,
      active,
      connectivityClass,
      aggregateMode: collapsed ? 'collapsed' : undefined,
    },
    className: [
      'cy-flow-node-wrap',
      active ? 'cy-flow-node-wrap--active' : '',
      selected ? 'cy-flow-node-wrap--selected' : '',
      connectivityClass === 'unused' ? 'cy-flow-node-wrap--unused' : '',
    ].filter(Boolean).join(' '),
    style: {
      width: collapsed ? 238 : NODE_WIDTH,
      height: collapsed ? 108 : NODE_HEIGHT,
      border: 'none',
      background: 'transparent',
      padding: 0,
    },
  }
}

function toCanvasEdge(
  item: AnalystEdge,
  event: EventView | null,
  selected: boolean,
  activity?: CanvasOptions['activity'],
): Edge<CanvasEdgeData> {
  const focusedRoute = item.routeIds.some((id) => event?.focus_edges.includes(id))
  const focusedSpatialLink = item.kind === 'spatial_link'
    && Boolean(event?.spatial_link_ids?.includes(item.id))
  const focusedEndpoints = Boolean(
    (
      event?.focus_ids.includes(item.source)
      && event.focus_ids.includes(item.target)
    ) || (
      event?.spatial_focus_ids?.includes(item.source)
      && event.spatial_focus_ids.includes(item.target)
    ),
  )
  // An endpoint match is not enough: token travel must name this retained,
  // resolved graph edge explicitly rather than infer a path from two nodes.
  const liveCue = Boolean(activity?.cue?.edge_ids.includes(item.id))
  const cue = liveCue ? activity?.cue ?? null : null
  const active = focusedRoute || focusedSpatialLink || focusedEndpoints || liveCue
  const color = active ? '#ffffff' : relationColor(item.kind)
  const supportingRelationship = [
    'mechanism_read',
    'mechanism_write',
    'mechanism_substrate',
    'observation_target',
  ].includes(item.kind)
  return {
    id: item.id,
    source: item.source,
    target: item.target,
    label: supportingRelationship && !active && !selected
      ? undefined
      : item.kind === 'spatial_link' && item.substrateEntityIds?.length
        ? `${relationLabel(item.kind)} ${item.substrateEntityIds.join(', ')}`
        : relationLabel(item.kind),
    // A moving token is reserved for a retained delivery/effect that names a
    // resolved visible edge. Other event kinds get a truthful pulse only.
    type: cue && ['information_transfer', 'observation_delivered'].includes(cue.kind)
      ? 'liveCue'
      : 'smoothstep',
    animated: active,
    data: { raw: item, cue },
    className: [
      `cy-flow-edge--${item.kind}`,
      active ? 'cy-flow-edge--active' : '',
      selected ? 'cy-flow-edge--selected' : '',
    ].filter(Boolean).join(' '),
    style: {
      stroke: color,
      strokeWidth: active || selected ? 3 : 1.6,
      opacity: item.enabled ? 0.9 : 0.3,
      strokeDasharray: edgeDash(item.kind),
    },
    markerEnd: item.kind === 'spatial_link' ? undefined : {
      type: MarkerType.ArrowClosed,
      color,
      width: 16,
      height: 16,
    },
    labelStyle: {
      fill: active ? '#ffffff' : '#9baabd',
      fontSize: 10,
      fontWeight: 700,
    },
    labelBgStyle: { fill: '#111923', fillOpacity: 0.92 },
    labelBgPadding: [4, 3],
    labelBgBorderRadius: 4,
  }
}

function LiveCueEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps<CanvasEdgeData>) {
  const [reducedMotion, setReducedMotion] = useState(
    () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false,
  )
  useEffect(() => {
    const query = window.matchMedia?.('(prefers-reduced-motion: reduce)')
    if (!query) return undefined
    const change = () => setReducedMotion(query.matches)
    query.addEventListener('change', change)
    return () => query.removeEventListener('change', change)
  }, [])
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })
  const cue = data?.cue
  if (!cue) return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {reducedMotion ? (
        <circle className="cy-live-token" r="6" cx={labelX} cy={labelY} />
      ) : (
        <circle className="cy-live-token" r="6">
          <animateMotion dur="760ms" repeatCount="1" fill="freeze" path={path} />
        </circle>
      )}
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan cy-live-token-label"
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)` }}
          title={cue.label}
        >
          {cue.label}
        </div>
      </EdgeLabelRenderer>
    </>
  )
}

function dagreLayout(
  nodes: Node<CanvasNodeData>[],
  edges: Edge<CanvasEdgeData>[],
): Node<CanvasNodeData>[] {
  const connectedEdges = edges.filter((edge) => edge.source !== edge.target)
  if (nodes.length > 1 && connectedEdges.length === 0) {
    const ordered = [...nodes].sort((left, right) =>
      left.data.raw.label.localeCompare(right.data.raw.label),
    )
    const columns = Math.min(4, Math.ceil(Math.sqrt(ordered.length)))
    return ordered.map((node, index) => {
      const width = Number(node.style?.width ?? NODE_WIDTH)
      const height = Number(node.style?.height ?? NODE_HEIGHT)
      return {
        ...node,
        position: {
          x: 50 + (index % columns) * (width + 80),
          y: 50 + Math.floor(index / columns) * (height + 70),
        },
      }
    })
  }
  const graph = new dagre.graphlib.Graph()
  graph.setDefaultEdgeLabel(() => ({}))
  graph.setGraph({
    rankdir: 'LR',
    nodesep: 80,
    ranksep: 180,
    marginx: 50,
    marginy: 50,
  })
  nodes.forEach((node) => {
    const width = Number(node.style?.width ?? NODE_WIDTH)
    const height = Number(node.style?.height ?? NODE_HEIGHT)
    graph.setNode(node.id, { width, height })
  })
  connectedEdges.forEach((edge) => {
    graph.setEdge(edge.source, edge.target)
  })
  dagre.layout(graph)
  return nodes.map((node) => {
    const point = graph.node(node.id)
    const width = Number(node.style?.width ?? NODE_WIDTH)
    const height = Number(node.style?.height ?? NODE_HEIGHT)
    return {
      ...node,
      position: {
        x: point.x - width / 2,
        y: point.y - height / 2,
      },
    }
  })
}

function trajectoryGridLayout(
  nodes: Node<CanvasNodeData>[],
): Node<CanvasNodeData>[] {
  const ordered = [...nodes].sort((left, right) => {
    const leftTime = Number((left.data.raw.state as TrajectoryNode).logical_time ?? 0)
    const rightTime = Number((right.data.raw.state as TrajectoryNode).logical_time ?? 0)
    return leftTime - rightTime || left.id.localeCompare(right.id)
  })
  const columns = ordered.length <= 6
    ? Math.min(3, Math.max(1, ordered.length))
    : Math.ceil(Math.sqrt(ordered.length))
  const columnGap = 94
  const rowGap = 96
  return ordered.map((node, index) => {
    const row = Math.floor(index / columns)
    const withinRow = index % columns
    const column = row % 2 === 0 ? withinRow : columns - 1 - withinRow
    return {
      ...node,
      position: {
        x: 50 + column * (NODE_WIDTH + columnGap),
        y: 50 + row * (NODE_HEIGHT + rowGap),
      },
    }
  })
}

function expandedBoundaryLayout(
  nodes: Node<CanvasNodeData>[],
  edges: Edge<CanvasEdgeData>[],
  boundary: BoundaryView,
  active: boolean,
  selected: boolean,
): Node<CanvasNodeData>[] {
  const memberIds = new Set(boundary.memberIds)
  const members = nodes
    .filter((node) => memberIds.has(node.id))
    .sort((left, right) => {
      const order: Record<string, number> = {
        person: 0,
        information: 1,
        document: 2,
        mechanism: 3,
      }
      return (order[left.data.raw.kind] ?? 2) - (order[right.data.raw.kind] ?? 2)
        || left.data.raw.label.localeCompare(right.data.raw.label)
    })
  if (!members.length) return dagreLayout(nodes, edges)

  const columns = Math.min(3, Math.max(1, members.length))
  const columnGap = 48
  const rowGap = 38
  const originX = 82
  const originY = 132
  const memberPositions = members.map((node, index) => ({
    ...node,
    position: {
      x: originX + (index % columns) * (NODE_WIDTH + columnGap),
      y: originY + Math.floor(index / columns) * (NODE_HEIGHT + rowGap),
    },
  }))
  const rows = Math.ceil(members.length / columns)
  const hullWidth = originX * 2 + columns * NODE_WIDTH + (columns - 1) * columnGap
  const hullHeight = originY + rows * NODE_HEIGHT + Math.max(0, rows - 1) * rowGap + 58

  const external = nodes.filter((node) => !memberIds.has(node.id))
  const externalIds = new Set(external.map((node) => node.id))
  const externalEdges = edges.filter(
    (edge) => externalIds.has(edge.source) && externalIds.has(edge.target),
  )
  const positionedExternal = dagreLayout(external, externalEdges).map((node) => ({
    ...node,
    position: {
      x: node.position.x + hullWidth + 270,
      y: node.position.y + 55,
    },
  }))
  const hullNode: Node<CanvasNodeData> = {
    id: boundary.id,
    position: { x: 20, y: 20 },
    data: {
      raw: {
        id: boundary.id,
        kind: 'analytical_boundary',
        label: boundary.label,
        description: boundary.description,
        state: {
          executor: false,
          hidden_facts: boundary.hiddenFacts,
          hidden_information: boundary.hiddenInformation,
          internal_routes: boundary.internalRoutes,
        },
      },
      active,
      aggregateMode: 'expanded',
      memberCount: members.length,
    },
    className: [
      'cy-boundary-hull',
      active ? 'cy-boundary-hull--active' : '',
      selected ? 'cy-boundary-hull--selected' : '',
    ].filter(Boolean).join(' '),
    draggable: false,
    selectable: true,
    style: {
      width: hullWidth,
      height: hullHeight,
      zIndex: -1,
    },
  }
  return [hullNode, ...memberPositions, ...positionedExternal]
}

function placeNode(
  place: PlaceView,
  options: {
    position: { x: number; y: number }
    width: number
    height: number
    parentNode?: string
    active: boolean
    selected: boolean
  },
): Node<CanvasNodeData> {
  const { position, width, height, parentNode, active, selected } = options
  return {
    id: place.id,
    position,
    parentNode,
    data: {
      raw: {
        id: place.id,
        kind: 'place',
        label: place.label,
        description: place.description,
        state: {
          place_kind: place.kind,
          parent_place_id: place.parentPlaceId,
        },
      },
      active,
      placeMode: parentNode ? 'place' : 'root',
    },
    className: [
      'cy-place-group',
      parentNode ? 'cy-place-group--leaf' : 'cy-place-group--root',
      active ? 'cy-place-group--active' : '',
      selected ? 'cy-place-group--selected' : '',
    ].filter(Boolean).join(' '),
    draggable: false,
    selectable: true,
    style: {
      width,
      height,
      zIndex: parentNode ? -1 : -2,
    },
  }
}

function nearestCommonPlace(
  placeIds: string[],
  placeById: Map<string, PlaceView>,
): string | null {
  if (!placeIds.length) return null
  const ancestors = (placeId: string): string[] => {
    const result: string[] = []
    let current: string | null = placeId
    const visited = new Set<string>()
    while (current && !visited.has(current)) {
      visited.add(current)
      result.push(current)
      current = placeById.get(current)?.parentPlaceId ?? null
    }
    return result
  }
  const chains = placeIds.map(ancestors)
  return chains[0].find((candidate) =>
    chains.every((chain) => chain.includes(candidate)),
  ) ?? null
}

function buildWorldGraph(options: CanvasOptions): {
  nodes: Node<CanvasNodeData>[]
  edges: Edge<CanvasEdgeData>[]
} {
  const world = options.world
  if (!world) return { nodes: [], edges: [] }
  const eventFocus = new Set(options.event?.spatial_focus_ids ?? [])
  const activeParticipants = new Set(options.activity?.participantIds ?? [])
  const placeById = new Map(world.places.map((place) => [place.id, place]))
  const boundary = options.boundary
  const collapsedBoundary = boundary
    && options.collapsedBoundaryId === boundary.id
    ? boundary
    : null
  const collapsedMemberIds = new Set(collapsedBoundary?.memberIds ?? [])
  const visibleOccupantCount = (placeId: string): number =>
    world.placements.filter(
      (placement) =>
        placement.placeId === placeId
        && !collapsedMemberIds.has(placement.entityId),
    ).length
  const placeHeight = (placeId: string): number => {
    const rows = Math.ceil(visibleOccupantCount(placeId) / 2)
    return Math.max(260, 112 + rows * 92)
  }
  const roots = world.places.filter((place) => place.parentPlaceId === null)
  const nodes: Node<CanvasNodeData>[] = []
  const placeWidths = new Map<string, number>()
  let rootOffset = 30

  roots.forEach((root) => {
    const children = world.places.filter(
      (place) => place.parentPlaceId === root.id,
    )
    const width = Math.max(800, 90 + Math.max(1, children.length) * 360)
    const tallestChild = Math.max(
      0,
      ...children.map((place) => placeHeight(place.id)),
    )
    const height = Math.max(560, 150 + tallestChild)
    placeWidths.set(root.id, width)
    nodes.push(placeNode(root, {
      position: { x: rootOffset, y: 30 },
      width,
      height,
      active: eventFocus.has(root.id),
      selected: options.selectedNodeId === root.id,
    }))
    children.forEach((place, index) => {
      nodes.push(placeNode(place, {
        position: { x: 46 + index * 350, y: 110 },
        width: 330,
        height: placeHeight(place.id),
        parentNode: root.id,
        active: eventFocus.has(place.id),
        selected: options.selectedNodeId === place.id,
      }))
    })
    rootOffset += width + 100
  })

  const currentNodes = new Map(options.nodes.map((node) => [node.id, node]))
  const occupants = new Map<string, PlacementView[]>()
  world.placements.forEach((placement) => {
    const list = occupants.get(placement.placeId) ?? []
    list.push(placement)
    occupants.set(placement.placeId, list)
  })
  const visibleOccupantCounts = new Map<string, number>()
  occupants.forEach((placements, placeId) => {
    if (!placeById.has(placeId)) return
    placements
      .sort((left, right) => left.entityId.localeCompare(right.entityId))
      .filter((placement) => !collapsedMemberIds.has(placement.entityId))
      .map((placement) => ({ placement, raw: currentNodes.get(placement.entityId) }))
      .filter((item): item is { placement: PlacementView; raw: AnalystNode } => Boolean(item.raw))
      .forEach(({ placement, raw }, index) => {
        const node = toCanvasNode(
          raw,
          eventFocus.has(raw.id)
            || activeParticipants.has(raw.id)
            || options.activity?.cue?.source_id === raw.id
            || options.activity?.cue?.target_id === raw.id,
          options.selectedNodeId === raw.id,
        )
        nodes.push({
          ...node,
          parentNode: placeId,
          extent: 'parent',
          position: {
            x: 12 + (index % 2) * 164,
            y: 88 + Math.floor(index / 2) * 92,
          },
          style: {
            ...node.style,
            width: WORLD_NODE_WIDTH,
            height: WORLD_NODE_HEIGHT,
          },
        })
        visibleOccupantCounts.set(placeId, index + 1)
      })
  })

  if (collapsedBoundary) {
    const memberPlacements = world.placements.filter((placement) =>
      collapsedMemberIds.has(placement.entityId),
    )
    const hostPlaceId = nearestCommonPlace(
      [...new Set(memberPlacements.map((placement) => placement.placeId))],
      placeById,
    )
    const aggregate = currentNodes.get(collapsedBoundary.id)
    const hostPlace = hostPlaceId ? placeById.get(hostPlaceId) : null
    if (hostPlaceId && hostPlace && aggregate) {
      const leaf = hostPlace.parentPlaceId !== null
      const visibleCount = visibleOccupantCounts.get(hostPlaceId) ?? 0
      const node = toCanvasNode(
        {
          ...aggregate,
          description: `${memberPlacements.length} placed member${memberPlacements.length === 1 ? '' : 's'} summarized at their nearest shared spatial container. The composite is an analytical view, not a physically located executor.`,
        },
        Boolean(options.event?.boundary_ids?.includes(collapsedBoundary.id))
          || memberPlacements.some((placement) =>
            eventFocus.has(placement.entityId) || activeParticipants.has(placement.entityId),
          ),
        options.selectedNodeId === collapsedBoundary.id,
      )
      nodes.push({
        ...node,
        parentNode: hostPlaceId,
        extent: 'parent',
        position: leaf
          ? { x: 38, y: 88 + Math.ceil(visibleCount / 2) * 92 }
          : { x: Math.max(18, (placeWidths.get(hostPlaceId) ?? 800) - 270), y: 18 },
        style: {
          ...node.style,
          width: 238,
          height: 108,
        },
      })
    }
  }

  return {
    nodes,
    edges: world.links.map((link) => toCanvasEdge(
      link,
      options.event,
      options.selectedEdgeId === link.id,
      options.activity,
    )),
  }
}

function buildGraph(options: CanvasOptions): {
  nodes: Node<CanvasNodeData>[]
  edges: Edge<CanvasEdgeData>[]
} {
  if (options.viewMode === 'world') return buildWorldGraph(options)
  if (options.viewMode === 'trajectory') {
    const selectedEventId = options.event?.event_id
    const nodes = options.trajectory?.nodes.map((item) => toCanvasNode(
      {
        id: item.id,
        kind: item.kind,
        label: `t${item.logical_time} · ${item.kind.replaceAll('_', ' ')}`,
        description: item.label.length > 78
          ? `${item.label.slice(0, 75)}…`
          : item.label,
        state: item,
      },
      selectedEventId === item.id,
      options.selectedNodeId === item.id,
    )) ?? []
    const edges = options.trajectory?.edges.map((item) => toCanvasEdge(
      {
        id: item.id,
        kind: 'causal_parent',
        source: item.source,
        target: item.target,
        enabled: true,
        description: 'Retained causal-parent link.',
        routeIds: [],
      },
      null,
      options.selectedEdgeId === item.id,
    )) ?? []
    return { nodes: trajectoryGridLayout(nodes), edges }
  }
  const event = options.event
  const activeIds = new Set([
    ...(event?.focus_ids ?? []),
    ...(options.activity?.participantIds ?? []),
    ...(options.activity?.cue?.source_id ? [options.activity.cue.source_id] : []),
    ...(options.activity?.cue?.target_id ? [options.activity.cue.target_id] : []),
  ])
  const canvasNodes = options.nodes.map((item) => {
    const boundaryActive = item.kind === 'analytical_boundary'
      && Boolean(event?.boundary_ids?.includes(item.id))
    return toCanvasNode(
      item,
      activeIds.has(item.id) || boundaryActive,
      options.selectedNodeId === item.id,
      options.graphDiagnostics?.nodeClassification[item.id],
    )
  })
  const canvasEdges = options.edges.map((item) =>
    toCanvasEdge(item, event, options.selectedEdgeId === item.id, options.activity),
  )
  if (options.boundary && options.collapsedBoundaryId === null) {
    return {
      nodes: expandedBoundaryLayout(
        canvasNodes,
        canvasEdges,
        options.boundary,
        Boolean(event?.boundary_ids?.includes(options.boundary.id)),
        options.selectedNodeId === options.boundary.id,
      ),
      edges: canvasEdges,
    }
  }
  return { nodes: dagreLayout(canvasNodes, canvasEdges), edges: canvasEdges }
}

function NodeLabel({ data }: { data: CanvasNodeData }) {
  if (data.placeMode) {
    return (
      <div className="cy-place-label">
        <span>{data.placeMode === 'root' ? 'spatial frame' : 'place'}</span>
        <strong>{data.raw.label}</strong>
        <small>{data.raw.description}</small>
      </div>
    )
  }
  if (data.aggregateMode === 'expanded') {
    return (
      <div className="cy-boundary-label">
        <span>analytical composite · does not act</span>
        <strong>{data.raw.label}</strong>
        <small>{data.memberCount} exact visible members · expanded</small>
      </div>
    )
  }
  return (
    <div
      className={`cy-flow-node cy-flow-node--${data.raw.kind}`}
      data-kind={data.raw.kind}
    >
      <span>
        <i className="cy-node-glyph" aria-hidden="true">
          {nodeGlyph(data.raw.kind)}
        </i>
        {data.aggregateMode === 'collapsed'
          ? 'analytical composite · does not act'
          : data.connectivityClass === 'unused'
            ? 'unconnected configured item'
          : data.raw.kind.replaceAll('_', ' ')}
      </span>
      <strong>{data.raw.label}</strong>
      <small>
        {data.aggregateMode === 'collapsed'
          ? 'Collapsed view; expand for exact components.'
          : data.raw.description}
      </small>
    </div>
  )
}

function GraphFlow({ options }: { options: CanvasOptions }) {
  const graph = useMemo(() => buildGraph(options), [options])
  const [nodes, setNodes, onNodesChange] = useNodesState(graph.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(graph.edges)
  const initialized = useNodesInitialized()
  const { fitBounds, fitView } = useReactFlow()
  const layoutKey = [
    options.viewMode,
    options.collapsedBoundaryId ?? 'exact',
    ...graph.nodes.map((node) => node.id),
    ...graph.edges.map((edge) => edge.id),
  ].join('|')

  useEffect(() => {
    setNodes(graph.nodes)
    setEdges(graph.edges)
  }, [graph.edges, graph.nodes, setEdges, setNodes])

  useEffect(() => {
    if (!initialized) return
    const frame = window.requestAnimationFrame(() => {
      if (!graph.nodes.length) return
      const mobileWorldMinimum =
        options.viewMode === 'world' && window.innerWidth <= 700 ? 0.65 : 0.1
      if (options.viewMode === 'world') {
        void fitView({
          padding: 0.12,
          duration: 280,
          minZoom: mobileWorldMinimum,
          maxZoom: 1.35,
        })
      } else {
        const left = Math.min(...graph.nodes.map((node) => node.position.x))
        const top = Math.min(...graph.nodes.map((node) => node.position.y))
        const right = Math.max(...graph.nodes.map(
          (node) => node.position.x + Number(node.style?.width ?? NODE_WIDTH),
        ))
        const bottom = Math.max(...graph.nodes.map(
          (node) => node.position.y + Number(node.style?.height ?? NODE_HEIGHT),
        ))
        void fitBounds(
          {
            x: left,
            y: top,
            width: Math.max(1, right - left),
            height: Math.max(1, bottom - top),
          },
          { padding: 0.12, duration: 280 },
        )
      }
      setEdges(graph.edges.map((edge) => ({ ...edge })))
    })
    return () => window.cancelAnimationFrame(frame)
  }, [
    fitView,
    fitBounds,
    initialized,
    layoutKey,
    graph.edges,
    options.viewMode,
    setEdges,
  ])

  const collapsed = options.collapsedBoundaryId !== null
  const worldMode = options.viewMode === 'world'
  const trajectoryMode = options.viewMode === 'trajectory'
  const unusedWarnings = options.viewMode === 'causal'
    ? options.graphDiagnostics?.warnings ?? []
    : []
  const legendNodeKinds = [...new Set(
    (options.legendNodes ?? options.nodes).map((node) => node.kind),
  )]
  const legendEdgeKinds = [...new Set(
    (options.legendEdges ?? options.edges).map((edge) => edge.kind),
  )]
  return (
    <section className="cy-graph-shell">
      <div className="cy-graph-bar">
        <span>
          <strong>
            {options.title ?? (worldMode
              ? collapsed ? 'World topology · collapsed composite' : 'World topology'
              : trajectoryMode
                ? 'Realized causal trajectory'
              : collapsed ? 'Collapsed composite' : 'Expanded exact network')}
          </strong>{options.subtitle
            ? ` · ${options.subtitle}`
            : ` · revision ${options.event?.state_revision ?? options.initialRevision ?? 'unavailable'}`}
          {worldMode && options.world?.unplacedEntityIds.length
            ? ` · ${options.world.unplacedEntityIds.length} logical entities are outside this spatial projection; inspect them in Configured interaction pathways`
            : ''}
        </span>
        {unusedWarnings.length > 0
          ? (
            <span
              className="cy-graph-warning"
              title={unusedWarnings.map((item) => item.message).join(' ')}
            >
              {unusedWarnings.length} unconnected configured item{
                unusedWarnings.length === 1 ? '' : 's'
              }
            </span>
          )
          : null}
      </div>
      {options.showLegend === false ? null : (
        <div className="cy-graph-legend" aria-label="Graph key">
          <div>
            <strong>Nodes</strong>
            {legendNodeKinds.map((kind) => (
              <span key={kind} className={`cy-legend-node cy-legend-node--${kind}`}>
                <i aria-hidden="true">{nodeGlyph(kind)}</i>{nodeTypeLabel(kind)}
              </span>
            ))}
          </div>
          <div>
            <strong>Relations</strong>
            {legendEdgeKinds.map((kind) => (
              <span key={kind} className={`cy-legend-edge cy-legend-edge--${kind}`}>
                <i style={{ borderColor: relationColor(kind) }} aria-hidden="true" />
                {relationLabel(kind)}
              </span>
            ))}
          </div>
        </div>
      )}
      <div className="cy-graph-canvas">
        <ReactFlow
          nodes={nodes.map((node) => ({
            ...node,
            data: {
              ...node.data,
              label: <NodeLabel data={node.data} />,
            },
          }))}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={(_, node) => options.onSelectNode(node.id)}
          onEdgeClick={(_, edge) => {
            const raw = (edge.data as CanvasEdgeData | undefined)?.raw
            if (raw) options.onSelectEdge(raw)
          }}
          fitView
          fitViewOptions={{ padding: 0.12, maxZoom: 1.35 }}
          minZoom={0.08}
          maxZoom={2.2}
          nodesDraggable
          nodesConnectable={false}
          edgeTypes={{ liveCue: LiveCueEdge }}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={22}
            size={1}
            color="#293440"
          />
          {options.showMiniMap === false ? null : (
            <MiniMap
              pannable
              zoomable
              nodeColor={nodeColor}
              maskColor="rgba(6, 10, 15, .72)"
            />
          )}
          <Controls position="bottom-left" />
        </ReactFlow>
      </div>
    </section>
  )
}

function render(element: Element, options: CanvasOptions): void {
  let root = roots.get(element)
  if (!root) {
    root = createRoot(element)
    roots.set(element, root)
  }
  root.render(
    <ReactFlowProvider>
      <GraphFlow options={options} />
    </ReactFlowProvider>,
  )
}

function clear(element: Element): void {
  const root = roots.get(element)
  if (!root) return
  root.unmount()
  roots.delete(element)
}

declare global {
  interface Window {
    CyberneticGraph?: { render: typeof render; clear: typeof clear }
  }
}

window.CyberneticGraph = { render, clear }
