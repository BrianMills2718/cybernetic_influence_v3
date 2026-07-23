import { useEffect, useMemo } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import dagre from '@dagrejs/dagre'
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlowProvider,
  type Edge,
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
  boundary_ids?: string[]
}

interface CanvasOptions {
  nodes: AnalystNode[]
  edges: AnalystEdge[]
  event: EventView | null
  boundary: BoundaryView | null
  collapsedBoundaryId: string | null
  selectedNodeId: string | null
  selectedEdgeId: string | null
  onSelectNode: (nodeId: string) => void
  onSelectEdge: (edge: AnalystEdge) => void
  onToggleBoundary: (boundaryId: string) => void
}

interface CanvasNodeData {
  raw: AnalystNode
  active: boolean
  aggregateMode?: 'expanded' | 'collapsed'
  memberCount?: number
}

interface CanvasEdgeData {
  raw: AnalystEdge
}

const NODE_WIDTH = 194
const NODE_HEIGHT = 92
const roots = new WeakMap<Element, Root>()

function relationLabel(kind: string): string {
  return {
    connection: 'route',
    mechanism_binding: 'input',
    information_location: 'carried',
    information_lineage: 'derived',
  }[kind] ?? kind.replaceAll('_', ' ')
}

function relationColor(kind: string): string {
  return {
    connection: '#5aa9e6',
    mechanism_binding: '#e8a84d',
    information_location: '#ef79b7',
    information_lineage: '#c36fa1',
  }[kind] ?? '#71849a'
}

function nodeColor(node: Node<CanvasNodeData>): string {
  return {
    person: '#58a6ff',
    information: '#ef79b7',
    mechanism: '#e8a84d',
    analytical_boundary: '#b891ff',
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
): Edge<CanvasEdgeData> {
  const focusedRoute = item.routeIds.some((id) => event?.focus_edges.includes(id))
  const focusedEndpoints = Boolean(
    event?.focus_ids.includes(item.source) && event.focus_ids.includes(item.target),
  )
  const active = focusedRoute || focusedEndpoints
  return {
    id: item.id,
    source: item.source,
    target: item.target,
    label: relationLabel(item.kind),
    type: 'smoothstep',
    animated: active,
    data: { raw: item },
    className: [
      `cy-flow-edge--${item.kind}`,
      active ? 'cy-flow-edge--active' : '',
      selected ? 'cy-flow-edge--selected' : '',
    ].filter(Boolean).join(' '),
    style: {
      stroke: active ? '#ffffff' : relationColor(item.kind),
      strokeWidth: active || selected ? 3 : 1.6,
      opacity: item.enabled ? 0.9 : 0.3,
      strokeDasharray: item.kind === 'mechanism_binding'
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

function buildGraph(options: CanvasOptions): {
  nodes: Node<CanvasNodeData>[]
  edges: Edge<CanvasEdgeData>[]
} {
  const event = options.event
  const activeIds = new Set(event?.focus_ids ?? [])
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
    toCanvasEdge(item, event, options.selectedEdgeId === item.id),
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
      void fitView({ padding: 0.12, duration: 280, maxZoom: 1.35 })
      setEdges(graph.edges.map((edge) => ({ ...edge })))
    })
    return () => window.cancelAnimationFrame(frame)
  }, [fitView, initialized, layoutKey, graph.edges, setEdges])

  const boundaryId = options.boundary?.id ?? options.collapsedBoundaryId
  const boundaryLabel = options.boundary?.label
    ?? options.nodes.find((node) => node.id === boundaryId)?.label
    ?? 'analytical composite'
  const collapsed = options.collapsedBoundaryId !== null
  return (
    <section className="cy-graph-shell">
      <div className="cy-graph-bar">
        <span>
          <strong>{collapsed ? 'Collapsed composite' : 'Expanded exact network'}</strong>
          {' · '}revision {options.event?.state_revision ?? 'final'}
        </span>
        {boundaryId && (
          <button onClick={() => options.onToggleBoundary(boundaryId)}>
            {collapsed ? 'Expand' : 'Collapse'} {boundaryLabel}
          </button>
        )}
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
