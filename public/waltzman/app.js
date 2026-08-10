'use strict'

const decisionOrder = ['support', 'conditional', 'defer', 'oppose']
const groupOrder = ['all', 'alba', 'borin', 'cyrenia', 'darsia', 'regional']
const groupLabels = {all:'All roles', alba:'Alba', borin:'Borin', cyrenia:'Cyrenia', darsia:'Darsia', regional:'Regional'}
const preferredModel = 'codex/gpt-5.6-luna'
const featuredRunIds = ['run_8924342b56ce', 'run_946a10a820fc', 'run_05acbaea1137']
const personProfileFields = {
  values:'person-values',
  goals:'person-goals',
  beliefs:'person-beliefs',
  decision_tendencies:'person-decision-tendencies',
  social_perceptions:'person-social-perceptions',
  current_state:'person-current-state',
  capabilities:'person-capabilities',
  limitations:'person-limitations',
}

let dataset = null
let runtimeConfig = null
let autonomousProbe = null
let resourceFork = null
let defaultConfiguration = null
let editableConfiguration = null
let selectedConfigurationPerson = 'alba_epidemiologist'
let selectedCondition = 'adaptive_cso_stabilization'
let liveModel = null
let liveReasoning = 'medium'
let activeRunId = null
let pollHandle = null

const state = {
  view:'overview',
  runId:null,
  round:3,
  personId:'regional_scientific_advisor',
  group:'all',
  mechanismPersonId:'regional_scientific_advisor',
  labSection:'overview',
  buildStep:'environment',
  exampleEnvironment:0,
  caseBranch:'complete',
  runScopeIds:null,
}

const $ = (selector) => document.querySelector(selector)
const all = (selector) => [...document.querySelectorAll(selector)]
const clone = (value) => JSON.parse(JSON.stringify(value))

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

