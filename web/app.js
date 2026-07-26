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
let previewRequestSerial = 0
let authoringDraft = null
let authoringPreview = null
let selectedAuthoringGraphView = 'causal'

const buttonTooltips = {
  'simulation-tab': 'Choose and run a configured simulation.',
  'authoring-tab': 'Describe a situation and review a typed scenario draft.',
  'history-tab': 'Open or remove previously retained simulation runs.',
  'readme-tab': 'Read how the simulator, maps, and evidence should be interpreted.',
  'authoring-draft': 'Send this message with the selected model and thinking level to generate the next saved draft revision.',
  'authoring-copy-link': 'Copy a link that reopens this automatically saved draft.',
  'authoring-approve': 'Freeze this exact reviewed draft so it can be run.',
  'authoring-run': 'Run the approved draft with fixed zero-cost reference actions. This checks the compiled routes and exact mechanisms, not the reviewed personalities.',
  'authoring-live-run': 'Run the approved draft with each concrete person driven by an LLM from their reviewed profile, private memory, delivered observations, and exposed interfaces.',
  'authoring-spatial-layout': 'Show the proposed places, occupants, and physical links. This does not grant access or permission.',
  'authoring-causal-layout': 'Show the proposed configured interaction pathways. A pathway does not itself grant authority.',
  'authoring-trajectory-layout': 'A realized causal graph becomes available only after the approved scenario runs.',
  'run': 'Run the selected scenario and condition.',
  'pause': 'Request a pause after the current causal step is safely retained.',
  'resume': 'Continue a paused run from its retained causal checkpoint.',
  'spatial-layout': 'Show authored places, occupants, and physical links. This does not grant access or permission.',
  'causal-layout': 'Show configured interaction pathways. A pathway does not itself grant authority.',
  'trajectory-layout': 'Show only the causal events that occurred in the selected run.',
  'previous-event': 'Select the previous causal step.',
  'next-event': 'Select the next causal step.',
}

function explainButton(button) {
  if (button.title) return
  let explanation = buttonTooltips[button.id]
  if (!explanation && button.classList.contains('help-button')) {
    explanation = `Show or hide help for ${button.getAttribute('aria-controls')?.replaceAll('-', ' ') || 'this control'}.`
  }
  if (!explanation && button.classList.contains('open-run')) explanation = 'Open this retained run for inspection.'
  if (!explanation && button.classList.contains('trash-run')) explanation = 'Move this retained run to recoverable server trash.'
  if (!explanation && button.classList.contains('turn-narrative')) explanation = 'Select this causal step and inspect its grounded evidence.'
  if (!explanation && button.classList.contains('timeline-marker')) explanation = 'Select this causal step.'
  if (!explanation && button.classList.contains('story-event')) explanation = 'Inspect the exact event behind this outcome step.'
  if (!explanation && button.classList.contains('save-person')) explanation = 'Validate and save these person assumptions as a new draft revision without calling an LLM.'
  if (!explanation && button.dataset.eventId) explanation = 'Inspect this exact event in the selected causal step.'
  if (!explanation && button.dataset.person) explanation = 'Show this participant or analytical composite account.'
  if (!explanation && button.dataset.nodeId) explanation = 'Inspect this retained node on the map.'
  if (!explanation && button.id === 'expand-boundary') explanation = 'Return to the exact components inside this analytical composite.'
  if (!explanation && button.id === 'inspect-composite') explanation = 'Show this analytical composite on the configured interaction map.'
  if (!explanation) explanation = `Use ${button.textContent.trim() || 'this control'}.`
  button.title = explanation
  if (!button.getAttribute('aria-label')) button.setAttribute('aria-label', explanation)
}

function applyButtonTooltips(root = document) {
  root.querySelectorAll('button').forEach(explainButton)
}

function setWorkspaceView(view) {
  const simulation = view === 'simulation'
  const authoring = view === 'authoring'
  const history = view === 'history'
  const readme = view === 'readme'
  $('#simulation-view').hidden = !simulation
  $('#authoring-view').hidden = !authoring
  $('#history-view').hidden = !history
  $('#readme-view').hidden = !readme
  for (const [tab, active] of [
    ['#simulation-tab', simulation],
    ['#authoring-tab', authoring],
    ['#history-tab', history],
    ['#readme-tab', readme],
  ]) {
    $(tab).classList.toggle('active', active)
    $(tab).setAttribute('aria-pressed', String(active))
  }
}

