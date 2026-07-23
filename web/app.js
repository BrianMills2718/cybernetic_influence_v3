const $ = (selector) => document.querySelector(selector)
const html = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
  '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;',
})[character])

let current = null
let selectedEventIndex = 0
let selectedPerson = null

async function request(url, options = {}) {
  const response = await fetch(url, options)
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

async function loadConfig() {
  const config = await request('/api/config')
  $('#cost-details').textContent =
    `${config.model} · ${config.reasoning_effort} reasoning · up to ${config.maximum_live_calls} calls · $${config.maximum_live_cost.toFixed(2)} cap. Scripted reference runs cost $0.`
  $('#live').disabled = !config.live_authorized
  if (!config.live_authorized) $('#live').parentElement.title = 'Start the server with CYBERNETIC_INFLUENCE_LIVE=1 to enable live agents.'
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
        <span>${html(run.arm?.replaceAll('_',' '))} · ${html(run.profile?.replaceAll('_',' '))}</span>
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

function showNode(node) {
  document.querySelectorAll('.node').forEach((button) => button.classList.toggle('selected', button.dataset.nodeId === node.id))
  $('#inspector').innerHTML = `
    <span class="eyebrow">${html(node.kind)}</span>
    <h2>${html(node.label)}</h2>
    <p>${html(node.description)}</p>
    <pre>${html(JSON.stringify(node.state, null, 2))}</pre>`
}

function showTrace(person) {
  selectedPerson = person
  document.querySelectorAll('.tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
  const selectedEvent = current?.timeline?.[selectedEventIndex]
  const entries = (current?.traces || []).filter((entry) => entry.person === person)
  $('#trace').innerHTML = entries.map((entry) => {
    const matches = selectedEvent && entry.logical_time === selectedEvent.logical_time
      && (!selectedEvent.person || selectedEvent.person === person)
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

function selectEvent(index) {
  if (!current?.timeline?.length) return
  selectedEventIndex = Math.max(0, Math.min(index, current.timeline.length - 1))
  const event = current.timeline[selectedEventIndex]
  $('#event-slider').value = selectedEventIndex
  $('#event-count').textContent = `${selectedEventIndex + 1} / ${current.timeline.length}`
  $('#previous-event').disabled = selectedEventIndex === 0
  $('#next-event').disabled = selectedEventIndex === current.timeline.length - 1
  $('#event-detail').innerHTML = `
    <div><span class="event-kind">${html(event.kind.replaceAll('_',' '))}</span><span>time ${html(event.logical_time)}</span></div>
    <h3>${html(event.summary)}</h3>
    <small>${html(event.event_id)}</small>`
  document.querySelectorAll('.timeline-marker').forEach((marker) => marker.classList.toggle('active', Number(marker.dataset.index) === selectedEventIndex))
  document.querySelectorAll('.story-event').forEach((button) => button.classList.toggle('active', button.dataset.eventId === event.event_id))
  document.querySelectorAll('.node').forEach((button) => button.classList.toggle('event-focus', event.focus_ids.includes(button.dataset.nodeId)))
  document.querySelectorAll('.route').forEach((route) => route.classList.toggle('event-focus', event.focus_edges.includes(route.dataset.edgeId)))

  const focusedNodes = current.nodes.filter((node) => event.focus_ids.includes(node.id))
  $('#inspector').innerHTML = focusedNodes.length
    ? `<span class="eyebrow">Focused by selected event</span><h2>${focusedNodes.length} participating ${focusedNodes.length === 1 ? 'entity' : 'entities'}</h2>
       <div class="focus-list">${focusedNodes.map((node) => `<button data-node-id="${html(node.id)}">${html(node.kind)} · ${html(node.label)}</button>`).join('')}</div>`
    : '<p class="muted">This event does not directly identify a retained world entity.</p>'
  document.querySelectorAll('.focus-list button').forEach((button) => {
    button.onclick = () => showNode(current.nodes.find((node) => node.id === button.dataset.nodeId))
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
    nodes: [], edges: [], timeline: [], traces: [], events: [],
    story: {headline: run.status, summary: run.error || 'No final account was retained.', steps: []},
    model_calls: 0, cost: 0,
    ...run,
  }
  selectedEventIndex = 0
  selectedPerson = null
  $('#result').hidden = false
  $('#result-status').textContent = `${current.status} · ${String(current.profile || '').replaceAll('_',' ')} · ${String(current.arm || '').replaceAll('_',' ')}`
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
  $('#routes').innerHTML = current.edges.map((edge) => `
    <span class="route ${edge.enabled ? '' : 'disabled'}" data-edge-id="${html(edge.id)}">
      <strong>${html(edge.source.replaceAll('_',' '))}</strong> → ${html(edge.target.replaceAll('_',' '))}
    </span>`).join('')
  $('#graph').innerHTML = ''
  current.nodes.forEach((node) => {
    const button = document.createElement('button')
    button.className = 'node'
    button.dataset.kind = node.kind
    button.dataset.nodeId = node.id
    button.innerHTML = `<span>${html(node.kind)}</span><strong>${html(node.label)}</strong><small>${html(node.description)}</small>`
    button.onclick = () => showNode(node)
    $('#graph').append(button)
  })
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

$('#run').onclick = async () => {
  $('#run').disabled = true
  $('#run-status').textContent = 'Running…'
  try {
    const body = await request('/api/runs', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
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
