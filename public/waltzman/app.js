'use strict'

const decisionOrder = ['support', 'conditional', 'defer', 'oppose']
const groupOrder = ['all', 'alba', 'borin', 'cyrenia', 'darsia', 'regional']
const groupLabels = {all:'All roles', alba:'Alba', borin:'Borin', cyrenia:'Cyrenia', darsia:'Darsia', regional:'Regional'}
const preferredModel = 'codex/gpt-5.6-luna'
const preferredAuthoringModel = 'codex/gpt-5.6-luna'
const featuredRunIds = ['run_8924342b56ce', 'run_946a10a820fc', 'run_05acbaea1137']
const caseNetworkRunId = 'run_5010214f2466'
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
const coordinationPositionBindings = [
  ['coordinator', 'mission_coordinator'],
  ['technical_reviewer', 'technical_validation_lead'],
  ['policy_reviewer', 'sovereignty_policy_representative'],
  ['local_health_reviewer', 'local_public_health_liaison'],
  ['partner_representative', 'partner_representative'],
]
const coordinationConcernBindings = [
  ['technical', 'technical_pressure_source', 'technical_concern', 'technical_pressure_message'],
  ['policy', 'policy_pressure_source', 'policy_concern', 'policy_pressure_message'],
  ['local', 'local_pressure_source', 'local_concern', 'local_pressure_message'],
]

let dataset = null
let runtimeConfig = null
let autonomousProbe = null
let resourceFork = null
let caseNetworkRun = null
let caseNetworkLoad = null
let caseNetworkError = null
let caseGraphMode = 'system'
let defaultConfiguration = null
let editableConfiguration = null
let selectedConfigurationPerson = 'alba_epidemiologist'
let selectedCondition = 'adaptive_cso_stabilization'
let liveModel = null
let liveReasoning = 'medium'
let activeRunId = null
let pollHandle = null
let authoringDraft = null
let selectedAuthoringPerson = null
let authoredRunPollHandle = null
let authoredRunId = null
let authoredRunProgressSequence = 0
let authoredRunPollFailures = 0
let authoringBusy = false
let authoredResult = null
let authoredResultRoundIndex = 0

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
  guideStep:0,
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

function coordinationConfigurationFromProposal(proposal) {
  const workflow = proposal.workflow || {}
  const people = new Map((proposal.people || []).map((item) => [item.entity_id, item]))
  const objects = new Map((proposal.objects || []).map((item) => [item.entity_id, item]))
  const information = new Map((proposal.information || []).map((item) => [item.information_id, item]))
  const messages = new Map((workflow.messages || []).map((item) => [item.message_id, item]))
  const places = new Map((proposal.places || []).map((item) => [item.place_id, item]))
  const boundaries = new Map((proposal.analytical_boundaries || []).map((item) => [item.boundary_id, item]))
  return {
    template_id:'coordination_decision_v1',
    title:proposal.title,
    description:proposal.description,
    condition:workflow.condition,
    people:coordinationPositionBindings.map(([positionKind, entityId]) => {
      const person = people.get(entityId)
      return {
        position_kind:positionKind,
        label:person.label,
        position:person.position,
        disposition:person.disposition,
        memories:person.memories,
        behavioral_profile:person.behavioral_profile,
      }
    }),
    concerns:coordinationConcernBindings.map(([concernKind, sourceId, informationId, messageId]) => ({
      concern_kind:concernKind,
      source_label:objects.get(sourceId).label,
      source_description:objects.get(sourceId).description,
      topic:information.get(informationId).label,
      content:information.get(informationId).content,
      delivery_minutes:messages.get(messageId).delivery_minutes,
    })),
    collective_goal:{
      label:workflow.collective_goal.label,
      description:workflow.collective_goal.description,
      acceptable_outcomes:workflow.collective_goal.acceptable_outcomes,
      constraints:workflow.collective_goal.constraints,
    },
    places:{
      partnership_label:places.get('partnership_hub').label,
      partnership_description:places.get('partnership_hub').description,
      source_site_label:places.get('source_operations_site').label,
      source_site_description:places.get('source_operations_site').description,
      registry_label:places.get('external_registry_site').label,
      registry_description:places.get('external_registry_site').description,
    },
    analytical_boundaries:{
      partnership_label:boundaries.get('deployment_partnership').label,
      partnership_description:boundaries.get('deployment_partnership').description,
      source_group_label:boundaries.get('pressure_source_ensemble').label,
      source_group_description:boundaries.get('pressure_source_ensemble').description,
    },
    meeting_days:workflow.meeting_days,
    deadline_day:workflow.deadline_day,
    analysis_ids:workflow.analysis.analysis_ids,
    assumptions:workflow.assumptions,
    known_omissions:workflow.known_omissions,
    fidelity_questions:proposal.fidelity_questions,
    unresolved_questions:proposal.unresolved_questions || [],
  }
}

function renderAuthoringCoverage(proposal) {
  const workflow = proposal.workflow || {}
  if (workflow.template_id === 'influence_network_v1') {
    const routes = (workflow.deliveries || []).reduce((total, item) => total + (item.recipient_ids || []).length, 0)
    const broadcasts = (workflow.deliveries || []).filter((item) => item.recipient_ids?.length === proposal.people.length).length
    $('#create-coverage-summary').textContent = `Execution coverage · ${proposal.people.length} people, ${workflow.deliveries.length} messages, ${routes} directed deliveries, ${workflow.round_minutes.length} decision rounds`
    $('#create-coverage-detail').innerHTML = `
      <p><strong>Runs as configured</strong><span>Messages accumulate through explicit routes. At each scheduled decision round, each person uses their edited character, memory, and available messages to choose support, conditional support, deferral, or opposition with Luna.</span></p>
      <p><strong>Information topology</strong><span>${broadcasts} broadcast message${broadcasts === 1 ? '' : 's'} plus targeted recipient sets compile into explicit directed routes. Delivery is not treated as belief or persuasion.</span></p>
      <p><strong>Prebuilt machinery</strong><span>Exact message fan-out, explicit round triggers, configurable public feedback, stance recording, and the configured collective decision gate.</span></p>
      <p><strong>Current boundary</strong><span>The people, sources, messages, recipients, personalities, memories, rounds, and gate are configurable. Arbitrary physical-world actions and new mechanism code are not generated by this workflow.</span></p>`
    return
  }
  if (workflow.template_id === 'coordination_decision_v1') {
    $('#create-coverage-summary').textContent = `Execution coverage · ${proposal.people.length} people, ${workflow.messages.length} incoming influences, one reviewed decision process`
    $('#create-coverage-detail').innerHTML = `
      <p><strong>Runs as configured</strong><span>People use the edited character, memory, goals, beliefs, and delivered information to choose actions with Luna.</span></p>
      <p><strong>Prebuilt world machinery</strong><span>Four decision meetings; technical input to the technical reviewer, policy input to the policy reviewer, and local-health input to the local reviewer; commitment and issue records; verification; and the terminal decision gate.</span></p>
      <p><strong>Descriptive context</strong><span>Names, place descriptions, analytical group labels, assumptions, omissions, and fidelity questions help interpretation but do not create new causal powers.</span></p>
      <p><strong>Fixed in this template</strong><span>Exactly five decision positions, three incoming-influence channels, the meeting cadence, and the available action interfaces. Natural-language authoring cannot invent new executable mechanisms here yet.</span></p>`
    return
  }
  $('#create-coverage-summary').textContent = `Execution coverage · ${draftTemplateLabel(workflow.template_id)}`
  $('#create-coverage-detail').innerHTML = `<p><strong>Bounded workflow</strong><span>This draft populates one reviewed executable template. Other described entities remain contextual unless the compiled workflow names them.</span></p><p><strong>Not open-ended</strong><span>The authoring model cannot generate mechanism code or silently make an unsupported behavior executable.</span></p>`
}

function renderInfluenceNetworkEditor(proposal) {
  const editor = $('#create-network-editor')
  const workflow = proposal.workflow || {}
  if (workflow.template_id !== 'influence_network_v1') {
    editor.hidden = true
    return
  }
  editor.hidden = false
  $('#create-network-title').value = proposal.title
  $('#create-network-description').value = proposal.description
  $('#create-network-question').value = workflow.collective_question
  $('#create-network-rounds').value = workflow.round_minutes.join(', ')
  $('#create-network-feedback').value = workflow.round_feedback || 'stances_and_reasons'
  $('#create-network-min-support').value = workflow.decision_rule.minimum_support
  $('#create-network-min-combined').value = workflow.decision_rule.minimum_support_or_conditional
  $('#create-network-max-oppose').value = workflow.decision_rule.maximum_oppose
  const objects = new Map((proposal.objects || []).map((item) => [item.entity_id, item]))
  const information = new Map((proposal.information || []).map((item) => [item.information_id, item]))
  $('#create-network-deliveries').innerHTML = workflow.deliveries.map((delivery) => {
    const source = objects.get(delivery.source_id)
    const message = information.get(delivery.information_id)
    const recipients = proposal.people.map((person) => `<label class="create-network-recipient"><input type="checkbox" data-recipient-id="${escapeHtml(person.entity_id)}" ${delivery.recipient_ids.includes(person.entity_id) ? 'checked' : ''}>${escapeHtml(person.label)}</label>`).join('')
    return `<article data-delivery-id="${escapeHtml(delivery.delivery_id)}"><header><strong>${escapeHtml(message?.label || sentence(delivery.delivery_id))}</strong><small>${delivery.recipient_ids.length === proposal.people.length ? 'Broadcast to everyone' : `${delivery.recipient_ids.length} selected recipients`}</small></header><label>Source name<input data-network-field="source_label" value="${escapeHtml(source?.label || delivery.source_id)}"></label><label>Message content<textarea data-network-field="content" rows="3">${escapeHtml(message?.content || '')}</textarea></label><label>Delivery time<input data-network-field="delivery_minutes" type="number" min="1" step="1" value="${Number(delivery.delivery_minutes)}"></label><fieldset><legend>Recipients</legend><div>${recipients}</div></fieldset></article>`
  }).join('')
  $('#create-network-status').textContent = 'Saving rebuilds the exact message routes and makes no model call.'
}