function labelPerson(personId) {
  return sentence(personId).replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function groupFor(personId) {
  const prefix = String(personId).split('_', 1)[0]
  return ['alba', 'borin', 'cyrenia', 'darsia'].includes(prefix) ? prefix : 'regional'
}

function runLabel(run) {
  if (run.display_label) return run.display_label
  const count = dataset.runs.filter((item) => item.condition === run.condition && !item.is_live).length
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

function countValues(values) {
  return values.reduce((counts, value) => ({...counts, [value]:(counts[value] || 0) + 1}), {})
}

function decisionPill(decision) {
  return `<span class="decision-pill decision-${escapeHtml(decision)}">${escapeHtml(sentence(decision))}</span>`
}

function outcomeBadge(run) {
  const approved = run.outcome === 'joint_response_approved'
  return `<span class="outcome-badge ${approved ? 'outcome-approved' : 'outcome-failed'}"><b aria-hidden="true">${approved ? '✓' : '×'}</b> ${approved ? 'Approved' : 'Not approved'}</span>`
}

function stackedBar(counts, className = 'stacked-bar', total = 12) {
  return `<div class="${className}" aria-label="${escapeHtml(countsText(counts))}">
    ${decisionOrder.map((decision) => {
      const count = Number(counts?.[decision] || 0)
      return count ? `<span class="bar-${decision}" style="width:${count / total * 100}%" title="${count} ${decision}"></span>` : ''
    }).join('')}
  </div>`
}

function currentRun() {
  return dataset.runs.find((run) => run.run_id === state.runId) || dataset.runs[0]
}

function currentRound(run = currentRun()) {
  return run.rounds.find((round) => round.round === state.round) || run.rounds.at(-1)
}

function conditionContract(conditionId) {
  return runtimeConfig?.scenarios?.regional_outbreak?.arms?.find((item) => item.id === conditionId) || {
    id:conditionId,
    label:sentence(conditionId),
    description:'The selected decision environment is retained with the run.',
  }
}

function configurationForRun(run) {
  return run.configuration || null
}

function configurationAgent(configuration, personId) {
  return configuration?.agents?.find((item) => item.agent_id === personId) || null
}

function retainedPersonExists(personId) {
  return dataset.runs.some((run) =>
    run.rounds?.some((round) => round.stances?.some((stance) => stance.person_id === personId))
  )
}

function lineItems(value) {
  return String(value || '').split('\n').map((item) => item.trim()).filter(Boolean)
}

function readStateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const requestedView = params.get('view')
  if (['overview', 'case', 'run', 'compare', 'mechanism', 'inspect', 'method'].includes(requestedView)) state.view = requestedView
  const requestedRun = params.get('run')
  if (requestedRun && dataset.runs.some((run) => run.run_id === requestedRun)) state.runId = requestedRun
  const requestedRound = Number(params.get('round'))
  if ([1, 2, 3].includes(requestedRound)) state.round = requestedRound
  const requestedPerson = params.get('person')
  if (requestedPerson && retainedPersonExists(requestedPerson)) state.personId = requestedPerson
  const requestedMechanismPerson = params.get('mechanism_person')
  if (requestedMechanismPerson && retainedPersonExists(requestedMechanismPerson)) state.mechanismPersonId = requestedMechanismPerson
  const requestedGroup = params.get('group')
  if (groupOrder.includes(requestedGroup)) state.group = requestedGroup
  const requestedSection = params.get('section')
  if (['overview', 'environments', 'participants', 'gate', 'evidence'].includes(requestedSection)) state.labSection = requestedSection
}

function applyRunScopeFromUrl() {
  const rawScope = new URLSearchParams(window.location.search).get('runs')
  if (!rawScope) return
  const requested = rawScope.split(',').map((item) => item.trim()).filter(Boolean)
  if (!requested.length || new Set(requested).size !== requested.length) throw new Error('requested run scope is invalid')
  const indexed = new Map(dataset.runs.map((run) => [run.run_id, run]))
  const missing = requested.filter((runId) => !indexed.has(runId))
  if (missing.length) throw new Error(`requested retained run scope is unavailable: ${missing.join(', ')}`)
  dataset.runs = requested.map((runId) => indexed.get(runId))
  state.runScopeIds = requested
  state.runId = requested[0]
}

function syncUrl() {
  const url = new URL(window.location.href)
  url.searchParams.set('view', state.view)
  for (const key of ['run', 'round', 'person', 'group', 'mechanism_person', 'section']) url.searchParams.delete(key)
  if (state.view === 'inspect') {
    url.searchParams.set('run', state.runId)
    url.searchParams.set('round', String(state.round))
    url.searchParams.set('person', state.personId)
    if (state.group !== 'all') url.searchParams.set('group', state.group)
  }
  if (state.view === 'mechanism') url.searchParams.set('mechanism_person', state.mechanismPersonId)
  if (['compare', 'inspect'].includes(state.view)) url.searchParams.set('section', state.labSection)
  window.history.replaceState({}, '', url)
}

function renderRail() {
  $('#scenario-title').textContent = dataset.scenario_title
  $('#scenario-summary').textContent = dataset.scenario_summary
  $('#fact-runs').textContent = dataset.runs.length
  $('#fact-agents').textContent = dataset.agent_count
  $('#fact-calls').textContent = dataset.runs.reduce((total, run) => total + Number(run.model_calls || 0), 0)
  $('#dataset-id').textContent = state.runScopeIds ? `pinned · ${state.runScopeIds.join(' · ')}` : dataset.dataset_id
}

function renderRunSetup() {
  const contracts = runtimeConfig?.scenarios?.regional_outbreak?.arms || [
    {id:'baseline', label:'Baseline', description:'Only common round feedback is delivered.'},
    {id:'responsive_exercise_injects', label:'Autonomous source pressure', description:'Four bounded source agents emit a complete external-signal bundle between rounds.'},
    {id:'capacity_inject_replay_with_stabilization', label:'Pressure + allocation stabilization', description:'Pressure is replayed and a verified capacity package is added.'},
    {id:'adaptive_cso_stabilization', label:'Pressure + adaptive CSO cell', description:'Three defensive agents detect, diagnose, and select one authorized intervention.'},
  ]
  const publicConditionCopy = {
    baseline:{label:'Baseline', description:'No additional pressure enters between rounds.'},
    responsive_exercise_injects:{label:'Heterogeneous local pressure', description:'Different locally relevant developments enter the coalition as reported concerns emerge.'},
    capacity_inject_replay_with_stabilization:{label:'Pressure + stabilization', description:'The same pressures remain, then an authoritative package bounds uncertainty and resolves dependencies.'},
    adaptive_cso_stabilization:{label:'Pressure + adaptive CSO cell', description:'The same pressures remain; a monitor, diagnostician, and planner choose whether and how to respond.'},
  }
  $('#condition-options').innerHTML = contracts.map((condition) => {
    const copy = publicConditionCopy[condition.id] || condition
    return `
    <button type="button" class="condition-option ${condition.id === selectedCondition ? 'active' : ''}" data-condition="${escapeHtml(condition.id)}" aria-pressed="${condition.id === selectedCondition}">
      <strong>${escapeHtml(copy.label)}</strong><span>${escapeHtml(copy.description)}</span>
    </button>`
  }).join('')
  all('[data-condition]').forEach((button) => {
    button.onclick = () => {
      selectedCondition = button.dataset.condition
      renderRunSetup()
    }
  })

  const people = editableConfiguration?.agents || []
  const maximumCalls = runtimeConfig?.scenarios?.regional_outbreak?.maximum_live_calls || people.length * 3
  $('#execution-participants').textContent = `${people.length} autonomous roles`
  $('#execution-max-calls').textContent = String(maximumCalls)
  $('#agent-config-select').innerHTML = people.map((agent) => `<option value="${escapeHtml(agent.agent_id)}">${escapeHtml(labelPerson(agent.agent_id))}</option>`).join('')
  $('#agent-config-select').value = selectedConfigurationPerson
  const selected = configurationAgent(editableConfiguration, selectedConfigurationPerson)
  $('#agent-mandate').value = selected?.mandate || ''
  $('#agent-context').value = selected?.institutional_context || ''
  $('#person-position').value = selected?.person?.position || ''
  $('#person-disposition').value = selected?.person?.disposition || ''
  $('#person-memories').value = (selected?.person?.memories || []).join('\n')
  Object.entries(personProfileFields).forEach(([fieldName, elementId]) => {
    $(`#${elementId}`).value = (selected?.person?.behavioral_profile?.[fieldName] || []).join('\n')
  })
  $('#shared-situation').value = editableConfiguration?.shared_situation || ''

  const condition = publicConditionCopy[selectedCondition] || conditionContract(selectedCondition)
  const controlNote = selectedCondition === 'baseline'
    ? 'No exercise-control development is introduced between rounds.'
    : selectedCondition === 'responsive_exercise_injects'
      ? 'After each round, four source agents observe the public snapshot. Their complete signal bundle arrives before participants decide again; none can access a stance port.'
      : selectedCondition === 'capacity_inject_replay_with_stabilization'
        ? 'The four source agents remain active. After round two, a fixed verified package joins their complete signal bundle before participants decide again.'
        : 'After round two, the CSO monitor detects directional changes, the diagnostician identifies the mechanism, and the planner selects one authorized intervention. None can access a stance port.'
  $('#control-preview').innerHTML = `<strong>${escapeHtml(condition.label)}</strong><p>${escapeHtml(condition.description)}</p><small>${escapeHtml(controlNote)}</small>`

  $('#agent-config-select').onchange = (event) => {
    persistEditor()
    selectedConfigurationPerson = event.target.value
    renderRunSetup()
  }
  $('#agent-mandate').oninput = persistEditor
  $('#agent-context').oninput = persistEditor
  $('#person-position').oninput = persistEditor
  $('#person-disposition').oninput = persistEditor
  $('#person-memories').oninput = persistEditor
  Object.values(personProfileFields).forEach((elementId) => { $(`#${elementId}`).oninput = persistEditor })
  $('#shared-situation').oninput = persistEditor
  renderBuildStep()
}

function renderBuildStep(step = state.buildStep) {
  state.buildStep = step
  all('[data-build-panel]').forEach((panel) => { panel.hidden = panel.dataset.buildPanel !== step })
  all('[data-build-step]').forEach((button) => {
    const order = ['environment', 'coalition', 'review']
    const active = button.dataset.buildStep === step
    button.classList.toggle('active', active)
    button.classList.toggle('complete', order.indexOf(button.dataset.buildStep) < order.indexOf(step))
    button.setAttribute('aria-current', active ? 'step' : 'false')
  })
  $('.run-workbench').classList.toggle('review-step', step === 'review')
}

function persistEditor() {
  if (!editableConfiguration) return
  const selected = configurationAgent(editableConfiguration, selectedConfigurationPerson)
  if (selected) {
    selected.mandate = $('#agent-mandate').value
    selected.institutional_context = $('#agent-context').value
    if (selected.person) {
      selected.person.position = $('#person-position').value
      selected.person.disposition = $('#person-disposition').value
      selected.person.memories = lineItems($('#person-memories').value)
      Object.entries(personProfileFields).forEach(([fieldName, elementId]) => {
        selected.person.behavioral_profile[fieldName] = lineItems($(`#${elementId}`).value)
      })
    }
  }
  editableConfiguration.shared_situation = $('#shared-situation').value
}

function configureRuntime() {
  const scenario = runtimeConfig?.scenarios?.regional_outbreak
  defaultConfiguration = clone(scenario?.editable_configuration || dataset.default_configuration || null)
  editableConfiguration = clone(defaultConfiguration)
  const models = runtimeConfig?.live_options?.models || []
  const allowed = new Set(scenario?.live_model_ids || [])
  const eligible = models.filter((item) => allowed.has(item.model))
  const selectedModel = eligible.find((item) => item.model === preferredModel) || eligible[0] || null
  liveModel = selectedModel?.model || null
  liveReasoning = selectedModel?.agent_reasoning_efforts?.includes('medium')
    ? 'medium'
    : selectedModel?.default_agent_reasoning_effort || 'medium'

  const live = Boolean(runtimeConfig?.live_authorized && scenario?.supports_live && liveModel && defaultConfiguration)
  $('#runtime-status').textContent = live ? 'Live simulator connected' : 'Live simulator unavailable'
  $('#runtime-status').className = `runtime-status ${live ? 'live' : 'unavailable'}`
  $('#live-capability').textContent = live ? 'Authentic LLM execution available' : 'Live route unavailable'
  $('#live-capability').className = `capability-badge ${live ? 'live' : 'unavailable'}`
  $('#execution-model').textContent = liveModel || 'Unavailable'
  $('#run-experiment').disabled = !live
  $('#run-availability').textContent = live
    ? 'One public run at a time. Every participant call and exact mechanism event is retained.'
    : 'Retained evidence remains available, but this deployment cannot start a model run.'
  renderRunSetup()
}

function renderComparison() {
  const approved = dataset.runs.filter((run) => run.outcome === 'joint_response_approved').length
  const notApproved = dataset.runs.length - approved
  const snapshotCount = dataset.runs.filter((run) => !run.is_live).length
  const configuredCount = dataset.runs.length - snapshotCount
  const sourceDescription = [
    snapshotCount ? `${snapshotCount} immutable snapshot ${snapshotCount === 1 ? 'trajectory' : 'trajectories'}` : '',
    configuredCount ? `${configuredCount} configured public ${configuredCount === 1 ? 'trajectory' : 'trajectories'}` : '',
  ].filter(Boolean).join(' and ')
  const scopeDescription = state.runScopeIds ? ' This URL is pinned to this exact run set.' : ''
  $('#comparison-summary').innerHTML = `
    <span class="comparison-icon" aria-hidden="true">${dataset.runs.length}×</span>
    <div><strong>${dataset.runs.length} authentic trajectories are loaded for comparison</strong><p>${approved} ended in approval and ${notApproved} ended without approval. Loaded evidence: ${sourceDescription}.${scopeDescription}</p></div>
    <small>${dataset.runs.reduce((total, run) => total + run.model_calls, 0)} retained participant calls</small>`

  $('#trajectory-grid').innerHTML = dataset.runs.map((run) => `
    <button type="button" class="trajectory-card" data-open-run="${escapeHtml(run.run_id)}" aria-label="Inspect ${escapeHtml(runLabel(run))}, ${escapeHtml(run.run_id)}">
      <span class="card-top"><span><h3>${escapeHtml(runLabel(run))}</h3><span class="run-code">${escapeHtml(run.run_id)}</span></span>${outcomeBadge(run)}</span>
      <span class="round-track">${run.rounds.map((round) => `<span class="round-track-row"><span class="round-label">R${round.round}</span>${stackedBar(round.decision_counts, 'stacked-bar', run.agent_count || 12)}</span>`).join('')}</span>
      <span class="final-line">Final · ${escapeHtml(countsText(run.rounds.at(-1).decision_counts))}</span>
    </button>`).join('')

  $('#run-matrix').innerHTML = dataset.runs.map((run) => {
    const pressure = new Set(run.developments.filter((item) => ['exercise_development', 'autonomous_source_bundle'].includes(item.document_kind)).map((item) => item.after_round)).size
    const hasAllocation = run.developments.some((item) => item.document_kind === 'authoritative_allocation_package' || item.has_stabilization)
    const environment = run.developments.length
      ? `${pressure} pressure phase${pressure === 1 ? '' : 's'}${hasAllocation ? ' + allocation package' : ''}`
      : 'Common snapshots only'
    return `<tr><td><button type="button" class="matrix-run" data-open-run="${escapeHtml(run.run_id)}">${escapeHtml(run.run_id)}</button></td><td>${escapeHtml(runLabel(run))}</td>${run.rounds.map((round) => `<td class="matrix-round">${escapeHtml(countsText(round.decision_counts))}</td>`).join('')}<td>${outcomeBadge(run)}</td><td>${escapeHtml(environment)}</td></tr>`
  }).join('')
  all('[data-open-run]').forEach((button) => { button.onclick = () => openRun(button.dataset.openRun) })
}

function personStance(run, roundNumber, personId) {
  return run.rounds.find((round) => round.round === roundNumber)?.stances.find((stance) => stance.person_id === personId) || null
}

function conditionStory(run) {
  const stories = {
    baseline:{step:'1', title:'Baseline', change:'No pressure enters the coalition.', explanation:'The agents receive only common round results and remain ready to act.'},
    responsive_exercise_injects:{step:'2', title:'Heterogeneous local pressure', change:'Different subgroups receive different locally relevant developments.', explanation:'The content varies by location, while reported risk and coordination move in the same direction.'},
    capacity_inject_replay_with_stabilization:{step:'3', title:'Pressure + stabilization', change:'The same pressure remains and an authoritative intervention is added.', explanation:'Verified allocations bound uncertainty and make the coalition’s commitments compatible.'},
    adaptive_cso_stabilization:{step:'4', title:'Pressure + adaptive CSO', change:'A defensive cell observes the degraded decision environment and chooses a bounded response.', explanation:'The monitor detects, the diagnostician explains, and the planner selects an authorized intervention before agents decide again.'},
  }
  return stories[run.condition] || {step:'•', title:run.condition_label, change:'External environment varied', explanation:'Inspect the retained run for its exact developments.'}
}

function renderMechanism() {
  if (autonomousProbe) {
    renderAutonomousProbe()
    return
  }
  $('#mechanism-person-select').innerHTML = dataset.people.map((person) => `<option value="${escapeHtml(person.person_id)}">${escapeHtml(person.person_label)}</option>`).join('')
  $('#mechanism-person-select').value = state.mechanismPersonId
  $('#mechanism-person-select').onchange = (event) => {
    state.mechanismPersonId = event.target.value
    renderMechanism()
    syncUrl()
  }
  const baseline = dataset.runs.find((run) => run.condition === 'baseline')
  const pressure = dataset.runs.find((run) => run.condition === 'responsive_exercise_injects')
  const stabilized = dataset.runs.find((run) => run.condition === 'capacity_inject_replay_with_stabilization')
  const exampleRuns = [baseline, pressure, stabilized].filter(Boolean)
  const stageStories = {
    baseline:{prompt:'No external pressure', development:'The coalition receives only its shared decision history.', chain:['Common information','Risks remain bounded','Coordination remains ready'], trust:'Not measured in this probe', risk:'No new risk enters the coalition'},
    responsive_exercise_injects:{prompt:'Different local signals. Same directional effect.', development:'Alba receives a laboratory failure, Borin a staffing demand, Cyrenia a supply condition, and the regional institution an infeasibility warning.', chain:['Heterogeneous local inputs','Capacity or legitimacy becomes primary','Coordination collapses'], trust:'Not measured in this probe', risk:'12 of 12 report capacity or legitimacy and request action'},
    capacity_inject_replay_with_stabilization:{prompt:'Detect → diagnose → stabilize', development:'The same local pressures remain. A verified allocation then supplies testing, clinicians, equipment, and reserve capacity.', chain:['Same heterogeneous pressure','Authoritative facts bound uncertainty','Coordination returns'], trust:'Reliance on the verified authority is observable; private trust is not measured', risk:'Named concerns receive concrete answers'},
  }
  const renderExampleStage = () => {
    const index = Math.min(state.exampleEnvironment, exampleRuns.length - 1)
    const run = exampleRuns[index]
    if (!run) return
    const story = conditionStory(run)
    const stage = stageStories[run.condition] || {prompt:story.title, development:story.explanation}
    $('#example-environment-select').innerHTML = exampleRuns.map((candidate, candidateIndex) => `<button type="button" data-example-environment="${candidateIndex}" class="${candidateIndex === index ? 'active' : ''}"><b>${candidateIndex + 1}</b><span>${escapeHtml(conditionStory(candidate).title)}</span></button>`).join('')
    const finalCounts = countsText(run.rounds.at(-1).decision_counts)
    const gateResult = run.outcome === 'joint_response_approved' ? 'gate passes' : 'gate fails'
    $('#example-stage').innerHTML = `<header><div><span>Condition ${index + 1} of ${exampleRuns.length}</span><h3>${escapeHtml(stage.prompt)}</h3></div>${outcomeBadge(run)}</header><p>${escapeHtml(stage.development)}</p><div class="probe-chain">${stage.chain.map((item) => `<span>${escapeHtml(item)}</span>`).join('<i>→</i>')}</div><div class="stage-trajectory">${run.rounds.map((round) => `<div><b>Round ${round.round}</b>${stackedBar(round.decision_counts, 'stage-bar')}<strong>${escapeHtml(countsText(round.decision_counts))}</strong></div>`).join('')}</div><dl class="decision-environment-readout"><div><dt>Trust structure</dt><dd>${escapeHtml(stage.trust)}</dd></div><div><dt>Perceived risk</dt><dd>${escapeHtml(stage.risk)}</dd></div><div><dt>Coordination readiness</dt><dd>${escapeHtml(`${finalCounts} · ${gateResult}`)}</dd></div></dl>`
    all('[data-example-environment]').forEach((button) => { button.onclick = () => { state.exampleEnvironment = Number(button.dataset.exampleEnvironment); renderExampleStage() } })
    $('#example-next').textContent = index === exampleRuns.length - 1 ? 'Restart probe ↻' : 'Next condition →'
  }
  renderExampleStage()
  $('#example-next').onclick = () => { state.exampleEnvironment = (state.exampleEnvironment + 1) % exampleRuns.length; renderExampleStage() }
  $('#open-full-analysis').onclick = () => { const details = $('#full-example-analysis'); details.open = true; details.scrollIntoView({behavior:'smooth', block:'start'}) }
  $('#case-trajectories').innerHTML = exampleRuns.map((run) => {
    const story = conditionStory(run)
    return `<article><header><span>Environment ${escapeHtml(story.step)}</span><strong>${escapeHtml(story.title)}</strong>${outcomeBadge(run)}</header><div>${run.rounds.map((round) => `<div class="case-trajectory-round"><b>R${round.round}</b>${stackedBar(round.decision_counts, 'case-trajectory-bar')}<span>${escapeHtml(countsText(round.decision_counts))}</span></div>`).join('')}</div></article>`
  }).join('')
  $('#case-overview-table').innerHTML = exampleRuns.map((run) => {
    const story = conditionStory(run)
    return `<tr><th scope="row"><span>Environment ${escapeHtml(story.step)}</span>${escapeHtml(story.title)}</th>${run.rounds.map((round) => `<td>${escapeHtml(countsText(round.decision_counts))}</td>`).join('')}<td>${outcomeBadge(run)}</td></tr>`
  }).join('')
  $('#case-gate-table').innerHTML = exampleRuns.map((run) => {
    const story = conditionStory(run)
    return run.gate_checks.map((check, index) => `<tr>${index === 0 ? `<th scope="rowgroup" rowspan="${run.gate_checks.length}">Environment ${escapeHtml(story.step)}<small>${escapeHtml(story.title)}</small></th>` : ''}<td>${escapeHtml(check.label)}</td><td>${escapeHtml(check.required)}</td><td>${escapeHtml(check.observed)}</td><td><span class="gate-status ${check.passed ? 'gate-pass' : 'gate-fail'}">${check.passed ? '✓ Passed' : '× Failed'}</span></td></tr>`).join('')
  }).join('')

  const finalStances = dataset.runs.map((run) => ({run, stance:personStance(run, 3, state.mechanismPersonId)})).filter((item) => item.stance)
  $('#waltzman-lens').innerHTML = finalStances.map(({run, stance}) => {
    const story = conditionStory(run)
    const path = [1, 2, 3].map((round) => sentence(personStance(run, round, state.mechanismPersonId)?.decision || 'unknown')).join(' → ')
    return `<article class="lens-card"><span>${escapeHtml(story.change)}</span><strong>${escapeHtml(path)}</strong><p>Final concern: ${escapeHtml(sentence(stance.risk))}. Final request: ${escapeHtml(sentence(stance.request))}.</p></article>`
  }).join('')
  $('#mechanism-person-title').textContent = `${labelPerson(state.mechanismPersonId)} across decision environments`
  $('#mechanism-table').innerHTML = dataset.runs.map((run) => {
    const cells = [1, 2, 3].map((round) => {
      const stance = personStance(run, round, state.mechanismPersonId)
      return `<td class="mechanism-cell">${decisionPill(stance?.decision || 'unknown')}<small>Risk · ${escapeHtml(sentence(stance?.risk || 'unknown'))}<br>Request · ${escapeHtml(sentence(stance?.request || 'unknown'))}</small></td>`
    }).join('')
    const story = conditionStory(run)
    return `<tr><td><button type="button" class="matrix-run" data-open-mechanism-run="${escapeHtml(run.run_id)}">${escapeHtml(story.title)}</button></td><td>${escapeHtml(story.change)}</td>${cells}<td>${outcomeBadge(run)}</td></tr>`
  }).join('')
  all('[data-open-mechanism-run]').forEach((button) => {
    button.onclick = () => {
      state.personId = state.mechanismPersonId
      openRun(button.dataset.openMechanismRun, false)
    }
  })

  const previewStance = pressure ? personStance(pressure, 3, state.mechanismPersonId) : null
  $('#agent-evidence-preview').innerHTML = previewStance ? `
    <div><span class="section-kicker">Evidence preview · Environment 2 · Round 3</span><h3 id="agent-preview-title">${escapeHtml(labelPerson(state.mechanismPersonId))}</h3></div>
    <dl><div><dt>Decision</dt><dd>${decisionPill(previewStance.decision)}</dd></div><div><dt>Primary concern</dt><dd>${escapeHtml(sentence(previewStance.risk))}</dd></div><div><dt>Requested next step</dt><dd>${escapeHtml(sentence(previewStance.request))}</dd></div><div><dt>Structured rationale</dt><dd>${escapeHtml(previewStance.rationale)}</dd></div></dl>
    <button id="inspect-all-evidence" class="secondary-cta" type="button">Inspect all agent decisions</button>` : `
    <div><span class="section-kicker">Evidence preview</span><h3 id="agent-preview-title">Participant evidence unavailable</h3></div>`
  const evidenceButton = $('#inspect-all-evidence')
  if (evidenceButton) evidenceButton.onclick = () => {
    const details = $('#all-agent-evidence')
    details.open = true
    details.scrollIntoView({behavior:'smooth', block:'start'})
  }
}

function renderAutonomousProbe() {
  const conditions = autonomousProbe.conditions
  const index = Math.min(state.exampleEnvironment, conditions.length - 1)
  const condition = conditions[index]
  $('#probe-condition-select').innerHTML = conditions.map((item, itemIndex) => `<button type="button" data-probe-condition="${itemIndex}" class="${itemIndex === index ? 'active' : ''}"><b>${itemIndex + 1}</b><span>${escapeHtml(item.label)}</span></button>`).join('')
  const meetings = condition.meetings.map((meeting) => {
    const tokens = ['support_full', 'support_reduced', 'support_conditional', 'defer', 'oppose', 'disengaged'].flatMap((stance) => Array.from({length:Number(meeting.stances[stance] || 0)}, () => `<i class="agent-token token-${escapeHtml(stance)}" title="${escapeHtml(sentence(stance))}"></i>`)).join('')
    return `<article class="meeting-turn"><span>${escapeHtml(meeting.label)}</span><div class="agent-tokens" aria-label="${escapeHtml(meeting.summary)}">${tokens}</div><strong>${escapeHtml(meeting.summary)}</strong><small>${meeting.open_risks} open ${meeting.open_risks === 1 ? 'risk' : 'risks'}</small></article>`
  }).join('<i class="turn-arrow">→</i>')
  const moves = condition.source_moves.length
    ? condition.source_moves.map((move) => `<li><b>${escapeHtml(move.source)}</b><span>${escapeHtml(move.choice)}</span><p>${escapeHtml(move.message)}</p></li>`).join('')
    : '<li class="source-silent"><b>No outside sources</b><span>The coalition receives no new influence messages.</span></li>'
  $('#probe-condition').innerHTML = `<header><div><span>Condition ${index + 1} of ${conditions.length}</span><h3>${escapeHtml(condition.label)}</h3></div><strong class="swarm-outcome ${escapeHtml(condition.outcome)}">${escapeHtml(condition.outcome_label)}</strong></header><p class="condition-summary">${escapeHtml(condition.summary)}</p><div class="meeting-track">${meetings}</div><section class="source-console"><header><span>Autonomous source decisions</span><small>Observe → choose → emit or stay silent</small></header><ul>${moves}</ul></section>`
  all('[data-probe-condition]').forEach((button) => { button.onclick = () => { state.exampleEnvironment = Number(button.dataset.probeCondition); renderAutonomousProbe() } })
  $('#probe-next').textContent = index === conditions.length - 1 ? 'Restart experiment ↻' : 'Next condition →'
  $('#probe-next').onclick = () => { state.exampleEnvironment = (index + 1) % conditions.length; renderAutonomousProbe() }
  $('#probe-raw-run').href = `api/runs/${encodeURIComponent(condition.run_id)}`
  $('#run-probe').onclick = () => startAutonomousProbe(condition.arm_id)
}

async function startAutonomousProbe(armId) {
  const status = $('#probe-run-status')
  const button = $('#run-probe')
  status.hidden = false
  status.textContent = 'Starting a new authentic run…'
  button.disabled = true
  try {
    const scenario = runtimeConfig?.scenarios?.coordination_decision
    const model = scenario?.live_model_ids?.[0]
    if (!runtimeConfig?.live_authorized || !model) throw new Error('The live coordination route is unavailable.')
    const started = await apiRequest('api/runs', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({scenario:'coordination_decision', arm_id:armId, execution:'live', llm_options:{model, agent_reasoning_effort:'medium', max_total_cost:0.74}})})
    status.innerHTML = `Run <code>${escapeHtml(started.run_id)}</code> started. This page can be closed; the retained run will continue on the simulator.`
  } catch (error) {
    status.textContent = `Run did not start: ${error.message}`
    button.disabled = false
  }
}

