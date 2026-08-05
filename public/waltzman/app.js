'use strict'

const decisionOrder = ['support', 'conditional', 'defer', 'oppose']
const groupOrder = ['all', 'alba', 'borin', 'cyrenia', 'regional']
const groupLabels = {
  all:'All roles',
  alba:'Alba',
  borin:'Borin',
  cyrenia:'Cyrenia',
  regional:'Regional',
}

let dataset = null
const state = {
  view:'compare',
  runId:null,
  round:3,
  personId:'regional_scientific_advisor',
  group:'all',
}

const $ = (selector) => document.querySelector(selector)
const all = (selector) => [...document.querySelectorAll(selector)]

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;')
}

function sentence(value) {
  return String(value || '').replaceAll('_', ' ')
}

function runLabel(run) {
  const count = dataset.runs.filter((item) => item.condition === run.condition).length
  return `${run.condition_label}${count > 1 ? ` ${run.replicate}` : ''}`
}

function countsText(counts) {
  const parts = decisionOrder
    .filter((decision) => Number(counts?.[decision] || 0) > 0)
    .map((decision) => `${counts[decision]} ${sentence(decision)}`)
  return parts.join(' · ') || 'No stances'
}

function categoryText(counts) {
  const entries = Object.entries(counts || {}).sort((left, right) => right[1] - left[1])
  return entries.map(([key, value]) => `${value} ${sentence(key)}`).join(' · ') || 'None reported'
}

function decisionPill(decision) {
  return `<span class="decision-pill decision-${escapeHtml(decision)}">${escapeHtml(sentence(decision))}</span>`
}

function outcomeBadge(run) {
  const approved = run.outcome === 'joint_response_approved'
  return `<span class="outcome-badge ${approved ? 'outcome-approved' : 'outcome-failed'}">${approved ? 'Approved' : 'Not approved'}</span>`
}

function stackedBar(counts, className = 'stacked-bar') {
  return `<div class="${className}" aria-label="${escapeHtml(countsText(counts))}">
    ${decisionOrder.map((decision) => {
      const count = Number(counts?.[decision] || 0)
      return count ? `<span class="bar-${decision}" style="width:${count / 12 * 100}%" title="${count} ${decision}"></span>` : ''
    }).join('')}
  </div>`
}

function currentRun() {
  return dataset.runs.find((run) => run.run_id === state.runId) || dataset.runs[0]
}

function currentRound(run = currentRun()) {
  return run.rounds.find((round) => round.round === state.round) || run.rounds.at(-1)
}

function readStateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const requestedView = params.get('view')
  if (['compare', 'inspect', 'method'].includes(requestedView)) state.view = requestedView
  const requestedRun = params.get('run')
  if (requestedRun && dataset.runs.some((run) => run.run_id === requestedRun)) state.runId = requestedRun
  const requestedRound = Number(params.get('round'))
  if ([1, 2, 3].includes(requestedRound)) state.round = requestedRound
  const requestedPerson = params.get('person')
  if (requestedPerson && dataset.people.some((person) => person.person_id === requestedPerson)) state.personId = requestedPerson
  const requestedGroup = params.get('group')
  if (groupOrder.includes(requestedGroup)) state.group = requestedGroup
}

function syncUrl() {
  const url = new URL(window.location.href)
  url.searchParams.set('view', state.view)
  if (state.view === 'inspect') {
    url.searchParams.set('run', state.runId)
    url.searchParams.set('round', String(state.round))
    url.searchParams.set('person', state.personId)
    if (state.group !== 'all') url.searchParams.set('group', state.group)
    else url.searchParams.delete('group')
  } else {
    for (const key of ['run', 'round', 'person', 'group']) url.searchParams.delete(key)
  }
  window.history.replaceState({}, '', url)
}

function renderRail() {
  $('#scenario-title').textContent = dataset.scenario_title
  $('#scenario-summary').textContent = dataset.scenario_summary
  $('#fact-runs').textContent = dataset.runs.length
  $('#fact-agents').textContent = dataset.agent_count
  $('#fact-calls').textContent = dataset.total_model_calls
  $('#dataset-id').textContent = dataset.dataset_id
}