function renderCoordinationScenarioEditor(proposal) {
  const editor = $('#create-scenario-editor')
  if (proposal.workflow?.template_id !== 'coordination_decision_v1') {
    editor.hidden = true
    return
  }
  const configuration = coordinationConfigurationFromProposal(proposal)
  editor.hidden = false
  $('#create-scenario-title').value = configuration.title
  $('#create-scenario-description').value = configuration.description
  $('#create-scenario-condition').value = configuration.condition
  $('#create-scenario-goal').value = configuration.collective_goal.description
  $('#create-scenario-constraints').value = configuration.collective_goal.constraints.join('\n')
  const recipients = {technical:'Technical reviewer', policy:'Policy reviewer', local:'Local-health reviewer'}
  $('#create-scenario-concerns').innerHTML = configuration.concerns.map((concern) => `<article data-concern-kind="${escapeHtml(concern.concern_kind)}"><strong>${escapeHtml(sentence(concern.concern_kind))}</strong><small>Delivered to: ${escapeHtml(recipients[concern.concern_kind])}</small><label>Source<input data-concern-field="source_label" value="${escapeHtml(concern.source_label)}"></label><label>Information delivered<textarea data-concern-field="content" rows="3">${escapeHtml(concern.content)}</textarea></label><label>Arrival time<input data-concern-field="delivery_minutes" type="number" min="1" step="1" value="${Number(concern.delivery_minutes)}"></label></article>`).join('')
  $('#create-scenario-status').textContent = 'Saving creates a new typed revision and makes no model call.'
}