function renderRunIdentity(run) {
  $('#run-identity').innerHTML = `<div><strong>${escapeHtml(runLabel(run))}</strong><small>${escapeHtml(run.run_id)} · ${escapeHtml(run.model)} · ${escapeHtml(run.reasoning_effort)} reasoning · ${run.model_calls} calls</small></div>${outcomeBadge(run)}`
}

function renderRoundSelector(run) {
  $('#round-buttons').innerHTML = run.rounds.map((round) => `<button type="button" data-round="${round.round}" class="${round.round === state.round ? 'active' : ''}" aria-pressed="${round.round === state.round}">Round ${round.round}</button>`).join('')
  all('[data-round]').forEach((button) => {
    button.onclick = () => { state.round = Number(button.dataset.round); renderInspector(); syncUrl() }
  })
}

function renderRoundOverview(round) {
  $('#round-state-note').textContent = state.round === 3 ? 'Terminal round' : `Intermediate state before round ${state.round + 1}`
  $('#decision-distribution').innerHTML = decisionOrder.map((decision) => {
    const count = Number(round.decision_counts[decision] || 0)
    const total = currentRun()?.agent_count || 12
    return count ? `<div class="bar-${decision}" style="width:${count / total * 100}%" title="${count} ${decision}">${count} ${decision}</div>` : ''
  }).join('')
  $('#decision-distribution').setAttribute('aria-label', countsText(round.decision_counts))
  $('#round-counts').innerHTML = `<article class="count-card"><span>Decisions</span><p>${escapeHtml(countsText(round.decision_counts))}</p></article><article class="count-card"><span>Primary risks</span><p>${escapeHtml(categoryText(round.risk_counts))}</p></article><article class="count-card"><span>Requested next steps</span><p>${escapeHtml(categoryText(round.request_counts))}</p></article>`
}