function renderComparison() {
  const approved = dataset.runs.filter((run) => run.outcome === 'joint_response_approved').length
  const notApproved = dataset.runs.length - approved
  $('#comparison-summary').innerHTML = `
    <span class="comparison-icon" aria-hidden="true">5×</span>
    <div><strong>Five authentic trajectories are loaded for comparison</strong><p>${approved} ended in approval and ${notApproved} ended without approval. The interface does not average these demonstrations into an effect estimate.</p></div>
    <small>${dataset.total_model_calls} retained participant calls</small>`

  $('#trajectory-grid').innerHTML = dataset.runs.map((run) => `
    <button type="button" class="trajectory-card" data-open-run="${escapeHtml(run.run_id)}" aria-label="Inspect ${escapeHtml(runLabel(run))}, ${escapeHtml(run.run_id)}">
      <span class="card-top"><span><h3>${escapeHtml(runLabel(run))}</h3><span class="run-code">${escapeHtml(run.run_id)}</span></span>${outcomeBadge(run)}</span>
      <span class="round-track">
        ${run.rounds.map((round) => `<span class="round-track-row"><span class="round-label">R${round.round}</span>${stackedBar(round.decision_counts)}</span>`).join('')}
      </span>
      <span class="final-line">Final · ${escapeHtml(countsText(run.rounds.at(-1).decision_counts))}</span>
    </button>`).join('')

  $('#run-matrix').innerHTML = dataset.runs.map((run) => {
    const environment = run.developments.length
      ? `${run.developments.filter((item) => item.document_kind === 'exercise_development').length / 4} pressure inject${run.developments.filter((item) => item.document_kind === 'exercise_development').length / 4 === 1 ? '' : 's'}${run.developments.some((item) => item.document_kind === 'authoritative_allocation_package') ? ' + allocation package' : ''}`
      : 'Common snapshots only'
    return `<tr>
      <td><button type="button" class="matrix-run" data-open-run="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</button></td>
      <td>${escapeHtml(runLabel(run))}</td>
      ${run.rounds.map((round) => `<td class="matrix-round">${escapeHtml(countsText(round.decision_counts))}</td>`).join('')}
      <td>${outcomeBadge(run)}</td>
      <td>${escapeHtml(environment)}</td>
    </tr>`
  }).join('')

  all('[data-open-run]').forEach((button) => {
    button.onclick = () => openRun(button.dataset.openRun)
  })
}

function renderRunIdentity(run) {
  $('#run-identity').innerHTML = `
    <div><strong>${escapeHtml(runLabel(run))}</strong><small>${escapeHtml(run.run_id)} · ${escapeHtml(run.model)} · ${escapeHtml(run.reasoning_effort)} reasoning · ${run.model_calls} calls</small></div>
    ${outcomeBadge(run)}`
}

function renderRoundSelector(run) {
  $('#round-buttons').innerHTML = run.rounds.map((round) => `
    <button type="button" data-round="${round.round}" class="${round.round === state.round ? 'active' : ''}" aria-pressed="${round.round === state.round}">Round ${round.round}</button>`).join('')
  all('[data-round]').forEach((button) => {
    button.onclick = () => {
      state.round = Number(button.dataset.round)
      renderInspector()
      syncUrl()
    }
  })
}

function renderRoundOverview(round) {
  $('#round-state-note').textContent = state.round === 3 ? 'Terminal round' : `Intermediate state before round ${state.round + 1}`
  $('#decision-distribution').innerHTML = decisionOrder.map((decision) => {
    const count = Number(round.decision_counts[decision] || 0)
    return count ? `<div class="bar-${decision}" style="width:${count / 12 * 100}%" title="${count} ${decision}">${count} ${decision}</div>` : ''
  }).join('')
  $('#decision-distribution').setAttribute('aria-label', countsText(round.decision_counts))
  $('#round-counts').innerHTML = `
    <article class="count-card"><span>Decisions</span><p>${escapeHtml(countsText(round.decision_counts))}</p></article>
    <article class="count-card"><span>Primary risks</span><p>${escapeHtml(categoryText(round.risk_counts))}</p></article>
    <article class="count-card"><span>Requested next steps</span><p>${escapeHtml(categoryText(round.request_counts))}</p></article>`
}