function readStateFromUrl() {
  const params = new URLSearchParams(window.location.search)
  const requestedView = params.get('view')
  if (['overview', 'guide', 'case', 'create', 'run', 'compare', 'mechanism', 'inspect', 'method'].includes(requestedView)) state.view = requestedView
  const requestedGuideStep = Number(params.get('guide_step'))
  if (Number.isInteger(requestedGuideStep) && requestedGuideStep >= 1 && requestedGuideStep <= 7) state.guideStep = requestedGuideStep - 1
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
  for (const key of ['run', 'round', 'person', 'group', 'mechanism_person', 'section', 'draft', 'authored_run', 'guide_step']) url.searchParams.delete(key)
  if (state.view === 'guide') url.searchParams.set('guide_step', String(state.guideStep + 1))
  if (state.view === 'inspect') {
    url.searchParams.set('run', state.runId)
    url.searchParams.set('round', String(state.round))
    url.searchParams.set('person', state.personId)
    if (state.group !== 'all') url.searchParams.set('group', state.group)
  }
  if (state.view === 'mechanism') url.searchParams.set('mechanism_person', state.mechanismPersonId)
  if (['compare', 'inspect'].includes(state.view)) url.searchParams.set('section', state.labSection)
  if (state.view === 'create' && authoringDraft?.draft_id) url.searchParams.set('draft', authoringDraft.draft_id)
  if (state.view === 'create' && authoredRunId) url.searchParams.set('authored_run', authoredRunId)
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

const guideNodes = [
  {id:'guide_clinic', kind:'thing', label:'Riverside clinic', description:'A clinic whose backup power fails at 6:00 PM.'},
  {id:'guide_generator', kind:'thing', label:'Emergency generator', description:'A physical generator held at the municipal depot.'},
  {id:'guide_truck', kind:'thing', label:'Delivery truck', description:'The vehicle that can move the generator to the clinic.'},
  {id:'guide_depot_manager', kind:'person', label:'Depot manager', description:'Can release the generator but cannot choose the route or drive the truck.'},
  {id:'guide_dispatcher', kind:'person', label:'Dispatcher', description:'Can choose and communicate a route but cannot release or transport the generator.'},
  {id:'guide_driver', kind:'person', label:'Driver', description:'Can drive the truck when a generator, route, and valid permit are available.'},
  {id:'guide_clinic_manager', kind:'person', label:'Clinic manager', description:'Can prepare the clinic to receive and connect the generator.'},
  {id:'guide_delivery_gate', kind:'mechanism', label:'Delivery readiness', description:'A world rule: release, route, transport, and receipt must all be ready before delivery can occur.'},
  {id:'guide_allocation_message', kind:'information', label:'“Generator allocated elsewhere”', description:'An unverified message delivered only to the depot manager.'},
  {id:'guide_bridge_message', kind:'information', label:'“Bridge is closed”', description:'An unverified message delivered only to the dispatcher.'},
  {id:'guide_permit_message', kind:'information', label:'“Truck permit is invalid”', description:'An unverified message delivered only to the driver.'},
  {id:'guide_power_message', kind:'information', label:'“Clinic power is restored”', description:'An unverified message delivered only to the clinic manager.'},
]

const guideEdges = [
  {id:'guide_depot_releases', kind:'authorizes_release', source:'guide_depot_manager', target:'guide_generator', enabled:true, description:'The depot manager may authorize release.', routeIds:['guide_depot_releases']},
  {id:'guide_generator_loaded', kind:'loaded_onto', source:'guide_generator', target:'guide_truck', enabled:true, description:'The released generator may be loaded onto the truck.', routeIds:['guide_generator_loaded']},
  {id:'guide_dispatcher_routes', kind:'assigns_route', source:'guide_dispatcher', target:'guide_truck', enabled:true, description:'The dispatcher may assign the truck a route.', routeIds:['guide_dispatcher_routes']},
  {id:'guide_driver_moves', kind:'operates', source:'guide_driver', target:'guide_truck', enabled:true, description:'The driver may operate the truck.', routeIds:['guide_driver_moves']},
  {id:'guide_truck_delivers', kind:'carries_to', source:'guide_truck', target:'guide_clinic', enabled:true, description:'The truck may carry the generator to the clinic.', routeIds:['guide_truck_delivers']},
  {id:'guide_clinic_receives', kind:'prepares_to_receive', source:'guide_clinic_manager', target:'guide_clinic', enabled:true, description:'The clinic manager may prepare for and accept delivery.', routeIds:['guide_clinic_receives']},
  {id:'guide_depot_ready', kind:'requires_release', source:'guide_depot_manager', target:'guide_delivery_gate', enabled:true, description:'Generator release is one required part of readiness.', routeIds:['guide_depot_ready']},
  {id:'guide_dispatch_ready', kind:'requires_route', source:'guide_dispatcher', target:'guide_delivery_gate', enabled:true, description:'A usable route is one required part of readiness.', routeIds:['guide_dispatch_ready']},
  {id:'guide_driver_ready', kind:'requires_transport', source:'guide_driver', target:'guide_delivery_gate', enabled:true, description:'Transport is one required part of readiness.', routeIds:['guide_driver_ready']},
  {id:'guide_clinic_ready', kind:'requires_receipt', source:'guide_clinic_manager', target:'guide_delivery_gate', enabled:true, description:'Receiving capacity is one required part of readiness.', routeIds:['guide_clinic_ready']},
  {id:'guide_gate_delivers', kind:'enables_delivery', source:'guide_delivery_gate', target:'guide_clinic', enabled:true, description:'When every requirement is ready, delivery can proceed.', routeIds:['guide_gate_delivers']},
  {id:'guide_allocation_delivered', kind:'delivered_to', source:'guide_allocation_message', target:'guide_depot_manager', enabled:true, description:'Only the depot manager receives this message.', routeIds:['guide_allocation_delivered']},
  {id:'guide_bridge_delivered', kind:'delivered_to', source:'guide_bridge_message', target:'guide_dispatcher', enabled:true, description:'Only the dispatcher receives this message.', routeIds:['guide_bridge_delivered']},
  {id:'guide_permit_delivered', kind:'delivered_to', source:'guide_permit_message', target:'guide_driver', enabled:true, description:'Only the driver receives this message.', routeIds:['guide_permit_delivered']},
  {id:'guide_power_delivered', kind:'delivered_to', source:'guide_power_message', target:'guide_clinic_manager', enabled:true, description:'Only the clinic manager receives this message.', routeIds:['guide_power_delivered']},
]

const guidePeopleAndThings = ['guide_clinic', 'guide_generator', 'guide_truck', 'guide_depot_manager', 'guide_dispatcher', 'guide_driver', 'guide_clinic_manager']
const guideWorld = [...guidePeopleAndThings, 'guide_delivery_gate']
const guideMessages = ['guide_allocation_message', 'guide_bridge_message', 'guide_permit_message', 'guide_power_message']
const guideInformationEdges = ['guide_allocation_delivered', 'guide_bridge_delivered', 'guide_permit_delivered', 'guide_power_delivered']
const guideSteps = [
  {
    kicker:'Start with the objective', title:'Get one generator to the clinic by 6:00 PM.',
    body:'This is the coordination situation: a concrete outcome that requires several people and things to line up in time.',
    nodes:['guide_clinic', 'guide_generator'], edges:[], focus:['guide_clinic', 'guide_generator'],
    facts:[['Deadline','6:00 PM'], ['Generator','At municipal depot'], ['Clinic','Backup power failing']],
    language:[['World','Everything that exists and can change in the simulation.'], ['Coordination situation','An outcome that depends on several local actions fitting together.']],
    takeaway:'Begin with what must happen—not with agents, votes, or institutional labels.',
  },
  {
    kicker:'Meet the participants', title:'No single person can complete the delivery.',
    body:'Each person perceives only part of the situation and can attempt only actions available to them. The generator and truck do not decide anything, but people can act through them.',
    nodes:guidePeopleAndThings, edges:['guide_depot_releases', 'guide_dispatcher_routes', 'guide_driver_moves', 'guide_clinic_receives'], focus:['guide_depot_manager', 'guide_dispatcher', 'guide_driver', 'guide_clinic_manager'],
    facts:[['Depot manager','Releases generator'], ['Dispatcher','Chooses route'], ['Driver','Moves truck'], ['Clinic manager','Receives delivery']],
    language:[['Person','A simulated individual who perceives, remembers, reasons, and attempts actions.'], ['Thing','A resource or technical object that can be used or moved but does not act autonomously.']],
    takeaway:'Positions shape access and capability; they do not dictate what a person decides.',
  },
  {
    kicker:'Connect the dependencies', title:'The arrows show what can travel or be attempted.',
    body:'Release, routing, transport, and receipt must all be ready. The process node applies that world rule; it is not another person making a decision.',
    nodes:guideWorld, edges:guideEdges.filter((edge) => !guideInformationEdges.includes(edge.id)).map((edge) => edge.id), focus:['guide_delivery_gate'],
    facts:[['Release','Generator can be loaded'], ['Route','Truck has a usable path'], ['Transport','Driver can depart'], ['Receipt','Clinic can accept delivery']],
    language:[['Arrow','A possible path—not evidence that something actually traveled.'], ['Process','A world mechanism that applies a rule or consequence without pretending to be a person.']],
    takeaway:'The network represents concrete dependencies beneath the collective outcome.',
  },
  {
    kicker:'Add uneven inputs', title:'Four different messages enter through four different channels.',
    body:'There is no shared slogan. Each unverified message targets a locally relevant uncertainty. At this point it could be influence, error, or ordinary disruption.',
    nodes:[...guideWorld, ...guideMessages], edges:guideEdges.map((edge) => edge.id), focus:guideMessages,
    facts:[['Depot','“Allocated elsewhere”'], ['Dispatcher','“Bridge closed”'], ['Driver','“Permit invalid”'], ['Clinic','“Power restored”']],
    language:[['Message','Information delivered to someone. Its presence does not make it true.'], ['Heterogeneous inputs','Different local signals that can still produce an aligned system-level effect.']],
    takeaway:'A coordinated effect does not require everyone to receive or believe the same story.',
  },
  {
    kicker:'Observe local reactions', title:'Each person adds a different prerequisite before acting.',
    body:'The people interpret their own messages in light of their memories, goals, relationships, and uncertainty. The simulation does not directly assign their decisions.',
    nodes:[...guideWorld, ...guideMessages], edges:guideEdges.map((edge) => edge.id), focus:['guide_depot_manager', 'guide_dispatcher', 'guide_driver', 'guide_clinic_manager'],
    facts:[['Depot manager','Verify allocation'], ['Dispatcher','Confirm bridge status'], ['Driver','Validate permit'], ['Clinic manager','Recheck power']],
    language:[['Prerequisite','Something a person now believes must be resolved before acting.'], ['Local reaction','A person’s response to what they perceived—not a centrally dictated vote.']],
    takeaway:'The local reasons differ even when their practical effect points in the same direction.',
  },
  {
    kicker:'See the collective effect', title:'The delivery stalls without a shared stop order.',
    body:'Every required action is now waiting on something else. Nobody needs to oppose the clinic or coordinate with any message source for the joint outcome to fail.',
    nodes:[...guideWorld, ...guideMessages], edges:guideEdges.map((edge) => edge.id), focus:['guide_delivery_gate'], blocked:true,
    facts:[['Release','Waiting'], ['Route','Waiting'], ['Transport','Waiting'], ['Receipt','Waiting']],
    language:[['Blocked pathway','A route that exists but cannot currently carry the required action or resource.'], ['Coordination readiness','Whether the required local actions can presently fit together.']],
    takeaway:'A macro-level coordination failure can emerge from several locally reasonable pauses.',
  },
  {
    kicker:'Read the system—not only the messages', title:'The useful evidence is the change in the network.',
    body:'The simulator can inspect which reliance paths weakened, which prerequisites appeared, where bottlenecks formed, and whether the group’s ability to act changed over time.',
    nodes:[...guideWorld, ...guideMessages], edges:guideEdges.map((edge) => edge.id), focus:['guide_delivery_gate'], blocked:true,
    facts:[['Reliance paths','Four weakened'], ['New prerequisites','Four unresolved'], ['Delivery readiness','Blocked'], ['Shared narrative','None required']],
    language:[['Coordination-level effect','A change in the system’s ability to produce joint action.'], ['Detection question','Is the directional change consistent with influence, ordinary disruption, or legitimate disagreement?']],
    takeaway:'This is the bridge to Waltzman: detect directional changes in coordination conditions across heterogeneous local interactions.',
  },
]

function guideProjection(step) {
  const nodeIds = new Set(step.nodes)
  const edgeIds = new Set(step.edges)
  return {
    nodes:guideNodes.filter((node) => nodeIds.has(node.id)),
    edges:guideEdges.filter((edge) => edgeIds.has(edge.id) && nodeIds.has(edge.source) && nodeIds.has(edge.target)).map((edge) => ({
      ...edge,
      enabled:step.blocked && !guideInformationEdges.includes(edge.id) ? false : edge.enabled,
    })),
  }
}

function renderGuideSelection(item, relationship = false) {
  $('#guide-selection').innerHTML = `<strong>${escapeHtml(item.label || sentence(item.id))}:</strong> ${escapeHtml(item.description || (relationship ? 'A retained possible path.' : 'A simulated world entity.'))}`
}

function renderGuideGraph(step) {
  const graph = $('#guide-graph')
  const projection = guideProjection(step)
  window.CyberneticGraph.render(graph, {
    nodes:projection.nodes,
    edges:projection.edges,
    boundaries:[], world:null, trajectory:{nodes:[], edges:[]},
    graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:'causal', event:{event_id:`guide_step_${state.guideStep + 1}`, state_revision:state.guideStep, focus_ids:step.focus, focus_edges:[], spatial_focus_ids:[], spatial_link_ids:[], boundary_ids:[]}, initialRevision:state.guideStep,
    selectedNodeId:null, selectedEdgeId:null, boundary:null, collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const node = projection.nodes.find((candidate) => candidate.id === nodeId)
      if (node) renderGuideSelection(node)
    },
    onSelectEdge:(edge) => renderGuideSelection(edge, true),
  })
}