function renderEnvironment(run) {
  if (state.round === 1) {
    $('#environment-events').innerHTML = '<p class="empty-state">No between-round development has occurred. Every role begins from the reviewed common situation and its own retained mandate and context.</p>'
    return
  }
  const prior = run.rounds.find((round) => round.round === state.round - 1)
  const dominantRisk = Object.entries(prior?.risk_counts || {}).sort((left, right) => right[1] - left[1])[0]?.[0]
  const developments = run.developments.filter((item) => item.after_round === state.round - 1)
  if (!developments.length) {
    $('#environment-events').innerHTML = `<p class="empty-state">Only the common coalition snapshot was delivered. No exercise-control or stabilization development entered this condition.</p>`
    return
  }
  $('#environment-events').innerHTML = `<div class="control-preview"><strong>Selection trace</strong><p>Prior dominant reported risk: ${escapeHtml(sentence(dominantRisk || 'none'))}. The condition supplied only preauthored exogenous developments; participant stances remained model-generated.</p></div>${developments.map((item) => {
    const allocation = item.document_kind === 'authoritative_allocation_package'
    const sourceLabel = allocation
      ? 'Allocation authority'
      : item.document_kind === 'cso_stabilization_bundle'
        ? 'CSO planner'
        : item.document_kind === 'autonomous_source_bundle'
          ? 'Autonomous sources'
          : 'Exercise control'
    return `<article class="environment-event"><header><span><strong>${escapeHtml(item.audience_group)}</strong><small> · after round ${item.after_round}</small></span><span class="source-badge">${sourceLabel}</span></header><p>${escapeHtml(item.content)}</p></article>`
  }).join('')}`
}