function renderEnvironment(run) {
  if (state.round === 1) {
    $('#environment-events').innerHTML = '<p class="empty-state">No between-round development has occurred. Every role begins from the common executable plan.</p>'
    return
  }
  const developments = run.developments.filter((item) => item.after_round === state.round - 1)
  if (!developments.length) {
    $('#environment-events').innerHTML = '<p class="empty-state">Only the common coalition round snapshot was delivered. No exercise-control or stabilization development entered this condition.</p>'
    return
  }
  $('#environment-events').innerHTML = developments.map((item) => {
    const allocation = item.document_kind === 'authoritative_allocation_package'
    return `<article class="environment-event">
      <header><span><strong>${escapeHtml(item.audience_group)}</strong><small> · after round ${item.after_round}</small></span><span class="source-badge">${allocation ? 'Allocation authority' : 'Exercise control'}</span></header>
      <p>${escapeHtml(item.content)}</p>
    </article>`
  }).join('')
}

function renderGate(run) {
  const approved = run.outcome === 'joint_response_approved'
  $('#gate-result').innerHTML = `<div class="gate-outcome ${approved ? 'approved' : 'failed'}"><strong>${escapeHtml(run.outcome_label)}</strong><small>Evaluated once after all twelve final-round stances were retained.</small></div>`
  $('#gate-checks').innerHTML = run.gate_checks.map((check) => `
    <div class="gate-check">
      <span class="check-icon ${check.passed ? 'check-pass' : 'check-fail'}">${check.passed ? '✓' : '×'}</span>
      <span>${escapeHtml(check.label)}</span>
      <small>${check.observed} · ${escapeHtml(check.required)}</small>
    </div>`).join('')
}

function visibleStances(round) {
  return round.stances.filter((stance) => state.group === 'all' || stance.group_id === state.group)
}

function ensureVisiblePerson(round) {
  const visible = visibleStances(round)
  if (!visible.some((stance) => stance.person_id === state.personId)) {
    state.personId = visible[0]?.person_id || round.stances[0].person_id
  }
}

function renderGroupFilters(round) {
  $('#group-filters').innerHTML = groupOrder.map((group) => {
    const count = group === 'all' ? round.stances.length : round.stances.filter((stance) => stance.group_id === group).length
    return `<button type="button" data-group="${group}" class="${group === state.group ? 'active' : ''}" aria-pressed="${group === state.group}">${groupLabels[group]} · ${count}</button>`
  }).join('')
  all('[data-group]').forEach((button) => {
    button.onclick = () => {
      state.group = button.dataset.group
      ensureVisiblePerson(round)
      renderAgents(currentRun(), round)
      syncUrl()
    }
  })
}

function renderAgentDetail(run, round) {
  const stance = round.stances.find((item) => item.person_id === state.personId) || round.stances[0]
  const personRounds = run.rounds.map((item) => item.stances.find((candidate) => candidate.person_id === stance.person_id))
  $('#agent-detail').innerHTML = `
    <header class="agent-detail-header">
      <div><span class="eyebrow">Round ${round.round} stance</span><h4>${escapeHtml(stance.person_label)}</h4><span class="group-label">${escapeHtml(stance.group_label)}</span></div>
      ${decisionPill(stance.decision)}
    </header>
    <div class="stance-meta"><span>Risk · ${escapeHtml(sentence(stance.risk))}</span><span>Request · ${escapeHtml(sentence(stance.request))}</span></div>
    <p class="rationale">${escapeHtml(stance.rationale)}</p>
    <div class="person-trajectory">
      ${personRounds.map((item, index) => `<button type="button" class="person-round ${index + 1 === state.round ? 'active' : ''}" data-person-round="${index + 1}"><small>Round ${index + 1}</small>${decisionPill(item.decision)}<span>Risk · ${escapeHtml(sentence(item.risk))}</span></button>`).join('')}
    </div>
    <div class="evidence-id">Exact structured evidence · ${escapeHtml(run.run_id)} · round ${round.round} · ${escapeHtml(stance.person_id)}</div>`
  all('[data-person-round]').forEach((button) => {
    button.onclick = () => {
      state.round = Number(button.dataset.personRound)
      renderInspector()
      syncUrl()
    }
  })
}

