'use strict'

const decisionOrder = ['support', 'conditional', 'defer', 'oppose']
const groupOrder = ['all', 'alba', 'borin', 'cyrenia', 'darsia', 'regional']
const groupLabels = {all:'All roles', alba:'Alba', borin:'Borin', cyrenia:'Cyrenia', darsia:'Darsia', regional:'Regional'}
const preferredModel = 'codex/gpt-5.6-luna'
const caseNetworkRunId = 'run_5010214f2466'
const guideRunId = 'run_ffe88e1c15d5'
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
let guideRun = null
let guideRunLoad = null
let guideRunError = null
let caseGraphMode = 'system'
let caseStudyStep = 0
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
let selectedGeneralPerson = null
let selectedGeneralRecord = null
let selectedGeneralState = null
let selectedGeneralInformation = null
let selectedGeneralMoment = null
let generalReviewStage = 'world'
let authoredRunPollHandle = null
let authoredRunId = null
let authoredRunProgressSequence = 0
let authoredRunPollFailures = 0
let authoringBusy = false
let authoredResult = null
let authoredResultRoundIndex = 0
let authoredReplaySceneIndex = 0
let authoredDraftWalkthroughStep = 0
let authoredDraftWalkthroughStepCount = 0
let retainedRunHistory = []
let retainedRunHistoryLoad = null
let retainedLiveRunsLoad = null
let retainedLiveRunsLoaded = false
let simulationLoadingRunId = null
const LOCAL_SIMULATION_IDS_KEY = 'coordination-environment-lab.simulation-ids.v1'

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
  if (['overview', 'guide', 'case', 'simulations', 'create', 'run', 'compare', 'mechanism', 'inspect', 'method'].includes(requestedView)) state.view = requestedView
  const requestedGuideStep = Number(params.get('guide_step'))
  if (Number.isInteger(requestedGuideStep) && requestedGuideStep >= 1 && requestedGuideStep <= 7) state.guideStep = requestedGuideStep - 1
  const requestedRun = params.get('run')
  if (requestedRun) state.runId = requestedRun
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
  if (!['compare', 'inspect'].includes(state.view)) return
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
  for (const key of ['run', 'round', 'person', 'group', 'mechanism_person', 'section', 'draft', 'authored_run', 'simulation', 'guide_step']) url.searchParams.delete(key)
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
  if (state.view === 'simulations' && authoredRunId) url.searchParams.set('simulation', authoredRunId)
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