function renderGate(run) {
  const approved = run.outcome === 'joint_response_approved'
  $('#gate-result').innerHTML = `<div class="gate-outcome ${approved ? 'approved' : 'failed'}"><strong>Final round-3 result · ${escapeHtml(run.outcome_label)}</strong><small>This terminal gate is shown alongside every selected round for reference.</small></div>`
  $('#gate-checks').innerHTML = run.gate_checks.map((check) => `<div class="gate-check"><span class="check-icon ${check.passed ? 'check-pass' : 'check-fail'}">${check.passed ? '✓' : '×'}</span><span>${escapeHtml(check.label)}</span><small>${check.observed} · ${escapeHtml(check.required)}</small></div>`).join('')
}

function visibleStances(round) {
  return round.stances.filter((stance) => state.group === 'all' || stance.group_id === state.group)
}

function ensureVisiblePerson(round) {
  const visible = visibleStances(round)
  if (!visible.some((stance) => stance.person_id === state.personId)) state.personId = visible[0]?.person_id || round.stances[0].person_id
}

function renderGroupFilters(round) {
  $('#group-filters').innerHTML = groupOrder.map((group) => {
    const count = group === 'all' ? round.stances.length : round.stances.filter((stance) => stance.group_id === group).length
    return `<button type="button" data-group="${group}" class="${group === state.group ? 'active' : ''}" aria-pressed="${group === state.group}">${groupLabels[group]} · ${count}</button>`
  }).join('')
  all('[data-group]').forEach((button) => {
    button.onclick = () => { state.group = button.dataset.group; ensureVisiblePerson(round); renderAgents(currentRun(), round); syncUrl() }
  })
}