function renderAgents(run, round) {
  ensureVisiblePerson(round)
  renderGroupFilters(round)
  $('#agent-list').innerHTML = visibleStances(round).map((stance) => `
    <button type="button" class="agent-button ${stance.person_id === state.personId ? 'active' : ''}" data-person="${escapeHtml(stance.person_id)}" aria-pressed="${stance.person_id === state.personId}">
      <strong>${escapeHtml(stance.person_label)}</strong>${decisionPill(stance.decision)}<small>${escapeHtml(sentence(stance.risk))} risk</small>
    </button>`).join('')
  all('[data-person]').forEach((button) => {
    button.onclick = () => {
      state.personId = button.dataset.person
      renderAgents(run, round)
      syncUrl()
    }
  })
  renderAgentDetail(run, round)
}

function renderInspector() {
  const run = currentRun()
  state.runId = run.run_id
  const round = currentRound(run)
  state.round = round.round
  $('#run-select').value = run.run_id
  renderRunIdentity(run)
  renderRoundSelector(run)
  renderRoundOverview(round)
  renderEnvironment(run)
  renderGate(run)
  renderAgents(run, round)
}

function renderMethod() {
  $('#initial-plan').innerHTML = dataset.initial_plan.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
  $('#limitations').innerHTML = dataset.limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')
  $('#provenance-dataset').textContent = dataset.dataset_id
  $('#provenance-digest').textContent = dataset.source_sha256
  $('#provenance-time').textContent = new Date(dataset.evidence_latest_at).toLocaleString()
  $('#provenance-time').dateTime = dataset.evidence_latest_at
}

function renderView() {
  for (const view of ['compare', 'inspect', 'method']) {
    $(`#${view}-view`).hidden = state.view !== view
  }
  all('[data-view]').forEach((button) => {
    const active = button.dataset.view === state.view
    button.classList.toggle('active', active)
    button.setAttribute('aria-pressed', String(active))
  })
  if (state.view === 'compare') renderComparison()
  if (state.view === 'inspect') renderInspector()
  if (state.view === 'method') renderMethod()
}

function openRun(runId) {
  state.runId = runId
  state.round = 3
  state.personId = 'regional_scientific_advisor'
  state.group = 'all'
  state.view = 'inspect'
  renderView()
  syncUrl()
  window.scrollTo({top:0, behavior:'auto'})
}

function configureControls() {
  $('#run-select').innerHTML = dataset.runs.map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(runLabel(run))} · ${escapeHtml(run.run_id)}</option>`).join('')
  $('#run-select').onchange = (event) => openRun(event.target.value)
  all('[data-view]').forEach((button) => {
    button.onclick = () => {
      state.view = button.dataset.view
      renderView()
      syncUrl()
    }
  })
}

async function loadWorkbench() {
  try {
    const response = await fetch('data.json', {cache:'no-store'})
    if (!response.ok) throw new Error(`public evidence request failed with ${response.status}`)
    const loaded = await response.json()
    if (loaded.schema_version !== 1 || !Array.isArray(loaded.runs) || loaded.runs.length !== 5) {
      throw new Error('public evidence contract is invalid')
    }
    dataset = loaded
    state.runId = dataset.runs[0].run_id
    readStateFromUrl()
    renderRail()
    configureControls()
    renderView()
    $('#loading').hidden = true
    $('#workbench').hidden = false
  } catch (error) {
    $('#loading').hidden = true
    $('#load-error').hidden = false
    console.error(error)
  }
}

window.addEventListener('popstate', () => {
  if (!dataset) return
  readStateFromUrl()
  renderView()
})

void loadWorkbench()