function renderGuide() {
  const step = guideSteps[state.guideStep]
  $('#guide-step-count').textContent = `Step ${state.guideStep + 1} of ${guideSteps.length}`
  $('#guide-step-kicker').textContent = step.kicker
  $('#guide-step-title').textContent = step.title
  $('#guide-step-body').textContent = step.body
  $('#guide-step-facts').innerHTML = step.facts.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')
  $('#guide-step-language').innerHTML = step.language.map(([term, definition]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join('')
  $('#guide-step-takeaway').innerHTML = `<span>Why this matters</span><strong>${escapeHtml(step.takeaway)}</strong>`
  $('#guide-progress').innerHTML = guideSteps.map((candidate, index) => `<button type="button" data-guide-step="${index}" class="${index === state.guideStep ? 'active' : ''}" aria-label="Open step ${index + 1}: ${escapeHtml(candidate.title)}" aria-current="${index === state.guideStep ? 'step' : 'false'}">${index + 1}</button>`).join('')
  $('#guide-previous').disabled = state.guideStep === 0
  $('#guide-next').textContent = state.guideStep === guideSteps.length - 1
    ? 'Continue: Open full outbreak case →'
    : `Next: ${guideSteps[state.guideStep + 1].kicker} →`
  all('[data-guide-step]').forEach((button) => {
    button.onclick = () => { state.guideStep = Number(button.dataset.guideStep); renderGuide(); syncUrl() }
  })
  renderGuideGraph(step)
}

function advanceGuide(direction) {
  const next = state.guideStep + direction
  if (next >= guideSteps.length) {
    state.view = 'case'
    renderView()
    syncUrl()
    window.scrollTo({top:0, behavior:'auto'})
    return
  }
  state.guideStep = Math.max(0, next)
  renderGuide()
  syncUrl()
}

function caseSystemProjection(raw) {
  const indexed = new Map((raw.nodes || []).map((node) => [node.id, node]))
  const sourceIds = [
    'technical_pressure_source',
    'legal_pressure_source',
    'logistics_pressure_source',
    'community_pressure_source',
  ]
  const exactNodes = [
    ...sourceIds.map((id) => indexed.get(id)).filter(Boolean),
    indexed.get('outbreak_source_delivery'),
    indexed.get('outbreak_stance_recorder'),
    indexed.get('outbreak_decision'),
    indexed.get('regional_allocation_authority'),
    indexed.get('cso_intervention_recorder'),
  ].filter(Boolean)
  const groups = [
    ['alba_network', 'Alba response network', 'Five people working through Alba’s evidence, policy, operations, community, and supply relationships.'],
    ['borin_network', 'Borin response network', 'Five people working through Borin’s evidence, policy, operations, community, and supply relationships.'],
    ['cyrenia_network', 'Cyrenia response network', 'Five people working through Cyrenia’s evidence, policy, operations, community, and supply relationships.'],
    ['darsia_network', 'Darsia response network', 'Five people working through Darsia’s evidence, policy, operations, community, and supply relationships.'],
    ['regional_network', 'Regional coordination network', 'Six people coordinating science, logistics, law, finance, public legitimacy, and the shared decision.'],
    ['cso_network', 'Defensive coordination cell', 'Three observer roles can detect, diagnose, and select a bounded intervention; they cannot choose participant stances.'],
  ].map(([id, label, description]) => ({id, label, description, kind:'analytical_boundary', state:{projection:'analytical_group'}}))
  const edges = []
  const addEdge = (source, target, description) => edges.push({
    id:`case_${source}_to_${target}`,
    kind:'connection', source, target, enabled:true, description, routeIds:[],
  })
  sourceIds.forEach((source) => addEdge(source, 'outbreak_source_delivery', 'A retained external source contributes a bounded signal; it cannot choose a participant stance.'))
  const participantGroups = ['alba_network', 'borin_network', 'cyrenia_network', 'darsia_network', 'regional_network']
  participantGroups.forEach((group) => {
    addEdge('outbreak_source_delivery', group, 'Analytical aggregation of exact observation routes carrying locally relevant signals to people in this network.')
    addEdge(group, 'outbreak_stance_recorder', 'Analytical aggregation of the network members’ exact autonomous stance routes.')
  })
  addEdge('outbreak_stance_recorder', 'outbreak_decision', 'The exact decision mechanism evaluates the retained participant stances against the fixed gate.')
  addEdge('outbreak_decision', 'cso_network', 'The defensive cell observes retained decision-environment evidence; it cannot edit participant decisions.')
  addEdge('cso_network', 'cso_intervention_recorder', 'The defensive planner may select one bounded response class from its authorized catalogue.')
  addEdge('regional_allocation_authority', 'cso_intervention_recorder', 'External resource facts require independent custody, release authority, and verification.')
  participantGroups.forEach((group) => addEdge('cso_intervention_recorder', group, 'Intervention facts enter the world; people in the network reassess them autonomously.'))
  return {nodes:[...exactNodes, ...groups], edges}
}

function caseExactProjection(raw) {
  return {
    nodes:raw.nodes || [],
    edges:(raw.edges || []).map((edge) => ({
      ...edge,
      kind:edge.kind || 'connection',
      routeIds:edge.exact_route_ids || [edge.id],
    })),
  }
}

function renderCaseNetworkSelection(item, relationship = false) {
  const inspector = $('#case-network-inspector')
  inspector.innerHTML = `<strong>${escapeHtml(item.label || sentence(item.id))}</strong><span>${escapeHtml(relationship ? `${sentence(item.kind)} · ${item.description || 'Retained connection.'}` : `${sentence(item.kind)} · ${item.description || 'Retained entity.'}`)}</span>`
}

function renderCaseNetworkGraph() {
  const graph = $('#case-network-graph')
  if (!graph) return
  all('[data-case-graph]').forEach((button) => {
    const active = button.dataset.caseGraph === caseGraphMode
    button.classList.toggle('active', active)
    button.setAttribute('aria-pressed', String(active))
  })
  if (caseNetworkError) {
    graph.classList.remove('react-canvas-host')
    graph.innerHTML = `<p class="case-network-unavailable"><strong>Network unavailable.</strong> ${escapeHtml(caseNetworkError)}</p>`
    $('#case-network-status').textContent = 'The completed result remains available below; the network projection failed visibly.'
    return
  }
  if (!caseNetworkRun || !window.CyberneticGraph) {
    graph.classList.remove('react-canvas-host')
    graph.innerHTML = '<p>Loading the retained network…</p>'
    return
  }
  const projection = caseGraphMode === 'exact' ? caseExactProjection(caseNetworkRun) : caseSystemProjection(caseNetworkRun)
  if (!graph.classList.contains('case-network-mounted')) graph.innerHTML = ''
  graph.classList.add('react-canvas-host', 'case-network-mounted')
  window.CyberneticGraph.render(graph, {
    nodes:projection.nodes,
    edges:projection.edges,
    boundaries:[],
    world:null,
    trajectory:{nodes:[], edges:[]},
    graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:'causal',
    event:null,
    initialRevision:caseNetworkRun.initial_revision ?? 0,
    selectedNodeId:null,
    selectedEdgeId:null,
    boundary:null,
    collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const node = projection.nodes.find((candidate) => candidate.id === nodeId)
      if (node) renderCaseNetworkSelection(node)
    },
    onSelectEdge:(edge) => renderCaseNetworkSelection(edge, true),
  })
  $('#case-network-status').textContent = caseGraphMode === 'exact'
    ? `${projection.nodes.length} exact entities · ${projection.edges.length} exact routes · drag, zoom, or select any item.`
    : `${projection.nodes.length} visible groups, sources, and mechanisms · analytical grouping over ${caseNetworkRun.nodes.length} exact entities and ${caseNetworkRun.edges.length} routes.`
}

async function ensureCaseNetwork() {
  if (caseNetworkRun || caseNetworkLoad) return caseNetworkLoad
  caseNetworkLoad = fetch('assets/case-network.json', {cache:'no-store'})
    .then((response) => {
      if (!response.ok) throw new Error(`retained network request failed with ${response.status}`)
      return response.json()
    })
    .then((artifact) => {
      if (artifact.schema_version !== 1 || artifact.status !== 'completed' || artifact.scenario !== 'regional_outbreak' || artifact.source_run_id !== caseNetworkRunId || !artifact.nodes?.length || !artifact.edges?.length) throw new Error('the retained outbreak network is incomplete')
      caseNetworkRun = artifact
      caseNetworkError = null
      if (state.view === 'case') renderCaseNetworkGraph()
    })
    .catch((error) => {
      caseNetworkError = error.message
      if (state.view === 'case') renderCaseNetworkGraph()
    })
  return caseNetworkLoad
}

function renderResearchCase() {
  if (!resourceFork?.branches?.length) {
    $('#research-case-runs').innerHTML = '<p class="case-data-error"><strong>Research case unavailable.</strong> The exact checkpoint evidence could not be loaded.</p>'
    $('#case-open-comparison').disabled = true
    return
  }

  $('#case-open-comparison').disabled = false
  const stories = {
    no_intervention:{label:'Nothing changes', short:'No new help arrives.', event:'No resource package enters the world.', result:'Without new capacity, most agents become less ready to proceed. Twenty-one defer the decision.', why:'The operational shortages remain, so the group has no executable path forward.'},
    partial:{label:'Two real resources', short:'Some shortages are fixed.', event:'Verified laboratory capacity and clinicians become available.', result:'Most agents become willing to proceed if their remaining conditions are met, but three still defer.', why:'The package resolves two capacity gaps, not the coalition’s other operational, legal, and scientific prerequisites.'},
    complete:{label:'Six real resources', short:'Every named shortage is fixed.', event:'All six requested resources are verified, assigned, and committed.', result:'Twenty-four agents become conditionally ready. Two still defer, so the group does not approve the response.', why:'Capacity is no longer the main blocker. Legal authority and the comparability of the scientific evidence remain unresolved.'},
    false_claim:{label:'Six false claims', short:'The audit catches them.', event:'Six resources are announced, but the simulated audit finds that none has a valid custodian.', result:'The claims change no real capacity. Twenty-one agents defer—the same final distribution as when nothing is provided.', why:'The intervention is not credible because the world model cannot verify that the resources exist or can be used.'},
  }
  const blockerSummaries = {
    no_intervention:{regional_logistics_coordinator:'The required resources still have no verified owners, release authority, or delivery sequence.', regional_coordinator:'Operational capacity, legal authority, and comparable evidence all remain unresolved.', regional_scientific_advisor:'The available datasets still cannot support one shared operational conclusion.'},
    partial:{regional_logistics_coordinator:'Several deployment resources and their delivery sequence remain unresolved.', regional_coordinator:'The partial package does not resolve legal authority or the evidence gap.', regional_scientific_advisor:'The available datasets still need a documented comparability assessment.'},
    complete:{regional_logistics_coordinator:'Remaining deployment dependencies need named owners and a timed release sequence.', regional_coordinator:'National data custody and independent audit authority still need a written protocol.', regional_scientific_advisor:'The three datasets still need a documented comparability and actionability assessment.'},
    false_claim:{regional_logistics_coordinator:'The announced resources have no verified custody or release authority.', regional_coordinator:'The resource claims fail audit and leave every operational dependency unresolved.', regional_scientific_advisor:'The allocation claims contradict the audit and cannot count as usable capacity.'},
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
    const story = stories[branch.id]
    const gateText = support >= resourceFork.gate.minimum_support
      ? 'The group approves the response.'
      : `The group does not approve: ${support} agents give an unconditional yes, and the rule requires ${resourceFork.gate.minimum_support}.`
    $('#case-branch-detail').innerHTML = `<div class="fork-explanation">
      <div><span>What changed</span><strong>${escapeHtml(story.event)}</strong></div>
      <div><span>How the agents responded</span><strong>${escapeHtml(story.result)}</strong></div>
      <div><span>Why</span><strong>${escapeHtml(story.why)}</strong></div>
      <div class="fork-verdict"><span>Collective result</span><strong>${escapeHtml(gateText)}</strong><small>${verified} verified resource${verified === 1 ? '' : 's'}${contradicted ? ` · ${contradicted} rejected by the audit` : ''} · ${ready} agents ready only conditionally or fully</small></div>
    </div>`
    const evidenceIds = ['regional_logistics_coordinator', 'regional_coordinator', 'regional_scientific_advisor']
    $('#case-evidence-records').innerHTML = evidenceIds.map((personId) => {
      const stance = branch.final_stances[personId]
      return `<article><header><span>${escapeHtml(labelPerson(personId))}</span>${decisionPill(stance.decision)}</header><strong>${escapeHtml(blockerSummaries[branch.id][personId])}</strong><details><summary>Read the agent's exact reasoning</summary><p>${escapeHtml(stance.rationale)}</p></details></article>`
    }).join('')
  }
  $('#research-case-runs').innerHTML = resourceFork.branches.map((branch) => `<button type="button" class="research-case-run ${branch.id === state.caseBranch ? 'active' : ''}" data-case-branch="${escapeHtml(branch.id)}">
    <header><span>${escapeHtml(stories[branch.id].short)}</span><h4>${escapeHtml(stories[branch.id].label)}</h4></header>
    ${stackedBar(branch.final_decisions, 'case-result-bar', resourceFork.agent_count)}
    <strong>${escapeHtml(countsText(branch.final_decisions))}</strong><small>${branch.outcome === 'joint_response_approved' ? 'Group approves' : 'Group remains blocked'}</small>
  </button>`).join('')
  all('[data-case-branch]').forEach((button) => { button.onclick = () => { state.caseBranch = button.dataset.caseBranch; renderBranch() } })
  renderBranch()
  renderCaseNetworkGraph()

  $('#case-open-comparison').onclick = () => {
    window.open('assets/resource-fork.json', '_blank', 'noopener')
  }
}

function renderView() {
  const publicView = ['overview', 'guide', 'case', 'create', 'mechanism'].includes(state.view)
  document.body.classList.toggle('guided-result', publicView)
  document.body.classList.toggle('public-shell', publicView)
  document.body.classList.toggle('lab-shell', !publicView)
  for (const view of ['overview', 'guide', 'case', 'create', 'run', 'compare', 'mechanism', 'inspect', 'method']) $(`#${view}-view`).hidden = state.view !== view
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
  if (state.view === 'guide') renderGuide()
  if (state.view === 'case') {
    renderResearchCase()
    void ensureCaseNetwork()
  }
  if (state.view === 'create') renderCreateSimulation()
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
  all('[data-case-graph]').forEach((button) => {
    button.onclick = () => { caseGraphMode = button.dataset.caseGraph; renderCaseNetworkGraph() }
  })
  $('#guide-previous').onclick = () => advanceGuide(-1)
  $('#guide-next').onclick = () => advanceGuide(1)
  all('[data-open-lab]').forEach((button) => { button.onclick = () => navigateLab('run') })
  all('[data-lab-view]').forEach((button) => {
    button.onclick = () => navigateLab(button.dataset.labView, button.dataset.labSection || 'overview')
  })
  all('[data-build-step], [data-build-next]').forEach((button) => {
    button.onclick = () => renderBuildStep(button.dataset.buildStep || button.dataset.buildNext)
  })
  $('#create-generate').onclick = generateAuthoringDraft
  $('#create-example-prompt').onclick = () => {
    $('#create-prompt').value = 'Model seven people deciding whether to issue a joint warning about a contested city election. Give them distinct election-administration, forensic, legal, community, local-media, civil-liberties, and coordination positions, personalities, and memories. Everyone should receive the same public audit bulletin. Then deliver separate technical, legal, and community claims to different overlapping subsets before three decision rounds. Do not dictate anyone’s stance. Let us inspect whether common and heterogeneous inputs change source reliance, perceived risk, dependencies, and readiness to coordinate.'
    $('#create-prompt').focus()
  }
  $('#create-revise').onclick = reviseAuthoringDraft
  $('#create-person-select').onchange = (event) => { selectedAuthoringPerson = event.target.value; renderAuthoringPersonEditor() }
  $('#create-save-person').onclick = saveAuthoringPerson
  $('#create-save-scenario').onclick = saveCoordinationScenario
  $('#create-save-network').onclick = saveInfluenceNetwork
  $('#create-edit-configuration').onclick = showAuthoredConfiguration
  $('#create-approve').onclick = approveAuthoringDraft
  $('#create-run').onclick = runAuthoredSimulation
  $('#create-stop').onclick = stopAuthoredSimulation
  $('#create-start-over').onclick = () => {
    authoringDraft = null
    authoredResult = null
    document.body.classList.remove('authored-result')
    selectedAuthoringPerson = null
    authoredRunId = null
    authoredRunProgressSequence = 0
    authoredRunPollFailures = 0
    if (authoredRunPollHandle) window.clearTimeout(authoredRunPollHandle)
    $('#create-run-status').hidden = true
    $('#create-result').hidden = true
    renderCreateSimulation()
    syncUrl()
  }
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

function authoringModel() {
  return runtimeConfig?.authoring?.models?.find((item) => item.model === preferredAuthoringModel) || null
}

function setAuthoringBusy(busy) {
  authoringBusy = busy
  for (const id of ['create-generate', 'create-revise', 'create-save-person', 'create-save-scenario', 'create-save-network', 'create-approve', 'create-start-over']) {
    const control = $(`#${id}`)
    if (control) control.disabled = busy
  }
}

function draftTemplateLabel(templateId) {
  const labels = {
    coordination_decision_v1:'Coordination decision',
    information_campaign_v1:'Information campaign',
    resource_request_v1:'Resource request',
    component_composition_v1:'Component interaction',
    influence_network_v1:'Influence network',
  }
  return labels[templateId] || sentence(templateId || 'unresolved template')
}

function renderAuthoringPersonEditor() {
  const people = authoringDraft?.proposal?.people || []
  if (!people.length) return
  if (!people.some((person) => person.entity_id === selectedAuthoringPerson)) selectedAuthoringPerson = people[0].entity_id
  const person = people.find((item) => item.entity_id === selectedAuthoringPerson)
  $('#create-person-select').value = person.entity_id
  $('#create-person-label').value = person.label
  $('#create-person-position').value = person.position
  $('#create-person-disposition').value = person.disposition
  $('#create-person-memories').value = (person.memories || []).join('\n')
  $('#create-person-values').value = (person.behavioral_profile?.values || []).join('\n')
  $('#create-person-goals').value = (person.behavioral_profile?.goals || []).join('\n')
  $('#create-person-beliefs').value = (person.behavioral_profile?.beliefs || []).join('\n')
}

function renderCreateSimulation() {
  const author = authoringModel()
  $('#create-generate').disabled = !author || authoringBusy
  if (!authoringDraft) {
    $('#create-review').hidden = true
    $('#create-status').textContent = author
      ? 'Describe a sociotechnical world to begin. The authoring model will generate a retained typed draft.'
      : 'The structured authoring route is unavailable. No provider-free fallback will be shown.'
    return
  }
  $('#create-review').hidden = false
  const proposal = authoringDraft.proposal
  const diagnostics = authoringDraft.diagnostics || []
  $('#create-draft-revision').textContent = `Saved revision ${authoringDraft.revision}`
  $('#create-draft-state').textContent = sentence(authoringDraft.status)
  $('#create-diagnostics').innerHTML = diagnostics.length
    ? diagnostics.map((item) => `<p class="create-diagnostic ${escapeHtml(item.severity)}"><strong>${escapeHtml(sentence(item.severity))}</strong>${escapeHtml(item.message)}</p>`).join('')
    : '<p class="create-diagnostic ready"><strong>Compiler check passed</strong>The draft can be reviewed and approved.</p>'
  if (!proposal) {
    $('#create-draft-title').textContent = 'Draft needs more information'
    $('#create-draft-description').textContent = authoringDraft.authoring_summary || 'Reply to the authoring model using the revision box below.'
    $('#create-world-facts').innerHTML = ''
    $('#create-world-groups').innerHTML = ''
    $('#create-people-list').innerHTML = ''
    $('#create-person-select').innerHTML = ''
    $('#create-scenario-editor').hidden = true
    $('#create-network-editor').hidden = true
    $('#create-raw-configuration').textContent = 'No valid typed configuration has been produced yet.'
    $('#create-approve').hidden = true
    $('#create-run').hidden = true
    return
  }
  const workflow = proposal.workflow || {}
  renderAuthoringCoverage(proposal)
  renderCoordinationScenarioEditor(proposal)
  renderInfluenceNetworkEditor(proposal)
  $('#create-draft-title').textContent = proposal.title
  $('#create-draft-description').textContent = proposal.description
  const boundaries = proposal.analytical_boundaries || []
  const places = proposal.places || []
  const information = proposal.information || []
  const objects = proposal.objects || []
  $('#create-world-facts').innerHTML = [
    [draftTemplateLabel(workflow.template_id), 'Simulation template'],
    [`${proposal.people?.length || 0}`, 'People'],
    [`${objects.length}`, 'World entities and processes'],
    [`${places.length}`, 'Places'],
    [`${information.length}`, 'Information items'],
    [`${boundaries.length}`, 'Analytical boundaries'],
  ].map(([value, label]) => `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join('')
  $('#create-world-groups').innerHTML = [
    ['Groups and analytical boundaries', boundaries.map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></li>`).join('')],
    ['World entities and processes', objects.map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></li>`).join('')],
    ['Information in the scenario', information.map((item) => `<li><strong>${escapeHtml(sentence(item.label))}</strong><span>${escapeHtml(item.content)}</span></li>`).join('')],
  ].filter(([, items]) => items).map(([label, items]) => `<section><h4>${escapeHtml(label)}</h4><ul>${items}</ul></section>`).join('')
  $('#create-people-list').innerHTML = proposal.people.map((person) => `<article><strong>${escapeHtml(person.label)}</strong><span>${escapeHtml(person.position)}</span><p>${escapeHtml(person.disposition)}</p></article>`).join('')
  $('#create-person-select').innerHTML = proposal.people.map((person) => `<option value="${escapeHtml(person.entity_id)}">${escapeHtml(person.label)}</option>`).join('')
  renderAuthoringPersonEditor()
  $('#create-raw-configuration').textContent = JSON.stringify(proposal, null, 2)
  const ready = authoringDraft.status === 'ready_for_review' && diagnostics.length === 0
  $('#create-approve').hidden = !ready
  $('#create-run').hidden = authoringDraft.status !== 'approved'
  setAuthoringBusy(authoringBusy)
  $('#create-status').textContent = 'Draft generated below. Edit a person, request a broader revision, or approve the exact configuration.'
}

async function advanceAuthoringDraft(message) {
  const author = authoringModel()
  if (!author) throw new Error('The structured authoring model is unavailable')
  if (!authoringDraft) authoringDraft = await apiRequest('api/authoring/drafts', {method:'POST'})
  authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/messages`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      expected_revision:authoringDraft.revision,
      message_id:crypto.randomUUID(),
      message,
      model:preferredAuthoringModel,
      reasoning_effort:'medium',
    }),
  })
  renderCreateSimulation()
  syncUrl()
}