function renderAgentDetail(run, round) {
  const stance = round.stances.find((item) => item.person_id === state.personId) || round.stances[0]
  const personRounds = run.rounds.map((item) => item.stances.find((candidate) => candidate.person_id === stance.person_id))
  const messages = run.coordination_messages || []
  const attempted = messages.find((item) => item.round === round.round && item.actor_id === stance.person_id)
  const received = messages.filter((item) => item.delivered_round === round.round && item.target_ref === stance.person_id)
  const incoming = received.length
    ? `<details class="interaction-incoming"${received.length <= 3 ? ' open' : ''}><summary>Messages received before this decision · ${received.length}</summary><div>${received.map((item) => `<article><strong>${escapeHtml(labelPerson(item.actor_id))}</strong><p>${escapeHtml(item.content)}</p></article>`).join('')}</div></details>`
    : ''
  const deliveryLink = attempted?.kind === 'send_message' && attempted.delivered_round
    ? `<button type="button" class="interaction-link" data-message-target="${escapeHtml(attempted.target_ref)}" data-message-round="${attempted.delivered_round}">View ${escapeHtml(labelPerson(attempted.target_ref))} in round ${attempted.delivered_round} →</button>`
    : ''
  const outgoing = attempted
    ? `<div class="interaction-outgoing"><strong>Message attempt → delivery outcome</strong><p>${attempted.kind === 'no_action' ? 'No direct message attempted' : `To ${escapeHtml(labelPerson(attempted.target_ref))}`}: ${escapeHtml(attempted.content)}</p><small>${escapeHtml(sentence(attempted.outcome))}${attempted.delivered_round ? ` · available in round ${attempted.delivered_round}` : ''}</small>${deliveryLink}</div>`
    : ''
  const interaction = incoming || outgoing ? `<div class="interaction-trace">${incoming}${outgoing}</div>` : ''
  $('#agent-detail').innerHTML = `<header class="agent-detail-header"><div><span class="eyebrow">Round ${round.round} stance</span><h4>${escapeHtml(stance.person_label)}</h4><span class="group-label">${escapeHtml(stance.group_label)}</span></div>${decisionPill(stance.decision)}</header><div class="stance-meta"><span>Risk · ${escapeHtml(sentence(stance.risk))}</span><span>Request · ${escapeHtml(sentence(stance.request))}</span></div><p class="rationale">${escapeHtml(stance.rationale)}</p>${interaction}<div class="person-trajectory">${personRounds.map((item, index) => `<button type="button" class="person-round ${index + 1 === state.round ? 'active' : ''}" data-person-round="${index + 1}"><small>Round ${index + 1}</small>${decisionPill(item.decision)}<span>Risk · ${escapeHtml(sentence(item.risk))}</span></button>`).join('')}</div><div class="evidence-id">Exact structured evidence · ${escapeHtml(run.run_id)} · round ${round.round} · ${escapeHtml(stance.person_id)}</div>`
  all('[data-person-round]').forEach((button) => {
    button.onclick = () => { state.round = Number(button.dataset.personRound); renderInspector(); syncUrl() }
  })
  all('[data-message-target]').forEach((button) => {
    button.onclick = () => {
      state.personId = button.dataset.messageTarget
      state.round = Number(button.dataset.messageRound)
      state.group = 'all'
      renderInspector()
      syncUrl()
      $('#agent-detail').scrollIntoView({behavior:'auto', block:'start'})
    }
  })
  renderRunInputs(run, stance.person_id)
}

function renderRunInputs(run, personId) {
  const configuration = configurationForRun(run)
  const agent = configurationAgent(configuration, personId)
  const condition = conditionContract(run.condition)
  const person = agent?.person
  const personalContext = person
    ? `${person.disposition} Goals: ${(person.behavioral_profile?.goals || []).join(' ')}`
    : 'This retained run predates the canonical person contract.'
  $('#run-inputs').innerHTML = configuration && agent ? `<div class="run-input-grid"><article><span>Common starting situation</span><p>${escapeHtml(configuration.shared_situation)}</p></article><article><span>${escapeHtml(labelPerson(personId))} · position expectations</span><p>${escapeHtml(agent.mandate)}</p></article><article><span>Personal starting context</span><p>${escapeHtml(personalContext)}</p></article><article><span>Private institutional context</span><p>${escapeHtml(agent.institutional_context)}</p></article><article><span>Exercise-control rule</span><p>${escapeHtml(condition.description)}</p></article><article><span>Execution configuration</span><p>${escapeHtml(run.model)} · ${escapeHtml(run.reasoning_effort)} reasoning · ${run.model_calls} retained calls</p></article></div>` : '<p class="empty-state">This legacy retained run predates the public configuration projection.</p>'
}