function authoringSummary(proposal) {
  const people = (proposal.people || []).map((person) => person.label).join(', ')
  const places = (proposal.places || []).map((place) => place.label).join(', ')
  const informationCampaign = proposal.workflow?.template_id === 'information_campaign_v1'
  const workflow = informationCampaign
    ? 'a retained claim is published through a configured channel, delivered to a recipient, and exactly recorded when assessed. Persuasion, truth, virality, and geopolitical outcomes are not inferred.'
    : 'an authored request is delivered to a reviewer, checked against copied eligibility and resource availability, then delivered back to the requester.'
  return `<span class="eyebrow">Compiled typed proposal · ${html(proposal.workflow?.template_id || 'unknown template')}</span><h3>${html(proposal.title || 'Untitled draft')}</h3><p>${html(proposal.description || '')}</p><p><strong>People:</strong> ${html(people)}. <strong>Places:</strong> ${html(places)}.</p><p><strong>Exact workflow:</strong> ${html(workflow)} The analytical boundary remains a view, not an executor.</p>`
}

function authoringModelLabel(model) {
  const option = (runtimeConfig.authoring?.models || []).find((item) => item.model === model)
  return option?.label || model || 'earlier model'
}

const behavioralProfileFields = [
  ['values', 'values', 'Principles or outcomes this person regards as important.'],
  ['goals', 'goals', 'What this person currently wants to achieve.'],
  ['beliefs', 'beliefs', 'What this person presently takes to be true; these beliefs may be wrong.'],
  ['decision_tendencies', 'decision tendencies', 'Scenario-relevant habits, biases, or ways this person tends to decide.'],
  ['social_perceptions', 'perceived social conditions', 'What this person thinks others do, value, or expect—not proof of an external norm.'],
  ['current_state', 'current state', 'Current emotions, attention, confidence, fatigue, or intent relevant to this scenario.'],
  ['capabilities', 'described capabilities', 'Things this person is believed able to do; this does not grant an interface or permission.'],
  ['limitations', 'described limitations', 'Relevant skill, knowledge, physical, or practical limits.'],
]

function statementLines(values) {
  return Array.isArray(values) ? values.join('\n') : ''
}

function readStatementLines(value) {
  return String(value || '').split('\n').map((item) => item.trim()).filter(Boolean)
}

function personCard(person) {
  const profile = person.behavioral_profile || {}
  const highlights = [
    person.disposition,
    profile.goals?.[0],
    profile.beliefs?.[0],
  ].filter(Boolean)
  const fields = behavioralProfileFields.map(([key, label, help]) => `
    <label>${html(person.label)} ${html(label)}
      <textarea data-profile-field="${html(key)}" rows="3">${html(statementLines(profile[key]))}</textarea>
      <small>${html(help)} Put one direct statement on each line.</small>
    </label>`).join('')
  return `
    <article class="person-card" data-person-id="${html(person.entity_id)}">
      <header>
        <span class="eyebrow">Person · editable scenario assumptions</span>
        <h3>${html(person.label)}</h3>
        <p>${html(person.position)}</p>
      </header>
      <div class="person-card-summary">
        ${highlights.map((item) => `<p>${html(item)}</p>`).join('') || '<p class="muted">No behavioral assumptions have been described yet.</p>'}
      </div>
      <details>
        <summary>Review or edit ${html(person.label)}’s person model</summary>
        <div class="person-editor">
          <label>Person’s displayed name
            <input data-person-field="label" value="${html(person.label)}">
          </label>
          <label>${html(person.label)} is positioned as…
            <textarea data-person-field="position" rows="2">${html(person.position)}</textarea>
            <small>This is descriptive social context, not a command.</small>
          </label>
          <label>${html(person.label)} is…
            <textarea data-person-field="disposition" rows="2">${html(person.disposition)}</textarea>
            <small>A concise descriptive tendency, written as a statement about the person.</small>
          </label>
          <label>${html(person.label)} remembers…
            <textarea data-person-field="memories" rows="3">${html(statementLines(person.memories))}</textarea>
            <small>Initial retained experiences or information, one statement per line.</small>
          </label>
          ${fields}
          <div class="person-edit-actions">
            <button type="button" class="save-person">Save person revision</button>
            <span class="person-edit-status" aria-live="polite"></span>
          </div>
        </div>
      </details>
    </article>`
}

function personFromCard(card, original) {
  const behavioralProfile = {}
  behavioralProfileFields.forEach(([key]) => {
    behavioralProfile[key] = readStatementLines(card.querySelector(`[data-profile-field="${key}"]`).value)
  })
  return {
    entity_id:original.entity_id,
    label:card.querySelector('[data-person-field="label"]').value.trim(),
    position:card.querySelector('[data-person-field="position"]').value.trim(),
    disposition:card.querySelector('[data-person-field="disposition"]').value.trim(),
    memories:readStatementLines(card.querySelector('[data-person-field="memories"]').value),
    behavioral_profile:behavioralProfile,
  }
}