async function generateAuthoringDraft() {
  const message = $('#create-prompt').value.trim()
  if (!message) {
    $('#create-status').textContent = 'Describe the world before generating a configuration.'
    return
  }
  setAuthoringBusy(true)
  $('#create-status').textContent = 'The authoring model is generating and validating a typed configuration…'
  try {
    await advanceAuthoringDraft(message)
    $('#create-prompt').value = ''
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
    $('#create-generate').disabled = !authoringModel()
  }
}

async function reviseAuthoringDraft() {
  const message = $('#create-revision-prompt').value.trim()
  if (!message || !authoringDraft) {
    $('#create-status').textContent = 'Describe the change you want to make.'
    return
  }
  setAuthoringBusy(true)
  $('#create-status').textContent = 'The authoring model is producing the next retained revision…'
  try {
    await advanceAuthoringDraft(message)
    $('#create-revision-prompt').value = ''
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

async function saveAuthoringPerson() {
  const people = authoringDraft?.proposal?.people || []
  const original = people.find((person) => person.entity_id === selectedAuthoringPerson)
  if (!original) return
  setAuthoringBusy(true)
  $('#create-status').textContent = 'Saving the typed person edit without a model call…'
  const person = clone(original)
  person.label = $('#create-person-label').value.trim()
  person.position = $('#create-person-position').value.trim()
  person.disposition = $('#create-person-disposition').value.trim()
  person.memories = lineItems($('#create-person-memories').value)
  person.behavioral_profile.values = lineItems($('#create-person-values').value)
  person.behavioral_profile.goals = lineItems($('#create-person-goals').value)
  person.behavioral_profile.beliefs = lineItems($('#create-person-beliefs').value)
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/people/${encodeURIComponent(person.entity_id)}`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision, edit_id:crypto.randomUUID(), person}),
    })
    renderCreateSimulation()
    syncUrl()
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

async function saveCoordinationScenario() {
  if (authoringDraft?.proposal?.workflow?.template_id !== 'coordination_decision_v1') return
  const configuration = coordinationConfigurationFromProposal(authoringDraft.proposal)
  configuration.title = $('#create-scenario-title').value.trim()
  configuration.description = $('#create-scenario-description').value.trim()
  configuration.condition = $('#create-scenario-condition').value
  configuration.collective_goal.description = $('#create-scenario-goal').value.trim()
  configuration.collective_goal.constraints = lineItems($('#create-scenario-constraints').value)
  const concernCards = [...document.querySelectorAll('#create-scenario-concerns [data-concern-kind]')]
  configuration.concerns = concernCards.map((card) => {
    const original = configuration.concerns.find((item) => item.concern_kind === card.dataset.concernKind)
    return {
      ...original,
      source_label:card.querySelector('[data-concern-field="source_label"]').value.trim(),
      content:card.querySelector('[data-concern-field="content"]').value.trim(),
      delivery_minutes:Number(card.querySelector('[data-concern-field="delivery_minutes"]').value),
    }
  })
  const invalidConcern = configuration.concerns.some((item) => !item.source_label || !item.content || !Number.isInteger(item.delivery_minutes) || item.delivery_minutes < 1)
  if (!configuration.title || !configuration.description || !configuration.collective_goal.description || !configuration.collective_goal.constraints.length || invalidConcern) {
    $('#create-scenario-status').textContent = 'Complete the decision, objective, requirements, and each incoming influence. Arrival times must be positive whole numbers.'
    return
  }
  setAuthoringBusy(true)
  $('#create-scenario-status').textContent = 'Saving the complete typed scenario revision…'
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/coordination-configuration`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        expected_revision:authoringDraft.revision,
        edit_id:crypto.randomUUID(),
        configuration,
      }),
    })
    renderCreateSimulation()
    syncUrl()
  } catch (error) {
    $('#create-scenario-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

async function saveInfluenceNetwork() {
  const original = authoringDraft?.proposal
  if (original?.workflow?.template_id !== 'influence_network_v1') return
  const proposal = clone(original)
  proposal.title = $('#create-network-title').value.trim()
  proposal.description = $('#create-network-description').value.trim()
  proposal.workflow.collective_question = $('#create-network-question').value.trim()
  proposal.workflow.round_feedback = $('#create-network-feedback').value
  const rounds = $('#create-network-rounds').value.split(/[\s,]+/).filter(Boolean).map(Number)
  proposal.workflow.round_minutes = rounds
  proposal.workflow.decision_rule = {
    minimum_support:Number($('#create-network-min-support').value),
    minimum_support_or_conditional:Number($('#create-network-min-combined').value),
    maximum_oppose:Number($('#create-network-max-oppose').value),
  }
  const objects = new Map(proposal.objects.map((item) => [item.entity_id, item]))
  const information = new Map(proposal.information.map((item) => [item.information_id, item]))
  const deliveryCards = [...document.querySelectorAll('#create-network-deliveries [data-delivery-id]')]
  for (const card of deliveryCards) {
    const delivery = proposal.workflow.deliveries.find((item) => item.delivery_id === card.dataset.deliveryId)
    if (!delivery) continue
    objects.get(delivery.source_id).label = card.querySelector('[data-network-field="source_label"]').value.trim()
    information.get(delivery.information_id).content = card.querySelector('[data-network-field="content"]').value.trim()
    delivery.delivery_minutes = Number(card.querySelector('[data-network-field="delivery_minutes"]').value)
    delivery.recipient_ids = [...card.querySelectorAll('[data-recipient-id]:checked')].map((input) => input.dataset.recipientId)
  }
  proposal.timing_assumptions = proposal.timing_assumptions.filter((item) => !item.name.startsWith('decision_round_'))
  for (const [index, minutes] of rounds.entries()) {
    proposal.timing_assumptions.push({name:`decision_round_${index + 1}`, minutes, basis:'directly edited schedule'})
  }
  for (const delivery of proposal.workflow.deliveries) {
    const timing = proposal.timing_assumptions.find((item) => item.name === delivery.delivery_id)
    if (timing) timing.minutes = delivery.delivery_minutes
    else proposal.timing_assumptions.push({name:delivery.delivery_id, minutes:delivery.delivery_minutes, basis:'directly edited schedule'})
  }
  const validIntegers = [...rounds, proposal.workflow.decision_rule.minimum_support, proposal.workflow.decision_rule.minimum_support_or_conditional, proposal.workflow.decision_rule.maximum_oppose].every(Number.isInteger)
  const invalidDelivery = proposal.workflow.deliveries.some((item) => !item.recipient_ids.length || !Number.isInteger(item.delivery_minutes) || item.delivery_minutes < 1 || !objects.get(item.source_id).label || !information.get(item.information_id).content)
  if (!proposal.title || !proposal.description || !proposal.workflow.collective_question || rounds.length < 2 || !validIntegers || invalidDelivery) {
    $('#create-network-status').textContent = 'Complete the title, decision, at least two whole-number round times, and every message’s source, content, time, and recipients.'
    return
  }
  setAuthoringBusy(true)
  $('#create-network-status').textContent = 'Saving and compiling the edited influence network…'
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/proposal`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision, edit_id:crypto.randomUUID(), proposal}),
    })
    renderCreateSimulation()
    syncUrl()
  } catch (error) {
    $('#create-network-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

async function approveAuthoringDraft() {
  if (!authoringDraft) return
  setAuthoringBusy(true)
  $('#create-status').textContent = 'Freezing this exact typed configuration…'
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/approve`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision}),
    })
    renderCreateSimulation()
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