function renderAgents(run, round) {
  ensureVisiblePerson(round)
  renderGroupFilters(round)
  $('#agent-list').innerHTML = visibleStances(round).map((stance) => `<button type="button" class="agent-button ${stance.person_id === state.personId ? 'active' : ''}" data-person="${escapeHtml(stance.person_id)}" aria-pressed="${stance.person_id === state.personId}"><strong>${escapeHtml(stance.person_label)}</strong>${decisionPill(stance.decision)}<small>${escapeHtml(sentence(stance.risk))} risk</small></button>`).join('')
  all('[data-person]').forEach((button) => {
    button.onclick = () => { state.personId = button.dataset.person; renderAgents(run, round); syncUrl() }
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
  const latest = state.runScopeIds
    ? dataset.runs.map((run) => run.created_at).sort().at(-1)
    : dataset.evidence_latest_at
  $('#provenance-dataset').textContent = state.runScopeIds ? 'Pinned retained-run comparison' : dataset.dataset_id
  $('#provenance-source-label').textContent = state.runScopeIds ? 'Retained run IDs' : 'Source digest'
  $('#provenance-digest').textContent = state.runScopeIds ? state.runScopeIds.join(' · ') : dataset.source_sha256
  $('#provenance-time').textContent = new Date(latest).toLocaleString()
  $('#provenance-time').dateTime = latest
}

function renderResearchCase() {
  if (!resourceFork?.branches?.length) {
    $('#research-case-runs').innerHTML = '<p class="case-data-error"><strong>Research case unavailable.</strong> The exact checkpoint evidence could not be loaded.</p>'
    $('#case-open-comparison').disabled = true
    return
  }

  $('#case-open-comparison').disabled = false
  const stories = {
    no_intervention:'No regional resource package was issued.',
    partial:'Two verified resources were committed: Alba laboratory capacity and Borin clinicians.',
    complete:'All six named resources were verified and committed.',
    false_claim:'All six resources were claimed as verified; the world audit found custody mismatches and changed no custody.',
  }
  const renderBranch = () => {
    const branch = resourceFork.branches.find((item) => item.id === state.caseBranch) || resourceFork.branches[0]
    state.caseBranch = branch.id
    all('[data-case-branch]').forEach((button) => button.classList.toggle('active', button.dataset.caseBranch === branch.id))
    const resources = branch.resource_commitments || []
    const verified = resources.filter((item) => item.audit_status === 'verified').length
    const contradicted = resources.filter((item) => item.audit_status === 'contradicted').length
    const support = Number(branch.final_decisions.support || 0)
    const ready = support + Number(branch.final_decisions.conditional || 0)
    const gateText = support >= resourceFork.gate.minimum_support ? 'Support threshold passed' : `Support threshold failed · ${support} of ${resourceFork.gate.minimum_support}`
    $('#case-branch-detail').innerHTML = `<div class="fork-readout">
      <div><span>World event</span><strong>${escapeHtml(stories[branch.id])}</strong></div>
      <div><span>Audit</span><strong>${verified} verified${contradicted ? ` · ${contradicted} contradicted` : ''}</strong></div>
      <div><span>Readiness</span><strong>${ready} support or conditional</strong></div>
      <div><span>Decision gate</span><strong>${escapeHtml(gateText)}</strong></div>
    </div>`
    const evidenceIds = ['regional_logistics_coordinator', 'regional_coordinator', 'regional_scientific_advisor']
    $('#case-evidence-records').innerHTML = evidenceIds.map((personId) => {
      const stance = branch.final_stances[personId]
      return `<article><header><span>${escapeHtml(labelPerson(personId))}</span>${decisionPill(stance.decision)}</header><p>${escapeHtml(stance.rationale)}</p></article>`
    }).join('')
  }
  $('#research-case-runs').innerHTML = resourceFork.branches.map((branch) => `<button type="button" class="research-case-run ${branch.id === state.caseBranch ? 'active' : ''}" data-case-branch="${escapeHtml(branch.id)}">
    <header><span>Final-round fork</span><h4>${escapeHtml(branch.label)}</h4>${outcomeBadge(branch)}</header>
    ${stackedBar(branch.final_decisions, 'case-result-bar', resourceFork.agent_count)}
    <strong>${escapeHtml(countsText(branch.final_decisions))}</strong>
  </button>`).join('')
  all('[data-case-branch]').forEach((button) => { button.onclick = () => { state.caseBranch = button.dataset.caseBranch; renderBranch() } })
  renderBranch()

  $('#case-open-comparison').onclick = () => {
    window.open('assets/resource-fork.json', '_blank', 'noopener')
  }
}

function renderView() {
  const publicView = ['overview', 'case', 'mechanism'].includes(state.view)
  document.body.classList.toggle('guided-result', publicView)
  document.body.classList.toggle('public-shell', publicView)
  document.body.classList.toggle('lab-shell', !publicView)
  for (const view of ['overview', 'case', 'run', 'compare', 'mechanism', 'inspect', 'method']) $(`#${view}-view`).hidden = state.view !== view
  all('[data-view]').forEach((button) => {
    const active = button.dataset.view === state.view
    button.classList.toggle('active', active)
    button.setAttribute('aria-pressed', String(active))
  })
  all('[data-open-lab]').forEach((button) => { button.classList.toggle('active', !publicView); button.setAttribute('aria-pressed', String(!publicView)) })
  all('[data-lab-view]').forEach((button) => {
    const sameView = button.dataset.labView === state.view
    const active = sameView && (!button.dataset.labSection || button.dataset.labSection === state.labSection)
    button.classList.toggle('active', active)
    button.setAttribute('aria-current', active ? 'page' : 'false')
  })
  if (state.view === 'run') renderRunSetup()
  if (state.view === 'case') renderResearchCase()
  if (state.view === 'compare') renderComparison()
  if (state.view === 'mechanism') renderMechanism()
  if (state.view === 'inspect') renderInspector()
  if (state.view === 'method') renderMethod()
}

function navigateLab(view, section = 'overview') {
  state.view = view
  state.labSection = section
  renderView()
  syncUrl()
  const targets = {environments:'#environment-results', participants:'#participant-results', gate:'#decision-gate-results', evidence:'#raw-evidence-results'}
  if (section === 'evidence') $('#raw-evidence-results').open = true
  const target = targets[section]
  window.requestAnimationFrame(() => target ? $(target).scrollIntoView({behavior:'auto', block:'start'}) : window.scrollTo({top:0, behavior:'auto'}))
}

function openRun(runId, resetPerson = true) {
  state.runId = runId
  state.round = 3
  if (resetPerson) state.personId = 'regional_scientific_advisor'
  state.group = 'all'
  state.view = 'inspect'
  state.labSection = 'participants'
  renderView()
  syncUrl()
  window.scrollTo({top:0, behavior:'auto'})
}

function configureControls() {
  $('#run-select').innerHTML = dataset.runs.map((run) => `<option value="${escapeHtml(run.run_id)}">${escapeHtml(runLabel(run))} · ${escapeHtml(run.run_id)}</option>`).join('')
  $('#run-select').onchange = (event) => openRun(event.target.value)
  all('[data-view]').forEach((button) => {
    button.onclick = () => { state.view = button.dataset.view; renderView(); syncUrl() }
  })
  all('[data-open-lab]').forEach((button) => { button.onclick = () => navigateLab('run') })
  all('[data-lab-view]').forEach((button) => {
    button.onclick = () => navigateLab(button.dataset.labView, button.dataset.labSection || 'overview')
  })
  all('[data-build-step], [data-build-next]').forEach((button) => {
    button.onclick = () => renderBuildStep(button.dataset.buildStep || button.dataset.buildNext)
  })
  all('[data-featured-example]').forEach((button) => {
    button.onclick = () => {
      const available = new Set(dataset.runs.map((run) => run.run_id))
      const missing = featuredRunIds.filter((runId) => !available.has(runId))
      if (missing.length) throw new Error(`featured example is unavailable: ${missing.join(', ')}`)
      const url = new URL(window.location.href)
      url.searchParams.set('view', 'mechanism')
      url.searchParams.set('mechanism_person', 'alba_epidemiologist')
      url.searchParams.set('runs', featuredRunIds.join(','))
      window.location.assign(url)
    }
  })
  $('#reset-configuration').onclick = () => {
    editableConfiguration = clone(defaultConfiguration)
    renderRunSetup()
  }
  $('#run-experiment').onclick = startLiveRun
  $('#open-live-run').onclick = () => {
    state.personId = selectedConfigurationPerson
    openRun(activeRunId, false)
  }
}

function gateChecks(finalCounts, participantCount = 12) {
  const support = Number(finalCounts.support || 0)
  const conditional = Number(finalCounts.conditional || 0)
  const oppose = Number(finalCounts.oppose || 0)
  return [
    {check_id:'executable_support', label:'Executable-now support', observed:support, required:`at least ${Math.ceil(participantCount / 2)}`, passed:support >= Math.ceil(participantCount / 2)},
    {check_id:'aligned_positions', label:'Support or conditional', observed:support + conditional, required:`at least ${Math.ceil(participantCount * 0.75)}`, passed:support + conditional >= Math.ceil(participantCount * 0.75)},
    {check_id:'opposition_ceiling', label:'Opposition', observed:oppose, required:`no more than ${Math.floor(participantCount * 0.1)}`, passed:oppose <= Math.floor(participantCount * 0.1)},
  ]
}

function projectDevelopments(raw) {
  const seen = new Set()
  const developments = []
  for (const event of raw.events || []) {
    for (const observation of event?.patch?.observations_added || []) {
      let content = null
      try { content = JSON.parse(observation.apparent_content) } catch (_error) { continue }
      if (!['exercise_development', 'autonomous_source_bundle', 'authoritative_allocation_package', 'cso_stabilization_bundle'].includes(content?.document_kind)) continue
      const audienceGroup = content.document_kind === 'authoritative_allocation_package'
        ? 'All participants'
        : groupLabels[groupFor(observation.target_entity_id)]
      const developmentId = content.inject_id || content.stabilization_id || content.intervention?.intervention_id || `source_bundle_round_${content.after_round}`
      const pressureContent = (content.documents || []).map((item) => `${sentence(item.source_id)}: ${item.content}`).join(' ')
      const interventionContent = content.intervention?.content ? ` Selected CSO intervention: ${content.intervention.content}` : ''
      const developmentContent = content.content || `${pressureContent}${interventionContent}`.trim()
      const key = `${content.after_round}|${content.document_kind}|${developmentId}|${audienceGroup}|${developmentContent}`
      if (seen.has(key)) continue
      seen.add(key)
      developments.push({
        after_round:content.after_round,
        document_kind:content.document_kind,
        development_id:developmentId,
        source:observation.apparent_source_ref || 'unknown',
        audience_group:audienceGroup,
        content:developmentContent,
        instruction:content.instruction,
        has_stabilization:Boolean(content.stabilization || content.intervention),
      })
    }
  }
  return developments.sort((left, right) => left.after_round - right.after_round || left.document_kind.localeCompare(right.document_kind) || left.audience_group.localeCompare(right.audience_group))
}

function projectLiveRun(raw) {
  const rounds = (raw.outcome?.round_history || []).map((roundDocument) => {
    const stances = Object.entries(roundDocument.stances || {}).sort().map(([personId, stance]) => ({
      person_id:personId,
      person_label:labelPerson(personId),
      group_id:groupFor(personId),
      group_label:groupLabels[groupFor(personId)],
      decision:stance.decision,
      risk:stance.risk,
      request:stance.request,
      rationale:stance.rationale,
    }))
    return {
      round:roundDocument.round,
      decision_counts:countValues(stances.map((stance) => stance.decision)),
      risk_counts:countValues(stances.map((stance) => stance.risk)),
      request_counts:countValues(stances.map((stance) => stance.request)),
      stances,
    }
  })
  const finalCounts = rounds.at(-1).decision_counts
  const agentCount = rounds.at(-1).stances.length
  const outcome = raw.outcome.outcome
  return {
    run_id:raw.run_id,
    condition:raw.arm,
    condition_label:conditionContract(raw.arm).label,
    display_label:`Live · ${conditionContract(raw.arm).label}`,
    replicate:1,
    created_at:raw.created_at,
    model:raw.llm_configuration?.model || liveModel,
    reasoning_effort:raw.llm_configuration?.agent_reasoning_effort || liveReasoning,
    model_calls:raw.model_calls,
    observed_cost:Number(raw.cost || 0),
    outcome,
    outcome_label:outcome === 'joint_response_approved' ? 'Joint response approved' : 'No joint response',
    gate_checks:gateChecks(finalCounts, agentCount),
    agent_count:agentCount,
    rounds,
    developments:projectDevelopments(raw),
    source_signals:raw.outcome?.exercise_injects || [],
    stabilization_events:raw.outcome?.stabilization_events || [],
    cso_records:raw.outcome?.cso_records || [],
    coordination_messages:raw.outcome?.coordination_messages || [],
    configuration:raw.regional_outbreak_configuration || null,
    is_live:true,
  }
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {cache:'no-store', ...options})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `${path} failed with ${response.status}`)
  return body
}