function renderAuthoringPeople(draft) {
  const people = draft?.proposal?.people || []
  $('#authoring-people-section').hidden = !people.length
  $('#authoring-people').innerHTML = people.map(personCard).join('')
  $('#authoring-people').querySelectorAll('.person-card').forEach((card) => {
    const original = people.find((person) => person.entity_id === card.dataset.personId)
    const button = card.querySelector('.save-person')
    const status = card.querySelector('.person-edit-status')
    button.onclick = async () => {
      const person = personFromCard(card, original)
      if (!person.label || !person.position || !person.disposition || !person.memories.length) {
        status.textContent = 'Name, position, “is” description, and at least one memory are required.'
        return
      }
      button.disabled = true
      status.textContent = 'Saving this typed revision…'
      try {
        authoringDraft = await request(
          `/api/authoring/drafts/${encodeURIComponent(draft.draft_id)}/people/${encodeURIComponent(person.entity_id)}`,
          {
            method:'PUT',
            headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
              expected_revision:draft.revision,
              edit_id:`person_edit_${crypto.randomUUID()}`,
              person,
            }),
          },
        )
        await loadAuthoringPreview()
        renderAuthoring()
        syncAuthoringUrl()
      } catch (error) {
        status.textContent = error.message
        button.disabled = false
      }
    }
  })
  applyButtonTooltips($('#authoring-people'))
}

function renderAuthoringChat(draft) {
  const messages = draft?.messages || []
  const welcome = `
    <article class="chat-message assistant">
      <span>Authoring assistant</span>
      <p>Describe the bounded situation you want to model. After I produce a draft, tell me what to change and I will generate the next saved revision.</p>
    </article>`
  const conversation = messages.map((message, index) => {
    const directEdit = message.source === 'direct_person_edit'
    const model = authoringModelLabel(message.model)
    const reasoning = message.reasoning_effort
      ? `${String(message.reasoning_effort).replaceAll('_', ' ')} thinking`
      : 'earlier thinking setting not retained'
    const fallbackReply = index === messages.length - 1 ? draft.authoring_summary : ''
    const reply = message.assistant_summary || fallbackReply
    return `
      <article class="chat-message user">
        <span>You · ${directEdit ? 'direct edit' : 'message'} ${index + 1}</span>
        <p>${html(message.content)}</p>
        <small>${directEdit ? 'Typed edit · no LLM call' : `${html(model)} · ${html(reasoning)}`}</small>
      </article>
      ${reply ? `<article class="chat-message assistant"><span>Authoring assistant</span><p>${html(reply)}</p></article>` : ''}`
  }).join('')
  $('#authoring-chat').innerHTML = welcome + conversation
  $('#authoring-chat').scrollTop = $('#authoring-chat').scrollHeight
}

