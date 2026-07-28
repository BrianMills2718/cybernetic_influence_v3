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
  viewMode: 'world' | 'causal' | 'trajectory'
  analyticalScaleHelp: string
  collapsedBoundaryId: string | null
  selectedNodeId: string | null
  selectedEdgeId: string | null
  activity?: {
    participantIds: string[]
    cue: CanvasAnimationCue | null
  } | null
  onSelectNode: (nodeId: string) => void
  onSelectEdge: (edge: AnalystEdge) => void
  onToggleBoundary: (boundaryId: string) => void
}

interface CanvasNodeData {
  raw: AnalystNode
  active: boolean
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
    mechanism_binding: 'input',
    information_location: 'carried',
    information_lineage: 'derived',
    spatial_link: 'adjacent via',
  }[kind] ?? kind.replaceAll('_', ' ')
}

function relationColor(kind: string): string {
  return {
    connection: '#5aa9e6',
    mechanism_binding: '#e8a84d',
    information_location: '#ef79b7',
    information_lineage: '#c36fa1',
    spatial_link: '#83d6c0',
  }[kind] ?? '#71849a'
}

function nodeColor(node: Node<CanvasNodeData>): string {
  return {
    person: '#58a6ff',
    information: '#ef79b7',
    mechanism: '#e8a84d',
    analytical_boundary: '#b891ff',
    place: '#83d6c0',
  }[node.data.raw.kind] ?? '#57b49d'
}

function toCanvasNode(
  item: AnalystNode,
  active: boolean,
  selected: boolean,
): Node<CanvasNodeData> {
  const collapsed = item.kind === 'analytical_boundary'
  return {
    id: item.id,
    position: { x: 0, y: 0 },
    data: {
      raw: item,
      active,
      aggregateMode: collapsed ? 'collapsed' : undefined,
    },
    className: [
      'cy-flow-node-wrap',
      active ? 'cy-flow-node-wrap--active' : '',
      selected ? 'cy-flow-node-wrap--selected' : '',
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
  return {
    id: item.id,
    source: item.source,
    target: item.target,
    label: item.kind === 'spatial_link' && item.substrateEntityIds?.length
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
      stroke: active ? '#ffffff' : relationColor(item.kind),
      strokeWidth: active || selected ? 3 : 1.6,
      opacity: item.enabled ? 0.9 : 0.3,
      strokeDasharray: item.kind === 'spatial_link'
        ? '10 5'
        : item.kind === 'mechanism_binding'
        ? '6 4'
        : item.kind === 'information_lineage' ? '3 4' : undefined,
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
  edges.forEach((edge) => {
    if (edge.source !== edge.target) graph.setEdge(edge.source, edge.target)
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

function buildWorldGraph(options: CanvasOptions): {
  nodes: Node<CanvasNodeData>[]
  edges: Edge<CanvasEdgeData>[]
} {
  const world = options.world
  if (!world) return { nodes: [], edges: [] }
  const eventFocus = new Set(options.event?.spatial_focus_ids ?? [])
  const activeParticipants = new Set(options.activity?.participantIds ?? [])
  const placeById = new Map(world.places.map((place) => [place.id, place]))
  const roots = world.places.filter((place) => place.parentPlaceId === null)
  const nodes: Node<CanvasNodeData>[] = []
  let rootOffset = 30

  roots.forEach((root) => {
    const children = world.places.filter(
      (place) => place.parentPlaceId === root.id,
    )
    const width = Math.max(800, 90 + Math.max(1, children.length) * 360)
    const height = 560
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
        width: 314,
        height: 390,
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
  occupants.forEach((placements, placeId) => {
    if (!placeById.has(placeId)) return
    placements
      .sort((left, right) => left.entityId.localeCompare(right.entityId))
      .forEach((placement, index) => {
        const raw = currentNodes.get(placement.entityId)
        if (!raw) return
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
            x: 18 + (index % 2) * 148,
            y: 88 + Math.floor(index / 2) * 92,
          },
          style: {
            ...node.style,
            width: WORLD_NODE_WIDTH,
            height: WORLD_NODE_HEIGHT,
          },
        })
      })
  })

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
        kind: 'realized_event',
        label: `t${item.logical_time} · ${item.kind.replaceAll('_', ' ')}`,
        description: item.label,
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
    return { nodes: dagreLayout(nodes, edges), edges }
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
    )
  })
  const canvasEdges = options.edges.map((item) =>
    toCanvasEdge(item, event, options.selectedEdgeId === item.id, options.activity),
  )
  if (options.boundary) {
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
        <span>analytical composite · executor=false</span>
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
        {data.aggregateMode === 'collapsed'
          ? 'analytical composite · executor=false'
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
  const { fitView } = useReactFlow()
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
      const mobileWorldMinimum =
        options.viewMode === 'world' && window.innerWidth <= 700 ? 0.65 : 0.1
      void fitView({
        padding: 0.12,
        duration: 280,
        minZoom: mobileWorldMinimum,
        maxZoom: 1.35,
      })
      setEdges(graph.edges.map((edge) => ({ ...edge })))
    })
    return () => window.cancelAnimationFrame(frame)
  }, [
    fitView,
    initialized,
    layoutKey,
    graph.edges,
    options.viewMode,
    setEdges,
  ])

  const boundaryId = options.boundary?.id ?? options.collapsedBoundaryId
  const boundaryLabel = options.boundary?.label
    ?? options.nodes.find((node) => node.id === boundaryId)?.label
    ?? 'analytical composite'
  const collapsed = options.collapsedBoundaryId !== null
  const worldMode = options.viewMode === 'world'
  const trajectoryMode = options.viewMode === 'trajectory'
  return (
    <section className="cy-graph-shell">
      <div className="cy-graph-bar">
        <span>
          <strong>
            {worldMode
              ? 'World topology'
              : trajectoryMode
                ? 'Realized causal trajectory'
              : collapsed ? 'Collapsed composite' : 'Expanded exact network'}
          </strong>
          {' · '}revision {options.event?.state_revision ?? options.initialRevision ?? 'unavailable'}
          {worldMode && options.world?.unplacedEntityIds.length
            ? ` · ${options.world.unplacedEntityIds.length} logical entities are outside this spatial projection; inspect them in Configured interaction pathways`
            : ''}
        </span>
        <div className="cy-graph-actions">
          {!worldMode && !trajectoryMode && boundaryId && (
          <button
            title={options.analyticalScaleHelp}
            aria-label={`Analytical scale: ${collapsed ? 'expand' : 'collapse'} ${boundaryLabel}`}
            onClick={() => options.onToggleBoundary(boundaryId)}
          >
            Analytical scale: {collapsed ? 'Expand' : 'Collapse'} {boundaryLabel}
          </button>
          )}
        </div>
      </div>
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
          <MiniMap
            pannable
            zoomable
            nodeColor={nodeColor}
            maskColor="rgba(6, 10, 15, .72)"
          />
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

declare global {
  interface Window {
    CyberneticGraph?: { render: typeof render }
  }
}

window.CyberneticGraph = { render }