async function startLiveRun() {
  persistEditor()
  $('#run-experiment').disabled = true
  $('#open-live-run').hidden = true
  $('#live-run-status').hidden = false
  $('#live-status-label').textContent = 'Starting authentic run…'
  $('#live-progress-detail').textContent = 'Validating the reviewed configuration and model route.'
  $('#live-progress-bar').style.width = '2%'
  try {
    const started = await apiRequest('api/runs', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        scenario:'regional_outbreak',
        arm_id:selectedCondition,
        execution:'live',
        llm_options:{model:liveModel, agent_reasoning_effort:liveReasoning, max_total_cost:0.74},
        regional_outbreak_configuration:editableConfiguration,
      }),
    })
    activeRunId = started.run_id
    $('#live-run-id').textContent = activeRunId
    $('#live-status-label').textContent = `${editableConfiguration.agents.length} participants are running`
    schedulePoll(250)
  } catch (error) {
    $('#live-status-label').textContent = 'Run did not start'
    $('#live-progress-detail').textContent = error.message
    $('#live-progress-bar').style.width = '0%'
    $('#run-experiment').disabled = false
  }
}

function schedulePoll(delay = 2000) {
  if (pollHandle) window.clearTimeout(pollHandle)
  pollHandle = window.setTimeout(pollLiveRun, delay)
}

async function pollLiveRun() {
  try {
    const raw = await apiRequest(`api/runs/${encodeURIComponent(activeRunId)}`)
    const calls = Number(raw.model_calls || 0)
    const maximumCalls = runtimeConfig?.scenarios?.regional_outbreak?.maximum_live_calls || editableConfiguration.agents.length * 3
    const progress = raw.status === 'completed' ? 100 : Math.min(95, 5 + calls / maximumCalls * 90)
    $('#live-progress-bar').style.width = `${progress}%`
    $('#live-progress-detail').textContent = `${calls} of at most ${maximumCalls} participant calls retained · status ${sentence(raw.status)}`
    if (raw.status === 'completed') {
      const projected = projectLiveRun(raw)
      dataset.runs = [projected, ...dataset.runs.filter((run) => run.run_id !== projected.run_id)]
      state.runId = projected.run_id
      configureControls()
      $('#live-status-label').textContent = projected.outcome_label
      $('#live-progress-detail').textContent = `${projected.model_calls} authentic participant calls retained. Inspect every input, stance, and control event.`
      $('#open-live-run').hidden = false
      $('#run-experiment').disabled = false
      return
    }
    if (['failed', 'interrupted', 'stopped'].includes(raw.status)) throw new Error(raw.error || `run ${raw.status}`)
    schedulePoll()
  } catch (error) {
    $('#live-status-label').textContent = 'Run failed visibly'
    $('#live-progress-detail').textContent = error.message
    $('#run-experiment').disabled = false
  }
}

async function loadRetainedLiveRuns() {
  let history
  try {
    history = await apiRequest('api/runs')
  } catch (error) {
    console.warn(`retained live runs unavailable: ${error.message}`)
    return
  }
  const summaries = (history.runs || []).filter((run) =>
    run.scenario === 'regional_outbreak' && run.execution === 'live' && run.status === 'completed'
  )
  const retained = []
  for (const summary of summaries) {
    try {
      retained.push(projectLiveRun(await apiRequest(`api/runs/${encodeURIComponent(summary.run_id)}`)))
    } catch (error) {
      console.warn(`retained run ${summary.run_id} unavailable: ${error.message}`)
    }
  }
  dataset.runs = [
    ...retained,
    ...dataset.runs.filter((run) => !retained.some((candidate) => candidate.run_id === run.run_id)),
  ]
}

async function loadWorkbench() {
  try {
    const response = await fetch('assets/data.json', {cache:'no-store'})
    if (!response.ok) throw new Error(`public evidence request failed with ${response.status}`)
    const loaded = await response.json()
    if (loaded.schema_version !== 1 || !Array.isArray(loaded.runs) || loaded.runs.length !== 5) throw new Error('public evidence contract is invalid')
    dataset = loaded
    try {
      const probeResponse = await fetch('assets/autonomous-probe.json', {cache:'no-store'})
      if (!probeResponse.ok) throw new Error(`autonomous probe request failed with ${probeResponse.status}`)
      autonomousProbe = await probeResponse.json()
    } catch (error) { console.warn(`autonomous probe unavailable: ${error.message}`) }
    try {
      const forkResponse = await fetch('assets/resource-fork.json', {cache:'no-store'})
      if (!forkResponse.ok) throw new Error(`resource fork request failed with ${forkResponse.status}`)
      resourceFork = await forkResponse.json()
      if (resourceFork.schema_version !== 1 || resourceFork.branches?.length !== 4) throw new Error('resource fork contract is invalid')
    } catch (error) { console.warn(`resource fork unavailable: ${error.message}`) }
    state.runId = dataset.runs[0].run_id
    try { runtimeConfig = await apiRequest('api/config') } catch (error) { console.warn(`live simulator unavailable: ${error.message}`) }
    configureRuntime()
    await loadRetainedLiveRuns()
    applyRunScopeFromUrl()
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