function renderAuthoring() {
  const draft = authoringDraft
  renderAuthoringChat(draft)
  $('#authoring-review').hidden = !draft || (!draft.proposal && !(draft.diagnostics || []).length)
  $('#authoring-copy-link').hidden = !draft
  if (!draft) return
  const diagnostics = draft.diagnostics || []
  const needsInput = draft.status === 'needs_input'
  const question = diagnostics.find((item) => item.severity === 'question')?.message || ''
  $('#authoring-status').textContent = `Saved automatically · revision ${draft.revision}. ${draft.authoring_summary || `Draft status: ${draft.status}.`}`
  $('#authoring-message-label').firstChild.nodeValue = needsInput
    ? 'Reply to the authoring assistant:'
    : draft.messages?.length
      ? 'Tell the assistant what to change:'
      : 'Message the authoring assistant:'
  $('#authoring-message').placeholder = needsInput && question
    ? question
    : 'For example: A campaign operator publishes a false claim about a diplomatic position through a media channel. A public-diplomacy analyst in another location receives and assesses it; both organizations are analytical views, not actors.'
  $('#authoring-draft').textContent = needsInput
    ? 'Answer and generate next revision'
    : (draft.messages?.length ? 'Generate next draft revision' : 'Generate first draft')
  const visibleDiagnostics = diagnostics.filter((item) => !(needsInput && item.severity === 'question'))
  $('#authoring-diagnostics').innerHTML = visibleDiagnostics.length
    ? visibleDiagnostics.map((item) => `<p class="warning"><strong>${html(item.severity)}:</strong> ${html(item.message)}</p>`).join('')
    : needsInput
      ? '<p class="muted">The proposal is saved. Answer the question above to make it ready for approval.</p>'
      : '<p class="muted">No unresolved compiler questions. Review the map, then approve this exact proposal.</p>'
  const attempts = draft.attempts || []
  $('#authoring-attempt-details').hidden = !attempts.length
  $('#authoring-attempts').textContent = attempts.length
    ? `Attempts: ${attempts.map((attempt) => `${attempt.attempt} (${attempt.status})`).join(' · ')}. Each attempt is traceable; no hidden retry loop is running.`
    : ''
  $('#authoring-summary').innerHTML = draft.proposal
    ? authoringSummary(draft.proposal)
    : '<span class="eyebrow">Draft needs correction</span><h3>No executable proposal yet</h3><p>The provider response was retained only as a validation diagnostic. Send a follow-up after correcting the shown schema issue; the earlier draft remains intact.</p>'
  renderAuthoringPeople(draft)
  const approvable = !!draft.proposal && diagnostics.length === 0 && draft.status === 'ready_for_review'
  $('#authoring-approve').hidden = !approvable
  $('#authoring-run').hidden = draft.status !== 'approved'
  const authoredLiveAvailable = runtimeConfig.live_authorized &&
    ((runtimeConfig.live_options?.models || []).length > 0)
  $('#authoring-live-run').hidden = draft.status !== 'approved' || !authoredLiveAvailable
  $('#authoring-live-settings').hidden = draft.status !== 'approved' || !authoredLiveAvailable
  renderAuthoringProjectionControls()
  if (authoringPreview?.nodes && window.CyberneticGraph) {
    $('#authoring-graph').classList.add('react-canvas-host')
    const revision = authoringPreview.initial_revision ?? 0
    const world = projectWorld(authoringPreview.world, revision)
    window.CyberneticGraph.render($('#authoring-graph'), {
      nodes: authoringPreview.nodes,
      edges: (authoringPreview.edges || []).map((edge) => ({
        ...edge,
        kind:edge.kind || 'connection',
        routeIds:edge.exact_route_ids || [edge.id],
      })),
      boundaries: authoringPreview.boundaries || [], world,
      trajectory: authoringPreview.trajectory || {nodes: [], edges: []},
      viewMode: selectedAuthoringGraphView, event: null,
      initialRevision: authoringPreview.initial_revision, selectedNodeId: null, selectedEdgeId: null,
      boundary: null, collapsedBoundaryId: null,
      analyticalScaleHelp: 'The analytical boundary is a view, not an actor.',
      onToggleBoundary: () => {}, onSelectNode: () => {}, onSelectEdge: () => {},
    })
  } else {
    $('#authoring-graph').classList.remove('react-canvas-host')
  }
}

function renderAuthoringProjectionControls() {
  const hasPreview = Boolean(authoringPreview?.nodes)
  const hasWorld = Boolean(authoringPreview?.world)
  $('#authoring-spatial-layout').disabled = !hasWorld
  $('#authoring-causal-layout').disabled = !hasPreview
  $('#authoring-trajectory-layout').disabled = true
  $('#authoring-spatial-layout').classList.toggle('active', selectedAuthoringGraphView === 'world')
  $('#authoring-causal-layout').classList.toggle('active', selectedAuthoringGraphView === 'causal')
  $('#authoring-trajectory-layout').classList.remove('active')
  $('#authoring-spatial-layout').setAttribute('aria-pressed', String(selectedAuthoringGraphView === 'world'))
  $('#authoring-causal-layout').setAttribute('aria-pressed', String(selectedAuthoringGraphView === 'causal'))
  $('#authoring-trajectory-layout').setAttribute('aria-pressed', 'false')
  $('#authoring-projection-help').textContent = selectedAuthoringGraphView === 'world'
    ? 'Spatial topology shows proposed places, occupants, and physical links. Adjacency does not grant access, communication, or authority.'
    : 'Configured interaction pathways show how information or action may travel in the proposed scenario. The realized causal graph becomes available only after execution.'
}

function syncAuthoringUrl() {
  if (!authoringDraft?.draft_id) return
  const url = new URL(window.location)
  url.searchParams.set('draft', authoringDraft.draft_id)
  url.searchParams.delete('run')
  window.history.replaceState({}, '', url)
}

async function openAuthoringDraft(draftId) {
  authoringDraft = await request(`/api/authoring/drafts/${encodeURIComponent(draftId)}`)
  await loadAuthoringPreview()
  setWorkspaceView('authoring')
  renderAuthoring()
  syncAuthoringUrl()
}

async function loadAuthoringPreview() {
  if (!authoringDraft?.proposal) return
  authoringPreview = await request(`/api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/preview`)
  selectedAuthoringGraphView = 'causal'
}

function modeledElapsedTime(event) {
  if (!event?.timing) return 'modeled elapsed time omitted'
  const unit = String(current?.time_unit || 'step').replaceAll('_', ' ')
  const plural = Number(event.logical_time) === 1 ? unit : `${unit}s`
  return `modeled elapsed time T+${event.logical_time} ${plural} (${String(event.timing.source_kind || 'scenario assumption').replaceAll('_', ' ')})`
}