function scheduleAuthoredRunPoll(runId, delay = 1800) {
  if (authoredRunPollHandle) window.clearTimeout(authoredRunPollHandle)
  authoredRunPollHandle = window.setTimeout(() => pollAuthoredRun(runId), delay)
}

function authoredStepPayload(step) {
  return step.actions?.map((item) => item.payload).find((payload) => payload?.stance) || null
}

function renderAuthoredResultRound() {
  const result = authoredResult
  const rounds = result?.rounds || []
  if (!rounds.length) {
    $('#create-result-round-tabs').innerHTML = ''
    $('#create-result-round').innerHTML = '<p>No decision rounds were retained for this workflow.</p>'
    return
  }
  authoredResultRoundIndex = Math.min(authoredResultRoundIndex, rounds.length - 1)
  $('#create-result-round-tabs').innerHTML = rounds.map((round, index) => {
    const counts = countValues((round.decisions || []).map((step) => authoredStepPayload(step)?.stance || 'defer'))
    return `<button type="button" data-authored-round="${index}" class="${index === authoredResultRoundIndex ? 'active' : ''}"><span>Round ${escapeHtml(round.round_index)}</span><strong>${escapeHtml(countsText(counts))}</strong></button>`
  }).join('')
  const round = rounds[authoredResultRoundIndex]
  const messages = new Map()
  for (const observation of round.new_information || []) {
    const key = observation.delivery_id || `${observation.apparent_source_ref}-${observation.topic}`
    const retained = messages.get(key) || {...observation, recipients:[]}
    const person = (result.participants || []).find((item) => item.person_id === observation.recipient_id)
    retained.recipients.push(person?.label || labelPerson(observation.recipient_id))
    messages.set(key, retained)
  }
  const informationHtml = messages.size
    ? [...messages.values()].map((message) => `<article><span>New information</span><strong>${escapeHtml(message.topic || sentence(message.delivery_id))}</strong><p>${escapeHtml(message.content)}</p><small>From ${escapeHtml(labelPerson(message.apparent_source_ref))} → ${escapeHtml(message.recipients.join(', '))}</small></article>`).join('')
    : '<p class="create-result-no-change">No new messages arrived since the prior decision round.</p>'
  const decisionsHtml = (round.decisions || []).map((step) => {
    const payload = authoredStepPayload(step)
    const stance = payload?.stance || 'defer'
    const details = [
      payload?.source_assessment ? `<p><b>Source judgment:</b> ${escapeHtml(payload.source_assessment)}</p>` : '',
      payload?.primary_risk ? `<p><b>Main risk:</b> ${escapeHtml(payload.primary_risk)}</p>` : '',
      payload?.blocking_dependency ? `<p><b>Still needed:</b> ${escapeHtml(payload.blocking_dependency)}</p>` : '',
      payload?.reason ? `<p><b>Decision:</b> ${escapeHtml(payload.reason)}</p>` : '',
    ].join('')
    return `<article><header><strong>${escapeHtml(step.person_label)}</strong>${decisionPill(stance)}</header>${details || `<p>${escapeHtml(step.orientation || 'No public rationale retained.')}</p>`}</article>`
  }).join('')
  $('#create-result-round').innerHTML = `<div class="create-result-round-intro"><span>Round ${escapeHtml(round.round_index)}</span><strong>${messages.size ? `${messages.size} new message${messages.size === 1 ? '' : 's'} entered before this decision` : 'The same information environment continued'}</strong></div><div class="create-result-round-columns"><section><h5>What entered the network</h5>${informationHtml}</section><section><h5>How each person responded</h5>${decisionsHtml}</section></div>`
  all('[data-authored-round]').forEach((button) => {
    button.onclick = () => {
      authoredResultRoundIndex = Number(button.dataset.authoredRound)
      renderAuthoredResultRound()
    }
  })
}

