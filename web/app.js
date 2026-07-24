const $ = (selector) => document.querySelector(selector)

function showTraceInPlace(person) {
  const trace = $('#trace')
  const retainedHeight = Math.ceil(trace.getBoundingClientRect().height)
  if (retainedHeight > 0) trace.style.minHeight = `${retainedHeight}px`
  showTrace(person)
}
const html = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
})[character])

let current = null
let selectedEventIndex = 0
let selectedMomentIndex = 0
let selectedPerson = null
let selectedScale = 'exact'
let selectedGraphView = 'causal'
let selectedNodeId = null
let selectedEdgeId = null
let scenarioCatalog = {}
let runtimeConfig = {}
let activeRunId = null

function setWorkspaceView(view) {
  const simulation = view === 'simulation'
  const history = view === 'history'
  const readme = view === 'readme'
  $('#simulation-view').hidden = !simulation
  $('#history-view').hidden = !history
  $('#readme-view').hidden = !readme
  for (const [tab, active] of [
    ['#simulation-tab', simulation],
    ['#history-tab', history],
    ['#readme-tab', readme],
  ]) {
    $(tab).classList.toggle('active', active)
    $(tab).setAttribute('aria-pressed', String(active))
  }
}

function simulatedTime(value) {
  const unit = current?.time_unit || 'step'
  const plural = Number(value) === 1 ? unit : `${unit}s`
  return `time ${value} ${plural}`
}

function causeSummary(causes = []) {
  return causes.map((cause) => {
    if (cause.kind === 'internal_wake') return 'internal wake'
    if (cause.kind === 'observation_delivery') {
      const count = cause.observation_ids?.length || 0
      return `${count} delivered observation${count === 1 ? '' : 's'}`
    }
    return String(cause.kind || 'unknown').replaceAll('_', ' ')
  }).join(' + ')
}