function renderMechanism() {
  if (autonomousProbe) renderAutonomousProbe()
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

const guideSteps = [
  {
    kicker:'Start with retained evidence',
    title:'One configured world produced one retained execution.',
    body:'This is not an illustrative story. It is a projection of run_ffe88e1c15d5: a completed city-election certification simulation authored in natural language, compiled into reviewed components, and executed with six retained Luna participant calls.',
    mode:'causal',
    nodeIds:['network_clock', 'election_director_mara_chen', 'investigative_journalist_eli_navarro', 'neighborhood_coalition_organizer_priya_shah', 'stance_recorder', 'decision_gate', 'decision_register'],
    edgeIds:['stance_election_director_mara_chen_route', 'stance_investigative_journalist_eli_navarro_route', 'stance_neighborhood_coalition_organizer_priya_shah_route', 'decision_evaluate_route', 'reads_decision_register_to_stance_recorder', 'writes_stance_recorder_to_decision_register', 'reads_decision_register_to_decision_gate', 'writes_decision_gate_to_decision_register'],
    focus:['decision_register'],
    facts:[['Run','run_ffe88e1c15d5'], ['Execution','Live · Luna'], ['World events','97 retained'], ['State revisions','20 committed']],
    language:[['Configured structure','Records and routes present in canonical state.'], ['Retained execution','The append-only evidence produced when that configuration ran.']],
    takeaway:'The walkthrough and raw run share one source of truth; there is no separate tutorial ontology.',
  },
  {
    kicker:'Separate existence from agency',
    title:'Entities can exist without being autonomous agents.',
    body:'Three person entities are bound to LLM active systems and produced six model traces. The information source, network clock, decision register, and exact mechanisms also exist and can participate causally, but they are not all people and they do not all reason with an LLM.',
    mode:'causal',
    nodeIds:['official_audit_bulletin_source', 'audit_bulletin_to_all_participants_election_director_mara_chen_delivery', 'election_director_mara_chen', 'network_clock', 'decision_gate', 'decision_register'],
    edgeIds:['audit_bulletin_to_all_participants_election_director_mara_chen_route', 'observation_audit_bulletin_to_all_participants_election_director_mara_chen_delivery_to_election_director_mara_chen', 'decision_evaluate_route', 'reads_decision_register_to_decision_gate', 'writes_decision_gate_to_decision_register'],
    focus:['election_director_mara_chen', 'network_clock'],
    facts:[['People','3 LLM active systems'], ['Participant activations','6 model calls'], ['Clock','Exact scripted process'], ['Gate','Exact registered mechanism']],
    language:[['Entity','Something with identity and state; agency is not implied.'], ['Active system','A separate trusted binding that may perceive and attempt actions for an entity.']],
    takeaway:'A car, document, source, organization, or process need not be made into a human-like agent to matter.',
  },
  {
    kicker:'Inspect information structure',
    title:'Source, representation, route, delivery, and observation are different records.',
    body:'The official audit source holds a specific representation. A directed connection can carry it to a delivery mechanism, and that mechanism is authorized to create an observation for Mara. Lineage records provenance; the observation-target relation records who may receive the result.',
    mode:'causal',
    nodeIds:['official_audit_bulletin_source', 'audit_bulletin_to_all_participants_representation', 'audit_bulletin_to_all_participants_election_director_mara_chen_delivery', 'election_director_mara_chen', 'decision_register'],
    edgeIds:['location_official_audit_bulletin_source_to_audit_bulletin_to_all_participants_representation', 'lineage_official_audit_bulletin_source_to_audit_bulletin_to_all_participants_representation', 'audit_bulletin_to_all_participants_election_director_mara_chen_route', 'observation_audit_bulletin_to_all_participants_election_director_mara_chen_delivery_to_election_director_mara_chen', 'substrate_audit_bulletin_to_all_participants_election_director_mara_chen_delivery_to_decision_register'],
    focus:['audit_bulletin_to_all_participants_representation'],
    facts:[['Actual source','Official audit office'], ['Representation','Typed influence-message JSON'], ['Recipient','Mara Chen only on this route'], ['Belief','Not implied by delivery']],
    language:[['Representation','Content with encoding, lineage, carrier revision, and actual provenance.'], ['Observation target','An authorized recipient of a mechanism outcome—not proof of belief.']],
    takeaway:'The system can distinguish what is true, what was represented, what arrived, and what an actor later inferred.',
  },
  {
    kicker:'Read configured arrows correctly',
    title:'A configured arrow is a possible directed relation—not an event.',
    body:'This graph is still the pre-execution structure. Connection arrows identify explicit output-port to input-port routes; read, write, substrate, lineage, location, and observation-target arrows identify other typed directed relations. They do not claim that an effect traveled during this run.',
    mode:'causal',
    nodeIds:['official_audit_bulletin_source', 'audit_bulletin_to_all_participants_representation', 'audit_bulletin_to_all_participants_election_director_mara_chen_delivery', 'election_director_mara_chen', 'stance_recorder', 'decision_register'],
    edgeIds:['location_official_audit_bulletin_source_to_audit_bulletin_to_all_participants_representation', 'lineage_official_audit_bulletin_source_to_audit_bulletin_to_all_participants_representation', 'audit_bulletin_to_all_participants_election_director_mara_chen_route', 'observation_audit_bulletin_to_all_participants_election_director_mara_chen_delivery_to_election_director_mara_chen', 'stance_election_director_mara_chen_route', 'reads_decision_register_to_stance_recorder', 'writes_stance_recorder_to_decision_register'],
    focus:['audit_bulletin_to_all_participants_election_director_mara_chen_delivery', 'stance_recorder'],
    facts:[['Connection','Directed possible route'], ['Reads','Declared state dependency'], ['Writes','Declared mutation authority'], ['Lineage','Directed provenance relation']],
    language:[['Topology','What is connected or related in the configured world.'], ['Trajectory','Which attempts, routes, mechanisms, and commits actually occurred.']],
    takeaway:'Configured topology and realized causality are shown separately because confusing them would misrepresent the simulation.',
  },
  {
    kicker:'Follow one realized delivery',
    title:'Six retained events prove that the audit became Mara’s observation.',
    body:'Now the visualization switches to the retained execution trajectory. The source attempted an injection, emitted an effect, routed it through the named connection, invoked an exact delivery mechanism, committed revision 1, and delivered observation_000000 to Mara. Every arrow here is a retained execution-parent link—not proof of counterfactual causation.',
    mode:'trajectory', eventSequences:[1, 2, 3, 4, 5, 6],
    facts:[['Attempt','event_000001'], ['Route','event_000003'], ['Commit','revision 1'], ['Observation','observation_000000']],
    language:[['Execution-parent arrow','The target event explicitly names the source event as execution ancestry.'], ['State commit','The validated patch changed canonical state and produced a new revision.']],
    takeaway:'Only the event chain—not the configured route by itself—establishes that information actually arrived.',
  },
  {
    kicker:'Follow an autonomous decision',
    title:'Mara proposed a stance; an exact mechanism recorded it.',
    body:'After receiving her authorized observations, Mara’s Luna active system supported certification while retaining a residual risk. Her action emitted and routed a typed stance. The exact stance recorder validated its contract and committed the position to revision 8.',
    mode:'trajectory', eventSequences:[33, 34, 39, 40, 41],
    facts:[['Actor','Election Director Mara Chen'], ['Model output','Support with stated risk'], ['Recorder','stance_recorder_v1'], ['Commit','revision 8']],
    language:[['Action attempt','What an active system tried to do; it is not yet world truth.'], ['Transition authority','The registered mechanism permitted to validate and propose the resulting patch.']],
    takeaway:'The LLM chose the proposed stance; exact world machinery decided how that proposal became retained state.',
  },
  {
    kicker:'Inspect the collective result',
    title:'The fixed gate read retained positions and committed the outcome.',
    body:'The network clock requested evaluation. The effect reached the exact decision gate, which read the retained positions and rule, passed its invariant, and committed the final counts and outcome at revision 20. The run then completed with a durable causal tail.',
    mode:'trajectory', eventSequences:[91, 92, 93, 94, 95, 96],
    facts:[['Final positions','1 support · 2 conditional'], ['Gate','Support threshold failed'], ['Outcome','Not approved'], ['Final revision','20']],
    language:[['Decision gate','A deterministic mechanism over retained positions and configured thresholds.'], ['Analysis','A later interpretation of evidence; it is not allowed to rewrite the trajectory.']],
    takeaway:'The result is inspectable from model output through typed action, exact mechanism, validated patch, and final evidence.',
  },
]

function canonicalGuideProjection(step) {
  const nodeIds = new Set(step.nodeIds || [])
  const edgeIds = new Set(step.edgeIds || [])
  return {
    nodes:(guideRun.nodes || []).filter((node) => nodeIds.has(node.id)),
    edges:(guideRun.edges || [])
      .filter((edge) => edgeIds.has(edge.id) && nodeIds.has(edge.source) && nodeIds.has(edge.target))
      .map((edge) => ({...edge, routeIds:edge.exact_route_ids || [edge.id]})),
  }
}

function canonicalGuideTrajectory(step) {
  const eventIds = new Set((step.eventSequences || []).map((sequence) => `event_${String(sequence).padStart(6, '0')}`))
  return {
    nodes:(guideRun.trajectory?.nodes || []).filter((node) => eventIds.has(node.id)),
    edges:(guideRun.trajectory?.edges || []).filter((edge) => eventIds.has(edge.source) && eventIds.has(edge.target)),
  }
}

function renderGuideSelection(item, relationship = false) {
  const type = relationship ? sentence(item.kind || 'relation') : sentence(item.event_kind || item.kind || 'record')
  const identity = item.event_id || item.id
  const description = item.summary || item.description || item.label || 'Retained runtime record.'
  $('#guide-selection').innerHTML = `<strong>${escapeHtml(identity)} · ${escapeHtml(type)}:</strong> ${escapeHtml(description)}`
}

function renderGuideGraph(step) {
  const graph = $('#guide-graph')
  const trajectory = step.mode === 'trajectory' ? canonicalGuideTrajectory(step) : {nodes:[], edges:[]}
  const projection = step.mode === 'causal' ? canonicalGuideProjection(step) : {nodes:[], edges:[]}
  const lastSequence = step.eventSequences?.at(-1)
  const lastEvent = Number.isInteger(lastSequence) ? guideRun.events.find((event) => event.sequence === lastSequence) : null
  window.CyberneticGraph.render(graph, {
    nodes:projection.nodes,
    edges:projection.edges,
    boundaries:[], world:null, trajectory,
    graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:step.mode,
    event:step.mode === 'causal' ? {event_id:`guide_structure_${state.guideStep + 1}`, state_revision:0, focus_ids:step.focus || [], focus_edges:[], spatial_focus_ids:[], spatial_link_ids:[], boundary_ids:[]} : null,
    initialRevision:lastEvent?.state_revision ?? 0,
    title:step.mode === 'trajectory' ? 'Realized retained events' : 'Configured canonical structure',
    subtitle:step.mode === 'trajectory' ? `${trajectory.nodes.length} retained events` : `${projection.nodes.length} records · ${projection.edges.length} typed relations`,
    showLegend:true,
    showMiniMap:false,
    selectedNodeId:null, selectedEdgeId:null, boundary:null, collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const item = step.mode === 'trajectory'
        ? guideRun.events.find((event) => event.event_id === nodeId)
        : projection.nodes.find((node) => node.id === nodeId)
      if (item) renderGuideSelection(item)
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
  $('#guide-visual-mode').textContent = step.mode === 'trajectory' ? 'Realized trajectory' : 'Configured structure'
  $('#guide-visual-title').textContent = step.mode === 'trajectory' ? 'Exact retained events and execution-parent links' : 'Exact canonical records and typed relations'
  $('#guide-step-facts').innerHTML = step.facts.map(([label, value]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`).join('')
  $('#guide-step-language').innerHTML = step.language.map(([term, definition]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join('')
  $('#guide-step-takeaway').innerHTML = `<span>Why this matters</span><strong>${escapeHtml(step.takeaway)}</strong>`
  $('#guide-progress').innerHTML = guideSteps.map((candidate, index) => `<button type="button" data-guide-step="${index}" class="${index === state.guideStep ? 'active' : ''}" aria-label="Open step ${index + 1}: ${escapeHtml(candidate.title)}" aria-current="${index === state.guideStep ? 'step' : 'false'}">${index + 1}</button>`).join('')
  $('#guide-previous').disabled = state.guideStep === 0
  $('#guide-next').textContent = state.guideStep === guideSteps.length - 1
    ? 'Continue: Create your own simulation →'
    : `Next: ${guideSteps[state.guideStep + 1].kicker} →`
  all('[data-guide-step]').forEach((button) => {
    button.onclick = () => { state.guideStep = Number(button.dataset.guideStep); renderGuide(); syncUrl() }
  })
  if (guideRunError) {
    $('#guide-graph').innerHTML = `<p class="guide-load-error"><strong>Retained walkthrough unavailable.</strong> ${escapeHtml(guideRunError)}</p>`
    $('#guide-selection').innerHTML = '<strong>No substitute is shown:</strong> this guide requires its exact canonical run.'
    return
  }
  if (!guideRun || !window.CyberneticGraph) {
    $('#guide-graph').innerHTML = '<p class="guide-loading">Loading the retained canonical execution…</p>'
    $('#guide-selection').innerHTML = '<strong>Loading:</strong> fetching the exact run, graph projection, events, and model traces.'
    return
  }
  renderGuideGraph(step)
  const selected = step.mode === 'trajectory'
    ? guideRun.events.find((event) => event.sequence === step.eventSequences[0])
    : canonicalGuideProjection(step).nodes[0]
  if (selected) renderGuideSelection(selected)
}

async function ensureGuideRun() {
  if (guideRun || guideRunLoad) return guideRunLoad
  guideRunLoad = apiRequest(`api/runs/${encodeURIComponent(guideRunId)}`)
    .then((run) => {
      if (run.run_id !== guideRunId || run.status !== 'completed' || run.scenario !== 'city_election_certification_influence' || run.execution !== 'live' || run.llm_configuration?.model !== preferredModel || run.model_calls !== 6 || !run.nodes?.length || !run.edges?.length || !run.events?.length || !run.trajectory?.nodes?.length || !run.traces?.length) throw new Error('the retained canonical run is incomplete or no longer matches the reviewed walkthrough')
      guideRun = run
      guideRunError = null
      if (state.view === 'guide') renderGuide()
      return run
    })
    .catch((error) => {
      guideRunError = error.message
      if (state.view === 'guide') renderGuide()
      return null
    })
  return guideRunLoad
}

function advanceGuide(direction) {
  const next = state.guideStep + direction
  if (next >= guideSteps.length) {
    state.view = 'create'
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
  const exactNodes = [
    indexed.get('outbreak_source_delivery'),
    indexed.get('outbreak_stance_recorder'),
    indexed.get('outbreak_decision'),
    indexed.get('regional_allocation_authority'),
  ].filter(Boolean)
  const groups = [
    ['pressure_sources', 'Four local pressure sources', 'Technical, legal, logistics, and community sources emit bounded exogenous signals. This node is an analytical grouping over four exact source agents.'],
    ['national_networks', 'Four national response networks', 'Twenty people participate through Alba, Borin, Cyrenia, and Darsia. This node groups their exact local information and stance routes.'],
    ['regional_network', 'Regional coordination network', 'Six people coordinating science, logistics, law, finance, public legitimacy, and the shared decision.'],
  ].map(([id, label, description]) => ({id, label, description, kind:'analytical_boundary', state:{projection:'analytical_group'}}))
  const edges = []
  const addEdge = (source, target, description) => edges.push({
    id:`case_${source}_to_${target}`,
    kind:'connection', source, target, enabled:true, description, routeIds:[],
  })
  addEdge('pressure_sources', 'outbreak_source_delivery', 'Four exact external sources contribute bounded signals; none can choose a participant stance.')
  const participantGroups = ['national_networks', 'regional_network']
  participantGroups.forEach((group) => {
    addEdge('outbreak_source_delivery', group, 'Analytical aggregation of exact observation routes carrying locally relevant signals to people in this network.')
    addEdge('regional_allocation_authority', group, 'Verified resource-package facts enter through exact observation routes; the authority cannot choose participant stances.')
    addEdge(group, 'outbreak_stance_recorder', 'Analytical aggregation of the network members’ exact autonomous stance routes.')
  })
  addEdge('outbreak_stance_recorder', 'outbreak_decision', 'The exact decision mechanism evaluates the retained participant stances against the fixed gate.')
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

function renderCaseChapter() {
  const chapters = [
    {kind:'The world', title:'Inspect the simulated response network.'},
    {kind:'The coordination problem', title:'See who depends on whom.'},
    {kind:'Pressure and experiment', title:'See what changed and what stayed fixed.'},
    {kind:'Result', title:'Compare four continuations of one saved moment.'},
    {kind:'Agent reasoning', title:'Inspect why the remaining agents deferred.'},
    {kind:'Waltzman analysis', title:'Connect retained behavior to the coordination theory.'},
  ]
  caseStudyStep = Math.max(0, Math.min(caseStudyStep, chapters.length - 1))
  const chapter = chapters[caseStudyStep]
  all('[data-case-chapter]').forEach((section) => { section.hidden = Number(section.dataset.caseChapter) !== caseStudyStep })
  $('#case-walkthrough-kind').textContent = chapter.kind
  $('#case-walkthrough-progress').textContent = `Step ${caseStudyStep + 1} of ${chapters.length} · ${chapter.title}`
  $('#case-walkthrough-previous').disabled = caseStudyStep === 0
  $('#case-walkthrough-next').hidden = caseStudyStep === chapters.length - 1
  $('#case-walkthrough-next').textContent = 'Next →'
  if (caseStudyStep === 0) window.requestAnimationFrame(() => renderCaseNetworkGraph())
  window.scrollTo({top:Math.max(0, $('#case-view').offsetTop - 70), behavior:'smooth'})
}

function renderResearchCase() {
  renderCaseChapter()
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

  $('#case-open-comparison').onclick = () => {
    window.open('assets/resource-fork.json', '_blank', 'noopener')
  }
}

function renderView() {
  const publicView = ['overview', 'guide', 'case', 'simulations', 'create', 'mechanism', 'method'].includes(state.view)
  document.body.classList.toggle('guided-result', publicView)
  document.body.classList.toggle('public-shell', publicView)
  document.body.classList.toggle('lab-shell', !publicView)
  for (const view of ['overview', 'guide', 'case', 'simulations', 'create', 'run', 'compare', 'mechanism', 'inspect', 'method']) $(`#${view}-view`).hidden = state.view !== view
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
  if (state.view === 'guide') {
    renderGuide()
    void ensureGuideRun()
  }
  if (state.view === 'case') {
    renderResearchCase()
    void ensureCaseNetwork()
  }
  if (state.view === 'simulations') renderSimulationLibrary()
  if (state.view === 'create') renderCreateSimulation()
  if (state.view === 'compare') {
    renderComparison()
    void ensureRetainedLiveRuns()
  }
  if (state.view === 'mechanism') renderMechanism()
  if (state.view === 'inspect') {
    renderInspector()
    if (!dataset.runs.some((run) => run.run_id === state.runId)) void ensureRetainedLiveRuns()
  }
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

function resetAuthoringWorkspace() {
  authoringDraft = null
  authoredResult = null
  authoredRunId = null
  authoredRunProgressSequence = 0
  authoredRunPollFailures = 0
  selectedAuthoringPerson = null
  selectedGeneralPerson = null
  selectedGeneralRecord = null
  selectedGeneralState = null
  selectedGeneralInformation = null
  selectedGeneralMoment = null
  generalReviewStage = 'world'
  document.body.classList.remove('authored-result')
  $('#create-review').classList.remove('result-mode')
  $('#create-run-status').hidden = true
  $('#create-result').hidden = true
  $('.create-composer').hidden = false
  $('.create-hero .case-label').textContent = 'Create a simulation'
  if (authoredRunPollHandle) window.clearTimeout(authoredRunPollHandle)
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
    button.onclick = () => {
      if (button.dataset.view === 'create') resetAuthoringWorkspace()
      if (button.dataset.view === 'case') caseStudyStep = 0
      state.view = button.dataset.view
      renderView()
      syncUrl()
    }
  })
  all('[data-case-graph]').forEach((button) => {
    button.onclick = () => { caseGraphMode = button.dataset.caseGraph; renderCaseNetworkGraph() }
  })
  $('#case-walkthrough-previous').onclick = () => {
    caseStudyStep = Math.max(0, caseStudyStep - 1)
    renderCaseChapter()
  }
  $('#case-walkthrough-next').onclick = () => {
    caseStudyStep = Math.min(5, caseStudyStep + 1)
    renderCaseChapter()
  }
  $('#guide-previous').onclick = () => advanceGuide(-1)
  $('#guide-next').onclick = () => advanceGuide(1)
  all('[data-open-lab]').forEach((button) => { button.onclick = () => navigateLab('run') })
  all('[data-lab-view]').forEach((button) => {
    button.onclick = () => navigateLab(button.dataset.labView, button.dataset.labSection || 'overview')
  })
  all('[data-build-step], [data-build-next]').forEach((button) => {
    button.onclick = () => renderBuildStep(button.dataset.buildStep || button.dataset.buildNext)
  })
  $('#create-generate').onclick = discussAuthoringDraft
  $('#create-configure-now').onclick = configureAuthoringDraft
  $('#create-example-prompt').onclick = () => {
    $('#create-prompt').value = 'Model a storm-damaged relief port containing a dock, an inland depot, one truck, finite fuel, relief cargo, a damaged bridge, communications, and four people responsible for port operations, transport, bridge inspection, and aid allocation. A hidden bridge defect should be known initially only to the inspector. At the same scheduled moment, the port operator and transport coordinator should independently propose what to do with the truck. Let an LLM game master adjudicate open-ended actions while exact mechanisms enforce placement, conserved fuel, information access, and valid topology. Explore whether the group can move the cargo before sunset without using unsafe infrastructure.'
    $('#create-prompt').focus()
  }
  $('#create-service-example-prompt').onclick = () => {
    $('#create-prompt').value = 'Model an online service outage involving an incident commander, database engineer, security analyst, and customer liaison. Credentials, service dependencies, status messages, access permissions, and recovery attempts change over time. Different people receive different claims about the cause. The group must restore service without erasing forensic evidence.'
    $('#create-prompt').focus()
  }
  $('#create-revise').onclick = reviseAuthoringDraft
  $('#create-person-select').onchange = (event) => { selectedAuthoringPerson = event.target.value; renderAuthoringPersonEditor() }
  $('#create-save-person').onclick = saveAuthoringPerson
  $('#create-save-scenario').onclick = saveCoordinationScenario
  $('#create-save-network').onclick = saveInfluenceNetwork
  $('#create-general-person-select').onchange = (event) => { selectedGeneralPerson = event.target.value; renderGeneralEditor(authoringDraft.proposal) }
  $('#create-general-record-select').onchange = (event) => { selectedGeneralRecord = event.target.value; selectedGeneralState = null; renderGeneralEditor(authoringDraft.proposal) }
  $('#create-general-state-select').onchange = (event) => { selectedGeneralState = event.target.value; renderGeneralEditor(authoringDraft.proposal) }
  $('#create-general-information-select').onchange = (event) => { selectedGeneralInformation = event.target.value; renderGeneralEditor(authoringDraft.proposal) }
  $('#create-general-moment-select').onchange = (event) => { selectedGeneralMoment = event.target.value; renderGeneralEditor(authoringDraft.proposal) }
  $('#create-save-general').onclick = saveGeneralProposal
  all('[data-general-review-stage]').forEach((button) => {
    button.onclick = () => {
      generalReviewStage = button.dataset.generalReviewStage
      if (generalReviewStage === 'world') renderGeneralDraftWalkthrough(authoringDraft?.proposal, authoringDraft?.configuration_graph)
      renderGeneralReviewStage(authoringDraft?.proposal)
      $('#create-review-tabs').scrollIntoView({behavior:'smooth', block:'nearest'})
    }
  })
  $('#create-draft-walkthrough-previous').onclick = () => {
    authoredDraftWalkthroughStep = Math.max(0, authoredDraftWalkthroughStep - 1)
    renderGeneralDraftWalkthrough(authoringDraft.proposal, authoringDraft.configuration_graph)
  }
  $('#create-draft-walkthrough-next').onclick = () => {
    if (authoredDraftWalkthroughStep < authoredDraftWalkthroughStepCount - 1) {
      authoredDraftWalkthroughStep += 1
      renderGeneralDraftWalkthrough(authoringDraft.proposal, authoringDraft.configuration_graph)
      return
    }
    $('.create-actions').scrollIntoView({behavior:'smooth', block:'center'})
  }
  $('#create-resolve-questions').onclick = keepQuestionsInsideSimulation
  $('#create-edit-configuration').onclick = showAuthoredConfiguration
  $('#create-approve').onclick = approveAuthoringDraft
  $('#create-run').onclick = runAuthoredSimulation
  $('#create-stop').onclick = stopAuthoredSimulation
  $('#create-start-over').onclick = () => {
    resetAuthoringWorkspace()
    renderCreateSimulation()
    syncUrl()
  }
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

const DEFAULT_API_TIMEOUT_MS = 20000

function projectAuthoredBundleV2(bundle) {
  const scenario = bundle?.scenario || {}
  const run = bundle?.default_run || {}
  const analyses = bundle?.analyses || []
  return {
    ...clone(scenario),
    schema_version:2,
    proposal_kind:'general_world_v2',
    simulation_id:scenario.scenario_id,
    question:bundle.analyst_question || scenario.description || '',
    analyst_question:bundle.analyst_question || null,
    schedule:clone(run.scheduled_moments || []),
    horizon_minutes:run.horizon_minutes,
    termination_conditions:clone(run.termination_conditions || []),
    analyses:clone(analyses),
    analysis_spec:analyses[0] || null,
    analysis_requests:analyses.map((item) => item.purpose),
    unresolved_questions:clone(bundle.unresolved_questions || []),
  }
}

function normalizeAuthoringDocument(document) {
  if (!document || typeof document !== 'object') return document
  if (document.draft && typeof document.draft === 'object') {
    document.draft = normalizeAuthoringDocument(document.draft)
    return document
  }
  if (document.target_kind === 'general_world_v2' && document.proposal?.bundle_version === 2) {
    document.native_bundle = clone(document.proposal)
    document.proposal = projectAuthoredBundleV2(document.native_bundle)
  }
  return document
}

function generalProposalForSave(proposal) {
  if (authoringDraft?.target_kind !== 'general_world_v2') return proposal
  const source = authoringDraft.native_bundle
  if (!source) throw new Error('The retained separated configuration is unavailable; reload this draft.')
  const scenario = clone(source.scenario)
  for (const key of [
    'title', 'description', 'people', 'world_records', 'active_systems',
    'component_requests', 'spatial_extension', 'information_extension',
    'resource_extension', 'relationship_extension', 'sensing_rules',
    'resource_transformations', 'resource_transports', 'fidelity_assumptions',
    'declared_invariants',
  ]) {
    if (Object.hasOwn(proposal, key)) scenario[key] = clone(proposal[key])
  }
  const moments = clone(proposal.schedule || [])
  return {
    proposal_kind:'general_world_v2',
    authored_study_id:source.authored_study_id,
    scenario,
    default_run:{
      horizon_minutes:Math.max(Number(proposal.horizon_minutes || 0), ...moments.map((item) => Number(item.minute || 0)), 1),
      scheduled_moments:moments,
      termination_conditions:clone(proposal.termination_conditions || []),
    },
    analyses:clone(proposal.analyses || []),
    unresolved_questions:clone(proposal.unresolved_questions || []),
    analyst_question:proposal.analyst_question || null,
  }
}

async function apiRequest(path, options = {}) {
  const {timeoutMs = DEFAULT_API_TIMEOUT_MS, ...fetchOptions} = options
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)
  let response
  try {
    response = await fetch(path, {cache:'no-store', signal:controller.signal, ...fetchOptions})
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error(`${path} did not respond within ${Math.round(timeoutMs / 1000)}s`)
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `${path} failed with ${response.status}`)
  return normalizeAuthoringDocument(body)
}

function authoringModel() {
  return runtimeConfig?.authoring?.models?.[0] || null
}

function generalRunModel() {
  return runtimeConfig?.model || runtimeConfig?.authoring?.models?.[0]?.model || null
}

function setAuthoringBusy(busy) {
  authoringBusy = busy
  for (const id of ['create-generate', 'create-configure-now', 'create-revise', 'create-save-person', 'create-save-scenario', 'create-save-network', 'create-save-general', 'create-resolve-questions', 'create-approve', 'create-start-over']) {
    const control = $(`#${id}`)
    if (control) control.disabled = busy
  }
}

function generalDraftProjection(proposal, compiledGraph = null) {
  const nodes = (compiledGraph?.nodes || []).map((item) => ({...item, kind:item.type || item.kind, description:item.description || item.content || item.label, state:{configured:true}}))
  const edges = (compiledGraph?.edges || []).map((item) => ({...item, description:item.description || item.label, enabled:true, routeIds:[item.id]}))
  const addNode = (id, kind, label, description) => {
    if (id && !nodes.some((item) => item.id === id)) nodes.push({id, kind, label, description, state:{configured:true}})
  }
  const addEdge = (id, kind, source, target, description) => {
    if (source && target && nodes.some((item) => item.id === source) && nodes.some((item) => item.id === target)) edges.push({id, kind, source, target, enabled:true, description, routeIds:[id]})
  }
  if (!compiledGraph) {
    for (const person of proposal.people || []) addNode(person.entity_id, 'person', person.label, `${person.position}. ${person.disposition}`)
    for (const record of proposal.world_records || []) addNode(record.record_id, record.kind === 'fulfillment_outcome' ? 'decision_record' : 'thing', record.label, `Canonical ${sentence(record.kind)} record with public and access-controlled state.`)
    for (const place of proposal.spatial_extension?.places || []) addNode(place.place_id, 'place', place.label, 'Configured place in the spatial extension.')
    for (const system of proposal.active_systems || []) addNode(system.system_id, 'mechanism', sentence(system.system_id), `${system.behavior_summary} Representation: ${sentence(system.representation_strategy)}.`)
  }
  for (const moment of proposal.schedule || []) addNode(`moment:${moment.moment_id}`, 'process', `Minute ${moment.minute}`, moment.description)
  if (!compiledGraph) for (const representation of proposal.information_extension?.representations || []) {
    const sourceId = `source:${representation.apparent_source}`
    addNode(sourceId, 'information_source', representation.apparent_source, 'Apparent source named by this configured representation.')
    addNode(representation.representation_id, 'information', sentence(representation.representation_id), representation.content)
    addEdge(`issued:${representation.representation_id}`, 'issued_information', sourceId, representation.representation_id, 'Configured apparent source of this information representation.')
    for (const recipientId of representation.recipient_ids || []) addEdge(`delivery:${representation.representation_id}:${recipientId}`, 'delivered_to', representation.representation_id, recipientId, 'Configured delivery route; receipt during the run is retained separately.')
  }
  if (!compiledGraph) for (const system of proposal.active_systems || []) {
    for (const subjectId of system.subject_refs || []) addEdge(`binding:${system.system_id}:${subjectId}`, 'mechanism_binding', subjectId, system.system_id, 'Configured subject within this transition authority’s causal responsibility.')
  }
  if (!compiledGraph) for (const placement of proposal.spatial_extension?.placements || []) addEdge(`placement:${placement.record_id}`, 'spatial_link', placement.record_id, placement.place_id, 'Configured placement before the run begins.')
  for (const moment of proposal.schedule || []) {
    for (const representationId of moment.external_inject_representation_ids || []) addEdge(`scheduled:${moment.moment_id}:${representationId}`, 'connection', representationId, `moment:${moment.moment_id}`, 'This representation is scheduled to enter at this moment.')
  }
  const orderedMoments = [...(proposal.schedule || [])].sort((left, right) => left.minute - right.minute || left.moment_id.localeCompare(right.moment_id))
  for (let index = 1; index < orderedMoments.length; index += 1) {
    const previous = orderedMoments[index - 1]
    const current = orderedMoments[index]
    addEdge(`schedule-sequence:${previous.moment_id}:${current.moment_id}`, 'scheduled_after', `moment:${previous.moment_id}`, `moment:${current.moment_id}`, `Minute ${current.minute} is scheduled after minute ${previous.minute}. This orders opportunities, not outcomes.`)
  }
  return {nodes, edges}
}

function renderGeneralDraftWalkthrough(proposal, compiledGraph = null) {
  const section = $('#create-draft-walkthrough')
  if (!isGeneralProposal(proposal)) {
    section.hidden = true
    window.CyberneticGraph?.clear?.($('#create-draft-network-graph'))
    return
  }
  if (generalReviewStage !== 'world') {
    section.hidden = true
    return
  }
  section.hidden = false
  const projection = generalDraftProjection(proposal, compiledGraph)
  const idsByType = (types) => new Set(projection.nodes.filter((item) => types.includes(item.type || item.kind)).map((item) => item.id))
  const scene = ({kind, title, summary, seeds, edgeKinds, includeNeighbors = true}) => {
    const seedIds = new Set(seeds)
    const nodeIds = new Set(seedIds)
    if (includeNeighbors) {
      for (const edge of projection.edges) {
        if (!edgeKinds.has(edge.kind) || (!seedIds.has(edge.source) && !seedIds.has(edge.target))) continue
        nodeIds.add(edge.source)
        nodeIds.add(edge.target)
      }
    }
    return {kind, title, summary, nodeIds, edgeKinds}
  }
  const scenesForNodes = ({nodes, kind, title, summary, edgeKinds}) => nodes.map((node, index) => scene({
    kind,
    title:title(node, index),
    summary:summary(node, index),
    seeds:[node.id],
    edgeKinds,
  }))
  const chunkedScenes = ({nodes, size, kind, title, summary, edgeKinds}) => {
    const chunks = []
    for (let index = 0; index < nodes.length; index += size) chunks.push(nodes.slice(index, index + size))
    return chunks.map((chunk, index) => scene({
      kind,
      title:title(chunk, index),
      summary:summary(chunk, index),
      seeds:chunk.map((item) => item.id),
      edgeKinds,
    }))
  }
  const nodesByType = (types) => projection.nodes.filter((item) => types.includes(item.type || item.kind))
  const people = nodesByType(['person'])
  const representations = nodesByType(['representation', 'information'])
  const activeSystems = nodesByType(['active_system'])
  const mechanisms = nodesByType(['mechanism'])
  const placesAndRoutes = idsByType(['place', 'route'])
  const scheduleIds = new Set((proposal.schedule || []).flatMap((item) => [`moment:${item.moment_id}`, ...(item.external_inject_representation_ids || [])]))
  const steps = [
    scene({
      kind:'Actors and relationships',
      title:'Who can perceive, decide, and attempt actions?',
      summary:`${people.length} modeled people act from their own configured memories, position, disposition, capabilities, and limitations. Relationship records describe relevant connections; they do not dictate anyone's behavior.`,
      seeds:people.map((item) => item.id),
      edgeKinds:new Set(['relationship_participant']),
    }),
    scene({
      kind:'Spatial topology',
      title:'Which places and routes exist?',
      summary:'Directed route arrows show configured topology. They indicate where movement may be attempted—not that anything has moved or that a route will work.',
      seeds:placesAndRoutes,
      edgeKinds:new Set(['route_origin', 'route_destination']),
      includeNeighbors:false,
    }),
    ...scenesForNodes({
      nodes:representations,
      kind:'Information path',
      title:(node) => `How can “${node.label}” enter the simulation?`,
      summary:() => 'The apparent source and authorized recipients are explicit. Delivery does not establish truth, attention, belief, or action.',
      edgeKinds:new Set(['apparent_source', 'information_delivery', 'issued_information', 'delivered_to']),
    }),
    ...scenesForNodes({
      nodes:activeSystems,
      kind:'Coarse transition system',
      title:(node) => `What is ${node.label} responsible for?`,
      summary:(node) => `${node.description} The system owns only the displayed causal subjects; it does not schedule actors or control unrelated state.`,
      edgeKinds:new Set(['causal_responsibility']),
    }),
    ...chunkedScenes({
      nodes:mechanisms,
      size:2,
      kind:'Exact transition contracts',
      title:(chunk) => chunk.length === 1 ? 'How does this exact contract constrain change?' : `How do these ${chunk.length} exact contracts constrain change?`,
      summary:(chunk) => `This scene shows ${chunk.map((item) => item.label).join(' and ')}. The arrows state who may attempt them, what they may read or consume, what they may write or produce, and which routes are permitted. Validation—not the actor's prose—determines whether an attempted change commits.`,
      edgeKinds:new Set(['mechanism_read', 'mechanism_write', 'capability', 'result_recipient', 'resource_input', 'resource_output', 'permitted_route']),
    }),
    {
      kind:'Timeline',
      title:'When can information and action enter?',
      summary:`${proposal.schedule.length} configured moments provide opportunities for observation, attempts, and world transitions. Sequence is scheduled; success is not.`,
      nodeIds:scheduleIds,
      edgeKinds:new Set(['connection', 'scheduled_after']),
    },
    {
      kind:'Evaluation',
      title:proposal.analysis_spec ? 'How will the completed run be analyzed?' : 'Is a theory-specific evaluation attached?',
      summary:proposal.analysis_spec
        ? `${proposal.analysis_spec.purpose} The ${sentence(proposal.analysis_spec.profile)} lens reads retained evidence after execution; it cannot change the world or any actor's decision.`
        : 'No analytical framework is selected. The run will retain world changes, observations, action attempts, and evidence without applying Waltzman or another theory-specific lens.',
      nodeIds:new Set(),
      edgeKinds:new Set(),
      informational:true,
    },
  ].filter((step) => step.informational || step.nodeIds.size > 0)
  authoredDraftWalkthroughStepCount = steps.length
  authoredDraftWalkthroughStep = Math.max(0, Math.min(authoredDraftWalkthroughStep, steps.length - 1))
  const step = steps[authoredDraftWalkthroughStep]
  const visibleNodes = projection.nodes.filter((item) => step.nodeIds.has(item.id))
  const visibleIds = new Set(visibleNodes.map((item) => item.id))
  const visibleEdges = projection.edges.filter((item) => step.edgeKinds.has(item.kind) && visibleIds.has(item.source) && visibleIds.has(item.target))
  $('#create-draft-walkthrough-progress').textContent = `Step ${authoredDraftWalkthroughStep + 1} of ${steps.length}`
  $('#create-draft-walkthrough-kind').textContent = step.kind
  $('#create-draft-walkthrough-title').textContent = step.title
  $('#create-draft-walkthrough-summary').textContent = step.summary
  $('#create-draft-walkthrough-previous').disabled = authoredDraftWalkthroughStep === 0
  $('#create-draft-walkthrough-next').textContent = authoredDraftWalkthroughStep === steps.length - 1 ? 'Review and approve ↓' : 'Next →'
  $('#create-draft-walkthrough-selection').textContent = step.informational
    ? 'Analysis is a read-only projection over retained evidence.'
    : 'Select a visible item or path to inspect its configured meaning.'
  $('#create-draft-network-status').textContent = `${visibleNodes.length} configured items · ${visibleEdges.length} configured paths · no runtime event is implied`
  const graph = $('#create-draft-network-graph')
  if (step.informational) {
    window.CyberneticGraph?.clear?.(graph)
    graph.innerHTML = `<div class="analysis-boundary-diagram">
      <article><span>1</span><strong>Simulation executes</strong><small>Actors and transition authorities may change canonical world state.</small></article>
      <i aria-hidden="true">→</i>
      <article><span>2</span><strong>Evidence is retained</strong><small>Observations, attempts, validations, commits, and outcomes remain auditable.</small></article>
      <i aria-hidden="true">→</i>
      <article><span>3</span><strong>${escapeHtml(proposal.analysis_spec ? sentence(proposal.analysis_spec.profile) : 'No selected lens')}</strong><small>${escapeHtml(proposal.analysis_spec ? 'Reads evidence after the run. Cannot write world state.' : 'Raw evidence remains available without a theory-specific score.')}</small></article>
    </div>`
    $('#create-draft-network-status').textContent = proposal.analysis_spec
      ? 'Selected analysis reads retained evidence after execution · it has no transition authority'
      : 'No theory-specific analysis is attached · execution evidence is still retained'
    return
  }
  if (!visibleNodes.length || !window.CyberneticGraph) {
    graph.innerHTML = '<p class="create-result-no-graph">No configured graph items are available for this step.</p>'
    return
  }
  window.CyberneticGraph.render(graph, {
    nodes:visibleNodes, edges:visibleEdges, legendNodes:visibleNodes, legendEdges:visibleEdges,
    boundaries:[], world:null, trajectory:{nodes:[], edges:[]}, graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:'causal', event:null, initialRevision:authoringDraft?.revision || 0, title:step.title, subtitle:'configured before execution', showLegend:true, showMiniMap:false,
    selectedNodeId:null, selectedEdgeId:null, boundary:null, collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const item = projection.nodes.find((candidate) => candidate.id === nodeId)
      if (item) $('#create-draft-walkthrough-selection').innerHTML = `<strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span>`
    },
    onSelectEdge:(item) => { $('#create-draft-walkthrough-selection').innerHTML = `<strong>${escapeHtml(sentence(item.kind))}</strong><span>${escapeHtml(item.description)}</span>` },
  })
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

function isGeneralProposal(proposal) {
  return ['general_world_v1', 'general_world_v2'].includes(proposal?.proposal_kind)
}

const generalReviewStageLabels = {
  world:'world state',
  people:'people',
  information:'information paths',
  processes:'transition processes',
  run:'run timing',
  analysis:'optional analysis',
}

function renderGeneralReviewStage(proposal) {
  const general = isGeneralProposal(proposal)
  const tabs = $('#create-review-tabs')
  tabs.hidden = !general
  if (!general) {
    for (const id of ['create-information-summary', 'create-process-summary', 'create-run-summary', 'create-analysis-summary']) $(`#${id}`).hidden = true
    $('#create-coverage').hidden = false
    $('.create-world-summary').hidden = false
    $('.create-people').hidden = false
    return
  }
  if (!Object.hasOwn(generalReviewStageLabels, generalReviewStage)) generalReviewStage = 'world'
  all('[data-general-review-stage]').forEach((button) => {
    const selected = button.dataset.generalReviewStage === generalReviewStage
    button.classList.toggle('active', selected)
    button.setAttribute('aria-selected', String(selected))
  })
  all('[data-general-review-panel]').forEach((panel) => {
    panel.hidden = panel.dataset.generalReviewPanel !== generalReviewStage
  })
  all('[data-general-editor-stage]').forEach((field) => {
    field.hidden = field.dataset.generalEditorStage !== generalReviewStage
  })
  const editor = $('#create-general-editor')
  editor.hidden = generalReviewStage === 'processes'
  $('#create-general-editor-heading').textContent = `Edit ${generalReviewStageLabels[generalReviewStage]} directly`
  $('#create-general-status').textContent = generalReviewStage === 'processes'
    ? 'Ask the authoring model below to change a transition process; compiler coverage will be regenerated.'
    : 'Change the visible fields, then save one retained typed revision without another model call.'
}

function renderGeneralStageSummaries(proposal) {
  const representations = proposal.information_extension?.representations || []
  const peopleById = new Map(proposal.people.map((person) => [person.entity_id, person.label]))
  const activeSystems = proposal.active_systems || []
  const requests = proposal.component_requests || []
  const coverageByRequest = new Map((authoringDraft?.coverage?.items || []).map((item) => [item.request_id, item]))
  $('#create-information-list').innerHTML = representations.length
    ? representations.map((item) => `<article><span>${escapeHtml(item.apparent_source)} → ${escapeHtml(item.recipient_ids.map((id) => peopleById.get(id) || id).join(', '))}</span><strong>${escapeHtml(sentence(item.representation_id))}</strong><p>${escapeHtml(item.content)}</p><small>Configured delivery path · not automatic truth or belief</small></article>`).join('')
    : '<p class="create-stage-empty">No information representations or delivery paths are configured.</p>'
  $('#create-process-list').innerHTML = [
    ...activeSystems.map((item) => `<article><span>Coarse transition system</span><strong>${escapeHtml(sentence(item.system_id))}</strong><p>${escapeHtml(item.behavior_summary)}</p><small>${escapeHtml(sentence(item.representation_strategy))} · owns ${escapeHtml((item.causal_responsibility_tags || []).map(sentence).join(', ') || 'declared bounded effects')}</small></article>`),
    ...requests.map((item) => {
      const coverage = coverageByRequest.get(item.request_id)
      const classification = coverage?.classification || 'unclassified'
      const closure = coverage?.causal_closure || 'unknown'
      return `<article><span>${escapeHtml(sentence(classification))} authority · ${escapeHtml(sentence(closure))} closure</span><strong>${escapeHtml(sentence(item.request_id))}</strong><p>${escapeHtml(item.behavior_description)}</p><small>${item.material_to_question ? 'Material to the configured world' : 'Supporting behavior'}${coverage?.blocking ? ' · blocks approval' : ''}</small></article>`
    }),
  ].join('') || '<p class="create-stage-empty">No executable transition process is configured.</p>'
  $('#create-run-list').innerHTML = proposal.schedule.length
    ? [...proposal.schedule].sort((left, right) => left.minute - right.minute).map((item, index) => `<article><span>Moment ${index + 1} · minute ${escapeHtml(item.minute)}</span><strong>${escapeHtml(sentence(item.moment_id))}</strong><p>${escapeHtml(item.description)}</p><small>${item.external_inject_representation_ids?.length ? `Introduces ${escapeHtml(item.external_inject_representation_ids.map(sentence).join(', '))}` : 'No external information injected at this moment'}</small></article>`).join('')
    : '<p class="create-stage-empty">No scheduled moments are configured.</p>'
  $('#create-analysis-detail').innerHTML = proposal.analysis_spec
    ? `<article><span>Post-run lens</span><strong>${escapeHtml(sentence(proposal.analysis_spec.profile))}</strong><p>${escapeHtml(proposal.analysis_spec.purpose)}</p><small>Reads retained evidence only · cannot affect execution</small></article>`
    : `<article><span>No selected lens</span><strong>Raw retained evidence remains available</strong><p>${escapeHtml(proposal.analyst_question || 'No analysis question is required to execute this simulation.')}</p><small>You can attach an analysis after the run without changing the simulated world.</small></article>`
  $('#create-review-world-count').textContent = `${proposal.world_records.length} records`
  $('#create-review-people-count').textContent = `${proposal.people.length} people`
  $('#create-review-information-count').textContent = `${representations.length} items`
  $('#create-review-processes-count').textContent = `${activeSystems.length + requests.length} definitions`
  $('#create-review-run-count').textContent = `${proposal.schedule.length} moments`
}

function hasCurrentDependencyReview(draft) {
  const latestMessage = (draft?.messages || []).at(-1)
  return latestMessage?.source === 'conversation'
    && (latestMessage.trace_ids || []).some((traceId) => String(traceId).includes('/dependency-review'))
}

function renderGeneralCoverage(draft) {
  const coverage = draft.coverage || {items:[], blocking_request_ids:[]}
  const dependencyReviewPassed = hasCurrentDependencyReview(draft)
  const counts = coverage.items.reduce((result, item) => {
    result[item.classification] = (result[item.classification] || 0) + 1
    return result
  }, {})
  const closureCounts = coverage.items.reduce((result, item) => {
    const closure = item.causal_closure || 'unknown'
    result[closure] = (result[closure] || 0) + 1
    return result
  }, {})
  $('#create-coverage').open = (coverage.blocking_request_ids || []).length > 0
  $('#create-coverage-summary').textContent = `Execution coverage · ${counts.exact || 0} exact authorities · ${counts.coarse_llm || 0} coarse LLM · causal closure: ${closureCounts.exact || 0} exact · ${closureCounts.partial || 0} partial · ${closureCounts.coarse || 0} coarse · ${closureCounts.descriptive || 0} descriptive · ${closureCounts.unsupported || 0} unsupported${dependencyReviewPassed ? ' · dependency review passed' : ''}`
  $('#create-coverage-detail').innerHTML = coverage.items.length
    ? coverage.items.map((item) => {
      const missing = item.unenforced_dependency_refs || []
      const enforced = (item.dependency_enforcement || []).filter((dependency) => dependency.enforcement === 'exact_read').map((dependency) => dependency.dependency_ref)
      const closure = item.causal_closure || 'unknown'
      return `<p><strong>${escapeHtml(sentence(item.request_id))} · ${escapeHtml(sentence(item.classification))} authority · ${escapeHtml(sentence(closure))} causal closure${item.blocking ? ' · blocks approval' : ''}</strong><span>${escapeHtml((item.what_can_change || []).join(' · ') || 'No executable change is claimed.')}</span>${enforced.length ? `<span>Exact reads and guards: ${escapeHtml(enforced.map(sentence).join(', '))}</span>` : ''}${missing.length ? `<span>Not read by an exact contract: ${escapeHtml(missing.map(sentence).join(', '))}</span>` : ''}<small>${escapeHtml((item.assumptions || []).join(' · ') || (item.compiler_evidence || []).join(' · '))}</small></p>`
    }).join('')
    : '<p><strong>No execution coverage was compiled.</strong><span>The draft cannot be approved until material behavior is classified.</span></p>'
}

function generalStateEntries(record) {
  return [...(record?.public_state || []), ...(record?.hidden_state || [])]
}

function renderGeneralEditor(proposal) {
  const editor = $('#create-general-editor')
  if (!isGeneralProposal(proposal)) {
    editor.hidden = true
    return
  }
  editor.hidden = false
  $('#create-general-question').value = proposal.analyst_question || ''
  $('#create-general-description').value = proposal.description

  if (!proposal.people.some((item) => item.entity_id === selectedGeneralPerson)) selectedGeneralPerson = proposal.people[0]?.entity_id
  $('#create-general-person-select').innerHTML = proposal.people.map((item) => `<option value="${escapeHtml(item.entity_id)}">${escapeHtml(item.label)}</option>`).join('')
  $('#create-general-person-select').value = selectedGeneralPerson
  const person = proposal.people.find((item) => item.entity_id === selectedGeneralPerson)
  $('#create-general-person-position').value = person?.position || ''
  $('#create-general-person-disposition').value = person?.disposition || ''
  $('#create-general-person-memories').value = (person?.memories || []).join('\n')

  if (!proposal.world_records.some((item) => item.record_id === selectedGeneralRecord)) selectedGeneralRecord = proposal.world_records[0]?.record_id
  $('#create-general-record-select').innerHTML = proposal.world_records.map((item) => `<option value="${escapeHtml(item.record_id)}">${escapeHtml(item.label)}</option>`).join('')
  $('#create-general-record-select').value = selectedGeneralRecord
  const record = proposal.world_records.find((item) => item.record_id === selectedGeneralRecord)
  const states = generalStateEntries(record)
  if (!states.some((item) => item.key === selectedGeneralState)) selectedGeneralState = states[0]?.key
  $('#create-general-state-select').innerHTML = states.map((item) => `<option value="${escapeHtml(item.key)}">${escapeHtml(sentence(item.key))}</option>`).join('')
  $('#create-general-state-select').value = selectedGeneralState
  const stateEntry = states.find((item) => item.key === selectedGeneralState)
  $('#create-general-state-value').value = Array.isArray(stateEntry?.value) ? JSON.stringify(stateEntry.value) : String(stateEntry?.value ?? '')

  const representations = proposal.information_extension?.representations || []
  if (!representations.some((item) => item.representation_id === selectedGeneralInformation)) selectedGeneralInformation = representations[0]?.representation_id
  $('#create-general-information-select').innerHTML = representations.map((item) => `<option value="${escapeHtml(item.representation_id)}">${escapeHtml(sentence(item.representation_id))}</option>`).join('')
  $('#create-general-information-select').value = selectedGeneralInformation || ''
  const representation = representations.find((item) => item.representation_id === selectedGeneralInformation)
  $('#create-general-recipients').innerHTML = proposal.people.map((item) => `<label><input type="checkbox" data-general-recipient="${escapeHtml(item.entity_id)}" ${(representation?.recipient_ids || []).includes(item.entity_id) ? 'checked' : ''}>${escapeHtml(item.label)}</label>`).join('')

  if (!proposal.schedule.some((item) => item.moment_id === selectedGeneralMoment)) selectedGeneralMoment = proposal.schedule[0]?.moment_id
  $('#create-general-moment-select').innerHTML = proposal.schedule.map((item) => `<option value="${escapeHtml(item.moment_id)}">${escapeHtml(item.description)}</option>`).join('')
  $('#create-general-moment-select').value = selectedGeneralMoment
  $('#create-general-minute').value = proposal.schedule.find((item) => item.moment_id === selectedGeneralMoment)?.minute ?? 0
  renderGeneralReviewStage(proposal)
}

function parseGeneralStateValue(text, original) {
  if (Array.isArray(original)) {
    const parsed = JSON.parse(text)
    if (!Array.isArray(parsed)) throw new Error('List-valued state must remain a JSON list.')
    return parsed
  }
  if (typeof original === 'boolean') {
    if (!['true', 'false'].includes(text.toLowerCase())) throw new Error('Boolean state must be true or false.')
    return text.toLowerCase() === 'true'
  }
  if (typeof original === 'number') {
    const parsed = Number(text)
    if (!Number.isFinite(parsed)) throw new Error('Numeric state must remain a number.')
    return parsed
  }
  return text
}

function renderAuthoringBrief(proposal) {
  if (isGeneralProposal(proposal)) {
    const representations = proposal.information_extension?.representations || []
    const peopleById = new Map(proposal.people.map((person) => [person.entity_id, person.label]))
    const recipients = representations.reduce((total, item) => total + item.recipient_ids.length, 0)
    const plannedCalls = proposal.schedule.length * (proposal.people.length + 1)
    const maximumCalls = proposal.schedule.length * ((proposal.people.length * 2) + 2)
    $('#create-brief-question').innerHTML = proposal.analyst_question
      ? `<strong>Optional review question</strong><p>${escapeHtml(proposal.analyst_question)}</p>`
      : `<strong>World to simulate</strong><p>${escapeHtml(proposal.description)}</p><small>No analytical question is required to run this world.</small>`
    $('#create-brief-people').innerHTML = `<strong>${proposal.people.length} simulated ${proposal.people.length === 1 ? 'person' : 'people'}</strong><p>${proposal.people.map((person) => escapeHtml(person.label)).join(' · ')}</p>`
    $('#create-brief-influences').innerHTML = representations.length
      ? `<strong>${representations.length} information ${representations.length === 1 ? 'item' : 'items'} · ${recipients} explicit deliveries</strong><ol>${representations.map((item) => `<li><strong>${escapeHtml(item.apparent_source)} → ${escapeHtml(item.recipient_ids.map((id) => peopleById.get(id) || id).join(', '))}</strong><span>${escapeHtml(item.content)}</span></li>`).join('')}</ol>`
      : '<strong>No information paths are configured.</strong>'
    $('#create-brief-rule').innerHTML = `<strong>${proposal.schedule.length} scheduled ${proposal.schedule.length === 1 ? 'moment' : 'moments'} · ${plannedCalls} planned model calls</strong><p>Up to ${maximumCalls} calls if every typed output needs one repair.<br>${proposal.schedule.map((item) => `Minute ${escapeHtml(item.minute)} · ${escapeHtml(item.description)}`).join('<br>')}</p>`
    $('#create-brief-analysis-card').hidden = false
    $('#create-brief-analysis').innerHTML = proposal.analysis_spec
      ? `<strong>${escapeHtml(sentence(proposal.analysis_spec.profile))}</strong><p>${escapeHtml(proposal.analysis_spec.purpose)}</p>`
      : '<strong>No analytical framework selected</strong><p>You can inspect the retained world changes, observations, actions, and evidence without a theory-specific score.</p>'
    all('[data-create-edit]').forEach((button) => {
      button.onclick = () => {
        const target = $('#create-general-editor')
        target.open = true
        target.scrollIntoView({behavior:'smooth', block:'start'})
      }
    })
    return
  }
  const workflow = proposal.workflow || {}
  $('#create-brief-analysis-card').hidden = false
  const people = proposal.people || []
  const peopleById = new Map(people.map((person) => [person.entity_id, person]))
  const objectsById = new Map((proposal.objects || []).map((item) => [item.entity_id, item]))
  const informationById = new Map((proposal.information || []).map((item) => [item.information_id, item]))
  const deliveries = workflow.deliveries || []
  const question = workflow.collective_question || workflow.collective_goal?.description || proposal.description
  $('#create-brief-question').innerHTML = `<strong>Configured purpose</strong><p>${escapeHtml(question)}</p>`
  $('#create-brief-analysis').innerHTML = '<strong>Built-in workflow assessment</strong><p>This earlier workflow evaluates its configured terminal decision rule.</p>'
  $('#create-brief-people').innerHTML = `<strong>${people.length} independent ${people.length === 1 ? 'person' : 'people'}</strong><p>${people.map((person) => escapeHtml(person.label)).join(' · ')}</p>`
  if (deliveries.length) {
    $('#create-brief-influences').innerHTML = `<ol>${deliveries.map((delivery) => {
      const source = objectsById.get(delivery.source_id)?.label || delivery.source_id
      const recipients = (delivery.recipient_ids || []).map((id) => peopleById.get(id)?.label || id)
      const content = informationById.get(delivery.information_id)?.content || delivery.information_id
      return `<li><strong>${escapeHtml(source)} → ${escapeHtml(recipients.join(', '))}</strong><span>Minute ${escapeHtml(delivery.delivery_minutes)} · ${escapeHtml(content)}</span></li>`
    }).join('')}</ol>`
  } else {
    const information = proposal.information || []
    $('#create-brief-influences').innerHTML = information.length
      ? `<strong>${information.length} configured information ${information.length === 1 ? 'item' : 'items'}</strong><p>${information.map((item) => escapeHtml(item.label)).join(' · ')}</p>`
      : '<strong>No incoming information is configured.</strong>'
  }
  const rounds = workflow.round_minutes || (proposal.timing_assumptions || []).filter((item) => item.name.startsWith('decision_round_')).map((item) => item.minutes)
  const rule = workflow.decision_rule
  $('#create-brief-rule').innerHTML = rule
    ? `<strong>${rounds.length} decision ${rounds.length === 1 ? 'round' : 'rounds'} · minutes ${escapeHtml(rounds.join(', '))}</strong><p>Passes with at least ${escapeHtml(rule.minimum_support)} full support, ${escapeHtml(rule.minimum_support_or_conditional)} support or conditional support, and no more than ${escapeHtml(rule.maximum_oppose)} opposition.</p>`
    : `<strong>${rounds.length ? `${rounds.length} configured decision rounds` : draftTemplateLabel(workflow.template_id)}</strong><p>The reviewed template supplies the exact terminal rule.</p>`
  const networkEditor = $('#create-network-editor')
  const scenarioEditor = $('#create-scenario-editor')
  all('[data-create-edit]').forEach((button) => {
    button.onclick = () => {
      let target
      if (button.dataset.createEdit === 'people') target = $('.create-person-editor')
      else target = !networkEditor.hidden ? networkEditor : !scenarioEditor.hidden ? scenarioEditor : $('.create-revise')
      if (target.tagName === 'DETAILS') target.open = true
      target.scrollIntoView({behavior:'smooth', block:'start'})
      const focusTarget = target.querySelector('select, textarea, input')
      if (focusTarget) window.setTimeout(() => focusTarget.focus(), 350)
    }
  })
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

function setCreateFlow(step) {
  const steps = ['describe', 'review', 'run', 'replay']
  all('.create-flow span').forEach((item, index) => {
    item.classList.toggle('active', steps[index] === step)
  })
}

function renderCreateSimulation() {
  const runStatus = $('#create-run-status')
  const review = $('#create-review')
  const leavingSimulationLibrary = runStatus.parentElement === $('#simulation-replay-host')
  if (runStatus.parentElement !== review) review.appendChild(runStatus)
  if (leavingSimulationLibrary) {
    authoringDraft = null
    authoredResult = null
    authoredRunId = null
    document.body.classList.remove('authored-result')
    review.classList.remove('result-mode')
    runStatus.hidden = true
    $('#create-result').hidden = true
  }
  const author = authoringModel()
  $('#create-view').classList.toggle('has-draft', Boolean(authoringDraft))
  $('#create-title').textContent = authoringDraft?.proposal
    ? 'Review and run this simulation.'
    : 'Design a simulation with the selected authoring model.'
  $('.create-hero > p').textContent = authoringDraft?.proposal
    ? 'Review the world, the run conditions, and any optional analysis separately. Everything below is retained and editable before the selected model runs the simulation.'
    : 'Describe a world in ordinary language. The authoring model can clarify it with you, or configure it immediately using disclosed assumptions.'
  $('#create-generate').disabled = !author || authoringBusy
  $('#create-configure-now').disabled = !author || authoringBusy
  renderAuthoringChat()
  if (!authoringDraft) {
    if (authoredResult && document.body.classList.contains('authored-result')) {
      setCreateFlow('replay')
      $('#create-review').hidden = false
      return
    }
    setCreateFlow('describe')
    $('.create-composer').hidden = false
    $('.create-hero .case-label').textContent = 'Create a simulation'
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
    : '<p class="create-diagnostic ready"><strong>Compiler check passed</strong>References and declared execution coverage are valid. Review causal-closure labels before approval.</p>'
  if (!proposal) {
    $('.create-composer').hidden = false
    $('#create-review').hidden = true
    $('.create-brief').hidden = true
    setCreateFlow('describe')
    $('#create-status').textContent = authoringDraft.authoring_summary || 'Reply to the authoring model using the revision box below.'
    $('#create-draft-title').textContent = 'Draft needs more information'
    $('#create-draft-description').textContent = authoringDraft.authoring_summary || 'Reply to the authoring model using the revision box below.'
    $('#create-world-facts').innerHTML = ''
    $('#create-world-groups').innerHTML = ''
    $('#create-people-list').innerHTML = ''
    $('#create-person-select').innerHTML = ''
    $('#create-scenario-editor').hidden = true
    $('#create-network-editor').hidden = true
    $('#create-general-editor').hidden = true
    $('#create-raw-configuration').textContent = 'No valid typed configuration has been produced yet.'
    $('#create-approve').hidden = true
    $('#create-run').hidden = true
    return
  }
  $('.create-composer').hidden = true
  const general = isGeneralProposal(proposal)
  const workflow = proposal.workflow || {}
  if (general) renderGeneralCoverage(authoringDraft)
  else renderAuthoringCoverage(proposal)
  renderCoordinationScenarioEditor(proposal)
  renderInfluenceNetworkEditor(proposal)
  renderGeneralEditor(proposal)
  renderGeneralDraftWalkthrough(proposal, authoringDraft.configuration_graph)
  $('.create-brief').hidden = general
  renderAuthoringBrief(proposal)
  $('#create-draft-title').textContent = proposal.title
  $('#create-draft-description').textContent = proposal.description
  const boundaries = proposal.analytical_boundaries || []
  const places = general ? (proposal.spatial_extension?.places || []) : (proposal.places || [])
  const information = general ? (proposal.information_extension?.representations || []) : (proposal.information || [])
  const objects = general ? proposal.world_records : (proposal.objects || [])
  $('#create-world-facts').innerHTML = [
    [general ? 'General compiled world' : draftTemplateLabel(workflow.template_id), 'Execution profile'],
    [`${proposal.people?.length || 0}`, 'People'],
    [`${objects.length}`, 'World records'],
    [`${places.length}`, 'Places'],
    [`${information.length}`, 'Information items'],
    [`${general ? proposal.active_systems.length : boundaries.length}`, general ? 'Active systems' : 'Analytical boundaries'],
  ].map(([value, label]) => `<div><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join('')
  $('#create-world-groups').innerHTML = general ? [
    ['World records', objects.map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(sentence(item.kind))} · ${(item.public_state || []).map((entry) => `${escapeHtml(sentence(entry.key))}: ${escapeHtml(Array.isArray(entry.value) ? JSON.stringify(entry.value) : entry.value)}`).join(' · ')}</span></li>`).join('')],
    ['Places and routes', [
      ...(proposal.spatial_extension?.places || []).map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>Configured place</span></li>`),
      ...(proposal.spatial_extension?.links || []).map((item) => `<li><strong>${escapeHtml(sentence(item.link_id))}</strong><span>${escapeHtml(item.origin_place_id)} → ${escapeHtml(item.destination_place_id)} · ${item.operational ? 'operational' : 'not operational'}</span></li>`),
    ].join('')],
    ['Conserved resources', (proposal.resource_extension?.stocks || []).map((item) => `<li><strong>${escapeHtml(sentence(item.resource_id))}</strong><span>${escapeHtml(item.quantity)} · custodian ${escapeHtml(item.custodian_id)}${item.conserved ? ' · conserved' : ''}</span></li>`).join('')],
  ].filter(([, items]) => items).map(([label, items]) => `<section><h4>${escapeHtml(label)}</h4><ul>${items}</ul></section>`).join('') : [
    ['Groups and analytical boundaries', boundaries.map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></li>`).join('')],
    ['World entities and processes', objects.map((item) => `<li><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></li>`).join('')],
    ['Information in the scenario', information.map((item) => `<li><strong>${escapeHtml(sentence(item.label))}</strong><span>${escapeHtml(item.content)}</span></li>`).join('')],
  ].filter(([, items]) => items).map(([label, items]) => `<section><h4>${escapeHtml(label)}</h4><ul>${items}</ul></section>`).join('')
  $('#create-people-list').innerHTML = proposal.people.map((person) => `<article><strong>${escapeHtml(person.label)}</strong><span>${escapeHtml(person.position)}</span><p>${escapeHtml(person.disposition)}</p></article>`).join('')
  if (general) renderGeneralStageSummaries(proposal)
  $('.create-person-editor').hidden = general
  $('#create-person-select').innerHTML = proposal.people.map((person) => `<option value="${escapeHtml(person.entity_id)}">${escapeHtml(person.label)}</option>`).join('')
  if (!general) renderAuthoringPersonEditor()
  $('#create-raw-configuration').textContent = JSON.stringify(proposal, null, 2)
  renderGeneralReviewStage(proposal)
  const coverageBlocked = (authoringDraft.coverage?.blocking_request_ids || []).length > 0
  const dependencyReviewPassed = !general || hasCurrentDependencyReview(authoringDraft)
  const ready = authoringDraft.status === 'ready_for_review' && diagnostics.length === 0 && !coverageBlocked
  const onlyOpenQuestions = general && diagnostics.length > 0 && diagnostics.every((item) => item.code === 'unresolved') && !coverageBlocked
  $('#create-resolve-questions').hidden = !onlyOpenQuestions
  $('#create-approve').hidden = !ready
  $('#create-run').hidden = authoringDraft.status !== 'approved' || coverageBlocked
  $('#create-action-heading').textContent = authoringDraft.status === 'approved'
    ? coverageBlocked
      ? 'Approval needs revision'
      : 'Approved and ready to run'
    : onlyOpenQuestions
      ? 'Choose where these decisions belong'
      : ready
        ? 'Ready for your decision'
        : 'Resolve the items above before running'
  $('#create-action-detail').textContent = authoringDraft.status === 'approved'
    ? coverageBlocked
      ? 'This saved approval predates the current causal-closure check. Revise and approve the configuration again before running.'
      : 'The selected model will now operate the modeled people and coarse transition authorities.'
    : onlyOpenQuestions
      ? 'These questions can remain endogenous: the modeled people decide them during the run instead of you deciding them in advance.'
      : ready
        ? dependencyReviewPassed
          ? 'The generated configuration passed a separate dependency-completeness review. Approve this exact retained configuration, then run it with the selected model.'
          : 'Direct edits passed typed compiler checks, but no semantic dependency review has run on this revision. You may inspect and approve it or ask the authoring model to review the revision.'
        : 'Unsupported material behavior or invalid configuration must be corrected before approval.'
  const showingResult = document.body.classList.contains('authored-result')
    && !$('#create-result').hidden
  setCreateFlow(showingResult ? 'replay' : authoringDraft.status === 'approved' ? 'run' : 'review')
  setAuthoringBusy(authoringBusy)
  $('#create-status').textContent = authoringDraft.status === 'approved'
    ? 'This exact simulation is approved. Run it now, or edit it to create a new revision.'
    : general
      ? 'Review the people, world state, information routes, timing, and execution coverage. Edit directly or request a revision.'
      : 'Review the people and incoming information. Request a change or approve the simulation.'
}

async function keepQuestionsInsideSimulation() {
  if (!authoringDraft || !isGeneralProposal(authoringDraft.proposal)) return
  const proposal = clone(authoringDraft.proposal)
  proposal.unresolved_questions = []
  setAuthoringBusy(true)
  $('#create-status').textContent = 'Keeping these choices inside the simulation and recompiling…'
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/general-proposal`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision, edit_id:crypto.randomUUID(), proposal:generalProposalForSave(proposal)}),
    })
    renderCreateSimulation()
    $('.create-actions').scrollIntoView({behavior:'smooth', block:'center'})
    syncUrl()
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
  }
}

function renderAuthoringChat() {
  const messages = authoringDraft?.messages || []
  if (!messages.length) return
  $('#create-chat').innerHTML = messages.map((item) => `<article class="user"><strong>You</strong><p>${escapeHtml(item.content)}</p></article><article class="assistant"><strong>Authoring model</strong><p>${escapeHtml(item.assistant_summary || 'I retained that context.')}</p></article>`).join('')
  $('#create-chat').scrollTop = $('#create-chat').scrollHeight
}

async function advanceAuthoringDraft(message, mode = 'configure') {
  const author = authoringModel()
  if (!author) throw new Error('The structured authoring model is unavailable')
  if (!authoringDraft) authoringDraft = await apiRequest('api/authoring/drafts', {method:'POST'})
  const messageId = crypto.randomUUID()
  const response = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/messages`, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({
      expected_revision:authoringDraft.revision,
      message_id:messageId,
      message,
      model:authoringModel()?.model,
      reasoning_effort:'medium',
      mode,
    }),
  })
  if (response.status === 'generating' && response.job_id) {
    const startedAt = Date.now()
    const deadline = startedAt + 900000
    let job = response
    while (job.status === 'generating' && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      job = await apiRequest(`api/authoring/jobs/${encodeURIComponent(response.job_id)}`)
      if (job.status === 'generating' && Date.now() - startedAt > 120000) {
        $('#create-status').textContent = 'Still compiling the typed world and checking its causal paths. Keep this tab open; the retained draft is safe to reload.'
      }
    }
    if (job.status === 'failed') throw new Error(job.error || 'Simulation generation failed')
    if (job.status !== 'completed' || !job.draft) {
      throw new Error('Simulation generation is still running. Reload this draft shortly.')
    }
    authoringDraft = job.draft
  } else {
    authoringDraft = response
  }
  renderCreateSimulation()
  syncUrl()
}

function focusAuthoringReview() {
  window.requestAnimationFrame(() => $('#create-review').scrollIntoView({behavior:'smooth', block:'start'}))
}

async function discussAuthoringDraft() {
  const message = $('#create-prompt').value.trim()
  if (!message) {
    $('#create-status').textContent = 'Write a message for the authoring model.'
    return
  }
  setAuthoringBusy(true)
  $('#create-status').textContent = 'The authoring model is considering what materially needs clarification…'
  try {
    await advanceAuthoringDraft(message, 'discuss')
    $('#create-prompt').value = ''
    $('#create-prompt').focus()
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
    $('#create-generate').disabled = !authoringModel()
  }
}

async function configureAuthoringDraft() {
  const typed = $('#create-prompt').value.trim()
  const message = typed || 'Configure the simulation now from our retained conversation. Make reasonable assumptions for every unanswered detail, disclose them in fidelity_assumptions, do not invent an analyst research question, and keep actor choices endogenous.'
  setAuthoringBusy(true)
  $('#create-status').textContent = 'The authoring model is making explicit assumptions and compiling the editable simulation…'
  try {
    await advanceAuthoringDraft(message, 'configure')
    $('#create-prompt').value = ''
    focusAuthoringReview()
  } catch (error) {
    $('#create-status').textContent = error.message
  } finally {
    setAuthoringBusy(false)
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
    focusAuthoringReview()
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

async function saveGeneralProposal() {
  const original = authoringDraft?.proposal
  if (!isGeneralProposal(original)) return
  const proposal = clone(original)
  const person = proposal.people.find((item) => item.entity_id === selectedGeneralPerson)
  const record = proposal.world_records.find((item) => item.record_id === selectedGeneralRecord)
  const representation = proposal.information_extension?.representations.find((item) => item.representation_id === selectedGeneralInformation)
  const moment = proposal.schedule.find((item) => item.moment_id === selectedGeneralMoment)
  const stateEntry = generalStateEntries(record).find((item) => item.key === selectedGeneralState)
  const minute = Number($('#create-general-minute').value)
  try {
    proposal.analyst_question = $('#create-general-question').value.trim() || null
    proposal.question = proposal.analyst_question || proposal.description
    proposal.description = $('#create-general-description').value.trim()
    if (!proposal.description) throw new Error('The world description cannot be empty.')
    if (person) {
      person.position = $('#create-general-person-position').value.trim()
      person.disposition = $('#create-general-person-disposition').value.trim()
      person.memories = lineItems($('#create-general-person-memories').value)
      if (!person.position || !person.disposition || !person.memories.length) throw new Error('The selected person needs a position, disposition, and at least one memory.')
    }
    if (stateEntry) stateEntry.value = parseGeneralStateValue($('#create-general-state-value').value.trim(), stateEntry.value)
    if (representation) {
      representation.recipient_ids = [...document.querySelectorAll('[data-general-recipient]:checked')].map((input) => input.dataset.generalRecipient)
      if (!representation.recipient_ids.length) throw new Error('The selected information item needs at least one recipient.')
    }
    if (moment) {
      if (!Number.isInteger(minute) || minute < 0) throw new Error('The scheduled minute must be a non-negative whole number.')
      moment.minute = minute
    }
  } catch (error) {
    $('#create-general-status').textContent = error.message
    return
  }
  setAuthoringBusy(true)
  $('#create-general-status').textContent = 'Saving this typed revision and recompiling coverage…'
  try {
    authoringDraft = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/general-proposal`, {
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision, edit_id:crypto.randomUUID(), proposal:generalProposalForSave(proposal)}),
    })
    renderCreateSimulation()
    syncUrl()
    $('#create-general-status').textContent = `Saved revision ${authoringDraft.revision}. Compiler coverage was regenerated without a model call.`
  } catch (error) {
    $('#create-general-status').textContent = error.message
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
  const payloads = step.actions?.map((item) => item.payload).filter((payload) => payload && typeof payload === 'object') || []
  return payloads.find((payload) => payload.stance) || payloads[0] || null
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
  const generalWorld = result.profile === 'general_world_v1'
  $('#create-result-round-tabs').innerHTML = rounds.map((round, index) => {
    const counts = countValues((round.decisions || []).map((step) => authoredStepPayload(step)?.stance || 'defer'))
    const summary = generalWorld ? `${round.decisions?.length || 0} actions` : countsText(counts)
    return `<button type="button" data-authored-round="${index}" class="${index === authoredResultRoundIndex ? 'active' : ''}"><span>${generalWorld ? 'Moment' : 'Round'} ${escapeHtml(round.round_index)}</span><strong>${escapeHtml(summary)}</strong></button>`
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
    if (generalWorld) {
      const details = [
        payload?.action ? `<p><b>Attempt:</b> ${escapeHtml(payload.action)}</p>` : `<p>${escapeHtml(step.orientation || 'No public action retained.')}</p>`,
        payload?.purpose ? `<p><b>Purpose:</b> ${escapeHtml(payload.purpose)}</p>` : '',
        payload?.stated_rationale ? `<p><b>Rationale:</b> ${escapeHtml(payload.stated_rationale)}</p>` : '',
      ].join('')
      return `<article><header><strong>${escapeHtml(step.person_label)}</strong><span class="decision-pill">action</span></header>${details}</article>`
    }
    const stance = payload?.stance || 'defer'
    const details = [
      payload?.source_assessment ? `<p><b>Source judgment:</b> ${escapeHtml(payload.source_assessment)}</p>` : '',
      payload?.primary_risk ? `<p><b>Main risk:</b> ${escapeHtml(payload.primary_risk)}</p>` : '',
      payload?.blocking_dependency ? `<p><b>Still needed:</b> ${escapeHtml(payload.blocking_dependency)}</p>` : '',
      payload?.reason ? `<p><b>Decision:</b> ${escapeHtml(payload.reason)}</p>` : '',
    ].join('')
    return `<article><header><strong>${escapeHtml(step.person_label)}</strong>${decisionPill(stance)}</header>${details || `<p>${escapeHtml(step.orientation || 'No public rationale retained.')}</p>`}</article>`
  }).join('')
  $('#create-result-round').innerHTML = `<div class="create-result-round-intro"><span>${generalWorld ? 'Moment' : 'Round'} ${escapeHtml(round.round_index)}</span><strong>${messages.size ? `${messages.size} new message${messages.size === 1 ? '' : 's'} entered before this ${generalWorld ? 'action' : 'decision'}` : 'The same information environment continued'}</strong></div><div class="create-result-round-columns"><section><h5>What entered the network</h5>${informationHtml}</section><section><h5>How each person responded</h5>${decisionsHtml}</section></div>`
  all('[data-authored-round]').forEach((button) => {
    button.onclick = () => {
      authoredResultRoundIndex = Number(button.dataset.authoredRound)
      renderAuthoredResultRound()
    }
  })
}

function renderAuthoredResultNetwork(result, scene = null) {
  const projection = result.influence_network || {nodes:[], edges:[]}
  const nodeOverrides = new Map((scene?.node_overrides || []).map((item) => [item.node_id, item]))
  const visibleNodeIds = scene ? new Set(scene.visible_node_ids || []) : null
  const visibleEdgeIds = scene ? new Set(scene.visible_edge_ids || []) : null
  const visibleNodes = visibleNodeIds
    ? projection.nodes.filter((item) => visibleNodeIds.has(item.id)).map((item) => ({...item, ...(nodeOverrides.get(item.id) || {})}))
    : projection.nodes.map((item) => ({...item, ...(nodeOverrides.get(item.id) || {})}))
  const visibleNodeSet = new Set(visibleNodes.map((item) => item.id))
  const visibleEdges = (visibleEdgeIds
    ? projection.edges.filter((item) => visibleEdgeIds.has(item.id))
    : projection.edges
  ).filter((item) => visibleNodeSet.has(item.source) && visibleNodeSet.has(item.target))
  const graph = $('#create-result-network-graph')
  if (!visibleNodes.length || !window.CyberneticGraph) {
    window.CyberneticGraph?.clear?.(graph)
    graph.classList.remove('react-canvas-host')
    graph.innerHTML = '<p class="create-result-no-graph">This step is retained as text; it has no graph items to display.</p>'
    return
  }
  graph.classList.add('react-canvas-host')
  window.CyberneticGraph.render(graph, {
    nodes:visibleNodes,
    edges:visibleEdges,
    legendNodes:projection.nodes,
    legendEdges:projection.edges,
    boundaries:[], world:null, trajectory:{nodes:[], edges:[]},
    graphDiagnostics:{nodeClassification:{}, edgeClassification:{}, warnings:[]},
    viewMode:'causal',
    event:scene ? {
      event_id:scene.scene_id,
      state_revision:scene.sequence,
      focus_ids:scene.focus_node_ids || [],
      focus_edges:scene.focus_edge_ids || [],
    } : null,
    initialRevision:0,
    title:scene?.title || 'Complete retained network',
    subtitle:scene ? `step ${scene.sequence}` : 'all retained evidence',
    showLegend:true,
    selectedNodeId:null, selectedEdgeId:null, boundary:null, collapsedBoundaryId:null,
    onSelectNode:(nodeId) => {
      const item = visibleNodes.find((candidate) => candidate.id === nodeId)
      if (item) $('#create-result-network-inspector').innerHTML = `<strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span>`
    },
    onSelectEdge:(item) => {
      $('#create-result-network-inspector').innerHTML = `<strong>${escapeHtml(sentence(item.kind))}</strong><span>${escapeHtml(item.description)}</span>`
    },
  })
  $('#create-result-network-status').textContent = scene
    ? `${visibleNodes.length} visible items · ${visibleEdges.length} visible arrows · ${(scene.focus_node_ids || []).length + (scene.focus_edge_ids || []).length} changed items highlighted · future evidence remains hidden`
    : `${projection.nodes.length} visible items · ${projection.edges.length} retained arrows`
}

function renderAuthoredReplay() {
  const replay = authoredResult?.simulation_replay
  const scenes = replay?.scenes || []
  if (!scenes.length) {
    $('#create-replay-title').textContent = 'No guided replay is available'
    $('#create-replay-summary').textContent = 'Open the complete retained evidence below.'
    $('#create-replay-facts').innerHTML = ''
    $('#create-replay-previous').disabled = true
    $('#create-replay-next').disabled = true
    renderAuthoredResultNetwork(authoredResult)
    return
  }
  authoredReplaySceneIndex = Math.max(0, Math.min(authoredReplaySceneIndex, scenes.length - 1))
  const scene = scenes[authoredReplaySceneIndex]
  $('#create-replay-progress').textContent = `Step ${scene.sequence} of ${scenes.length}`
  $('#create-replay-kind').textContent = sentence(scene.kind)
  $('#create-replay-title').textContent = scene.title
  $('#create-replay-summary').textContent = scene.summary
  $('#create-replay-facts').innerHTML = (scene.facts || []).map((fact) => `<div><dt>${escapeHtml(fact.label)}</dt><dd>${escapeHtml(fact.value)}</dd></div>`).join('')
  const previous = $('#create-replay-previous')
  const next = $('#create-replay-next')
  previous.disabled = authoredReplaySceneIndex === 0
  next.disabled = authoredReplaySceneIndex === scenes.length - 1
  next.textContent = authoredReplaySceneIndex === scenes.length - 1
    ? 'Replay complete'
    : `Next: ${scenes[authoredReplaySceneIndex + 1].title} →`
  previous.onclick = () => {
    authoredReplaySceneIndex -= 1
    renderAuthoredReplay()
  }
  next.onclick = () => {
    authoredReplaySceneIndex += 1
    renderAuthoredReplay()
  }
  $('#create-replay-whole').onclick = () => {
    authoredReplaySceneIndex = scenes.length - 1
    renderAuthoredReplay()
  }
  renderAuthoredResultNetwork(authoredResult, scene)
}

function completedSimulationHistory() {
  const localIds = localSimulationIds()
  return retainedRunHistory.filter((run) => run.status === 'completed' && localIds.has(run.run_id))
}

function localSimulationIds() {
  try {
    const retained = JSON.parse(window.localStorage.getItem(LOCAL_SIMULATION_IDS_KEY) || '[]')
    return new Set(Array.isArray(retained) ? retained.filter((item) => typeof item === 'string') : [])
  } catch (_error) {
    return new Set()
  }
}

function rememberLocalSimulationId(runId) {
  try {
    const retained = localSimulationIds()
    retained.add(runId)
    window.localStorage.setItem(LOCAL_SIMULATION_IDS_KEY, JSON.stringify([...retained]))
  } catch (error) {
    console.warn(`browser simulation index unavailable: ${error.message}`)
  }
}

function simulationHistoryTitle(run) {
  return run.headline || sentence(run.scenario || 'Retained simulation')
}

function rememberCompletedSimulation(result) {
  if (!result?.run_id || result.status !== 'completed') return
  const retained = {
    run_id:result.run_id,
    created_at:result.created_at,
    status:result.status,
    scenario:result.scenario,
    arm:result.arm,
    execution:result.execution,
    headline:result.headline,
  }
  const existingIndex = retainedRunHistory.findIndex((run) => run.run_id === result.run_id)
  if (existingIndex === -1) retainedRunHistory.unshift(retained)
  else retainedRunHistory[existingIndex] = {...retainedRunHistory[existingIndex], ...retained}
}

function renderSimulationList() {
  const list = $('#simulation-list')
  const completed = completedSimulationHistory()
  if (!retainedRunHistory.length) {
    list.innerHTML = '<p>Loading completed simulations…</p>'
    return
  }
  if (!completed.length) {
    list.innerHTML = '<p>No simulations have been completed in this browser yet. Create one here, or open the curated case study.</p>'
    return
  }
  list.innerHTML = completed.map((run) => {
    const created = run.created_at ? new Date(run.created_at).toLocaleString([], {dateStyle:'medium', timeStyle:'short'}) : 'Retained run'
    const context = [sentence(run.scenario), sentence(run.arm)].filter(Boolean).join(' · ')
    return `<button type="button" data-simulation-run="${escapeHtml(run.run_id)}" class="${run.run_id === authoredRunId ? 'active' : ''}" aria-pressed="${run.run_id === authoredRunId}"><span><b>Created in this browser</b> · ${escapeHtml(context || 'Completed simulation')}</span><strong>${escapeHtml(simulationHistoryTitle(run))}</strong><small>${escapeHtml(created)}</small></button>`
  }).join('')
  all('[data-simulation-run]').forEach((button) => {
    button.onclick = () => { void openSimulationReplay(button.dataset.simulationRun) }
  })
}

function renderSimulationLibrary() {
  renderSimulationList()
  const host = $('#simulation-replay-host')
  const empty = $('#simulation-library-empty')
  if (authoredRunId && authoredResult?.run_id === authoredRunId) {
    host.appendChild($('#create-run-status'))
    $('#create-run-status').hidden = false
    empty.hidden = true
    return
  }
  empty.hidden = false
  const first = completedSimulationHistory()[0]
  if (!authoredRunId && first) void openSimulationReplay(first.run_id)
}

async function openSimulationReplay(runId) {
  if (!runId || simulationLoadingRunId === runId) return
  simulationLoadingRunId = runId
  window.CyberneticGraph?.clear?.($('#create-result-network-graph'))
  authoredRunId = runId
  authoredResult = null
  authoredReplaySceneIndex = 0
  const host = $('#simulation-replay-host')
  const runStatus = $('#create-run-status')
  host.appendChild(runStatus)
  $('#simulation-library-empty').hidden = true
  runStatus.hidden = false
  $('#create-result').hidden = true
  $('#create-run-heading').textContent = 'Opening retained simulation…'
  $('#create-run-detail').textContent = 'Building its walkthrough from retained world and event evidence.'
  renderSimulationList()
  syncUrl()
  try {
    const result = await apiRequest(`api/runs/${encodeURIComponent(runId)}/summary`)
    renderAuthoredResult(result)
    $('#create-edit-configuration').hidden = true
    renderSimulationList()
  } catch (error) {
    $('#create-run-heading').textContent = 'Retained simulation unavailable'
    $('#create-run-detail').textContent = error.message
  } finally {
    simulationLoadingRunId = null
  }
}

function builtInAnalysisSpec(profile) {
  if (profile === 'waltzman_coordination_v1') return {
    analysis_spec_version:2,
    analysis_id:'waltzman_coordination_review',
    profile,
    purpose:'Inspect information topology, dependencies, perceived risk, and coordination readiness in retained evidence.',
    construct_definitions:['Waltzman-informed coordination constructs are derived from retained evidence after execution.'],
    required_evidence_kinds:['configuration', 'terminal_state', 'causal_event', 'information_lineage', 'participant_activation'],
    method_classes:['exact', 'calculated', 'llm_coded'],
    aggregation:'Preserve per-person and per-moment variation before synthesis.',
    uncertainty:'This interprets one synthetic AI-agent execution; it does not measure real institutions.',
    limitations:['One execution does not establish an invariant.', 'Model outputs are audit records, not independent observations.'],
    subject_refs:[],
  }
  return {
    analysis_spec_version:2,
    analysis_id:'exact_terminal_review',
    profile:'exact_outcome_v1',
    purpose:'Read the retained terminal outcome without changing the run.',
    construct_definitions:['Terminal state is read directly from retained evidence.'],
    required_evidence_kinds:['configuration', 'terminal_state'],
    method_classes:['exact'],
    aggregation:'Report the retained terminal evidence.',
    uncertainty:'No inference beyond retained state.',
    limitations:['This does not establish a counterfactual.'],
    subject_refs:[],
  }
}

function renderAnalysisValue(value) {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return `<dl class="analysis-finding-values">${Object.entries(value).map(([label, item]) => `<div><dt>${escapeHtml(sentence(label))}</dt><dd>${escapeHtml(Array.isArray(item) ? item.join(' · ') : String(item))}</dd></div>`).join('')}</dl>`
  }
  return `<span>${escapeHtml(Array.isArray(value) ? value.join(' · ') : String(value))}</span>`
}

function renderResultAnalysisLenses(result) {
  const section = $('#create-result-lenses')
  const supported = result.execution_contract === 'general_world_v2' && result.status === 'completed'
  section.hidden = !supported
  if (!supported) return
  const specs = result.analysis_specs || []
  const resultsByDigest = new Map((result.analysis_results || []).map((item) => [item.analysis_spec_digest, item]))
  $('#create-result-lens-list').innerHTML = specs.length
    ? specs.map((spec) => {
      const analysis = [...resultsByDigest.values()].find((item) => item.result_id?.includes(spec.analysis_id))
      const findings = analysis?.findings || []
      return `<article><div><strong>${escapeHtml(sentence(spec.profile))}</strong><span>${escapeHtml(sentence(analysis?.coverage_status || 'attached'))}</span></div><p>${escapeHtml(spec.purpose)}</p>${findings.length ? `<ul>${findings.map((finding) => `<li><strong>${escapeHtml(sentence(finding.construct_id))}</strong>${renderAnalysisValue(finding.value)}</li>`).join('')}</ul>` : ''}<button class="quiet-button" type="button" data-remove-analysis="${escapeHtml(spec.analysis_id)}">Remove lens</button></article>`
    }).join('')
    : '<p><strong>No analysis attached.</strong> The retained execution is still available on its own.</p>'
  const profiles = new Set(specs.map((item) => item.profile))
  $('#create-add-waltzman-analysis').hidden = profiles.has('waltzman_coordination_v1')
  $('#create-add-outcome-analysis').hidden = profiles.has('exact_outcome_v1')
  $('#create-add-waltzman-analysis').onclick = () => attachResultAnalysis('waltzman_coordination_v1')
  $('#create-add-outcome-analysis').onclick = () => attachResultAnalysis('exact_outcome_v1')
  all('[data-remove-analysis]').forEach((button) => {
    button.onclick = () => removeResultAnalysis(button.dataset.removeAnalysis)
  })
}

async function attachResultAnalysis(profile) {
  if (!authoredResult?.run_id) return
  $('#create-result-lens-status').textContent = 'Analyzing retained evidence…'
  try {
    await apiRequest(`api/runs/${encodeURIComponent(authoredResult.run_id)}/analyses`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({analysis_spec:builtInAnalysisSpec(profile)}),
    })
    renderAuthoredResult(await apiRequest(`api/runs/${encodeURIComponent(authoredResult.run_id)}/summary`))
    $('#create-result-lens-status').textContent = 'Analysis attached. No simulated person was called and the world revision is unchanged.'
  } catch (error) {
    $('#create-result-lens-status').textContent = error.message
  }
}

async function removeResultAnalysis(analysisId) {
  if (!authoredResult?.run_id) return
  $('#create-result-lens-status').textContent = 'Removing the interpretation…'
  try {
    await apiRequest(`api/runs/${encodeURIComponent(authoredResult.run_id)}/analyses/${encodeURIComponent(analysisId)}`, {method:'DELETE'})
    renderAuthoredResult(await apiRequest(`api/runs/${encodeURIComponent(authoredResult.run_id)}/summary`))
    $('#create-result-lens-status').textContent = 'Analysis removed. The retained simulation is unchanged.'
  } catch (error) {
    $('#create-result-lens-status').textContent = error.message
  }
}

function renderAuthoredResult(result) {
  authoredResult = result
  rememberCompletedSimulation(result)
  authoredResultRoundIndex = 0
  authoredReplaySceneIndex = 0
  document.body.classList.add('authored-result')
  setCreateFlow('replay')
  const review = $('#create-review')
  const runStatus = $('#create-run-status')
  review.hidden = false
  review.classList.add('result-mode')
  if (state.view === 'simulations') {
    $('#simulation-replay-host').appendChild(runStatus)
    $('#simulation-library-empty').hidden = true
  } else {
    review.insertBefore(runStatus, review.firstElementChild)
  }
  $('.create-composer').hidden = true
  $('.create-hero .case-label').textContent = 'Completed simulation'
  $('#create-title').textContent = result.title || 'Simulation result'
  const replayQuestion = result.simulation_replay?.question
  const analystQuestion = result.authoring?.question
  const questionLabel = result.execution_contract === 'general_world_v2'
    ? analystQuestion ? 'Your analysis question' : 'Simulation brief'
    : 'Collective question'
  $('.create-hero > p').textContent = replayQuestion
    ? `${questionLabel}: ${replayQuestion} Advance through the retained run one step at a time.`
    : 'Advance through this retained simulation one step at a time.'
  $('#create-run-heading').textContent = 'Simulation complete'
  $('#create-run-detail').textContent = 'Replay retained information, decisions, actions, and world changes below.'
  $('#create-result-title').textContent = 'Follow what entered the simulation, what actors attempted, and what the world accepted.'
  $('#create-result-summary').textContent = replayQuestion
    ? `${questionLabel}: ${replayQuestion}`
    : 'Advance one retained step at a time.'
  const gateChecks = result.outcome?.gate_checks
  const generalWorldResult = ['general_world_v1', 'general_world_v2'].includes(result.profile)
  const resultFacts = [
    [String((result.participants || []).length), 'Simulated people'],
    generalWorldResult
      ? [String(Number(result.causal_moments || 0)), 'Causal moments']
      : [String((result.rounds || []).length || (result.simulation_replay?.scenes || []).filter((scene) => scene.kind === 'event').length), (result.rounds || []).length ? 'Decision rounds' : 'Retained events'],
    [String(Number(result.participant_model_calls || 0)), generalWorldResult ? 'Retained model decisions' : result.execution === 'live' ? 'Retained model decisions' : 'Retained reference decisions'],
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
  renderResultAnalysisLenses(result)
  renderAuthoredResultRound()
  renderAuthoredReplay()
  const readout = result.coordination_measurement_readout
  const theory = result.theory_analysis
  const gateRows = gateChecks ? Object.entries(gateChecks).map(([name, check]) => `<li><strong>${escapeHtml(sentence(name))}</strong> ${check.passed ? 'passed' : 'failed'} (${escapeHtml(check.actual)} ${name === 'opposition' ? `of maximum ${check.maximum}` : `of ${check.required} required`})</li>`).join('') : ''
  const limitations = readout?.limitations || ['This is a synthetic model run and does not predict real people or institutions.']
  const theoryFindings = theory?.findings?.map((finding) => `<li><strong>${escapeHtml(finding.label)}</strong><span>${escapeHtml(finding.value)}</span><details><summary>Method and limits</summary><p>${escapeHtml(finding.method)}</p><p><strong>Uncertainty:</strong> ${escapeHtml(finding.uncertainty)}</p><p><strong>Limitation:</strong> ${escapeHtml(finding.limitation)}</p><p><strong>Evidence:</strong> ${escapeHtml((finding.evidence_refs || []).join(' · '))}</p></details></li>`).join('') || ''
  $('#create-result-analysis').innerHTML = theory
    ? `<p><strong>${escapeHtml(theory.framework)}</strong> ${escapeHtml(theory.method)}</p><ul>${theoryFindings}</ul><h5>Interpretation boundary</h5><p>${escapeHtml(theory.interpretation_boundary)}</p>`
    : `<p><strong>${escapeHtml(readout?.headline || 'Retained simulation evidence')}</strong> ${escapeHtml(readout?.explanation || 'The run retains delivered information, decisions, and the exact collective gate.')}</p>${gateRows ? `<h5>Exact decision rule</h5><ul>${gateRows}</ul>` : ''}<h5>Interpret carefully</h5><ul>${limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
  $('#create-run-evidence').href = `api/runs/${encodeURIComponent(result.run_id)}`
  $('#create-run-evidence').textContent = 'Open raw retained run'
  $('#create-run-evidence').hidden = false
  $('#create-edit-configuration').hidden = state.view === 'simulations'
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
    $('#create-run-detail').textContent = `${Number(run.model_calls || 0)} model decisions retained. The world is still advancing.`
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
  $('#create-run-detail').textContent = 'Validating the approved configuration and selected model route.'
  $('#create-result').hidden = true
  authoredResult = null
  document.body.classList.remove('authored-result')
  $('#create-run-evidence').hidden = true
  $('#create-stop').hidden = true
  try {
    const run = await apiRequest(`api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/runs`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({execution:'live', narration:'deterministic', llm_options:{model:generalRunModel(), agent_reasoning_effort:'medium', max_total_cost:0.74}}),
    })
    authoredRunId = run.run_id
    rememberLocalSimulationId(run.run_id)
    authoredRunProgressSequence = 0
    authoredRunPollFailures = 0
    $('#create-run-heading').textContent = 'Simulation running'
    $('#create-run-detail').textContent = `Retained run ${run.run_id} has started.`
    $('#create-stop').disabled = false
    $('#create-stop').hidden = isGeneralProposal(authoringDraft.proposal)
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
  const params = new URLSearchParams(window.location.search)
  const runId = state.view === 'simulations'
    ? params.get('simulation')
    : params.get('authored_run')
  if (!runId || !['create', 'simulations'].includes(state.view)) return
  if (state.view === 'simulations') {
    await openSimulationReplay(runId)
    return
  }
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
    $('#create-run-detail').textContent = `${Number(progress.model_calls || 0)} model decisions retained. The simulation is ${sentence(progress.status)}.`
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
  $('.create-composer').hidden = true
  $('.create-hero .case-label').textContent = 'Create a simulation'
  $('#create-title').textContent = 'Describe the coordination problem you want to explore.'
  $('.create-hero > p').textContent = 'Describe the people, information sources, who receives which messages, and the collective decision. The authoring model turns that description into an editable influence network; the selected model then drives each person independently from their own character, memory, and received information.'
  $('#create-edit-configuration').hidden = true
  setCreateFlow(authoringDraft?.status === 'approved' ? 'run' : 'review')
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

async function loadRetainedRunHistory() {
  if (retainedRunHistoryLoad) return retainedRunHistoryLoad
  retainedRunHistoryLoad = apiRequest('api/runs').then((history) => {
    retainedRunHistory = history.runs || []
    if (state.view === 'simulations') renderSimulationLibrary()
    return retainedRunHistory
  }).catch((error) => {
    retainedRunHistoryLoad = null
    console.warn(`retained live runs unavailable: ${error.message}`)
    return retainedRunHistory
  })
  return retainedRunHistoryLoad
}

async function ensureRetainedLiveRuns() {
  if (retainedLiveRunsLoaded) return
  if (retainedLiveRunsLoad) return retainedLiveRunsLoad
  retainedLiveRunsLoad = (async () => {
    const history = await loadRetainedRunHistory()
    const summaries = history.filter((run) =>
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
    retainedLiveRunsLoaded = true
    applyRunScopeFromUrl()
    renderRail()
    configureControls()
    renderView()
  })().catch((error) => {
    retainedLiveRunsLoad = null
    console.warn(`regional evidence unavailable: ${error.message}`)
  })
  return retainedLiveRunsLoad
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
    readStateFromUrl()
    const requestedScope = new URLSearchParams(window.location.search).get('runs')
    const needsRetainedRegionalEvidence = state.view === 'compare' ||
      (['compare', 'inspect'].includes(state.view) && Boolean(requestedScope)) ||
      (state.view === 'inspect' && !dataset.runs.some((run) => run.run_id === state.runId))
    if (needsRetainedRegionalEvidence) await ensureRetainedLiveRuns()
    applyRunScopeFromUrl()
    await loadAuthoringDraftFromUrl()
    renderRail()
    configureControls()
    renderView()
    await loadAuthoredRunFromUrl()
    $('#loading').hidden = true
    $('#workbench').hidden = false
    void loadRetainedRunHistory()
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