function renderAuthoredResultNetwork(result) {
  const projection = result.influence_network || {nodes:[], edges:[]}
  const graph = $('#create-result-network-graph')
  if (!projection.nodes.length || !window.CyberneticGraph) {
    graph.classList.remove('react-canvas-host')
    graph.innerHTML = '<p>The retained information network is unavailable.</p>'
    return
  }
  window.CyberneticGraph.render(graph, {
    nodes:projection.nodes,
    edges:projection.edges,
    boundaries:[], world:null, trajectory:{nodes:[], edges:[]},
    graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:'causal', event:null, initialRevision:0,
    selectedNodeId:null, selectedEdgeId:null, boundary:null, collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const item = projection.nodes.find((candidate) => candidate.id === nodeId)
      if (item) $('#create-result-network-inspector').innerHTML = `<strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span>`
    },
    onSelectEdge:(item) => {
      $('#create-result-network-inspector').innerHTML = `<strong>${escapeHtml(sentence(item.kind))}</strong><span>${escapeHtml(item.description)}</span>`
    },
  })
  $('#create-result-network-status').textContent = `${projection.nodes.length} visible people, sources, messages, and decision items · ${projection.edges.length} retained paths`
}

function renderAuthoredResult(result) {
  authoredResult = result
  authoredResultRoundIndex = 0
  document.body.classList.add('authored-result')
  const review = $('#create-review')
  const runStatus = $('#create-run-status')
  review.classList.add('result-mode')
  review.insertBefore(runStatus, review.firstElementChild)
  $('.create-composer').hidden = true
  $('.create-hero .case-label').textContent = 'Completed simulation'
  $('#create-title').textContent = result.title || 'Simulation result'
  $('.create-hero > p').textContent = result.description || 'A retained Luna simulation.'
  const outcome = result.outcome?.final_status || result.completion?.reason || 'completed'
  const outcomeLabel = {
    no_decision_by_horizon:'No decision before the deadline',
    deploy_on_time:'Full proposal approved',
    scope_reduced:'Narrower proposal approved',
    delayed:'Decision delayed',
    partner_disengaged:'Partner disengaged',
  }[outcome] || sentence(outcome)
  $('#create-run-heading').textContent = `Result: ${outcomeLabel}`
  $('#create-run-detail').textContent = result.completion?.public_summary || result.summary || 'The simulation reached a terminal state.'
  $('#create-result-title').textContent = result.headline || result.title || 'Simulation complete'
  $('#create-result-summary').textContent = result.summary || result.description || ''
  const stanceCounts = result.outcome?.counts
  const gateChecks = result.outcome?.gate_checks
  const resultFacts = stanceCounts && gateChecks ? [
    [outcomeLabel, 'Collective outcome'],
    [`${Number(stanceCounts.support || 0)} support · ${Number(stanceCounts.conditional || 0)} conditional · ${Number(stanceCounts.defer || 0)} defer · ${Number(stanceCounts.oppose || 0)} oppose`, 'Final positions'],
    [`${(result.rounds || []).length} rounds · ${(result.decision_steps || []).length} decisions`, result.execution === 'live' ? 'Retained Luna execution' : 'Retained reference execution'],
  ] : [
    [outcomeLabel, 'Collective outcome'],
    [String((result.participants || []).length), 'People'],
    [String(Number(result.participant_model_calls || 0)), 'Luna decisions'],
  ]
  $('#create-result-facts').innerHTML = resultFacts.map(([value, label]) => `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join('')
  $('#create-result-people').innerHTML = (result.participants || []).map((person) => {
    const commitment = person.last_explicit_commitment ? sentence(person.last_explicit_commitment) : 'No explicit position change'
    const payload = person.latest_actions?.map((item) => item.payload).find((item) => item?.stance)
    return `<article><div><div><strong>${escapeHtml(person.label)}</strong>${person.position ? `<small>${escapeHtml(person.position)}</small>` : ''}</div><span>${escapeHtml(commitment)}</span></div><p>${escapeHtml(payload?.reason || person.latest_orientation || 'No additional public rationale was retained.')}</p></article>`
  }).join('') || '<p>No person-level decision records were retained for this workflow.</p>'
  const steps = (result.decision_steps || []).filter((step) => step.actions?.length || step.orientation)
  $('#create-result-steps').innerHTML = steps.map((step) => {
    const payload = authoredStepPayload(step)
    return `<li><strong>Round ${escapeHtml(step.round_index || '?')} · ${escapeHtml(step.person_label)}</strong><span>${escapeHtml(sentence(payload?.stance || 'no stated position'))}</span><p>${escapeHtml(payload?.reason || step.orientation || '')}</p></li>`
  }).join('')
  $('#create-result').hidden = false
  renderAuthoredResultRound()
  renderAuthoredResultNetwork(result)
  const readout = result.coordination_measurement_readout
  const gateRows = gateChecks ? Object.entries(gateChecks).map(([name, check]) => `<li><strong>${escapeHtml(sentence(name))}</strong> ${check.passed ? 'passed' : 'failed'} (${escapeHtml(check.actual)} ${name === 'opposition' ? `of maximum ${check.maximum}` : `of ${check.required} required`})</li>`).join('') : ''
  const limitations = readout?.limitations || ['This is a synthetic model run and does not predict real people or institutions.']
  $('#create-result-analysis').innerHTML = `<p><strong>${escapeHtml(readout?.headline || 'Retained simulation evidence')}</strong> ${escapeHtml(readout?.explanation || 'The run retains delivered information, decisions, and the exact collective gate.')}</p>${gateRows ? `<h5>Exact decision rule</h5><ul>${gateRows}</ul>` : ''}<h5>Interpret carefully</h5><ul>${limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
  $('#create-run-evidence').href = `api/runs/${encodeURIComponent(result.run_id)}`
  $('#create-run-evidence').textContent = 'Open raw retained run'
  $('#create-run-evidence').hidden = false
  $('#create-edit-configuration').hidden = false
  $('#create-stop').hidden = true
  $('#create-run').disabled = false
}

async function pollAuthoredRun(runId) {
  try {
    const run = await apiRequest(`api/runs/${encodeURIComponent(runId)}/progress?after_sequence=${authoredRunProgressSequence}&include_projection=false`)
    authoredRunPollFailures = 0
    authoredRunProgressSequence = Math.max(authoredRunProgressSequence, Number(run.latest_sequence || 0))
    if (run.status === 'completed') {
      const result = await apiRequest(`api/runs/${encodeURIComponent(runId)}/summary`)
      renderAuthoredResult(result)
      syncUrl()
      return
    }
    $('#create-run-heading').textContent = `Simulation ${sentence(run.status)}`
    $('#create-run-detail').textContent = `${Number(run.model_calls || 0)} Luna decisions retained. The world is still advancing.`
    if (['failed', 'interrupted', 'stopped'].includes(run.status)) throw new Error(run.error || `simulation ${run.status}`)
    scheduleAuthoredRunPoll(runId)
  } catch (error) {
    authoredRunPollFailures += 1
    if (authoredRunPollFailures <= 3) {
      $('#create-run-heading').textContent = 'Reconnecting to the simulation…'
      $('#create-run-detail').textContent = error.message
      scheduleAuthoredRunPoll(runId, 2200)
      return
    }
    $('#create-run-heading').textContent = 'Simulation failed visibly'
    $('#create-run-detail').textContent = error.message
    $('#create-stop').hidden = true
    $('#create-run').disabled = false
  }
}

async function stopAuthoredSimulation() {
  if (!authoredRunId) return
  $('#create-stop').disabled = true
  $('#create-run-heading').textContent = 'Stopping after the current causal step…'
  try {
    await apiRequest(`api/runs/${encodeURIComponent(authoredRunId)}/stop`, {method:'POST'})
    scheduleAuthoredRunPoll(authoredRunId, 250)
  } catch (error) {
    $('#create-run-detail').textContent = error.message
    $('#create-stop').disabled = false
  }
}

async function runAuthoredSimulation() {
  if (!authoringDraft || authoringDraft.status !== 'approved') return
  $('#create-run').disabled = true
  $('#create-run-status').hidden = false
  $('#create-run-heading').textContent = 'Starting the authored simulation…'
  $('#create-run-detail').textContent = 'Validating the approved configuration and Luna route.'
  $('#create-result').hidden = true
  authoredResult = null
  document.body.classList.remove('authored-result')
  $('#create-run-evidence').hidden = true
  $('#create-stop').hidden = true
  try {
    const run = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/runs`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({execution:'live', narration:'deterministic', llm_options:{model:preferredModel, agent_reasoning_effort:'medium', max_total_cost:0.74}}),
    })
    authoredRunId = run.run_id
    authoredRunProgressSequence = 0
    authoredRunPollFailures = 0
    $('#create-run-heading').textContent = 'Simulation running'
    $('#create-run-detail').textContent = `Retained run ${run.run_id} has started.`
    $('#create-stop').disabled = false
    $('#create-stop').hidden = false
    syncUrl()
    scheduleAuthoredRunPoll(run.run_id, 300)
  } catch (error) {
    $('#create-run-heading').textContent = 'Simulation did not start'
    $('#create-run-detail').textContent = error.message
    $('#create-run').disabled = false
  }
}

async function loadAuthoringDraftFromUrl() {
  const draftId = new URLSearchParams(window.location.search).get('draft')
  if (!draftId || state.view !== 'create') return
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(draftId)}`)
  } catch (error) {
    $('#create-status').textContent = `Saved draft unavailable: ${error.message}`
  }
}

async function loadAuthoredRunFromUrl() {
  const runId = new URLSearchParams(window.location.search).get('authored_run')
  if (!runId || state.view !== 'create') return
  authoredRunId = runId
  $('#create-run-status').hidden = false
  $('#create-run-heading').textContent = 'Opening retained simulation…'
  try {
    const progress = await apiRequest(`api/runs/${encodeURIComponent(runId)}/progress?include_projection=false`)
    authoredRunProgressSequence = Number(progress.latest_sequence || 0)
    if (progress.status === 'completed') {
      renderAuthoredResult(await apiRequest(`api/runs/${encodeURIComponent(runId)}/summary`))
      return
    }
    $('#create-stop').hidden = progress.status === 'failed'
    $('#create-run-detail').textContent = `${Number(progress.model_calls || 0)} Luna decisions retained. The simulation is ${sentence(progress.status)}.`
    scheduleAuthoredRunPoll(runId, 300)
  } catch (error) {
    $('#create-run-heading').textContent = 'Retained simulation unavailable'
    $('#create-run-detail').textContent = error.message
  }
}

function showAuthoredConfiguration() {
  const review = $('#create-review')
  const runStatus = $('#create-run-status')
  review.classList.remove('result-mode')
  document.body.classList.remove('authored-result')
  review.appendChild(runStatus)
  $('.create-composer').hidden = false
  $('.create-hero .case-label').textContent = 'Create a simulation'
  $('#create-title').textContent = 'Describe the coordination problem you want to explore.'
  $('.create-hero > p').textContent = 'Describe the people, information sources, who receives which messages, and the collective decision. The authoring model turns that description into an editable influence network; Luna then drives each person independently from their own character, memory, and received information.'
  $('#create-edit-configuration').hidden = true
  $('#create-draft-title').scrollIntoView({behavior:'smooth', block:'start'})
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
      const raw = summary.run_id === caseNetworkRunId && caseNetworkRun
        ? caseNetworkRun
        : await apiRequest(`api/runs/${encodeURIComponent(summary.run_id)}`)
      if (summary.run_id === caseNetworkRunId) {
        caseNetworkRun = raw
        caseNetworkError = null
      }
      retained.push(projectLiveRun(raw))
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
    applyRunScopeFromUrl()
    readStateFromUrl()
    await loadAuthoringDraftFromUrl()
    renderRail()
    configureControls()
    renderView()
    await loadAuthoredRunFromUrl()
    $('#loading').hidden = true
    $('#workbench').hidden = false
    void loadRetainedLiveRuns().then(() => {
      applyRunScopeFromUrl()
      renderRail()
      configureControls()
      renderView()
    })
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