function causalTime(item, fallback = 1) {
  const activationMatch = String(item?.activation || '').match(/^activation_(\d+)$/)
  const derived = activationMatch ? Number(activationMatch[1]) + 1 : fallback
  const value = Number.isInteger(item?.causal_time) ? item.causal_time : derived
  return `causal order c${value}`
}

function renderLifecycleControls(run = current) {
  const status = run?.status || 'ready'
  const paused = status === 'paused'
  const pausing = status === 'pause_requested'
  $('#resume').hidden = !paused
  $('#resume').disabled = false
  $('#pause').hidden = true
  $('#pause').disabled = false
  if (paused) {
    $('#run-status').textContent = 'Paused'
    $('#lifecycle-help').textContent = run.pause_message || 'This run stopped at a validated causal boundary. Resume continues from the retained checkpoint.'
  } else if (pausing) {
    $('#run-status').textContent = 'Pause requested'
    $('#lifecycle-help').textContent = run.pause_message || 'The current causal step is finishing before the checkpoint is retained.'
  } else if (status === 'completed') {
    $('#run-status').textContent = 'Completed'
    $('#lifecycle-help').textContent = 'This run is complete. Choose another condition or open a saved run from Run history.'
  } else if (status === 'failed' || status === 'interrupted') {
    $('#run-status').textContent = status === 'failed' ? 'Failed' : 'Interrupted'
    $('#lifecycle-help').textContent = run.error || 'This run did not reach a resumable checkpoint.'
  } else if (!run) {
    $('#lifecycle-help').textContent = 'Choose a scenario and condition, then play it to inspect what changed and why.'
  }
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
  const authoring = config.authoring || {}
  const authoringModels = authoring.models || (
    authoring.model ? [{model:authoring.model, label:authoring.model, provider:'configured provider'}] : []
  )
  $('#authoring-model').innerHTML = authoringModels.map((choice) =>
    `<option value="${html(choice.model)}">${html(choice.label)} · ${html(choice.provider)}</option>`
  ).join('')
  $('#authoring-model').value = authoring.model || authoringModels[0]?.model || ''
  const authoringReasoning = authoring.reasoning_efforts || [authoring.reasoning_effort || 'medium']
  $('#authoring-reasoning').innerHTML = authoringReasoning.map((effort) => {
    const label = {none:'None', low:'Low', medium:'Medium', high:'High', xhigh:'Extra high', max:'Max'}[effort] || effort
    return `<option value="${html(effort)}">${html(label)}</option>`
  }).join('')
  $('#authoring-reasoning').value = authoring.reasoning_effort || authoringReasoning[0]
  $('#authoring-model').title = 'The model selected here will produce only the next saved draft revision.'
  $('#authoring-reasoning').title = 'The thinking level selected here will apply only to the next saved draft revision.'
  $('#authoring-runtime').textContent = authoringModels.length
    ? `Your selected model and thinking level apply only to the next message. One message may make up to ${authoring.maximum_attempts_per_message || 1} structured attempt(s), each capped at $${Number(authoring.maximum_cost_per_attempt || 0).toFixed(2)}. The saved conversation records the selection, trace, and observed cost for every revision.`
    : 'Structured authoring configuration is unavailable.'
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
  $('#authoring-live-model').innerHTML = choices.map((choice) =>
    `<option value="${html(choice.model)}">${html(choice.label)}</option>`
  ).join('')
  $('#authoring-live-model').value = liveOptions.defaults?.model || config.model
  configureAuthoringLiveReasoning(
    liveOptions.defaults?.agent_reasoning_effort || config.reasoning_effort
  )
  $('#authoring-live-cost').value = Number(
    liveOptions.defaults?.max_total_cost || config.maximum_live_cost
  ).toFixed(2)
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

async function loadScenarioPreview() {
  const scenario = $('#scenario').value
  const arm = $('#arm').value
  if (!scenario || !arm) return
  const requestSerial = ++previewRequestSerial
  let preview
  try {
    preview = await request(
      `/api/scenarios/${encodeURIComponent(scenario)}/preview?arm_id=${encodeURIComponent(arm)}&cognition_profile=position_context`,
    )
  } catch (error) {
    if (requestSerial !== previewRequestSerial) return false
    throw error
  }
  if (
    requestSerial !== previewRequestSerial
    || scenario !== $('#scenario').value
    || arm !== $('#arm').value
  ) return false
  current = {
    nodes: [], snapshots: {}, edges: [], boundaries: [], timeline: [], moments: [], traces: [],
    trajectory: {nodes: [], edges: []},
    ...preview,
  }
  selectedEventIndex = 0
  selectedMomentIndex = 0
  selectedScale = 'exact'
  selectedGraphView = current.world ? 'world' : 'causal'
  selectedNodeId = null
  selectedEdgeId = null
  $('#map-section').hidden = false
  renderProjectionControls()
  renderGraph()
  $('#inspector').innerHTML = `<span class="eyebrow">Configured starting state</span><h2>Ready to play</h2><p>Select a place, person, record, mechanism, or pathway to inspect the scenario as configured. The realized causal graph will appear after the simulation commits events.</p>`
  return true
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

function configureAuthoringLiveReasoning(preferred = null) {
  const choices = runtimeConfig.live_options?.models || []
  const choice = choices.find((item) => item.model === $('#authoring-live-model').value)
  const efforts = choice?.agent_reasoning_efforts || ['low', 'medium', 'high']
  const experimental = new Set(choice?.experimental_agent_reasoning_efforts || [])
  $('#authoring-live-reasoning').innerHTML = efforts.map((effort) =>
    `<option value="${html(effort)}">${html(formatReasoningEffort(effort))}${experimental.has(effort) ? ' (experimental)' : ''}</option>`
  ).join('')
  $('#authoring-live-reasoning').value = efforts.includes(preferred)
    ? preferred
    : choice?.default_agent_reasoning_effort || efforts[0]
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
    `${estimate} Hard authorization: $${authorized.toFixed(2)}; no hidden overage. Each participant call is capped at $${Number(limits.participant_per_call_ceiling || 0).toFixed(2)} and each narrator call at $${Number(limits.narrator_per_call_ceiling || 0).toFixed(2)} (up to ${Number(limits.maximum_narrator_calls || 0)} retained causal moments). Narration starts only when the remaining authorization can reserve every retained moment.`
}

function describeCondition() {
  const scenario = scenarioCatalog[$('#scenario').value]
  const arm = scenario?.arms.find((item) => item.id === $('#arm').value)
  const question = $('#scenario').value === 'service_desk'
    ? 'After Play, ask: how did this condition change the path to safe closure?'
    : 'After Play, ask: what changed, why, and which retained evidence supports it?'
  $('#arm-help').textContent = `${arm?.description || 'Choose the concrete condition you want the simulation to test.'} ${question}`
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
  const revision = event?.state_revision ?? current?.initial_revision
  return boundary?.snapshots?.[String(revision)] || null
}

function worldProjection() {
  const world = current?.world
  const event = current?.timeline?.[selectedEventIndex]
  const revision = event?.state_revision ?? current?.initial_revision
  return projectWorld(world, revision)
}

function projectWorld(world, revision) {
  if (!world || revision === undefined) return null
  const snapshot = world.snapshots?.[String(revision)]
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

function renderTrajectoryInspector(event) {
  const timing = event?.timing
  const queueDelay = Number(timing?.serialization_delay || 0)
  const timingDetails = timing
    ? `<dt>Elapsed duration</dt><dd>${html(timing.duration)} ${html(current.time_unit)} · ${html(timing.source_kind.replaceAll('_', ' '))}</dd>
       <dt>Minimum modeled duration</dt><dd>${html(timing.minimum_duration)} ${html(current.time_unit)} · ${html(timing.source_ref)}</dd>
       ${queueDelay > 0 ? `<dt>Runtime serialization delay</dt><dd>${html(queueDelay)} ${html(current.time_unit)}; retained separately from the scenario assumption.</dd>` : ''}`
    : ''
  $('#inspector').innerHTML = `<span class="eyebrow">Realized event</span><h2>${html(event.kind.replaceAll('_', ' '))}</h2><p>${html(event.summary)}</p><dl class="detail-list"><dt>Modeled elapsed time</dt><dd>${html(modeledElapsedTime(event))}</dd><dt>Causal parents</dt><dd>${html((event.causal_parent_event_ids || []).join(', ') || 'run root')}</dd>${timingDetails}</dl>`
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
  if (selectedGraphView === 'trajectory') {
    renderTrajectoryInspector(event)
    return
  }
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
        <strong>${html(entry.activation)} · ${html(causalTime(entry))} · ${html(entry.status)}</strong>
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
      initialRevision:current?.initial_revision ?? null,
      world:worldProjection(),
      trajectory:current?.trajectory || null,
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
      onSelectNode:(nodeId) => {
        if (selectedGraphView === 'trajectory') {
          const index = current.timeline.findIndex((event) => event.event_id === nodeId)
          if (index >= 0) {
            selectEvent(index)
            showNode(nodeId)
          }
          return
        }
        showNode(nodeId)
      },
      onSelectEdge:(edge) => showEdge(edge),
      onToggleBoundary:(boundaryId) => {
        selectedScale = selectedScale === 'exact' ? boundaryId : 'exact'
        selectedNodeId = null
        selectedEdgeId = null
        renderScaleControls()
        if (current?.timeline?.length) selectEvent(selectedEventIndex)
        else renderGraph()
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
  const hasTrajectory = Boolean(current?.timeline?.length)
  $('#spatial-layout').disabled = !hasWorld
  $('#causal-layout').disabled = !current
  $('#trajectory-layout').disabled = !hasTrajectory
  $('#spatial-layout').classList.toggle('active', selectedGraphView === 'world')
  $('#causal-layout').classList.toggle('active', selectedGraphView === 'causal')
  $('#trajectory-layout').classList.toggle('active', selectedGraphView === 'trajectory')
  $('#spatial-layout').setAttribute('aria-pressed', String(selectedGraphView === 'world'))
  $('#causal-layout').setAttribute('aria-pressed', String(selectedGraphView === 'causal'))
  $('#trajectory-layout').setAttribute('aria-pressed', String(selectedGraphView === 'trajectory'))
  $('#projection-help').textContent = current?.preview
    ? 'This is the configured starting state. Spatial topology and configured interaction pathways are available before Play; the realized causal graph appears only after events are committed.'
    : !hasWorld
    ? 'This scenario has no authored places or spatial topology yet, so only configured interaction pathways and the realized causal graph can be shown.'
    : selectedGraphView === 'world'
      ? 'Spatial topology shows authored places, occupants, and physical links. Adjacency does not itself grant permission or traversal.'
      : selectedGraphView === 'trajectory'
        ? 'The realized causal graph shows only retained events that occurred. Its arrows are explicit causal-parent links, not possible routes or physical adjacency.'
      : 'Configured interaction pathways show scenario-configured information routes, actions, records, and mechanisms. They do not imply physical proximity or authorization.'
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
      causal_time:traces[0]?.causal_time ?? index + 1,
      causal_timestamp:traces[0]?.causal_timestamp ?? `c${index + 1}`,
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
  const stepEvent = (moment.event_ids || [])
    .map((eventId) => current.timeline.find((item) => item.event_id === eventId))
    .find(Boolean)
  $('#event-count').textContent = `${selectedMomentIndex + 1} / ${moments.length} steps · ${causalTime(moment, selectedMomentIndex + 1)} · ${modeledElapsedTime(stepEvent)}`
  $('#previous-event').disabled = selectedMomentIndex === 0
  $('#next-event').disabled = selectedMomentIndex === moments.length - 1
  const exactBelongsToMoment = event.activation === activation
  $('#event-detail').innerHTML = exactBelongsToMoment ? `
    <div><span class="event-kind">${html(event.kind.replaceAll('_',' '))}</span><span>${html(event.causal_timestamp || causalTime(moment, selectedMomentIndex + 1))}</span><span>${html(modeledElapsedTime(event))}</span><span>revision ${html(event.state_revision)}</span>${event.activation ? `<span>${html(event.activation)}</span>` : ''}</div>
    <h3>${html(event.summary)}</h3>
    <small>${html(event.event_id)}</small>` : `
    <div><span class="event-kind">No committed event</span><span>${html(causalTime(moment, selectedMomentIndex + 1))}</span><span>${html(activation)}</span></div>
    <h3>Every participant remained silent in this causal step.</h3>
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
  if (selectedGraphView === 'trajectory') renderTrajectoryInspector(event)
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
    $('#step-account-title').textContent = `Causal step ${momentNumber} · ${causalTime(narration, momentNumber)} · ${participants.map((item) => String(item).replaceAll('_', ' ')).join(' + ')}`
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
        <span>Causal step ${html(momentNumber)} · ${html(causalTime(moment, momentNumber))} · ${html(participants.map((item) => String(item).replaceAll('_',' ')).join(' + '))}</span>
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
    marker.title = `Causal step ${index + 1}, ${causalTime(moment, index + 1)}: ${people}; ${causeSummary(causes)}${moment.silent ? ' (silent)' : ''}`
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
  renderLifecycleControls(current)
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
$('#simulation-tab').onclick = async () => {
  setWorkspaceView('simulation')
  if (current) return
  try {
    await loadScenarioPreview()
  } catch (error) {
    $('#run-status').textContent = error.message
  }
}
$('#authoring-tab').onclick = () => setWorkspaceView('authoring')
$('#history-tab').onclick = () => setWorkspaceView('history')
$('#readme-tab').onclick = () => setWorkspaceView('readme')
$('#authoring-spatial-layout').onclick = () => {
  if (!authoringPreview?.world) return
  selectedAuthoringGraphView = 'world'
  renderAuthoring()
}
$('#authoring-causal-layout').onclick = () => {
  if (!authoringPreview) return
  selectedAuthoringGraphView = 'causal'
  renderAuthoring()
}
$('#scenario').onchange = async (event) => {
  configureScenario(event.target.value)
  try {
    await loadScenarioPreview()
  } catch (error) {
    $('#run-status').textContent = error.message
  }
}
$('#arm').onchange = async () => {
  describeCondition()
  try {
    await loadScenarioPreview()
  } catch (error) {
    $('#run-status').textContent = error.message
  }
}
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

$('#trajectory-layout').onclick = () => {
  selectedGraphView = 'trajectory'
  selectedNodeId = current?.timeline?.[selectedEventIndex]?.event_id || null
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
$('#authoring-live-model').onchange = () => configureAuthoringLiveReasoning()
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
    renderLifecycleControls(body)
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
    $('#run-status').textContent = 'Pause requested; finishing this causal step…'
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

$('#authoring-draft').onclick = async () => {
  const message = $('#authoring-message').value.trim()
  if (!message) {
    $('#authoring-status').textContent = 'Describe the situation before drafting it.'
    return
  }
  $('#authoring-draft').disabled = true
  $('#authoring-status').textContent = 'Drafting a typed scenario…'
  try {
    if (!authoringDraft) authoringDraft = await request('/api/authoring/drafts', {method:'POST'})
    authoringDraft = await request(`/api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/messages`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        expected_revision:authoringDraft.revision,
        message_id:crypto.randomUUID(), message,
        model:$('#authoring-model').value,
        reasoning_effort:$('#authoring-reasoning').value,
      }),
    })
    await loadAuthoringPreview()
    syncAuthoringUrl()
    $('#authoring-message').value = ''
    renderAuthoring()
  } catch (error) {
    $('#authoring-status').textContent = error.message
  } finally {
    $('#authoring-draft').disabled = false
  }
}

$('#authoring-copy-link').onclick = async () => {
  if (!authoringDraft) return
  syncAuthoringUrl()
  const link = window.location.href
  try {
    await navigator.clipboard.writeText(link)
    $('#authoring-status').textContent = `Saved draft link copied · revision ${authoringDraft.revision}.`
  } catch (error) {
    $('#authoring-status').textContent = `Saved draft link: ${link}`
  }
}

$('#authoring-approve').onclick = async () => {
  if (!authoringDraft) return
  try {
    authoringDraft = await request(`/api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/approve`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({expected_revision:authoringDraft.revision}),
    })
    syncAuthoringUrl()
    renderAuthoring()
  } catch (error) {
    $('#authoring-status').textContent = error.message
  }
}

$('#authoring-run').onclick = async () => {
  if (!authoringDraft) return
  $('#authoring-run').disabled = true
  try {
    const run = await request(`/api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/runs`, {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({execution:'scripted'}),
    })
    setWorkspaceView('simulation')
    render(run)
    await loadHistory()
  } catch (error) {
    $('#authoring-status').textContent = error.message
  } finally {
    $('#authoring-run').disabled = false
  }
}

$('#authoring-live-run').onclick = async () => {
  if (!authoringDraft) return
  $('#authoring-live-run').disabled = true
  $('#authoring-run').disabled = true
  $('#authoring-status').textContent = 'Running the approved scenario with live people…'
  try {
    const run = await request(`/api/authoring/drafts/${encodeURIComponent(authoringDraft.draft_id)}/runs`, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        execution:'live',
        llm_options:{
          model:$('#authoring-live-model').value,
          agent_reasoning_effort:$('#authoring-live-reasoning').value,
          max_total_cost:Number($('#authoring-live-cost').value),
        },
      }),
    })
    setWorkspaceView('simulation')
    render(run)
    const url = new URL(window.location)
    url.searchParams.delete('draft')
    url.searchParams.set('run', run.run_id)
    window.history.replaceState({}, '', url)
    await loadHistory()
  } catch (error) {
    $('#authoring-status').textContent = error.message
  } finally {
    $('#authoring-live-run').disabled = false
    $('#authoring-run').disabled = false
  }
}

Promise.all([loadConfig(), loadHistory()])
  .then(async () => {
    renderLifecycleControls()
    const search = new URLSearchParams(window.location.search)
    const retainedId = search.get('run')
    const draftId = search.get('draft')
    if (retainedId) await openRetained(retainedId)
    else if (draftId) await openAuthoringDraft(draftId)
    else await loadScenarioPreview()
  })
  .catch((error) => { $('#run-status').textContent = error.message })

applyButtonTooltips()
new MutationObserver((records) => {
  records.forEach((record) => record.addedNodes.forEach((node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      if (node.matches?.('button')) explainButton(node)
      applyButtonTooltips(node)
    }
  }))
}).observe(document.body, {childList:true, subtree:true})

window.addEventListener('resize', () => {
  if (current) drawGraphLines(graphProjection().edges)
})
