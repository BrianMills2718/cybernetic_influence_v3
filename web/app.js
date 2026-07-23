const $ = (selector) => document.querySelector(selector)
const html = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
})[character])

let current = null
let selectedEventIndex = 0
let selectedPerson = null
let selectedScale = 'exact'
let scenarioCatalog = {}

async function request(url, options = {}) {
  const response = await fetch(url, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

async function loadConfig() {
  const config = await request('/api/config')
  scenarioCatalog = config.scenarios || {}
  $('#scenario').innerHTML = Object.entries(scenarioCatalog).map(([id, item]) =>
    `<option value="${html(id)}">${html(item.label)}</option>`
  ).join('')
  $('#scenario').value = config.scenario
  configureScenario(config.scenario)
  $('#cost-details').textContent =
    `${config.model} · ${config.reasoning_effort} reasoning · up to ${config.maximum_live_calls} calls · $${config.maximum_live_cost.toFixed(2)} cap. Scripted reference runs cost $0.`
  $('#live').disabled = !config.live_authorized
  if (!config.live_authorized) $('#live').parentElement.title = 'Start the server with CYBERNETIC_INFLUENCE_LIVE=1 to enable live agents.'
}

function configureScenario(scenarioId) {
  const selected = scenarioCatalog[scenarioId]
  if (!selected) return
  const profileLabels = {
    position_context:'Personal dispositions + remembered position',
    procedural_control:'Explicit procedural instructions',
  }
  $('#profile').innerHTML = selected.profiles.map((profile) =>
    `<option value="${html(profile)}">${html(profileLabels[profile] || profile.replaceAll('_',' '))}</option>`
  ).join('')
  $('#arm').innerHTML = selected.arms.map((arm) =>
    `<option value="${html(arm.id)}">${html(arm.label)}</option>`
  ).join('')
  $('#scenario-title').textContent = selected.label
  $('#scenario-description').textContent = scenarioId === 'physical_access'
    ? 'Separate credential proof, policy authorization, latch operation, physical crossing, and observed feedback.'
    : 'Run people, information, records, connections, and exact mechanisms together.'
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

function graphProjection() {
  const exactNodes = nodesAtSelectedEvent()
  if (selectedScale === 'exact') {
    return {
      nodes: exactNodes,
      edges: current.edges.map((edge) => ({...edge, routeIds:[edge.id]})),
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
  current.edges.forEach((edge) => {
    const source = memberIds.has(edge.source) ? boundary.id : edge.source
    const target = memberIds.has(edge.target) ? boundary.id : edge.target
    if (source === target) return
    const key = `${source}|${target}|${edge.enabled}`
    if (!grouped.has(key)) {
      grouped.set(key, {
        id:`coarse_${grouped.size}`,
        source,
        target,
        enabled:edge.enabled,
        description:'Coarse route backed by exact declared connections.',
        routeIds:[],
      })
    }
    grouped.get(key).routeIds.push(edge.id)
  })
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
  $('#scale-tabs').innerHTML = [
    `<button data-scale="exact" class="${selectedScale === 'exact' ? 'active' : ''}">Exact components</button>`,
    ...boundaries.map((boundary) =>
      `<button data-scale="${html(boundary.id)}" class="${selectedScale === boundary.id ? 'active' : ''}">${html(boundary.label)}</button>`
    ),
  ].join('')
  document.querySelectorAll('#scale-tabs button').forEach((button) => {
    button.onclick = () => {
      selectedScale = button.dataset.scale
      renderScaleControls()
      renderGraph()
      selectEvent(selectedEventIndex)
    }
  })
  const snapshot = boundarySnapshot()
  $('#scale-loss').textContent = snapshot
    ? `Coarse analytical view: ${snapshot.selectable_member_count} selectable components and ${snapshot.internal_route_ids.length} internal routes are hidden; ${snapshot.hidden_fact_count} state facts and ${snapshot.hidden_information_count} information tokens are summarized. The boundary does not act.`
    : boundaries.length
      ? 'Exact view: every retained component and declared connection remains selectable.'
      : 'Exact view: this older retained run has no authored analytical boundary.'
}

function showBoundary(boundaryId) {
  const boundary = (current?.boundaries || []).find((item) => item.id === boundaryId)
  const snapshot = boundarySnapshot(boundary)
  const event = current?.timeline?.[selectedEventIndex]
  if (!boundary || !snapshot) return
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
  const event = current?.timeline?.[selectedEventIndex]
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
  $('#inspector').innerHTML = `
    <span class="eyebrow">${html(node.kind)} · revision ${html(event?.state_revision)}</span>
    <h2>${html(node.label)}</h2>
    <p>${html(node.description)}</p>
    <pre>${html(JSON.stringify(node.state, null, 2))}</pre>`
}

function showTrace(person) {
  selectedPerson = person
  document.querySelectorAll('#trace-tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
  const selectedEvent = current?.timeline?.[selectedEventIndex]
  const entries = (current?.traces || []).filter((entry) => entry.person === person)
  $('#trace').innerHTML = entries.map((entry) => {
    const matches = selectedEvent?.activation === entry.activation
    return `
      <article class="trace-step ${matches ? 'event-match' : ''}">
        <strong>${html(entry.activation)} · time ${html(entry.logical_time)} · ${html(entry.status)}</strong>
        <p>${html(entry.orientation || 'No private orientation was recorded.')}</p>
        <details>
          <summary>${entry.observations.length} observations · ${entry.actions.length} actions</summary>
          <pre>${html(JSON.stringify({observations:entry.observations, actions:entry.actions}, null, 2))}</pre>
        </details>
      </article>`
  }).join('') || '<p class="muted">No retained activations for this person.</p>'
  document.querySelector('.trace-step.event-match')?.scrollIntoView({behavior:'smooth', block:'nearest'})
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
    path.classList.toggle('disabled', !edge.enabled)
    path.classList.toggle('event-focus', edge.routeIds.some((routeId) => event?.focus_edges?.includes(routeId)))
    svg.append(path)
  })
}

function renderGraph() {
  const projection = graphProjection()
  $('#routes').innerHTML = projection.edges.map((edge) => `
    <span class="route ${edge.enabled ? '' : 'disabled'}" data-route-ids="${html(edge.routeIds.join(' '))}">
      <strong>${html(edge.source.replaceAll('_',' '))}</strong> → ${html(edge.target.replaceAll('_',' '))}
      ${edge.routeIds.length > 1 ? `<small>${edge.routeIds.length} exact routes</small>` : ''}
    </span>`).join('') || '<span class="muted">No external route is visible at this scale.</span>'
  const graph = $('#graph')
  graph.innerHTML = '<svg class="graph-lines" aria-hidden="true"></svg>'
  projection.nodes.forEach((node) => {
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

function selectEvent(index) {
  if (!current?.timeline?.length) return
  selectedEventIndex = Math.max(0, Math.min(index, current.timeline.length - 1))
  const event = current.timeline[selectedEventIndex]
  $('#event-slider').value = selectedEventIndex
  $('#event-count').textContent = `${selectedEventIndex + 1} / ${current.timeline.length}`
  $('#previous-event').disabled = selectedEventIndex === 0
  $('#next-event').disabled = selectedEventIndex === current.timeline.length - 1
  $('#event-detail').innerHTML = `
    <div><span class="event-kind">${html(event.kind.replaceAll('_',' '))}</span><span>time ${html(event.logical_time)}</span><span>revision ${html(event.state_revision)}</span>${event.activation ? `<span>${html(event.activation)}</span>` : ''}</div>
    <h3>${html(event.summary)}</h3>
    <small>${html(event.event_id)}</small>`
  document.querySelectorAll('.timeline-marker').forEach((marker) => marker.classList.toggle('active', Number(marker.dataset.index) === selectedEventIndex))
  document.querySelectorAll('.story-event').forEach((button) => button.classList.toggle('active', button.dataset.eventId === event.event_id))
  renderScaleControls()
  renderGraph()

  const focusedNodes = graphProjection().nodes.filter((node) =>
    event.focus_ids.includes(node.id)
    || (node.kind === 'analytical_boundary' && event.boundary_ids?.includes(node.id))
  )
  $('#inspector').innerHTML = focusedNodes.length
    ? `<span class="eyebrow">Focused by selected event</span><h2>${focusedNodes.length} participating ${focusedNodes.length === 1 ? 'entity' : 'entities'}</h2>
       <div class="focus-list">${focusedNodes.map((node) => `<button data-node-id="${html(node.id)}">${html(node.kind)} · ${html(node.label)}</button>`).join('')}</div>`
    : '<p class="muted">This event does not directly identify a retained world entity.</p>'
  document.querySelectorAll('.focus-list button').forEach((button) => {
    button.onclick = () => showNode(button.dataset.nodeId)
  })

  if (event.person) showTrace(event.person)
  else if (selectedPerson) showTrace(selectedPerson)
}

function renderTimeline(run) {
  const timeline = run.timeline || []
  $('#event-slider').max = Math.max(0, timeline.length - 1)
  $('#timeline-track').innerHTML = ''
  timeline.forEach((event, index) => {
    const marker = document.createElement('button')
    marker.className = `timeline-marker kind-${event.kind}`
    marker.dataset.index = index
    marker.title = `${event.kind.replaceAll('_',' ')}: ${event.summary}`
    marker.setAttribute('aria-label', `Event ${index + 1}: ${event.summary}`)
    marker.onclick = () => selectEvent(index)
    $('#timeline-track').append(marker)
  })
  if (timeline.length) {
    const firstAction = timeline.findIndex((event) => event.kind === 'action_attempted')
    selectEvent(firstAction >= 0 ? firstAction : 0)
  }
  else {
    $('#event-count').textContent = 'No causal events'
    $('#event-detail').innerHTML = `<h3>${html(run.error || 'This retained run has no completed event trace.')}</h3>`
  }
}

function render(run) {
  current = {
    nodes: [], snapshots: {}, edges: [], boundaries: [], timeline: [], traces: [], events: [],
    story: {headline: run.status, summary: run.error || 'No final account was retained.', steps: []},
    model_calls: 0, cost: 0,
    ...run,
  }
  selectedEventIndex = 0
  selectedPerson = null
  selectedScale = 'exact'
  if (scenarioCatalog[current.scenario]) {
    $('#scenario').value = current.scenario
    configureScenario(current.scenario)
    if ([...$('#profile').options].some((option) => option.value === current.profile)) {
      $('#profile').value = current.profile
    }
    if ([...$('#arm').options].some((option) => option.value === current.arm)) {
      $('#arm').value = current.arm
    }
  }
  $('#result').hidden = false
  $('#result-status').textContent = `${current.status} · ${String(current.scenario || '').replaceAll('_',' ')} · ${String(current.profile || '').replaceAll('_',' ')} · ${String(current.arm || '').replaceAll('_',' ')}`
  $('#result-cost').textContent = `${current.model_calls} model calls · $${Number(current.cost).toFixed(6)} · ${current.run_id}`
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
  const people = [...new Set(current.traces.map((entry) => entry.person))]
  $('#trace-tabs').innerHTML = people.map((person) => `<button data-person="${html(person)}">${html(person.replaceAll('_',' '))}</button>`).join('')
  document.querySelectorAll('#trace-tabs button').forEach((button) => button.onclick = () => showTrace(button.dataset.person))
  if (people.length) showTrace(people[0])
  else $('#trace').innerHTML = '<p class="muted">No completed person traces were retained.</p>'
  renderTimeline(current)
  $('#raw').textContent = JSON.stringify(current, null, 2)
  $('#result').scrollIntoView({behavior:'smooth', block:'start'})
}

$('#event-slider').oninput = (event) => selectEvent(Number(event.target.value))
$('#previous-event').onclick = () => selectEvent(selectedEventIndex - 1)
$('#next-event').onclick = () => selectEvent(selectedEventIndex + 1)
$('#scenario').onchange = (event) => configureScenario(event.target.value)

$('#run').onclick = async () => {
  $('#run').disabled = true
  $('#run-status').textContent = 'Running…'
  try {
    const body = await request('/api/runs', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        scenario:$('#scenario').value,
        cognition_profile:$('#profile').value,
        arm_id:$('#arm').value,
        execution:$('#live').checked ? 'live' : 'scripted',
      }),
    })
    render(body)
    const url = new URL(window.location)
    url.searchParams.set('run', body.run_id)
    window.history.replaceState({}, '', url)
    await loadHistory()
    $('#run-status').textContent = 'Completed'
  } catch (error) {
    $('#run-status').textContent = error.message
    await loadHistory()
  } finally {
    $('#run').disabled = false
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