async function request(url, options = {}) {
  const response = await fetch(url, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

async function loadConfig() {
  const config = await request('/api/config')
  runtimeConfig = config
  scenarioCatalog = config.scenarios || {}
  $('#scenario').innerHTML = Object.entries(scenarioCatalog).map(([id, item]) =>
    `<option value="${html(id)}">${html(item.label)}</option>`
  ).join('')
  $('#scenario').value = config.scenario
  const liveOptions = config.live_options || {}
  const choices = liveOptions.models || []
  $('#model').innerHTML = choices.map((choice) =>
    `<option value="${html(choice.model)}">${html(choice.label)}</option>`
  ).join('')
  $('#model').value = liveOptions.defaults?.model || config.model
  configureReasoningChoices(
    liveOptions.defaults?.agent_reasoning_effort || config.reasoning_effort
  )
  $('#max-cost').value = Number(liveOptions.defaults?.max_total_cost || config.maximum_live_cost).toFixed(2)
  $('#max-cost').max = liveOptions.limits?.server_max_total_cost || config.maximum_live_cost
  const help = liveOptions.help || {}
  $('#model-help').textContent = help.model || ''
  updateReasoningHelp()
  $('#max-cost-help').textContent = help.max_total_cost || ''
  $('#map-help').textContent = help.map_projection || ''
  $('#moment-help').textContent = help.causal_moment || ''
  $('#narrative-help').textContent = help.narrative || ''
  configureScenario(config.scenario)
  $('#live').disabled = !config.live_authorized || choices.length === 0
  $('#live').checked = config.live_authorized
  $('#run').textContent = config.live_authorized ? 'Play live simulation' : 'Play reference simulation'
  if (!config.live_authorized) {
    $('#live-help').textContent = 'Live execution is disabled on this server. Reference runs remain zero-cost.'
  } else if (!choices.length) {
    $('#live').checked = false
    $('#live-help').textContent = 'No deployment-certified model route is currently selectable.'
  } else {
    $('#live-help').textContent = help.live_execution || 'People reason from their own memory, position, and delivered observations.'
  }
  configureLiveControls()
}

function configureScenario(scenarioId) {
  const selected = scenarioCatalog[scenarioId]
  if (!selected) return
  $('#arm').innerHTML = selected.arms.map((arm) =>
    `<option value="${html(arm.id)}">${html(arm.label)}</option>`
  ).join('')
  $('#scenario-title').textContent = selected.label
  $('#scenario-description').textContent = selected.representation_summary ||
    'Choose one bounded scenario, its concrete condition, and a live or reference execution.'
  $('#representation-summary').textContent = selected.representation_summary || ''
  fillList('#scenario-assumptions', selected.assumptions)
  fillList('#scenario-omissions', selected.known_omissions)
  fillList('#scenario-questions', selected.fidelity_questions)
  updateAuthorizationPreview()
  describeCondition()
}

function fillList(selector, values = []) {
  $(selector).innerHTML = values.map((value) => `<li>${html(value)}</li>`).join('')
}

function configureLiveControls() {
  const enabled = $('#live').checked && !$('#live').disabled
  for (const selector of ['#model', '#reasoning', '#max-cost']) {
    $(selector).disabled = !enabled
  }
  updateAuthorizationPreview()
}

function selectedModelChoice() {
  const choices = runtimeConfig.live_options?.models || []
  return choices.find((choice) => choice.model === $('#model').value)
}

function configureReasoningChoices(preferred = null) {
  const choice = selectedModelChoice()
  const efforts = choice?.agent_reasoning_efforts || ['low', 'medium', 'high']
  const experimental = new Set(choice?.experimental_agent_reasoning_efforts || [])
  $('#reasoning').innerHTML = efforts.map((effort) =>
    `<option value="${html(effort)}">${html(formatReasoningEffort(effort))}${experimental.has(effort) ? ' (experimental)' : ''}</option>`
  ).join('')
  $('#reasoning').value = efforts.includes(preferred)
    ? preferred
    : choice?.default_agent_reasoning_effort || efforts[0]
  updateReasoningHelp()
}

function formatReasoningEffort(effort) {
  return effort === 'xhigh' ? 'X-high' : effort[0].toUpperCase() + effort.slice(1)
}

function updateReasoningHelp() {
  const base = runtimeConfig.live_options?.help?.agent_reasoning_effort || ''
  const experimental = new Set(selectedModelChoice()?.experimental_agent_reasoning_efforts || [])
  const effort = $('#reasoning')?.value
  $('#reasoning-help').textContent = experimental.has(effort)
    ? `${base} ${formatReasoningEffort(effort)} is experimental for this simulator: a focused structured-output probe did not complete reliably. Inspect the retained call trace after use.`
    : base
}

function updateAuthorizationPreview() {
  const limits = runtimeConfig.live_options?.limits || {}
  if (!$('#live').checked) {
    $('#cost-details').textContent = 'Reference execution uses fixed policies, makes zero model calls, and costs $0.'
    return
  }
  const modelLabel = $('#model').selectedOptions[0]?.textContent || 'No eligible model'
  const reasoning = $('#reasoning').value || 'medium'
  const narratorReasoning = selectedModelChoice()?.narrator_reasoning_effort || 'low'
  const authorized = Number($('#max-cost').value || 0)
  const baseline = (runtimeConfig.cost_baselines || []).find((item) =>
    item.scenario === $('#scenario').value &&
    item.arm === $('#arm').value &&
    item.model === $('#model').value &&
    item.agent_reasoning_effort === reasoning &&
    item.narrator_reasoning_effort === narratorReasoning
  )
  const estimate = baseline
    ? `Expected observed spend: about $${Number(baseline.median_cost).toFixed(4)} from ${baseline.sample_count} comparable completed live run${baseline.sample_count === 1 ? '' : 's'} (range $${Number(baseline.minimum_cost).toFixed(4)}–$${Number(baseline.maximum_cost).toFixed(4)}).`
    : 'Expected observed spend: no comparable completed live run is retained yet.'
  $('#cost-details').textContent =
    `${estimate} Hard authorization: $${authorized.toFixed(2)}; no hidden overage. Each participant call is capped at $${Number(limits.participant_per_call_ceiling || 0).toFixed(2)} and each narrator call at $${Number(limits.narrator_per_call_ceiling || 0).toFixed(2)}.`
}

function describeCondition() {
  const scenario = scenarioCatalog[$('#scenario').value]
  const arm = scenario?.arms.find((item) => item.id === $('#arm').value)
  $('#arm-help').textContent = arm?.description || 'Choose the concrete condition you want the simulation to test.'
}

async function loadHistory() {
  const result = await request('/api/runs')
  $('#history-empty').hidden = result.runs.length > 0
  $('#storage-warning').hidden = result.corrupt_files.length === 0
  $('#storage-warning').textContent = result.corrupt_files.length
    ? `${result.corrupt_files.length} unreadable retained run file(s) require operator attention.`
    : ''
  $('#history').innerHTML = result.runs.map((run) => `
    <article class="history-item">
      <button class="open-run" data-run-id="${run.run_id}">
        <strong>${html(run.headline || run.status)}</strong>
        <span>${html(run.scenario?.replaceAll('_',' '))} · ${html(run.arm?.replaceAll('_',' '))}</span>
        <small>${html(run.status)} · ${html(new Date(run.created_at).toLocaleString())}</small>
      </button>
      <button class="trash-run" data-run-id="${run.run_id}" aria-label="Move ${run.run_id} to trash">×</button>
    </article>
  `).join('')
  document.querySelectorAll('.open-run').forEach((button) => {
    button.onclick = async () => {
      $('#run-status').textContent = 'Opening…'
      try {
        await openRetained(button.dataset.runId)
        $('#run-status').textContent = 'Opened retained run'
      } catch (error) {
        $('#run-status').textContent = error.message
      }
    }
  })
  document.querySelectorAll('.trash-run').forEach((button) => {
    button.onclick = async () => {
      if (!confirm('Move this retained run to recoverable server trash?')) return
      try {
        await request(`/api/runs/${button.dataset.runId}`, {method:'DELETE'})
        if (current?.run_id === button.dataset.runId) {
          current = null
          $('#result').hidden = true
          const url = new URL(window.location)
          url.searchParams.delete('run')
          window.history.replaceState({}, '', url)
        }
        await loadHistory()
      } catch (error) {
        $('#run-status').textContent = error.message
      }
    }
  })
}

async function openRetained(runId) {
  render(await request(`/api/runs/${runId}`))
  setWorkspaceView('simulation')
  const url = new URL(window.location)
  url.searchParams.set('run', runId)
  window.history.replaceState({}, '', url)
}

function nodesAtSelectedEvent() {
  const event = current?.timeline?.[selectedEventIndex]
  if (!event) return current?.nodes || []
  return current.snapshots?.[String(event.state_revision)] || []
}

function selectedBoundary() {
  return (current?.boundaries || []).find((boundary) => boundary.id === selectedScale)
}

function boundarySnapshot(boundary = selectedBoundary()) {
  const event = current?.timeline?.[selectedEventIndex]
  return boundary?.snapshots?.[String(event?.state_revision)] || null
}

function worldProjection() {
  const world = current?.world
  const event = current?.timeline?.[selectedEventIndex]
  if (!world || !event) return null
  const snapshot = world.snapshots?.[String(event.state_revision)]
  if (!snapshot) return null
  return {
    places:(world.places || []).map((place) => ({
      id:place.id,
      kind:place.kind,
      label:place.label,
      description:place.description,
      parentPlaceId:place.parent_place_id,
    })),
    links:(world.links || []).map((link) => ({
      id:link.id,
      kind:'spatial_link',
      source:link.endpoint_a_place_id,
      target:link.endpoint_b_place_id,
      enabled:true,
      description:link.description,
      routeIds:[],
      substrateEntityIds:link.substrate_entity_ids || [],
    })),
    placements:(snapshot.placements || []).map((placement) => ({
      entityId:placement.entity_id,
      placeId:placement.place_id,
    })),
    unplacedEntityIds:snapshot.unplaced_entity_ids || [],
  }
}

function graphProjection() {
  const exactNodes = nodesAtSelectedEvent()
  const exactNodeIds = new Set(exactNodes.map((node) => node.id))
  const temporalEdges = current.edges.filter((edge) =>
    exactNodeIds.has(edge.source) && exactNodeIds.has(edge.target)
  )
  if (selectedScale === 'exact') {
    return {
      nodes: exactNodes,
      edges: temporalEdges.map((edge) => ({
        ...edge,
        kind:edge.kind || 'connection',
        routeIds:edge.exact_route_ids || [edge.id],
      })),
    }
  }
  const boundary = selectedBoundary()
  const snapshot = boundarySnapshot(boundary)
  if (!boundary || !snapshot) return {nodes:exactNodes, edges:[]}
  const memberIds = new Set(snapshot.member_ids)
  const aggregateNode = {
    id:boundary.id,
    kind:'analytical_boundary',
    label:boundary.label,
    description:boundary.description,
    state:{
      executor:false,
      member_kinds:snapshot.member_kind_counts,
      hidden_state_facts:snapshot.hidden_fact_count,
      hidden_information_tokens:snapshot.hidden_information_count,
    },
  }
  const grouped = new Map()
  temporalEdges.forEach((edge) => {
    const kind = edge.kind || 'connection'
    const source = memberIds.has(edge.source) ? boundary.id : edge.source
    const target = memberIds.has(edge.target) ? boundary.id : edge.target
    if (source === target) return
    const key = `${kind}|${source}|${target}|${edge.enabled}`
    if (!grouped.has(key)) {
      grouped.set(key, {
        id:`coarse_${grouped.size}`,
        kind,
        source,
        target,
        enabled:edge.enabled,
        description:'Coarse route backed by exact declared connections.',
        routeIds:[],
      })
    }
    grouped.get(key).routeIds.push(...(edge.exact_route_ids || [edge.id]))
  })
  grouped.forEach((edge) => { edge.routeIds = [...new Set(edge.routeIds)] })
  return {
    nodes:[...exactNodes.filter((node) => !memberIds.has(node.id)), aggregateNode],
    edges:[...grouped.values()],
  }
}

function renderScaleControls() {
  const boundaries = current?.boundaries || []
  if (selectedScale !== 'exact' && !boundaries.some((item) => item.id === selectedScale)) {
    selectedScale = 'exact'
  }
}

function showBoundary(boundaryId) {
  const boundary = (current?.boundaries || []).find((item) => item.id === boundaryId)
  const snapshot = boundarySnapshot(boundary)
  const event = current?.timeline?.[selectedEventIndex]
  if (!boundary || !snapshot) return
  selectedNodeId = boundaryId
  selectedEdgeId = null
  renderGraph()
  document.querySelectorAll('.node').forEach((button) => button.classList.toggle('selected', button.dataset.nodeId === boundaryId))
  const linked = boundary.trace_event_ids.filter((eventId) =>
    current.timeline.findIndex((item) => item.event_id === eventId) <= selectedEventIndex
  )
  $('#inspector').innerHTML = `
    <span class="eyebrow">Analytical boundary · revision ${html(event?.state_revision)}</span>
    <h2>${html(boundary.label)}</h2>
    <p>${html(boundary.description)}</p>
    <p><strong>Execution-inert.</strong> This is a derived view, not another mind or world executor.</p>
    <dl class="aggregate-facts">
      <div><dt>Selectable components hidden</dt><dd>${html(snapshot.selectable_member_count)}</dd></div>
      <div><dt>Internal routes hidden</dt><dd>${html(snapshot.internal_route_ids.length)}</dd></div>
      <div><dt>State facts summarized</dt><dd>${html(snapshot.hidden_fact_count)}</dd></div>
      <div><dt>Information tokens summarized</dt><dd>${html(snapshot.hidden_information_count)}</dd></div>
      <div><dt>Linked events through here</dt><dd>${html(linked.length)}</dd></div>
    </dl>
    <button id="expand-boundary">Expand exact components at revision ${html(event?.state_revision)}</button>
    <details><summary>Exact evidence identifiers</summary><pre>${html(JSON.stringify({
      members:snapshot.member_ids,
      internal_routes:snapshot.internal_route_ids,
      inbound_routes:snapshot.inbound_route_ids,
      outbound_routes:snapshot.outbound_route_ids,
      trace_events:linked,
    }, null, 2))}</pre></details>`
  $('#expand-boundary').onclick = () => {
    selectedScale = 'exact'
    renderScaleControls()
    renderGraph()
    $('#inspector').innerHTML = `
      <span class="eyebrow">Exact components · revision ${html(event?.state_revision)}</span>
      <h2>${html(boundary.label)} expanded</h2>
      <p>Select any component for its exact retained state.</p>
      <div class="focus-list">${snapshot.member_ids.map((memberId) => {
        const node = nodesAtSelectedEvent().find((item) => item.id === memberId)
        return node ? `<button data-node-id="${html(node.id)}">${html(node.kind)} · ${html(node.label)}</button>` : ''
      }).join('')}</div>`
    document.querySelectorAll('.focus-list button').forEach((button) => {
      button.onclick = () => showNode(button.dataset.nodeId)
    })
  }
}

function showNode(nodeId) {
  if ((current?.boundaries || []).some((boundary) => boundary.id === nodeId)) {
    showBoundary(nodeId)
    return
  }
  selectedNodeId = nodeId
  selectedEdgeId = null
  renderGraph()
  const event = current?.timeline?.[selectedEventIndex]
  const world = worldProjection()
  const place = world?.places?.find((candidate) => candidate.id === nodeId)
  if (place) {
    const occupants = world.placements
      .filter((placement) => placement.placeId === nodeId)
      .map((placement) => placement.entityId)
    $('#inspector').innerHTML = `
      <span class="eyebrow">Place · revision ${html(event?.state_revision)}</span>
      <h2>${html(place.label)}</h2>
      <p>${html(place.description)}</p>
      <dl class="aggregate-facts">
        <div><dt>Place kind</dt><dd>${html(place.kind)}</dd></div>
        <div><dt>Immediate occupants</dt><dd>${html(occupants.length)}</dd></div>
      </dl>
      <pre>${html(JSON.stringify({parent_place_id:place.parentPlaceId, occupant_entity_ids:occupants}, null, 2))}</pre>`
    return
  }
  const node = nodesAtSelectedEvent().find((candidate) => candidate.id === nodeId)
  const finalNode = current?.nodes?.find((candidate) => candidate.id === nodeId)
  document.querySelectorAll('.node').forEach((button) => button.classList.toggle('selected', button.dataset.nodeId === nodeId))
  if (!node) {
    $('#inspector').innerHTML = `
      <span class="eyebrow">Not present at selected event</span>
      <h2>${html(finalNode?.label || nodeId)}</h2>
      <p>This entity or representation did not yet exist at state revision ${html(event?.state_revision)}.</p>`
    return
  }
  const placement = world?.placements?.find(
    (candidate) => candidate.entityId === nodeId,
  )
  $('#inspector').innerHTML = `
    <span class="eyebrow">${html(node.kind)} · revision ${html(event?.state_revision)}</span>
    <h2>${html(node.label)}</h2>
    <p>${html(node.description)}</p>
    ${placement ? `<p><strong>Located in:</strong> ${html(placement.placeId.replaceAll('_',' '))}</p>` : ''}
    <pre>${html(JSON.stringify(node.state, null, 2))}</pre>`
}

function showEdge(edge) {
  selectedNodeId = null
  selectedEdgeId = edge.id
  renderGraph()
  if (edge.kind === 'spatial_link') {
    $('#inspector').innerHTML = `
      <span class="eyebrow">Topological connection · does not imply traversability</span>
      <h2>${html(edge.source.replaceAll('_',' '))} ↔ ${html(edge.target.replaceAll('_',' '))}</h2>
      <p>${html(edge.description)}</p>
      <dl class="aggregate-facts">
        <div><dt>Link</dt><dd>${html(edge.id)}</dd></div>
        <div><dt>Concrete substrates</dt><dd>${html(edge.substrateEntityIds?.length || 0)}</dd></div>
      </dl>
      <pre>${html(JSON.stringify({spatial_link_id:edge.id, substrate_entity_ids:edge.substrateEntityIds || []}, null, 2))}</pre>`
    return
  }
  $('#inspector').innerHTML = `
    <span class="eyebrow">${html(edge.kind.replaceAll('_',' '))}</span>
    <h2>${html(edge.source.replaceAll('_',' '))} → ${html(edge.target.replaceAll('_',' '))}</h2>
    <p>${html(edge.description)}</p>
    <dl class="aggregate-facts">
      <div><dt>Enabled</dt><dd>${html(edge.enabled)}</dd></div>
      <div><dt>Exact route evidence</dt><dd>${html(edge.routeIds.length)}</dd></div>
    </dl>
    <pre>${html(JSON.stringify({id:edge.id, exact_route_ids:edge.routeIds}, null, 2))}</pre>`
}

function showTrace(person) {
  const boundary = (current?.boundaries || []).find((item) => item.id === person)
  if (boundary) {
    selectedPerson = person
    document.querySelectorAll('#trace-tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
    const snapshot = boundarySnapshot(boundary)
    const members = (snapshot?.member_ids || []).map((memberId) =>
      nodesAtSelectedEvent().find((node) => node.id === memberId),
    ).filter(Boolean)
    const people = members.filter((member) => member.kind === 'person').map((member) => member.label)
    const processes = members.filter((member) => member.kind === 'mechanism').map((member) => member.label)
    $('#trace').innerHTML = `
      <article class="trace-step composite-account">
        <span class="eyebrow">Analytical composite · does not act</span>
        <h3>${html(boundary.label)}</h3>
        <p>${html(boundary.description)} At this selected moment it summarizes ${html(people.length)} people${people.length ? ` (${html(people.join(', '))})` : ''}${processes.length ? ` and ${html(processes.length)} exact mechanism${processes.length === 1 ? '' : 's'}` : ''}. Its members produce the actions and effects; the composite is only a way to inspect them together.</p>
        <dl class="aggregate-facts">
          <div><dt>Visible exact members</dt><dd>${html(snapshot?.member_ids?.length || 0)}</dd></div>
          <div><dt>Internal routes</dt><dd>${html(snapshot?.internal_route_ids?.length || 0)}</dd></div>
          <div><dt>World executor</dt><dd>No</dd></div>
        </dl>
        <button id="inspect-composite">Inspect this composite on the map</button>
      </article>`
    $('#inspect-composite').onclick = () => showBoundary(boundary.id)
    return
  }
  selectedPerson = person
  document.querySelectorAll('#trace-tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
  const selectedEvent = current?.timeline?.[selectedEventIndex]
  const entries = (current?.traces || []).filter((entry) => entry.person === person)
  const totalActions = entries.reduce((count, entry) => count + (entry.actions?.length || 0), 0)
  const totalObservations = entries.reduce((count, entry) => count + (entry.observations?.length || 0), 0)
  const label = person.replaceAll('_', ' ')
  $('#trace').innerHTML = entries.length ? `
    <article class="trace-summary">
      <span class="eyebrow">${html(String(entries[0].participant_kind || 'person').replaceAll('_', ' '))} account</span>
      <p>${html(label)} was activated ${entries.length} time${entries.length === 1 ? '' : 's'}, received ${totalObservations} retained observation${totalObservations === 1 ? '' : 's'}, and made ${totalActions} proposed action${totalActions === 1 ? '' : 's'}. The retained moments below show what it knew and did without treating this account as access to the whole world.</p>
    </article>` + entries.map((entry) => {
    const matches = selectedEvent?.activation === entry.activation
    return `
      <article class="trace-step ${matches ? 'event-match' : ''}">
        <strong>${html(entry.activation)} · ${html(simulatedTime(entry.logical_time))} · ${html(entry.status)}</strong>
        <small>${html(String(entry.participant_kind || 'person').replaceAll('_',' '))} · activated by ${html(causeSummary(entry.activation_causes) || 'legacy schedule')} · ${html(entry.model_call_count || 0)} model call(s)</small>
        <p>${html(entry.orientation || 'No private orientation was recorded.')}</p>
        <details>
          <summary>${entry.observations.length} observations · ${entry.actions.length} actions</summary>
          <pre>${html(JSON.stringify({
            activation_causes:entry.activation_causes,
            scheduled_update_before:entry.scheduled_update_before,
            update_schedule:entry.update_schedule,
            observations:entry.observations,
            actions:entry.actions,
          }, null, 2))}</pre>
        </details>
      </article>`
  }).join('') : '<p class="muted">No retained activations for this participant.</p>'
}

function drawGraphLines(edges) {
  const graph = $('#graph')
  const svg = graph.querySelector('.graph-lines')
  if (!svg) return
  const box = graph.getBoundingClientRect()
  svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`)
  svg.innerHTML = `
    <defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 z"></path>
    </marker></defs>`
  const event = current?.timeline?.[selectedEventIndex]
  edges.forEach((edge, index) => {
    const source = graph.querySelector(`[data-node-id="${CSS.escape(edge.source)}"]`)
    const target = graph.querySelector(`[data-node-id="${CSS.escape(edge.target)}"]`)
    if (!source || !target) return
    const sourceBox = source.getBoundingClientRect()
    const targetBox = target.getBoundingClientRect()
    const x1 = sourceBox.left - box.left + sourceBox.width / 2
    const y1 = sourceBox.top - box.top + sourceBox.height / 2
    const x2 = targetBox.left - box.left + targetBox.width / 2
    const y2 = targetBox.top - box.top + targetBox.height / 2
    const bend = Math.max(30, Math.abs(x2 - x1) * .35) + index % 3 * 8
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path')
    path.setAttribute('d', `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`)
    path.setAttribute('marker-end', 'url(#arrowhead)')
    path.classList.add(`kind-${edge.kind}`)
    path.classList.toggle('disabled', !edge.enabled)
    const routeFocused = edge.routeIds.some((routeId) => event?.focus_edges?.includes(routeId))
    const endpointsFocused = event?.focus_ids?.includes(edge.source) && event?.focus_ids?.includes(edge.target)
    path.classList.toggle('event-focus', routeFocused || endpointsFocused)
    svg.append(path)
  })
}

function flowOrderedNodes(nodes) {
  const firstFocus = new Map()
  current.timeline.forEach((event, index) => {
    event.focus_ids.forEach((nodeId) => {
      if (!firstFocus.has(nodeId)) firstFocus.set(nodeId, index)
    })
  })
  return nodes.map((node, index) => ({node, index})).sort((left, right) => {
    const leftEvent = firstFocus.get(left.node.id) ?? Number.MAX_SAFE_INTEGER
    const rightEvent = firstFocus.get(right.node.id) ?? Number.MAX_SAFE_INTEGER
    return leftEvent - rightEvent || left.index - right.index
  }).map((item) => item.node)
}

function renderGraph() {
  const projection = graphProjection()
  $('#routes').classList.toggle('canvas-replaced', Boolean(window.CyberneticGraph))
  $('#routes').innerHTML = projection.edges.map((edge) => `
    <span class="route ${edge.enabled ? '' : 'disabled'}" data-route-ids="${html(edge.routeIds.join(' '))}">
      <strong>${html(edge.source.replaceAll('_',' '))}</strong> → ${html(edge.target.replaceAll('_',' '))}
      ${edge.kind === 'mechanism_binding'
        ? '<small>declared input binding</small>'
        : edge.kind === 'information_lineage'
          ? '<small>information lineage</small>'
        : edge.kind === 'information_location'
          ? '<small>information carrier</small>'
        : edge.routeIds.length > 1 ? `<small>${edge.routeIds.length} exact routes</small>` : ''}
    </span>`).join('') || '<span class="muted">No external route is visible at this scale.</span>'
  const graph = $('#graph')
  if (window.CyberneticGraph) {
    graph.classList.add('react-canvas-host')
    const authoredBoundary = selectedScale === 'exact'
      ? (current.boundaries || [])[0] || null
      : null
    const snapshot = boundarySnapshot(authoredBoundary)
    window.CyberneticGraph.render(graph, {
      nodes:projection.nodes,
      edges:projection.edges,
      event:current?.timeline?.[selectedEventIndex] || null,
      world:worldProjection(),
      viewMode:selectedGraphView,
      analyticalScaleHelp:runtimeConfig.live_options?.help?.analytical_scale || 'Analytical scale collapses an execution-inert composite for inspection; it does not create another acting system.',
      boundary:authoredBoundary && snapshot ? {
        id:authoredBoundary.id,
        label:authoredBoundary.label,
        description:authoredBoundary.description,
        executor:false,
        memberIds:snapshot.member_ids,
        hiddenFacts:snapshot.hidden_fact_count,
        hiddenInformation:snapshot.hidden_information_count,
        internalRoutes:snapshot.internal_route_ids.length,
      } : null,
      collapsedBoundaryId:selectedScale === 'exact' ? null : selectedScale,
      selectedNodeId,
      selectedEdgeId,
      onSelectNode:(nodeId) => showNode(nodeId),
      onSelectEdge:(edge) => showEdge(edge),
      onToggleBoundary:(boundaryId) => {
        selectedScale = selectedScale === 'exact' ? boundaryId : 'exact'
        selectedNodeId = null
        selectedEdgeId = null
        renderScaleControls()
        selectEvent(selectedEventIndex)
      },
    })
    return
  }
  graph.classList.remove('react-canvas-host')
  graph.innerHTML = '<svg class="graph-lines" aria-hidden="true"></svg>'
  flowOrderedNodes(projection.nodes).forEach((node) => {
    const button = document.createElement('button')
    button.className = 'node'
    button.dataset.kind = node.kind
    button.dataset.nodeId = node.id
    button.innerHTML = `<span>${html(node.kind.replaceAll('_',' '))}</span><strong>${html(node.label)}</strong><small>${html(node.description)}</small>`
    button.onclick = () => showNode(node.id)
    graph.append(button)
  })
  const event = current?.timeline?.[selectedEventIndex]
  const boundary = selectedBoundary()
  document.querySelectorAll('.node').forEach((button) => {
    const exactFocus = event?.focus_ids?.includes(button.dataset.nodeId)
    const boundaryFocus = button.dataset.nodeId === boundary?.id && event?.boundary_ids?.includes(boundary.id)
    button.classList.toggle('event-focus', exactFocus || boundaryFocus)
  })
  document.querySelectorAll('.route').forEach((route) => {
    const ids = route.dataset.routeIds.split(' ').filter(Boolean)
    route.classList.toggle('event-focus', ids.some((id) => event?.focus_edges?.includes(id)))
  })
  requestAnimationFrame(() => drawGraphLines(projection.edges))
}

function renderProjectionControls() {
  const hasWorld = Boolean(current?.world)
  $('#spatial-layout').disabled = !hasWorld
  $('#spatial-layout').classList.toggle('active', selectedGraphView === 'world')
  $('#causal-layout').classList.toggle('active', selectedGraphView === 'causal')
  $('#spatial-layout').setAttribute('aria-pressed', String(selectedGraphView === 'world'))
  $('#causal-layout').setAttribute('aria-pressed', String(selectedGraphView === 'causal'))
  $('#projection-help').textContent = !hasWorld
    ? 'This scenario has no authored places or spatial topology yet, so only its causal flow can be shown.'
    : selectedGraphView === 'world'
      ? 'Spatial layout shows authored places, occupants, and physical links. Adjacency does not itself grant permission or traversal.'
      : 'Causal flow shows retained information routes, actions, records, and mechanisms. It does not imply physical proximity.'
}

function causalMoments() {
  if (current?.moments?.length) return current.moments
  const activations = [...new Set((current?.traces || []).map((trace) => trace.activation))]
  return activations.map((activation, index) => {
    const traces = current.traces.filter((trace) => trace.activation === activation)
    const eventIds = current.timeline.filter((event) => event.activation === activation).map((event) => event.event_id)
    return {
      moment:index + 1,
      activation,
      logical_time:traces[0]?.logical_time ?? index,
      participants:traces.map((trace) => trace.person),
      event_ids:eventIds,
      representative_event_index:Math.max(0, current.timeline.findIndex((event) => event.event_id === eventIds[0])),
      silent:eventIds.length === 0,
    }
  })
}

function selectMoment(index) {
  const moments = causalMoments()
  if (!moments.length) return
  selectedMomentIndex = Math.max(0, Math.min(index, moments.length - 1))
  const moment = moments[selectedMomentIndex]
  const eventIndex = moment.event_ids.length
    ? current.timeline.findIndex((event) => event.event_id === moment.event_ids[0])
    : moment.representative_event_index
  selectEvent(Math.max(0, eventIndex), moment.activation)
}

function selectEvent(index, momentActivation = null) {
  if (!current?.timeline?.length) return
  selectedEventIndex = Math.max(0, Math.min(index, current.timeline.length - 1))
  const event = current.timeline[selectedEventIndex]
  const moments = causalMoments()
  const activation = momentActivation || event.activation
  const momentIndex = Math.max(0, moments.findIndex((moment) => moment.activation === activation))
  const moment = moments[momentIndex]
  selectedMomentIndex = momentIndex
  $('#event-slider').value = selectedMomentIndex
  $('#event-count').textContent = `${selectedMomentIndex + 1} / ${moments.length} moments · ${simulatedTime(moment?.logical_time)}`
  $('#previous-event').disabled = selectedMomentIndex === 0
  $('#next-event').disabled = selectedMomentIndex === moments.length - 1
  const exactBelongsToMoment = event.activation === activation
  $('#event-detail').innerHTML = exactBelongsToMoment ? `
    <div><span class="event-kind">${html(event.kind.replaceAll('_',' '))}</span><span>${html(simulatedTime(event.logical_time))}</span><span>revision ${html(event.state_revision)}</span>${event.activation ? `<span>${html(event.activation)}</span>` : ''}</div>
    <h3>${html(event.summary)}</h3>
    <small>${html(event.event_id)}</small>` : `
    <div><span class="event-kind">No committed event</span><span>${html(simulatedTime(moment?.logical_time))}</span><span>${html(activation)}</span></div>
    <h3>Every participant remained silent in this causal moment.</h3>
    <small>The map remains at the latest preceding exact event.</small>`
  const accountEvent = exactBelongsToMoment ? event : {...event, activation, person:null}
  renderStepAccount(accountEvent)
  const momentEventIds = moment?.event_ids || []
  $('#moment-events').innerHTML = momentEventIds.length
    ? momentEventIds.map((eventId) => {
        const exact = current.timeline.find((item) => item.event_id === eventId)
        return `<button data-event-id="${html(eventId)}" class="${eventId === event.event_id ? 'active' : ''}">${html(exact?.kind?.replaceAll('_',' ') || eventId)}</button>`
      }).join('')
    : '<span class="muted">No exact event was committed in this moment.</span>'
  document.querySelectorAll('#moment-events button').forEach((button) => {
    button.onclick = () => {
      const exactIndex = current.timeline.findIndex((item) => item.event_id === button.dataset.eventId)
      if (exactIndex >= 0) selectEvent(exactIndex, activation)
    }
  })
  document.querySelectorAll('.timeline-marker').forEach((marker) => marker.classList.toggle('active', Number(marker.dataset.index) === selectedMomentIndex))
  document.querySelectorAll('.story-event').forEach((button) => button.classList.toggle('active', button.dataset.eventId === event.event_id))
  renderScaleControls()
  renderGraph()

  const world = worldProjection()
  const worldNodes = selectedGraphView === 'world' && world
    ? [
        ...world.places.map((place) => ({...place, kind:'place'})),
        ...nodesAtSelectedEvent().filter((node) =>
          event.spatial_focus_ids?.includes(node.id)
        ),
      ].filter((node) => event.spatial_focus_ids?.includes(node.id))
    : []
  const focusedNodes = selectedGraphView === 'world'
    ? worldNodes
    : graphProjection().nodes.filter((node) =>
        event.focus_ids.includes(node.id)
        || (node.kind === 'analytical_boundary' && event.boundary_ids?.includes(node.id))
      )
  $('#inspector').innerHTML = focusedNodes.length
    ? `<span class="eyebrow">${selectedGraphView === 'world' ? 'Spatial evidence' : 'Focused by selected event'}</span><h2>${focusedNodes.length} participating ${focusedNodes.length === 1 ? 'referent' : 'referents'}</h2>
       <div class="focus-list">${focusedNodes.map((node) => `<button data-node-id="${html(node.id)}">${html(node.kind)} · ${html(node.label)}</button>`).join('')}</div>`
    : selectedGraphView === 'world' && event.spatial_link_ids?.length
      ? `<span class="eyebrow">Spatial evidence</span><h2>${html(event.spatial_link_ids.length)} topological link</h2><p>The selected event read or changed state across ${html(event.spatial_link_ids.join(', '))}.</p>`
      : '<p class="muted">This event does not directly identify a retained world entity.</p>'
  document.querySelectorAll('.focus-list button').forEach((button) => {
    button.onclick = () => showNode(button.dataset.nodeId)
  })

  if (event.person) showTraceInPlace(event.person)
  else if (selectedPerson) showTraceInPlace(selectedPerson)
}

function renderStepAccount(event) {
  const narrations = current.narration?.moments || current.narration?.turns || []
  const narration = narrations.find((moment) => moment.activation === event.activation)
  const trace = event.person && event.activation
    ? current.traces.find((entry) => entry.person === event.person && entry.activation === event.activation)
    : null
  const person = event.person?.replaceAll('_', ' ')
  const exactProcess = trace?.participant_kind === 'state_machine'
  const title = {
    action_attempted:exactProcess ? 'An exact process emitted an action' : 'A person chose an action',
    mechanism_executed:'An exact mechanism evaluated it',
    effect_routed:'An effect moved along a declared route',
    observation_delivered:'Someone received an observation',
    state_committed:'The world state changed',
  }[event.kind] || event.kind.replaceAll('_', ' ')
  if (narration) {
    const momentNumber = narration.moment || narration.turn
    const participants = narration.participants || [narration.person || 'system']
    $('#step-account-title').textContent = `Causal moment ${momentNumber} · ${simulatedTime(narration.logical_time)} · ${participants.map((item) => String(item).replaceAll('_', ' ')).join(' + ')}`
    $('#step-account-body').textContent = narration.narrative
    $('#step-account-source').textContent = `Live LLM narrator · grounded in ${narration.source_event_ids.join(', ')}. It received this moment’s trace and the earlier moment narratives.`
  } else if (exactProcess) {
    $('#step-account-title').textContent = title
    const name = person ? `${person[0].toUpperCase()}${person.slice(1)}` : 'The exact process'
    $('#step-account-body').textContent = `${name} advanced from retained exact process state. ${event.summary}`
    $('#step-account-source').textContent = 'This transition came from the deterministic process controller and exact mechanism trace; it made no LLM call.'
  } else if (trace?.orientation && current.execution === 'live') {
    $('#step-account-title').textContent = title
    const name = person ? `${person[0].toUpperCase()}${person.slice(1)}` : 'The active person'
    $('#step-account-body').textContent = `${name} read the situation as: “${trace.orientation}” ${event.summary}`
    $('#step-account-source').textContent = current.narration?.status === 'unavailable'
      ? 'The live narrator was unavailable, so this is the acting agent’s own LLM orientation paired with the exact recorded event.'
      : 'This run predates causal-moment narration, so this is the acting agent’s own LLM orientation paired with the exact recorded event.'
  } else if (trace?.orientation) {
    $('#step-account-title').textContent = title
    const name = person ? `${person[0].toUpperCase()}${person.slice(1)}` : 'The active person'
    $('#step-account-body').textContent = `${name} acted from available observations and remembered context. ${event.summary}`
    $('#step-account-source').textContent = 'This is a zero-cost reference account derived from the exact scripted trace, not a live LLM narration.'
  } else {
    $('#step-account-title').textContent = title
    $('#step-account-body').textContent = event.summary
    $('#step-account-source').textContent = 'This is an exact mechanism or delivery event, so it has no separate agent narration.'
  }
  document.querySelectorAll('.turn-narrative').forEach((card) => {
    card.classList.toggle('active', card.dataset.activation === event.activation)
  })
}

function renderTurnNarratives() {
  const narration = current.narration || {}
  const container = $('#turn-narratives')
  const moments = narration.moments || narration.turns || []
  if (narration.status === 'completed' && moments.length) {
    container.innerHTML = moments.map((moment) => {
      const momentNumber = moment.moment || moment.turn
      const participants = moment.participants || [moment.person || 'system']
      return `
      <button class="turn-narrative" data-activation="${html(moment.activation)}">
        <span>Causal moment ${html(momentNumber)} · ${html(simulatedTime(moment.logical_time))} · ${html(participants.map((item) => String(item).replaceAll('_',' ')).join(' + '))}</span>
        <p>${html(moment.narrative)}</p>
        <small>${html((moment.source_event_ids || []).join(' · '))}</small>
      </button>`
    }).join('')
    document.querySelectorAll('.turn-narrative').forEach((button) => {
      button.onclick = () => {
        const index = causalMoments().findIndex((moment) => moment.activation === button.dataset.activation)
        if (index >= 0) selectMoment(index)
      }
    })
    return
  }
  const reason = narration.reason || 'No causal-moment narration was retained for this run.'
  container.innerHTML = `<p class="muted">${html(reason)}</p>`
}

function renderTimeline(run) {
  const timeline = run.timeline || []
  const moments = causalMoments()
  $('#event-slider').max = Math.max(0, moments.length - 1)
  $('#timeline-track').innerHTML = ''
  moments.forEach((moment, index) => {
    const marker = document.createElement('button')
    marker.className = 'timeline-marker'
    marker.dataset.index = index
    const people = moment.participants.map((person) => person.replaceAll('_',' ')).join(' + ')
    const causes = Object.values(moment.activation_causes || {}).flat()
    marker.title = `Causal moment ${index + 1}, ${simulatedTime(moment.logical_time)}: ${people}; ${causeSummary(causes)}${moment.silent ? ' (silent)' : ''}`
    marker.setAttribute('aria-label', marker.title)
    marker.onclick = () => selectMoment(index)
    $('#timeline-track').append(marker)
  })
  if (moments.length) {
    selectMoment(0)
  }
  else {
    $('#event-count').textContent = 'No causal events'
    $('#event-detail').innerHTML = `<h3>${html(run.error || 'This retained run has no completed event trace.')}</h3>`
  }
}

function render(run) {
  current = {
    nodes: [], snapshots: {}, edges: [], boundaries: [], timeline: [], moments: [], traces: [], events: [],
    story: {headline: run.status, summary: run.error || 'No final account was retained.', steps: []},
    narration: {status:'not_requested', moments:[]},
    model_calls: 0, cost: 0,
    ...run,
  }
  selectedEventIndex = 0
  selectedMomentIndex = 0
  selectedPerson = null
  selectedScale = 'exact'
  selectedGraphView = current.world && current.scenario !== 'purchase_payment'
    ? 'world'
    : 'causal'
  selectedNodeId = null
  selectedEdgeId = null
  if (scenarioCatalog[current.scenario]) {
    $('#scenario').value = current.scenario
    configureScenario(current.scenario)
    if ([...$('#arm').options].some((option) => option.value === current.arm)) {
      $('#arm').value = current.arm
    }
    describeCondition()
  }
  $('#result').hidden = false
  renderProjectionControls()
  $('#result-status').textContent = `${current.status} · ${String(current.scenario || '').replaceAll('_',' ')} · ${String(current.profile || '').replaceAll('_',' ')} · ${String(current.arm || '').replaceAll('_',' ')}`
  $('#result-cost').textContent = `${current.model_calls} model calls (${current.agent_model_calls ?? current.model_calls} agent, ${current.narration_model_calls ?? 0} narrator) · $${Number(current.cost).toFixed(6)} · ${current.run_id}`
  const llm = current.llm_configuration
  $('#run-config-readout').innerHTML = llm ? `
    <strong>Effective live configuration</strong>
    <span>${html(llm.model)}</span>
    <span>${html(llm.agent_reasoning_effort)} agent reasoning · ${html(llm.narrator_reasoning_effort)} narrator reasoning</span>
    <span>$${Number(llm.max_total_cost).toFixed(2)} authorized · $${Number(current.cost).toFixed(6)} observed</span>
    <small>${html(String(llm.selection_basis).replaceAll('_',' '))} · llm_client ${html(llm.llm_client_revision)}</small>
  ` : `
    <strong>Reference execution</strong>
    <span>Fixed zero-call policies · $0 observed</span>
  `
  $('#story-headline').textContent = current.story.headline
  $('#story-summary').textContent = current.story.summary
  $('#story-steps').innerHTML = ''
  current.story.steps.forEach((step) => {
    const item = document.createElement('li')
    const button = document.createElement('button')
    button.className = 'story-event'
    button.dataset.eventId = step.event_id
    button.textContent = step.summary
    button.onclick = () => {
      const index = current.timeline.findIndex((event) => event.event_id === step.event_id)
      if (index >= 0) selectEvent(index)
    }
    item.append(button)
    $('#story-steps').append(item)
  })
  renderScaleControls()
  renderTurnNarratives()
  const people = [...new Set(current.traces.map((entry) => entry.person))]
  const participantTabs = people.map((person) => {
    const kind = current.traces.find((entry) => entry.person === person)?.participant_kind
    const suffix = kind === 'state_machine' ? ' · exact process' : ''
    return `<button data-person="${html(person)}">${html(person.replaceAll('_',' '))}${html(suffix)}</button>`
  })
  const compositeTabs = (current.boundaries || []).map((boundary) =>
    `<button data-person="${html(boundary.id)}" title="Analytical composite; it summarizes members but does not act">${html(boundary.label)} · composite</button>`
  )
  $('#trace-tabs').innerHTML = [...participantTabs, ...compositeTabs].join('')
  $('#trace').style.minHeight = ''
  document.querySelectorAll('#trace-tabs button').forEach((button) => {
    button.onclick = () => showTraceInPlace(button.dataset.person)
  })
  if (people.length) showTrace(people[0])
  else $('#trace').innerHTML = '<p class="muted">No completed participant traces were retained.</p>'
  renderTimeline(current)
  $('#raw').textContent = JSON.stringify(current, null, 2)
}

$('#event-slider').oninput = (event) => selectMoment(Number(event.target.value))
$('#previous-event').onclick = () => selectMoment(selectedMomentIndex - 1)
$('#next-event').onclick = () => selectMoment(selectedMomentIndex + 1)
$('#simulation-tab').onclick = () => setWorkspaceView('simulation')
$('#history-tab').onclick = () => setWorkspaceView('history')
$('#readme-tab').onclick = () => setWorkspaceView('readme')
$('#scenario').onchange = (event) => configureScenario(event.target.value)
$('#arm').onchange = describeCondition
$('#spatial-layout').onclick = () => {
  if (!current?.world) return
  selectedGraphView = 'world'
  selectedNodeId = null
  selectedEdgeId = null
  renderProjectionControls()
  renderGraph()
}
$('#causal-layout').onclick = () => {
  if (!current) return
  selectedGraphView = 'causal'
  selectedNodeId = null
  selectedEdgeId = null
  renderProjectionControls()
  renderGraph()
}
$('#live').onchange = () => {
  $('#run').textContent = $('#live').checked ? 'Play live simulation' : 'Play reference simulation'
  configureLiveControls()
}
$('#model').onchange = () => {
  configureReasoningChoices()
  updateAuthorizationPreview()
}
$('#reasoning').onchange = () => {
  updateReasoningHelp()
  updateAuthorizationPreview()
}
$('#max-cost').oninput = updateAuthorizationPreview
document.querySelectorAll('.help-button').forEach((button) => {
  button.onclick = () => {
    const target = document.getElementById(button.dataset.help)
    const expanded = button.getAttribute('aria-expanded') === 'true'
    button.setAttribute('aria-expanded', String(!expanded))
    target.hidden = expanded
  }
})

$('#run').onclick = async () => {
  $('#run').disabled = true
  $('#run-status').textContent = 'Running…'
  activeRunId = `run_${crypto.getRandomValues(new Uint32Array(3)).join('').slice(0, 12)}`
  const pausable = $('#scenario').value === 'service_desk'
  $('#pause').hidden = !pausable
  try {
    const body = await request('/api/runs', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        scenario:$('#scenario').value,
        cognition_profile:'position_context',
        arm_id:$('#arm').value,
        execution:$('#live').checked ? 'live' : 'scripted',
        run_id:activeRunId,
        ...($('#live').checked ? {
          llm_options:{
            model:$('#model').value,
            agent_reasoning_effort:$('#reasoning').value,
            max_total_cost:Number($('#max-cost').value),
          },
        } : {}),
      }),
    })
    render(body)
    const url = new URL(window.location)
    url.searchParams.set('run', body.run_id)
    window.history.replaceState({}, '', url)
    await loadHistory()
    $('#run-status').textContent = body.status === 'paused' ? 'Paused' : 'Completed'
    $('#resume').hidden = body.status !== 'paused'
  } catch (error) {
    $('#run-status').textContent = error.message
    await loadHistory()
  } finally {
    $('#run').disabled = false
    $('#pause').hidden = true
  }
}

$('#pause').onclick = async () => {
  if (!activeRunId) return
  $('#pause').disabled = true
  try {
    await request(`/api/runs/${activeRunId}/pause`, {method:'POST'})
    $('#run-status').textContent = 'Pause requested; finishing this causal moment…'
  } catch (error) {
    $('#run-status').textContent = error.message
  }
}

$('#resume').onclick = async () => {
  if (!current?.run_id) return
  $('#resume').disabled = true
  $('#run-status').textContent = 'Resuming…'
  try {
    const body = await request(`/api/runs/${current.run_id}/resume`, {method:'POST'})
    render(body)
    $('#run-status').textContent = 'Completed'
    $('#resume').hidden = true
    await loadHistory()
  } catch (error) {
    $('#run-status').textContent = error.message
  } finally {
    $('#resume').disabled = false
  }
}

Promise.all([loadConfig(), loadHistory()])
  .then(async () => {
    const retainedId = new URLSearchParams(window.location.search).get('run')
    if (retainedId) await openRetained(retainedId)
  })
  .catch((error) => { $('#run-status').textContent = error.message })

window.addEventListener('resize', () => {
  if (current) drawGraphLines(graphProjection().edges)
})
