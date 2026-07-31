const $ = (selector) => document.querySelector(selector)

function showTraceInPlace(person) {
  const trace = $('#trace')
  const retainedHeight = Math.ceil(trace.getBoundingClientRect().height)
  if (retainedHeight > 0) trace.style.minHeight = `${Math.min(retainedHeight, 520)}px`
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
let liveProgressSequence = 0
let liveProjection = null
let liveActivity = null
let livePolling = false
let previewRequestSerial = 0
let authoringDraft = null
let authoringPreview = null
let selectedAuthoringGraphView = 'causal'
let selectedNarrativeDetail = 'concise'
let selectedBoundaryActivities = null
let selectedBoundaryScope = 'full'
let boundaryActivityRequestSerial = 0
const compositeAssayCache = new Map()

const buttonTooltips = {
  'simulation-tab': 'Choose and run a configured simulation.',
  'authoring-tab': 'Describe a situation and review a typed scenario draft.',
  'history-tab': 'Open or remove previously retained simulation runs.',
  'readme-tab': 'Read how the simulator, maps, and evidence should be interpreted.',
  'authoring-draft': 'Send this message with the selected model and thinking level to generate the next saved draft revision.',
  'authoring-load-coordination': 'Create a saved, already typed coordination example without making a model call.',
  'authoring-copy-link': 'Copy a link that reopens this automatically saved draft.',
  'authoring-approve': 'Freeze this exact reviewed draft so it can be run.',
  'authoring-run': 'Run the approved draft with fixed zero-cost reference actions. This checks the compiled routes and exact mechanisms, not the reviewed personalities.',
  'authoring-live-run': 'Run the approved draft with each concrete person driven by an LLM from their reviewed profile, private memory, delivered observations, and exposed interfaces.',
  'authoring-save-configuration': 'Validate these semantic fields and save a new draft revision without calling an LLM. Compiler-owned routes, mechanisms, and IDs remain unchanged.',
  'authoring-spatial-layout': 'Show the proposed places, occupants, and physical links. This does not grant access or permission.',
  'authoring-causal-layout': 'Show the proposed configured interaction pathways. A pathway does not itself grant authority.',
  'authoring-trajectory-layout': 'A realized causal graph becomes available only after the approved scenario runs.',
  'run': 'Run the selected scenario and condition.',
  'pause': 'Request a pause after the current causal step is safely retained.',
  'stop': 'End this run after the current causal step. A stopped run cannot be resumed.',
  'resume': 'Continue a paused run from its retained causal checkpoint.',
  'spatial-layout': 'Show authored places, occupants, and physical links. This does not grant access or permission.',
  'causal-layout': 'Show configured interaction pathways. A pathway does not itself grant authority.',
  'trajectory-layout': 'Show only the causal events that occurred in the selected run.',
  'analytical-scale-toggle': 'Collapse the selected analytical composite into one node, or expand it back into its exact components.',
  'previous-event': 'Select the previous causal step.',
  'next-event': 'Select the next causal step.',
  'narrative-concise': 'Read the one-sentence account for each causal step.',
  'narrative-detailed': 'Read how each participant action changed the world, with exact evidence available on demand.',
  'run-composite-assay': 'Run the reviewed five-condition scripted comparison. It makes no model calls and retains five independently inspectable runs.',
}

function explainButton(button) {
  if (button.title) return
  let explanation = buttonTooltips[button.id]
  if (!explanation && button.classList.contains('help-button')) {
    explanation = `Show or hide help for ${button.getAttribute('aria-controls')?.replaceAll('-', ' ') || 'this control'}.`
  }
  if (!explanation && button.classList.contains('open-run')) explanation = 'Open this retained run for inspection.'
  if (!explanation && button.classList.contains('assay-row-select')) explanation = 'Compare this condition and show what crossed the group boundary.'
  if (!explanation && button.classList.contains('open-assay-group')) explanation = 'Open the retained run with the partnership group account selected.'
  if (!explanation && button.classList.contains('open-assay-run')) explanation = 'Open the full retained run, including its maps, story, people, measures, and exact evidence.'
  if (!explanation && button.classList.contains('trash-run')) explanation = 'Move this retained run to recoverable server trash.'
  if (!explanation && button.classList.contains('trash-assay')) explanation = 'Move all five retained rows in this comparison to recoverable server trash.'
  if (!explanation && button.classList.contains('measurement-evidence-button')) explanation = 'Select the cited exact event on the simulation map and in Advanced evidence.'
  if (!explanation && button.classList.contains('turn-narrative')) explanation = 'Select this causal step and inspect its grounded evidence.'
  if (!explanation && button.classList.contains('timeline-marker')) explanation = 'Select this causal step.'
  if (!explanation && button.classList.contains('story-event')) explanation = 'Inspect the exact event behind this outcome step.'
  if (!explanation && button.classList.contains('inspect-boundary-path')) explanation = 'Show the exact recorded events supporting this group response and select its first event.'
  if (!explanation && button.classList.contains('group-scope-button')) explanation = 'Choose whether this group account covers the completed run or only the selected causal moment.'
  if (!explanation && button.classList.contains('save-person')) explanation = 'Validate and save these person assumptions as a new draft revision without calling an LLM.'
  if (!explanation && button.dataset.eventId) explanation = 'Inspect this exact event in the selected causal step.'
  if (!explanation && button.dataset.person) explanation = 'Show what this participant did or what crossed this group.'
  if (!explanation && button.dataset.nodeId) explanation = 'Inspect this retained node on the map.'
  if (!explanation && button.id === 'expand-boundary') explanation = 'Return to the exact components inside this analytical composite.'
  if (!explanation && button.id === 'inspect-composite') explanation = 'Highlight the members of this group on the map.'
  if (!explanation) explanation = `Use ${button.textContent.trim() || 'this control'}.`
  button.title = explanation
  if (!button.getAttribute('aria-label')) button.setAttribute('aria-label', explanation)
}

function applyButtonTooltips(root = document) {
  root.querySelectorAll('button').forEach(explainButton)
}

function setWorkspaceView(view) {
  const priorView = [
    ['simulation', '#simulation-view'],
    ['authoring', '#authoring-view'],
    ['history', '#history-view'],
    ['readme', '#readme-view'],
  ].find(([, selector]) => !$(selector).hidden)?.[0]
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
  if (priorView && priorView !== view) window.scrollTo({top:0, left:0, behavior:'auto'})
}

function authoringSummary(proposal) {
  const people = (proposal.people || []).map((person) => person.label).join(', ')
  const places = (proposal.places || []).map((place) => place.label).join(', ')
  const coordination = proposal.workflow?.template_id === 'coordination_decision_v1'
  const informationCampaign = proposal.workflow?.template_id === 'information_campaign_v1'
  if (coordination) {
    const workflow = proposal.workflow
    const goal = workflow.collective_goal || {}
    const analyses = new Set(workflow.analysis?.analysis_ids || [])
    return `
      <span class="eyebrow">Compiled typed proposal · coordination decision</span>
      <h3>${html(proposal.title || 'Untitled coordination draft')}</h3>
      <p>${html(proposal.description || '')}</p>
      <div class="configuration-review">
        <section>
          <span class="eyebrow">Scenario inputs</span>
          <h4>Who and what is being modeled</h4>
          <p><strong>${html((proposal.people || []).length)} people</strong> review one shared decision while ${html((proposal.information || []).length)} concrete concerns arrive through configured routes.</p>
          <p><strong>Candidate goal:</strong> ${html(goal.description || goal.label || 'No goal supplied')}</p>
          <small>${html(people)} · ${html(workflow.condition?.replaceAll('_', ' '))} condition · meetings on days ${html((workflow.meeting_days || []).join(', '))}, with a day ${html(workflow.deadline_day)} deadline</small>
        </section>
        <section>
          <span class="eyebrow">Run controls</span>
          <h4>What changes only this execution</h4>
          <p>Choose a zero-cost reference run or, when authorized, live LLM-driven people. Model, thinking level, and spending limit belong to the run—not to the scenario.</p>
          <small>The scenario’s goal, people, concerns, routes, places, and decision deadline stay unchanged.</small>
        </section>
        <section>
          <span class="eyebrow">Selected per-run analyses</span>
          <h4>What will be calculated afterward</h4>
          <p>${analyses.has('waltzman_decision_environment_v1') ? '<strong>Decision environment</strong> examines information, risk, verification, commitments, and timing. ' : ''}${analyses.has('levin_collective_competence_v1') ? '<strong>Collective competence</strong> examines the configured boundary relative to its candidate goal.' : ''}</p>
          <small>These analyses read retained evidence, make zero additional model calls in this MVP, and cannot act in the simulation.</small>
        </section>
        <section>
          <span class="eyebrow">After this MVP</span>
          <h4>Questions one run cannot answer</h4>
          <p>Repeated comparisons, controlled perturbations, member replacement, recovery from shock, and claims about causal influence remain separate future experiments.</p>
          <small>This run reports only what occurred in its retained trajectory.</small>
        </section>
      </div>`
  }
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
const coordinationOutcomes = [
  ['deploy_on_time', 'Full deployment on time'],
  ['scope_reduced', 'Smaller deployment'],
  ['delayed', 'Delayed decision'],
  ['partner_disengaged', 'Partner disengages'],
  ['no_decision_by_horizon', 'No decision by deadline'],
]
const coordinationAnalyses = [
  ['waltzman_decision_environment_v1', 'Decision environment'],
  ['levin_collective_competence_v1', 'Collective competence'],
]

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

function coordinationEditor(configuration) {
  const concernCards = configuration.concerns.map((concern) => `
    <section class="coordination-editor-group coordination-concern" data-concern-kind="${html(concern.concern_kind)}">
      <h4>${html(concern.concern_kind[0].toUpperCase() + concern.concern_kind.slice(1))} concern</h4>
      <label>Source shown to the user
        <input data-concern-field="source_label" value="${html(concern.source_label)}">
      </label>
      <label>What that source is
        <textarea data-concern-field="source_description" rows="2">${html(concern.source_description)}</textarea>
      </label>
      <label>Concern topic
        <input data-concern-field="topic" value="${html(concern.topic)}">
      </label>
      <label>Information delivered
        <textarea data-concern-field="content" rows="3">${html(concern.content)}</textarea>
      </label>
      <label>Delivery delay in scenario minutes
        <input data-concern-field="delivery_minutes" type="number" min="1" step="1" value="${html(concern.delivery_minutes)}">
      </label>
    </section>`).join('')
  const checkedOutcomes = new Set(configuration.collective_goal.acceptable_outcomes)
  const selectedAnalyses = new Set(configuration.analysis_ids)
  return `
    <div class="coordination-editor">
      <div class="coordination-editor-grid">
        <section class="coordination-editor-group">
          <h3>Decision situation</h3>
          <label>Scenario title
            <input data-config-field="title" value="${html(configuration.title)}">
          </label>
          <label>What is happening
            <textarea data-config-field="description" rows="3">${html(configuration.description)}</textarea>
          </label>
          <label>Scenario condition
            <select data-config-field="condition">
              ${[
                ['baseline', 'Baseline — no new outside concerns'],
                ['heterogeneous_pressure', 'Heterogeneous pressure — concerns arrive without stabilizers'],
                ['stabilization', 'Stabilization — concerns arrive with verification and feedback'],
              ].map(([value, label]) => `<option value="${value}"${configuration.condition === value ? ' selected' : ''}>${html(label)}</option>`).join('')}
            </select>
          </label>
          <p class="coordination-fixed-cadence">This reviewed runtime currently uses meetings on days ${html(configuration.meeting_days.join(', '))} and a day ${html(configuration.deadline_day)} deadline. The cadence is visible but fixed by this bounded template.</p>
        </section>
        <section class="coordination-editor-group">
          <h3>Candidate collective goal</h3>
          <label>Goal name
            <input data-goal-field="label" value="${html(configuration.collective_goal.label)}">
          </label>
          <label>What success means
            <textarea data-goal-field="description" rows="3">${html(configuration.collective_goal.description)}</textarea>
          </label>
          <fieldset>
            <legend>Outcomes that count as acceptable</legend>
            <div class="coordination-checks">${coordinationOutcomes.map(([value, label]) => `<label><input type="checkbox" data-goal-outcome="${value}"${checkedOutcomes.has(value) ? ' checked' : ''}> ${html(label)}</label>`).join('')}</div>
          </fieldset>
          <label>Constraints, one per line
            <textarea data-goal-field="constraints" rows="4">${html(statementLines(configuration.collective_goal.constraints))}</textarea>
          </label>
        </section>
      </div>
      <div class="coordination-editor-grid">${concernCards}</div>
      <div class="coordination-editor-grid">
        <section class="coordination-editor-group">
          <h3>Spatial context</h3>
          <label>Partnership place name<input data-place-field="partnership_label" value="${html(configuration.places.partnership_label)}"></label>
          <label>Partnership place description<textarea data-place-field="partnership_description" rows="2">${html(configuration.places.partnership_description)}</textarea></label>
          <label>Concern-source place name<input data-place-field="source_site_label" value="${html(configuration.places.source_site_label)}"></label>
          <label>Concern-source place description<textarea data-place-field="source_site_description" rows="2">${html(configuration.places.source_site_description)}</textarea></label>
          <label>Decision-registry place name<input data-place-field="registry_label" value="${html(configuration.places.registry_label)}"></label>
          <label>Decision-registry place description<textarea data-place-field="registry_description" rows="2">${html(configuration.places.registry_description)}</textarea></label>
        </section>
        <section class="coordination-editor-group">
          <h3>Analytical group views</h3>
          <p class="muted">These views group lower-level activity for analysis. They do not add a mind or an actor.</p>
          <label>Partnership view name<input data-boundary-field="partnership_label" value="${html(configuration.analytical_boundaries.partnership_label)}"></label>
          <label>What the partnership view includes<textarea data-boundary-field="partnership_description" rows="2">${html(configuration.analytical_boundaries.partnership_description)}</textarea></label>
          <label>Source-group view name<input data-boundary-field="source_group_label" value="${html(configuration.analytical_boundaries.source_group_label)}"></label>
          <label>What the source-group view includes<textarea data-boundary-field="source_group_description" rows="2">${html(configuration.analytical_boundaries.source_group_description)}</textarea></label>
        </section>
      </div>
      <div class="coordination-editor-grid">
        <section class="coordination-editor-group">
          <h3>Post-run analyses</h3>
          <p class="muted">Select at least one. These inspect retained evidence after the simulation and cannot alter the run.</p>
          <div class="coordination-checks">${coordinationAnalyses.map(([value, label]) => `<label><input type="checkbox" data-analysis-id="${value}"${selectedAnalyses.has(value) ? ' checked' : ''}> ${html(label)}</label>`).join('')}</div>
        </section>
        <section class="coordination-editor-group">
          <h3>Fidelity review</h3>
          <label>Assumptions, one per line<textarea data-list-field="assumptions" rows="4">${html(statementLines(configuration.assumptions))}</textarea></label>
          <label>Known omissions, one per line<textarea data-list-field="known_omissions" rows="4">${html(statementLines(configuration.known_omissions))}</textarea></label>
          <label>Questions to check in the trace, one per line<textarea data-list-field="fidelity_questions" rows="4">${html(statementLines(configuration.fidelity_questions))}</textarea></label>
        </section>
      </div>
      <div class="coordination-edit-actions">
        <button id="authoring-save-configuration" type="button">Save configuration revision</button>
        <span class="coordination-edit-status" aria-live="polite"></span>
      </div>
    </div>`
}

function coordinationConfigurationFromEditor(editor, original) {
  const value = (selector) => editor.querySelector(selector).value.trim()
  const fieldMap = (attribute, keys) => Object.fromEntries(
    keys.map((key) => [key, value(`[${attribute}="${key}"]`)]),
  )
  const concerns = [...editor.querySelectorAll('.coordination-concern')].map((card) => ({
    concern_kind:card.dataset.concernKind,
    source_label:card.querySelector('[data-concern-field="source_label"]').value.trim(),
    source_description:card.querySelector('[data-concern-field="source_description"]').value.trim(),
    topic:card.querySelector('[data-concern-field="topic"]').value.trim(),
    content:card.querySelector('[data-concern-field="content"]').value.trim(),
    delivery_minutes:Number(card.querySelector('[data-concern-field="delivery_minutes"]').value),
  }))
  return {
    ...original,
    title:value('[data-config-field="title"]'),
    description:value('[data-config-field="description"]'),
    condition:value('[data-config-field="condition"]'),
    concerns,
    collective_goal:{
      label:value('[data-goal-field="label"]'),
      description:value('[data-goal-field="description"]'),
      acceptable_outcomes:[...editor.querySelectorAll('[data-goal-outcome]:checked')].map((input) => input.dataset.goalOutcome),
      constraints:readStatementLines(value('[data-goal-field="constraints"]')),
    },
    places:fieldMap('data-place-field', [
      'partnership_label', 'partnership_description', 'source_site_label',
      'source_site_description', 'registry_label', 'registry_description',
    ]),
    analytical_boundaries:fieldMap('data-boundary-field', [
      'partnership_label', 'partnership_description',
      'source_group_label', 'source_group_description',
    ]),
    analysis_ids:[...editor.querySelectorAll('[data-analysis-id]:checked')].map((input) => input.dataset.analysisId),
    assumptions:readStatementLines(value('[data-list-field="assumptions"]')),
    known_omissions:readStatementLines(value('[data-list-field="known_omissions"]')),
    fidelity_questions:readStatementLines(value('[data-list-field="fidelity_questions"]')),
  }
}

function renderAuthoringConfiguration(draft) {
  const section = $('#authoring-configuration-section')
  const coordination = draft?.proposal?.workflow?.template_id === 'coordination_decision_v1'
  section.hidden = !coordination
  if (!coordination) {
    $('#authoring-coordination-editor').innerHTML = ''
    return
  }
  const configuration = coordinationConfigurationFromProposal(draft.proposal)
  const editor = $('#authoring-coordination-editor')
  editor.innerHTML = coordinationEditor(configuration)
  const button = $('#authoring-save-configuration')
  const status = editor.querySelector('.coordination-edit-status')
  button.onclick = async () => {
    const edited = coordinationConfigurationFromEditor(editor, configuration)
    if (!edited.title || !edited.description || !edited.collective_goal.label ||
        !edited.collective_goal.description || !edited.collective_goal.constraints.length ||
        !edited.collective_goal.acceptable_outcomes.length || !edited.analysis_ids.length ||
        !edited.assumptions.length || !edited.known_omissions.length ||
        !edited.fidelity_questions.length ||
        edited.concerns.some((item) => !item.source_label || !item.source_description ||
          !item.topic || !item.content || !Number.isInteger(item.delivery_minutes) ||
          item.delivery_minutes < 1)) {
      status.textContent = 'Complete every field, select at least one acceptable outcome and analysis, and use positive whole-minute delivery delays.'
      return
    }
    button.disabled = true
    status.textContent = 'Saving this typed revision…'
    try {
      authoringDraft = await request(
        `/api/authoring/drafts/${encodeURIComponent(draft.draft_id)}/coordination-configuration`,
        {
          method:'PUT',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({
            expected_revision:draft.revision,
            edit_id:`coordination_edit_${crypto.randomUUID()}`,
            configuration:edited,
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
  applyButtonTooltips(section)
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
    const directEdit = ['direct_person_edit', 'direct_coordination_edit'].includes(message.source)
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
  renderAuthoringConfiguration(draft)
  renderAuthoringPeople(draft)
  const approvable = !!draft.proposal && diagnostics.length === 0 && draft.status === 'ready_for_review'
  $('#authoring-approve').hidden = !approvable
  $('#authoring-run').hidden = draft.status !== 'approved'
  const authoredLiveAvailable = runtimeConfig.live_authorized &&
    ((runtimeConfig.live_options?.models || []).length > 0) &&
    (
      draft.proposal?.workflow?.template_id !== 'coordination_decision_v1' ||
      (runtimeConfig.scenarios?.coordination_decision?.live_model_ids || []).length > 0
    )
  configureAuthoringLiveModels()
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
      graphDiagnostics:graphDiagnostics(authoringPreview.graph_diagnostics),
      viewMode: selectedAuthoringGraphView, event: null,
      initialRevision: authoringPreview.initial_revision, selectedNodeId: null, selectedEdgeId: null,
      boundary: null, collapsedBoundaryId: null,
      onSelectNode: () => {}, onSelectEdge: () => {},
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

function storyTime(item, fallback = 1) {
  const logicalTime = Number(item?.logical_time)
  if (!Number.isFinite(logicalTime)) return `Moment ${fallback}`
  const unit = String(current?.time_unit || 'step')
  if (unit === 'minute' || unit === 'scenario_minute') {
    const day = Math.floor(logicalTime / (24 * 60))
    const minute = logicalTime % (24 * 60)
    return minute === 0 ? `Day ${day}` : `Day ${day} · minute ${minute}`
  }
  const label = unit.replaceAll('_', ' ')
  return `${logicalTime} ${label}${logicalTime === 1 ? '' : 's'} into the simulation`
}

function storyParticipants(participants) {
  if (participants.length > 1 && participants.every((item) => String(item).endsWith('_pressure_source'))) {
    return 'Outside concern sources'
  }
  if (participants.length > 3 && participants.includes('meeting_clock')) return 'Team review'
  if (participants.length > 3) return `${participants.length} participants`
  return participants.map((item) => {
    const label = String(item).replaceAll('_', ' ')
    return `${label[0]?.toUpperCase() || ''}${label.slice(1)}`
  }).join(' + ')
}

function renderLifecycleControls(run = current) {
  const status = run?.status || 'ready'
  const paused = status === 'paused'
  const pausing = status === 'pause_requested'
  const resumableScenario = ['service_desk', 'coordination_decision'].includes(
    run?.scenario || $('#scenario')?.value
  )
  const retainedCheckpoint = Boolean(run?.continuation?.checkpoint)
  const narrationResumable = status === 'completed'
    && run?.execution === 'live'
    && run?.narration?.status === 'unavailable'
    && run?.narration?.failure_boundary?.kind === 'call_limit_preflight'
    && Number(run?.narration?.model_calls || 0) === 0
  const resumable = narrationResumable
    || (resumableScenario && retainedCheckpoint && ['paused', 'failed'].includes(status))
  const running = status === 'running' && resumableScenario
  $('#resume').hidden = !resumable
  $('#resume').disabled = false
  $('#resume').textContent = narrationResumable
    ? 'Finish missing narrative'
    : 'Resume from retained step'
  $('#resume').title = narrationResumable
    ? 'Generate only the missing narrative from the completed retained trace. The simulated world and participant calls are not replayed.'
    : buttonTooltips.resume
  $('#resume').setAttribute('aria-label', $('#resume').title)
  $('#pause').hidden = !running
  $('#pause').disabled = false
  $('#stop').hidden = !running
  $('#stop').disabled = false
  if (paused) {
    $('#run-status').textContent = 'Paused'
    $('#lifecycle-help').textContent = run.pause_message || 'This run stopped at a validated causal boundary. Resume continues from the retained checkpoint.'
  } else if (pausing) {
    $('#run-status').textContent = 'Pause requested'
    $('#lifecycle-help').textContent = run.pause_message || 'The current causal step is finishing before the checkpoint is retained.'
  } else if (status === 'completed') {
    $('#run-status').textContent = 'Completed'
    $('#lifecycle-help').textContent = narrationResumable
      ? 'The simulation completed, but its narrative was not generated. Finish only that missing presentation phase without replaying the run.'
      : run.completion?.public_summary || 'This run is complete. Choose another condition or open a saved run from Run history.'
  } else if (status === 'narrating') {
    $('#run-status').textContent = 'Writing narrative'
    $('#lifecycle-help').textContent = 'The world run is complete. The narrator is now turning its retained causal moments into a readable account.'
  } else if (status === 'stop_requested') {
    $('#run-status').textContent = 'Stop requested'
    $('#lifecycle-help').textContent = run.stop_message || 'The current causal step is finishing before this run ends.'
  } else if (status === 'failed' || status === 'interrupted') {
    $('#run-status').textContent = status === 'failed' ? 'Failed' : 'Interrupted'
    $('#lifecycle-help').textContent = resumable
      ? 'The run stopped after a validated causal boundary. Resume continues from the retained step instead of replaying the run.'
      : run.error || 'This run did not reach a resumable checkpoint.'
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
  configureAuthoringReasoningChoices(authoring.reasoning_effort)
  $('#authoring-model').title = 'The model selected here will produce only the next saved draft revision.'
  $('#authoring-reasoning').title = 'The thinking level selected here will apply only to the next saved draft revision.'
  updateAuthoringRuntime()
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
  configureAuthoringLiveModels(
    liveOptions.defaults?.model || config.model,
    liveOptions.defaults?.agent_reasoning_effort || config.reasoning_effort,
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
  const controls = selected.run_control_options
  $('#run-control-field').hidden = !controls || scenarioId !== 'service_desk'
  if (controls) {
    $('#modeled-horizon').min = controls.minimum_horizon
    $('#modeled-horizon').max = controls.maximum_horizon
    $('#modeled-horizon').value = controls.default_horizon
    $('#modeled-horizon-help').textContent = 'The simulation stops before activating a later causal step once this modeled time is reached, unless its compiled terminal condition is met first.'
  }
  const allLiveChoices = runtimeConfig.live_options?.models || []
  const allowedModelIds = Array.isArray(selected.live_model_ids)
    ? new Set(selected.live_model_ids)
    : null
  const liveChoices = allowedModelIds
    ? allLiveChoices.filter((choice) => allowedModelIds.has(choice.model))
    : allLiveChoices
  const priorModel = $('#model').value
  $('#model').innerHTML = liveChoices.map((choice) =>
    `<option value="${html(choice.model)}">${html(choice.label)}</option>`
  ).join('')
  $('#model').value = liveChoices.some((choice) => choice.model === priorModel)
    ? priorModel
    : liveChoices.find((choice) => choice.default)?.model || liveChoices[0]?.model || ''
  configureReasoningChoices()
  const liveAvailable = Boolean(
    runtimeConfig.live_authorized
    && liveChoices.length
  )
  const scenarioSupportsLive = selected.supports_live !== false
  $('#live').disabled = !liveAvailable || !scenarioSupportsLive
  if (!scenarioSupportsLive) {
    $('#live').checked = false
    $('#live-help').textContent = 'This scenario currently has a zero-cost scripted implementation only.'
  }
  $('#run').textContent = $('#live').checked ? 'Play live simulation' : 'Play reference simulation'
  configureLiveControls()
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
  selectedBoundaryActivities = null
  boundaryActivityRequestSerial += 1
  selectedScale = 'exact'
  selectedGraphView = current.world ? 'world' : 'causal'
  selectedNodeId = null
  selectedEdgeId = null
  $('#map-section').hidden = false
  renderScaleControls()
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

function isSubscriptionModel(choice = selectedModelChoice()) {
  return choice?.billing_mode === 'subscription_included'
}

function updateAuthoringRuntime() {
  const authoring = runtimeConfig.authoring || {}
  const choice = (authoring.models || []).find(
    (item) => item.model === $('#authoring-model').value
  )
  if (!choice) {
    $('#authoring-runtime').textContent = 'Structured authoring configuration is unavailable.'
    return
  }
  const attempts = authoring.maximum_attempts_per_message || 1
  const contract = authoring.structured_contract || {}
  const accounting = choice.billing_mode === 'subscription_included'
    ? 'It is included with the signed-in ChatGPT Codex subscription; Codex usage limits apply.'
    : `Each attempt has a $${Number(authoring.maximum_cost_per_attempt || 0).toFixed(2)} request ceiling, so one message exposes at most $${Number(contract.maximum_usage_based_cost_per_message || attempts * Number(authoring.maximum_cost_per_attempt || 0)).toFixed(2)} across all attempts.`
  $('#authoring-runtime').textContent =
    `Your selected model and thinking level apply only to the next message. One message may make up to ${attempts} structured attempt(s). ${accounting} The saved conversation records the selection, trace, and observed cost for every revision. Contract ${contract.prompt_version || 'version unavailable'} · schema ${String(contract.schema_digest || 'digest unavailable').slice(0, 12)}.`
}

function configureAuthoringReasoningChoices(preferred = null) {
  const authoring = runtimeConfig.authoring || {}
  const choice = (authoring.models || []).find(
    (item) => item.model === $('#authoring-model').value
  )
  const efforts = choice?.reasoning_efforts || authoring.reasoning_efforts || ['medium']
  $('#authoring-reasoning').innerHTML = efforts.map((effort) => {
    const label = {none:'None', low:'Low', medium:'Medium', high:'High', xhigh:'Extra high', max:'Max'}[effort] || effort
    return `<option value="${html(effort)}">${html(label)}</option>`
  }).join('')
  $('#authoring-reasoning').value = efforts.includes(preferred)
    ? preferred
    : choice?.default_reasoning_effort || efforts[0]
  updateAuthoringRuntime()
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

function configureAuthoringLiveModels(preferredModel = null, preferredReasoning = null) {
  const allChoices = runtimeConfig.live_options?.models || []
  const coordination = authoringDraft?.proposal?.workflow?.template_id === 'coordination_decision_v1'
  const allowed = coordination
    ? new Set(runtimeConfig.scenarios?.coordination_decision?.live_model_ids || [])
    : null
  const choices = allowed
    ? allChoices.filter((item) => allowed.has(item.model))
    : allChoices
  const prior = preferredModel || $('#authoring-live-model').value
  $('#authoring-live-model').innerHTML = choices.map((choice) =>
    `<option value="${html(choice.model)}">${html(choice.label)}</option>`
  ).join('')
  $('#authoring-live-model').value = choices.some((choice) => choice.model === prior)
    ? prior
    : choices.find((choice) => choice.default)?.model || choices[0]?.model || ''
  configureAuthoringLiveReasoning(preferredReasoning)
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
  const planned = Number($('#max-cost').value || 0)
  const subscriptionIncluded = isSubscriptionModel()
  const measuresCoordination = $('#scenario').value === 'coordination_decision'
  const selectedScenario = scenarioCatalog[$('#scenario').value] || {}
  const participantDecisionLimit = Number(
    selectedScenario.run_control_options?.max_participant_calls_cap ||
    selectedScenario.maximum_live_calls ||
    limits.maximum_participant_calls ||
    0
  )
  const measurementPolicy = runtimeConfig.coordination_measurement || {}
  const coderCalls = measuresCoordination ? Number(measurementPolicy.maximum_coder_calls || 0) : 0
  const coderCeiling = measuresCoordination ? Number(measurementPolicy.coder_per_call_ceiling || 0) : 0
  $('#max-cost-field').hidden = subscriptionIncluded
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
  $('#cost-details').textContent = subscriptionIncluded
    ? `${modelLabel} is included with the signed-in ChatGPT Codex subscription; marginal provider cost is recorded as $0. Codex usage limits still apply. This run permits at most ${participantDecisionLimit} LLM-driven participant decisions before its run-length guard stops it; it does not aim for that number or change the scenario's simulated pressure. It also permits at most ${Number(limits.maximum_narrator_calls || 0)} narrator calls${coderCalls ? ` and ${coderCalls} post-run evidence-coder call` : ''}.`
    : `${estimate} Retained planning amount: $${(planned + coderCeiling * coderCalls).toFixed(2)}${coderCalls ? `, including ${coderCalls} post-run coder request capped at $${coderCeiling.toFixed(2)}` : ''}. A returned valid simulation is not terminated because observed or partially observed cost crosses this amount. Provider requests still carry per-call budgets of $${Number(limits.participant_per_call_ceiling || 0).toFixed(2)} for participants and $${Number(limits.narrator_per_call_ceiling || 0).toFixed(2)} for narration; the ${participantDecisionLimit}-decision run-length guard and causal-step limit bound runtime growth.`
}

function describeCondition() {
  const scenario = scenarioCatalog[$('#scenario').value]
  const arm = scenario?.arms.find((item) => item.id === $('#arm').value)
  const question = $('#scenario').value === 'service_desk'
    ? 'After Play, ask: how did this condition change the path to safe closure?'
    : 'After Play, ask: what changed, why, and which retained evidence supports it?'
  $('#arm-help').textContent = `${arm?.description || 'Choose the concrete condition you want the simulation to test.'} ${question}`
}

const compositeRowPresentation = {
  matched_control: {
    label:'Matched control',
    change:'No perturbation; the original people, routes, and feedback remain in place.',
  },
  member_replacement: {
    label:'Member replaced',
    change:'A different person occupies the technical-validation position while its interfaces and responsibilities stay fixed.',
  },
  route_interruption: {
    label:'Decision route interrupted',
    change:'The direct final-proposal path becomes unavailable on day 4; a configured alternate path remains.',
  },
  feedback_interruption: {
    label:'Verification feedback lost',
    change:'Verification responses stop reaching the five decision makers after day 4.',
  },
  external_risk: {
    label:'Legitimate external risk',
    change:'A concrete outside source delivers relevant risk information to the validation position on day 4.',
  },
}

function compositeOutcomeLabel(value) {
  return {
    deploy_on_time:'Full deployment approved',
    scope_reduced:'Reduced scope approved',
    delayed:'Decision delayed',
    partner_disengaged:'Partner disengaged',
    no_decision_by_horizon:'No decision by the deadline',
  }[value] || String(value || 'No retained outcome').replaceAll('_', ' ')
}

function compositeRecoveryLabel(value, rowId) {
  if (rowId === 'matched_control') return 'Not tested'
  if (value === 'not_observed') return 'No recovery observed'
  if (value && typeof value === 'object') {
    return `Recovered after ${Number(value.scenario_minutes).toLocaleString()} modeled minutes`
  }
  return 'No recovery claim'
}

function compositeCorrectionLabel(values) {
  const count = Array.isArray(values) ? values.length : 0
  return count ? `${count} issue correction${count === 1 ? '' : 's'}` : 'No correction episode'
}

function compositeRouteLabel(values, rowId) {
  if (Array.isArray(values) && values.length) return 'Alternate path used'
  if (rowId === 'feedback_interruption') return 'Verification delivery blocked'
  if (rowId === 'external_risk') return 'Outside input delivered'
  return rowId === 'route_interruption' ? 'No alternate path used' : 'Original paths used'
}

function compositeMemberLabel(values) {
  if (!Array.isArray(values) || !values.length) return 'Original five people'
  return 'Technical position reoccupied'
}

function compositeFlowSummary(row) {
  const activity = row.boundary_activity || {crossings:[], episodes:[]}
  const crossings = activity.crossings || []
  const incoming = crossings.filter((item) => item.direction === 'incoming')
  const outgoing = crossings.filter((item) => item.direction === 'outgoing')
  const episodes = activity.episodes || []
  const completed = episodes.filter((item) => item.status === 'completed')
  const external = row.readout?.external_result_event_ids || []
  const crossingLine = (crossing) => `${refLabel(crossing.source_ref)} → ${refLabel(crossing.target_ref)}`
  return `
    <div class="assay-flow-grid">
      <article><span class="eyebrow">What reached the group</span><strong>${incoming.length ? `${incoming.length} incoming flow${incoming.length === 1 ? '' : 's'}` : 'No outside input'}</strong><p>${incoming.length ? incoming.map(crossingLine).join('; ') : 'This condition began and remained within the configured partnership boundary.'}</p></article>
      <article><span class="eyebrow">What the group sent out</span><strong>${outgoing.length ? `${outgoing.length} outward result${outgoing.length === 1 ? '' : 's'}` : 'No outward result'}</strong><p>${outgoing.length ? outgoing.map(crossingLine).join('; ') : 'No result crossed from the partnership to the external decision registry.'}</p></article>
      <article><span class="eyebrow">How work connected</span><strong>${completed.length} completed group episode${completed.length === 1 ? '' : 's'}</strong><p>${episodes.length - completed.length ? `${episodes.length - completed.length} incoming thread is retained separately because it did not itself produce a boundary output.` : 'Every retained group episode with an output completed.'}</p></article>
      <article><span class="eyebrow">What happened outside</span><strong>${external.length ? `${external.length} external result event${external.length === 1 ? '' : 's'}` : 'No external result'}</strong><p>External acceptance is kept separate from the group’s attempted and routed output.</p></article>
    </div>`
}

function renderCompositeAssaySelection(assayId, rowId, updateUrl = true) {
  const assay = compositeAssayCache.get(assayId)
  const row = assay?.rows?.find((item) => item.row_id === rowId)
  if (!row) return
  if (updateUrl) {
    const url = new URL(window.location)
    url.searchParams.delete('run')
    url.searchParams.delete('draft')
    url.searchParams.set('assay', assayId)
    window.history.replaceState({}, '', url)
  }
  const presentation = compositeRowPresentation[rowId] || {label:rowId.replaceAll('_',' '), change:'Reviewed condition.'}
  const exact = row.readout.exact_values || {}
  const pattern = row.readout.coded_patterns?.[0]
  const changed = [
    ...(row.configuration_diff.initial_configuration_changed_refs || []),
    ...(row.configuration_diff.scheduled_configuration_changed_refs || []),
    ...(row.configuration_diff.created_refs || []),
  ]
  const selection = document.querySelector(`[data-assay-selection="${assayId}"]`)
  if (!selection) return
  document.querySelectorAll(`[data-assay-id="${assayId}"] .assay-row-select`).forEach((button) => {
    const selected = button.dataset.rowId === rowId
    button.closest('tr').classList.toggle('selected', selected)
    button.setAttribute('aria-pressed', String(selected))
  })
  selection.innerHTML = `
    <span class="eyebrow">Selected condition · ${html(presentation.label)}</span>
    <h4>${html(compositeOutcomeLabel(exact.terminal_outcome))}</h4>
    <p>${html(presentation.change)}</p>
    ${compositeFlowSummary(row)}
    <div class="assay-interpretation">
      <strong>${html(rowId === 'matched_control' ? 'Comparison reference' : pattern?.pattern_id === 'rational_caution' ? 'Observed response: rational caution' : pattern?.pattern_id?.replaceAll('_',' ') || 'No pattern claim')}</strong>
      <p>${html(pattern?.explanation || 'The matched control is the comparison reference and makes no perturbation-pattern claim.')}</p>
      <small>This is a coded reference pattern over retained evidence, not an organization-level thought or a causal attribution.</small>
    </div>
    <div class="assay-selection-actions">
      <button class="open-assay-group" data-run-id="${html(row.run_id)}">View this group in the simulation</button>
      <button class="open-assay-run" data-run-id="${html(row.run_id)}">Open the exact run</button>
    </div>
    <details class="assay-evidence-details"><summary>Changed components and exact evidence</summary>
      <p><strong>Changed configuration:</strong> ${changed.length ? changed.map((item) => html(refLabel(item))).join(' · ') : 'None; this is the matched control.'}</p>
      <p><strong>Boundary inputs:</strong> ${html(row.readout.input_crossing_ids.join(' · ') || 'none')}</p>
      <p><strong>Coordination episodes:</strong> ${html(row.readout.coordination_episode_ids.join(' · ') || 'none')}</p>
      <p><strong>Boundary outputs:</strong> ${html(row.readout.output_crossing_ids.join(' · ') || 'none')}</p>
      <p><strong>External results:</strong> ${html(row.readout.external_result_event_ids.join(' · ') || 'none')}</p>
      <div class="assay-evidence-buttons">${(pattern?.source_event_ids || []).map((eventId) => `<button data-assay-event="${html(eventId)}" data-run-id="${html(row.run_id)}">Inspect ${html(eventId)}</button>`).join('')}</div>
    </details>`
  selection.querySelector('.open-assay-group').onclick = async (event) => {
    await openRetained(event.target.dataset.runId)
    selectedPerson = 'deployment_partnership'
    showTraceInPlace(selectedPerson)
    showBoundary(selectedPerson)
  }
  selection.querySelector('.open-assay-run').onclick = (event) => openRetained(event.target.dataset.runId)
  selection.querySelectorAll('[data-assay-event]').forEach((button) => {
    button.onclick = async () => {
      await openRetained(button.dataset.runId)
      const index = current.timeline.findIndex((item) => item.event_id === button.dataset.assayEvent)
      if (index >= 0) selectEvent(index)
    }
  })
  applyButtonTooltips(selection)
}

function renderCompositeAssay(assay) {
  if (assay.error) return `<section class="composite-assay assay-unavailable" data-assay-id="${html(assay.assay_id)}"><span class="eyebrow">Retained comparison unavailable</span><h3>${html(assay.error)}</h3><p>The rest of Run history remains available. Restore the missing retained rows or move the incomplete files aside before reopening this comparison.</p></section>`
  const rows = assay.rows || []
  return `<section class="composite-assay" data-assay-id="${html(assay.assay_id)}">
    <header><div><span class="eyebrow">Retained five-condition comparison</span><h3>Can the partnership preserve a valid collective decision?</h3></div><div class="assay-header-actions"><small>${html(new Date(rows[0]?.created_at).toLocaleString())} · 0 model calls</small><button class="trash-assay" data-trash-assay-id="${html(assay.assay_id)}">Move comparison to trash</button></div></header>
    <p class="assay-question">Compare concrete changes to people, routes, feedback, and relevant outside information. A slower or different decision is not automatically a loss of collective capability.</p>
    <div class="assay-table-wrap"><table class="assay-table"><thead><tr><th>Condition</th><th>Goal and rules</th><th>Correction</th><th>Recovery</th><th>Routing</th><th>Members</th><th>Outcome</th></tr></thead><tbody>
      ${rows.map((row) => {
        const exact = row.readout.exact_values || {}
        const presentation = compositeRowPresentation[row.row_id] || {label:row.row_id.replaceAll('_',' ')}
        return `<tr><td><button class="assay-row-select" data-row-id="${html(row.row_id)}" aria-pressed="false">${html(presentation.label)}</button></td>
          <td><strong>${exact.capability_satisfied ? 'Preserved' : 'Not preserved'}</strong><small>${exact.all_constraints_satisfied ? 'All reviewed rules met' : `Failed: ${(exact.failed_constraint_ids || []).map((item) => item.replaceAll('_',' ')).join(', ')}`}</small></td>
          <td>${html(compositeCorrectionLabel(exact.correction_event_pairs))}</td>
          <td>${html(compositeRecoveryLabel(exact.recovery, row.row_id))}</td>
          <td>${html(compositeRouteLabel(exact.alternate_routes_used, row.row_id))}</td>
          <td>${html(compositeMemberLabel(exact.member_replacements))}</td>
          <td>${html(compositeOutcomeLabel(exact.terminal_outcome))}</td></tr>`
      }).join('')}
    </tbody></table></div>
    <article class="assay-selection" data-assay-selection="${html(assay.assay_id)}"></article>
  </section>`
}

async function loadHistory() {
  const result = await request('/api/runs')
  const assayIds = [...new Set(result.runs.map((run) => run.composite_assay?.assay_id).filter(Boolean))]
  const assays = await Promise.all(assayIds.map(async (assayId) => {
    try {
      if (!compositeAssayCache.has(assayId)) {
        compositeAssayCache.set(assayId, await request(`/api/composite-assays/${assayId}`))
      }
      return compositeAssayCache.get(assayId)
    } catch (error) {
      return {assay_id:assayId, error:error.message}
    }
  }))
  $('#composite-assays').innerHTML = assays.map(renderCompositeAssay).join('')
  assays.filter((assay) => !assay.error).forEach((assay) => {
    document.querySelectorAll(`[data-assay-id="${assay.assay_id}"] .assay-row-select`).forEach((button) => {
      button.onclick = () => renderCompositeAssaySelection(assay.assay_id, button.dataset.rowId)
    })
    renderCompositeAssaySelection(assay.assay_id, assay.rows[0].row_id, false)
  })
  document.querySelectorAll('.trash-assay').forEach((button) => {
    button.onclick = async () => {
      if (!confirm('Move all five retained rows in this comparison to recoverable server trash?')) return
      try {
        await request(`/api/composite-assays/${button.dataset.trashAssayId}`, {method:'DELETE'})
        compositeAssayCache.delete(button.dataset.trashAssayId)
        await loadHistory()
      } catch (error) {
        $('#assay-status').textContent = error.message
      }
    }
  })
  const ordinaryRuns = result.runs.filter((run) => !run.composite_assay)
  $('#history-empty').hidden = ordinaryRuns.length > 0 || assays.length > 0
  $('#storage-warning').hidden = result.corrupt_files.length === 0
  $('#storage-warning').textContent = result.corrupt_files.length
    ? `${result.corrupt_files.length} unreadable retained run file(s) require operator attention.`
    : ''
  $('#history').innerHTML = ordinaryRuns.map((run) => `
    <article class="history-item">
      <button class="open-run" data-run-id="${run.run_id}">
        <strong>${html(run.headline || run.status)}</strong>
        <span>${html(run.scenario?.replaceAll('_',' '))} · ${html(run.arm?.replaceAll('_',' '))}</span>
        <small>${html(run.status)} · ${html(new Date(run.created_at).toLocaleString())}</small>
        <small class="history-run-id">Run ID · ${html(run.run_id)}</small>
        ${run.scenario === 'coordination_decision' ? `<small class="measurement-history-status ${html(run.coordination_measurement_status || 'not_measured')}">${html({available:'Assay available',measuring:'Assay running',invalid:'Assay needs attention',not_measured:'Not measured'}[run.coordination_measurement_status] || 'Not measured')}</small>` : ''}
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
  url.searchParams.delete('assay')
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
  if (liveProjection?.nodes && liveProjection?.edges) {
    return {
      nodes:liveProjection.nodes,
      edges:liveProjection.edges.map((edge) => ({
        ...edge,
        kind:edge.kind || 'connection',
        routeIds:edge.exact_route_ids || edge.routeIds || [edge.id],
      })),
    }
  }
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

function graphDiagnostics(raw = liveProjection?.graph_diagnostics || current?.graph_diagnostics) {
  if (!raw || raw.contract !== 'configured-graph-diagnostics.v1') return null
  return {
    contract:raw.contract,
    counts:raw.counts || {},
    nodeClassification:raw.node_classification || {},
    warnings:(raw.warnings || []).map((item) => ({
      code:item.code,
      nodeId:item.node_id,
      message:item.message,
    })),
  }
}

function renderScaleControls() {
  const boundaries = current?.boundaries || []
  if (selectedScale !== 'exact' && !boundaries.some((item) => item.id === selectedScale)) {
    selectedScale = 'exact'
  }
  const control = $('#analytical-scale-control')
  control.hidden = boundaries.length === 0
  if (!boundaries.length) return
  const selector = $('#analytical-boundary')
  const priorChoice = selector.value
  selector.innerHTML = boundaries.map((boundary) =>
    `<option value="${html(boundary.id)}">${html(boundary.label)}</option>`
  ).join('')
  const selectedBoundaryId = selectedScale !== 'exact'
    ? selectedScale
    : boundaries.some((item) => item.id === priorChoice) ? priorChoice : boundaries[0].id
  selector.value = selectedBoundaryId
  const selected = boundaries.find((item) => item.id === selectedBoundaryId)
  const collapsed = selectedScale !== 'exact'
  const toggle = $('#analytical-scale-toggle')
  const available = selectedGraphView !== 'trajectory'
  toggle.textContent = `${collapsed ? 'Expand' : 'Collapse'} ${selected?.label || 'analytical composite'}`
  toggle.disabled = !available
  selector.disabled = !available
  $('#analytical-scale-help').textContent = available
    ? 'Group a composite system into one node, or expand its components. This changes analytical granularity without changing the selected map view.'
    : 'Realized causal events do not yet have a composite coarse-graining. Choose Spatial topology or Configured interaction pathways to change analytical scale.'
  toggle.title = !available
    ? 'Choose Spatial topology or Configured interaction pathways to change analytical scale; this control will not switch map views for you.'
    : collapsed
      ? 'Show the exact people, information, objects, and mechanisms inside this analytical composite without changing map view.'
      : 'Group this analytical composite into one derived node without changing map view. This changes only the view, not what acts in the simulation.'
  toggle.setAttribute('aria-label', `Analytical scale: ${toggle.textContent}`)
}

function selectedScaleBoundaryId() {
  const boundaries = current?.boundaries || []
  if (selectedScale !== 'exact') return selectedScale
  const selected = $('#analytical-boundary')?.value
  return boundaries.some((item) => item.id === selected) ? selected : boundaries[0]?.id || null
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

function refLabel(ref) {
  const node = (current?.nodes || []).find((item) => item.id === ref)
  return node?.label || String(ref || '').replaceAll('_', ' ')
}

function readableActionSummary(value) {
  return String(value || '').replace(
    'The coordinator proposed scope_reduced at reduced scope.',
    'The coordinator submitted the smaller deployment for final approval.',
  )
}

function exactEvent(eventId) {
  return (current?.timeline || []).find((item) => item.event_id === eventId)
    || (current?.events || []).find((item) => item.event_id === eventId)
}

function episodeEvidenceIds(episode, crossingById) {
  const crossingEvents = [
    ...(episode.input_crossing_ids || []),
    ...(episode.prior_output_crossing_ids || []),
    ...(episode.output_crossing_id ? [episode.output_crossing_id] : []),
  ].map((crossingId) => crossingById.get(crossingId)?.event_id).filter(Boolean)
  return [...new Set([
    ...crossingEvents,
    ...(episode.trigger_event_ids || []),
    ...(episode.internal_event_ids || []),
    ...(episode.external_result_event_ids || []),
  ])].sort((left, right) => Number(exactEvent(left)?.sequence || 0) - Number(exactEvent(right)?.sequence || 0))
}

function renderCrossing(crossing) {
  if (!crossing) return 'none retained'
  return `${html(refLabel(crossing.source_ref))} → ${html(refLabel(crossing.target_ref))}`
}

function renderBoundaryActivity(activity, snapshot, scope = 'full') {
  if (activity === undefined) {
    return '<p class="muted">This saved run predates group-flow summaries. Its individual participant histories and exact evidence are still available.</p>'
  }
  if (activity === null) {
    return '<p class="muted">Loading what had entered or left this group at the selected point…</p>'
  }
  const crossingById = new Map((activity.crossings || []).map((item) => [item.crossing_id, item]))
  if (!(activity.crossings || []).length) {
    return '<p><strong>Nothing has entered or left this group yet.</strong> The selected point is before any recorded exchange with the rest of the simulation.</p>'
  }
  const episodeAccounts = (activity.episodes || []).map((episode, episodeIndex) => {
    const inputs = (episode.input_crossing_ids || []).map((id) => renderCrossing(crossingById.get(id)))
    const output = episode.output_crossing_id ? renderCrossing(crossingById.get(episode.output_crossing_id)) : null
    const contributorNodes = (episode.contributing_member_ids || []).map((memberId) =>
      nodesAtSelectedEvent().find((node) => node.id === memberId),
    ).filter(Boolean)
    const contributorPeople = contributorNodes.filter((node) => node.kind === 'person').map((node) => node.label)
    const contributorProcesses = contributorNodes.filter((node) => node.kind !== 'person')
    const contributorSummary = contributorPeople.length
      ? `${contributorPeople.join(', ')}${contributorProcesses.length ? `, with ${contributorProcesses.length} supporting process${contributorProcesses.length === 1 ? '' : 'es'}` : ''}`
      : contributorProcesses.length
        ? `${contributorProcesses.length} supporting process${contributorProcesses.length === 1 ? '' : 'es'}`
        : 'No member contribution is recorded yet.'
    const external = (episode.external_result_event_ids || []).map((eventId) =>
      exactEvent(eventId)?.summary || String(exactEvent(eventId)?.event_kind || eventId).replaceAll('_', ' ')
    )
    const evidenceIds = episodeEvidenceIds(episode, crossingById)
    const status = episode.status === 'completed' ? 'complete' : 'in progress'
    return `<section class="boundary-episode ${episode.status}">
      <span class="eyebrow">Group response ${html(episodeIndex + 1)} · ${html(status)}</span>
      <dl class="boundary-flow">
        <div><dt>What reached the group</dt><dd>${inputs.length ? inputs.join('<br>') : 'This activity began inside the group; nothing arrived from outside.'}</dd></div>
        <div><dt>Who responded inside</dt><dd>${html(contributorSummary)}</dd></div>
        <div><dt>What left the group</dt><dd>${output || 'Nothing has left the group yet.'}</dd></div>
        <div><dt>What changed outside</dt><dd>${external.length ? html(external.join(' ')) : output ? 'No outside change is recorded yet.' : 'Nothing yet; the activity remains inside the group.'}</dd></div>
      </dl>
      <button type="button" class="inspect-boundary-path" data-episode-index="${episodeIndex}" ${evidenceIds.length ? '' : 'disabled'}>Show supporting events</button>
      <details class="boundary-evidence" data-episode-index="${episodeIndex}"><summary>Technical evidence · ${html(evidenceIds.length)} exact event${evidenceIds.length === 1 ? '' : 's'}</summary><div class="focus-list">${evidenceIds.map((eventId) => `<button type="button" data-event-id="${html(eventId)}">${html(exactEvent(eventId)?.kind?.replaceAll('_', ' ') || eventId)}</button>`).join('')}</div></details>
    </section>`
  }).join('')
  const incoming = (activity.crossings || []).filter((crossing) => crossing.direction === 'incoming')
  const outgoing = (activity.crossings || []).filter((crossing) => crossing.direction === 'outgoing')
  const incomingSources = [...new Set(incoming.map((crossing) => refLabel(crossing.source_ref)))]
  const outgoingTargets = [...new Set(outgoing.map((crossing) => refLabel(crossing.target_ref)))]
  const contributorIds = [...new Set((activity.episodes || []).flatMap((episode) => episode.contributing_member_ids || []))]
  const contributorPeople = contributorIds.map((memberId) =>
    nodesAtSelectedEvent().find((node) => node.id === memberId),
  ).filter((node) => node?.kind === 'person').map((node) => node.label)
  const received = incoming.length
    ? `The group received ${incoming.length} outside input${incoming.length === 1 ? '' : 's'} from ${incomingSources.join(', ')}.`
    : 'No outside input reached the group.'
  const responded = contributorPeople.length
    ? `${contributorPeople.join(', ')} contributed to the response inside the group.`
    : 'Its configured processes handled the retained activity inside the group.'
  const produced = outgoing.length
    ? `Its members and supporting processes produced ${outgoing.length} outward action${outgoing.length === 1 ? '' : 's'}, sent to ${outgoingTargets.join(', ')}.`
    : 'No action or message has left the group yet.'
  return `<section class="group-flow-summary">
      <h4>${scope === 'full' ? 'What the group did in this run' : 'What the group had done by the selected moment'}</h4>
      <p>${html(received)} ${html(responded)} ${html(produced)}</p>
    </section>
    <details class="group-activity-details">
      <summary>Show how this group activity was derived</summary>
      <div class="group-episode-list">${episodeAccounts}</div>
    </details>`
}

async function refreshBoundaryActivitiesAtSelection() {
  const boundarySelected = (current?.boundaries || []).some((item) => item.id === selectedPerson)
  if (selectedBoundaryScope !== 'moment' || !boundarySelected || !current?.run_id || !current?.timeline?.length) return
  const eventId = current.timeline[selectedEventIndex]?.event_id
  if (!eventId) return
  const requestSerial = ++boundaryActivityRequestSerial
  selectedBoundaryActivities = null
  try {
    const clipped = await request(`/api/runs/${encodeURIComponent(current.run_id)}?through_event_id=${encodeURIComponent(eventId)}`)
    if (requestSerial !== boundaryActivityRequestSerial || current.timeline[selectedEventIndex]?.event_id !== eventId) return
    selectedBoundaryActivities = Object.fromEntries(
      (clipped.boundaries || []).map((boundary) => [boundary.id, boundary.activity]),
    )
    showTrace(selectedPerson)
  } catch (error) {
    if (requestSerial !== boundaryActivityRequestSerial) return
    $('#trace').innerHTML = `<p class="error">${html(error.message)}</p>`
  }
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
    const groupExplanation = people.length
      ? `This view follows ${people.length} people as one group. It shows what reached them, how they responded, and what left. The people and supporting processes make decisions and cause changes; “${boundary.label}” only summarizes their combined activity.`
      : `This view groups ${snapshot?.member_ids?.length || 0} modeled components. It shows what entered or left the group and which components produced those changes; “${boundary.label}” does not make decisions itself.`
    const hasTypedActivity = Object.prototype.hasOwnProperty.call(boundary, 'activity')
    const completedFullRun = current?.status === 'completed' && selectedBoundaryScope === 'full'
    const activity = completedFullRun
      ? (hasTypedActivity ? boundary.activity : undefined)
      : selectedBoundaryActivities
        ? selectedBoundaryActivities[boundary.id]
        : selectedBoundaryScope === 'moment' && current?.timeline?.length
          ? null
          : (hasTypedActivity ? boundary.activity : undefined)
    const scopeExplanation = selectedBoundaryScope === 'full'
      ? 'Showing all retained activity in this completed run.'
      : 'Showing only activity retained through the selected causal moment.'
    $('#trace').innerHTML = `
      <article class="trace-step composite-account">
        <span class="eyebrow">Group view</span>
        <h3>${html(boundary.label)}</h3>
        <p>${html(groupExplanation)}</p>
        <div class="group-scope" role="group" aria-label="Group account time scope">
          <button type="button" class="group-scope-button" data-boundary-scope="full" aria-pressed="${selectedBoundaryScope === 'full'}">Full run</button>
          <button type="button" class="group-scope-button" data-boundary-scope="moment" aria-pressed="${selectedBoundaryScope === 'moment'}">Selected moment</button>
        </div>
        <small class="muted">${html(scopeExplanation)}</small>
        <div class="boundary-activity">${renderBoundaryActivity(activity, snapshot, selectedBoundaryScope)}</div>
        <button id="inspect-composite">Highlight this group on the map</button>
        <details class="participant-technical">
          <summary>Technical details</summary>
          <dl class="aggregate-facts">
            <div><dt>Modeled components</dt><dd>${html(snapshot?.member_ids?.length || 0)}</dd></div>
            <div><dt>Internal connections</dt><dd>${html(snapshot?.internal_route_ids?.length || 0)}</dd></div>
            <div><dt>People included</dt><dd>${html(people.length)}</dd></div>
            <div><dt>Supporting processes</dt><dd>${html(processes.length)}</dd></div>
            <div><dt>Acts as a separate world entity?</dt><dd>No — analysis only</dd></div>
          </dl>
        </details>
      </article>`
    $('#inspect-composite').onclick = () => showBoundary(boundary.id)
    document.querySelectorAll('.group-scope-button').forEach((button) => {
      button.onclick = () => {
        selectedBoundaryScope = button.dataset.boundaryScope
        selectedBoundaryActivities = null
        boundaryActivityRequestSerial += 1
        showTrace(selectedPerson)
      }
    })
    document.querySelectorAll('.inspect-boundary-path').forEach((button) => {
      button.onclick = () => {
        const details = document.querySelector(`.boundary-evidence[data-episode-index="${button.dataset.episodeIndex}"]`)
        if (details) details.open = true
        const first = details?.querySelector('button[data-event-id]')
        const index = first ? current.timeline.findIndex((item) => item.event_id === first.dataset.eventId) : -1
        if (index >= 0) selectEvent(index)
      }
    })
    document.querySelectorAll('.boundary-evidence button[data-event-id]').forEach((button) => {
      button.onclick = () => {
        const index = current.timeline.findIndex((item) => item.event_id === button.dataset.eventId)
        if (index >= 0) selectEvent(index)
      }
    })
    if (selectedBoundaryScope === 'moment' && current?.timeline?.length && !selectedBoundaryActivities) {
      void refreshBoundaryActivitiesAtSelection()
    }
    applyButtonTooltips($('#trace'))
    return
  }
  selectedPerson = person
  document.querySelectorAll('#trace-tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
  const selectedEvent = current?.timeline?.[selectedEventIndex]
  const entries = (current?.traces || []).filter((entry) => entry.person === person)
  const totalActions = entries.reduce((count, entry) => count + (entry.actions?.length || 0), 0)
  const totalObservations = entries.reduce((count, entry) => count + (entry.observations?.length || 0), 0)
  const label = refLabel(person)
  const participantKind = entries[0]?.participant_kind
  const accountType = participantKind === 'person'
    ? 'Person history'
    : participantKind === 'source_process'
      ? 'Information source history'
      : 'Process history'
  const accountSummary = participantKind === 'person'
    ? `${label} took part in ${entries.length} moment${entries.length === 1 ? '' : 's'}, received ${totalObservations} piece${totalObservations === 1 ? '' : 's'} of information, and proposed ${totalActions} action${totalActions === 1 ? '' : 's'}. The moments below show what was available and what happened next.`
    : participantKind === 'source_process'
      ? `${label} ran at ${entries.length} configured moment${entries.length === 1 ? '' : 's'} and emitted ${totalActions} output${totalActions === 1 ? '' : 's'}. This is a modeled source process, not a person making a decision.`
      : `${label} ran at ${entries.length} configured moment${entries.length === 1 ? '' : 's'} and produced ${totalActions} state transition${totalActions === 1 ? '' : 's'}. This is an exact process, not a person making a decision.`
  $('#trace').innerHTML = entries.length ? `
    <article class="trace-summary">
      <span class="eyebrow">${html(accountType)}</span>
      <h3>${html(label)}</h3>
      <p>${html(accountSummary)}</p>
    </article>` + entries.map((entry, entryIndex) => {
    const matches = selectedEvent?.activation === entry.activation
    const actionSummaries = (entry.actions || []).map((action) => readableActionSummary(action.public_summary)).filter(Boolean)
    const observationSources = [...new Set((entry.observations || []).map((observation) =>
      refLabel(observation.apparent_source_ref),
    ).filter(Boolean))]
    const observationAccount = entry.observations.length
      ? `Received ${entry.observations.length} new piece${entry.observations.length === 1 ? '' : 's'} of information${observationSources.length ? ` from ${observationSources.join(', ')}` : ''}.`
      : 'No new information arrived at this moment.'
    const orientation = entry.orientation && entry.orientation !== 'Scripted zero-cost reference action.'
      ? `<p class="participant-reasoning"><strong>Reasoning:</strong> ${html(entry.orientation)}</p>`
      : ''
    return `
      <article class="trace-step ${matches ? 'event-match' : ''}">
        <strong>${html(storyTime(entry, entryIndex + 1))}</strong>
        <p>${html(actionSummaries.length ? actionSummaries.join(' ') : 'No outward action was taken.')}</p>
        <small>${html(observationAccount)}</small>
        ${orientation}
        <details class="participant-technical">
          <summary>Technical trace</summary>
          <pre>${html(JSON.stringify({
            activation_id:entry.activation,
            causal_order:entry.causal_timestamp,
            status:entry.status,
            participant_kind:entry.participant_kind,
            model_call_count:entry.model_call_count || 0,
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
        : edge.kind === 'mechanism_read'
          ? '<small>configured read</small>'
        : edge.kind === 'mechanism_write'
          ? '<small>configured update</small>'
        : edge.kind === 'mechanism_substrate'
          ? '<small>configured substrate</small>'
        : edge.kind === 'observation_target'
          ? '<small>configured observation delivery</small>'
        : edge.kind === 'information_lineage'
          ? '<small>information lineage</small>'
        : edge.kind === 'information_location'
          ? '<small>information carrier</small>'
        : edge.routeIds.length > 1 ? `<small>${edge.routeIds.length} exact routes</small>` : ''}
    </span>`).join('') || '<span class="muted">No external route is visible at this scale.</span>'
  const graph = $('#graph')
  if (window.CyberneticGraph) {
    graph.classList.add('react-canvas-host')
    const authoredBoundary = (current.boundaries || []).find(
      (item) => item.id === selectedScaleBoundaryId(),
    ) || null
    const snapshot = boundarySnapshot(authoredBoundary)
    window.CyberneticGraph.render(graph, {
      nodes:projection.nodes,
      edges:projection.edges,
      event:current?.timeline?.[selectedEventIndex] || null,
      initialRevision:current?.initial_revision ?? null,
      world:worldProjection(),
      trajectory:current?.trajectory || null,
      graphDiagnostics:graphDiagnostics(),
      viewMode:selectedGraphView,
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
      activity:liveActivity,
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

function applyLiveProgress(record) {
  const projection = record.projection || {}
  if (projection.nodes && projection.edges) liveProjection = projection
  if (projection.boundaries) {
    selectedBoundaryActivities = Object.fromEntries(
      projection.boundaries.map((boundary) => [boundary.id, boundary.activity]),
    )
    if ((current?.boundaries || []).some((boundary) => boundary.id === selectedPerson)) {
      showTrace(selectedPerson)
    }
  }
  const cue = projection.animation_cues?.[0] || null
  liveActivity = {
    participantIds:record.kind === 'activation_started' ? (record.participant_ids || []) : [],
    cue,
  }
  $('#live-evidence').hidden = false
  if (record.kind === 'activation_started') {
    $('#live-evidence-title').textContent = `Pending activation · ${(record.participant_ids || []).join(', ').replaceAll('_', ' ')}`
    $('#live-evidence-body').textContent = 'These participants share one frozen pre-moment state. No same-moment action is yet committed.'
  } else if (cue) {
    $('#live-evidence-title').textContent = cue.kind.replaceAll('_', ' ')
    $('#live-evidence-body').textContent = cue.label
  } else {
    $('#live-evidence-title').textContent = record.kind.replaceAll('_', ' ')
    $('#live-evidence-body').textContent = 'The runtime retained this causal checkpoint; inspect the final timeline for its complete evidence.'
  }
  renderGraph()
  if (record.kind === 'activation_started') {
    $('#run-status').textContent = `Thinking: ${(record.participant_ids || []).join(', ').replaceAll('_', ' ') || 'participant'}…`
  } else if (cue) {
    $('#run-status').textContent = cue.label
  }
}

async function pollLiveRun(runId) {
  if (livePolling) return
  livePolling = true
  try {
    while (activeRunId === runId) {
      const update = await request(`/api/runs/${encodeURIComponent(runId)}/progress?after_sequence=${liveProgressSequence}`)
      for (const record of update.records || []) {
        // A retry, delayed poll, or duplicate response cannot replay an older
        // visual state over a later retained checkpoint.
        if (!Number.isInteger(record.sequence) || record.sequence <= liveProgressSequence) continue
        liveProgressSequence = record.sequence
        applyLiveProgress(record)
      }
      const measurementRunning = update.status === 'completed' && update.coordination_measurement_status === 'running'
      if (!measurementRunning && !['running', 'pause_requested', 'stop_requested', 'narrating'].includes(update.status)) {
        const finalRun = await request(`/api/runs/${encodeURIComponent(runId)}`)
        liveActivity = null
        liveProjection = null
        $('#live-evidence').hidden = true
        render(finalRun)
        await loadHistory()
        return
      }
      await new Promise((resolve) => window.setTimeout(resolve, 400))
    }
  } catch (error) {
    $('#run-status').textContent = error.message
  } finally {
    livePolling = false
  }
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
    ? current.timeline.findIndex((event) => event.event_id === moment.event_ids.at(-1))
    : moment.representative_event_index
  selectEvent(Math.max(0, eventIndex), moment.activation)
}

function selectEvent(index, momentActivation = null) {
  if (!current?.timeline?.length) return
  const priorSelectedEventIndex = selectedEventIndex
  selectedEventIndex = Math.max(0, Math.min(index, current.timeline.length - 1))
  if (selectedEventIndex !== priorSelectedEventIndex) {
    if (selectedBoundaryScope === 'moment') {
      selectedBoundaryActivities = null
      boundaryActivityRequestSerial += 1
    }
  }
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

  const selectedIsBoundary = (current?.boundaries || []).some((boundary) => boundary.id === selectedPerson)
  if (selectedIsBoundary) showTraceInPlace(selectedPerson)
  else if (selectedPerson) showTraceInPlace(selectedPerson)
  else if (event.person) showTraceInPlace(event.person)
  if (selectedGraphView === 'trajectory') renderTrajectoryInspector(event)
}

function renderStepAccount(event) {
  const narrations = current.narration?.moments || current.narration?.turns || []
  const narration = narrations.find((moment) => moment.activation === event.activation)
  const trace = event.person && event.activation
    ? current.traces.find((entry) => entry.person === event.person && entry.activation === event.activation)
    : null
  const person = event.person?.replaceAll('_', ' ')
  const exactProcess = trace?.participant_kind && trace.participant_kind !== 'person'
  const title = {
    action_attempted:exactProcess ? 'An exact process emitted an action' : 'A person chose an action',
    mechanism_executed:'An exact mechanism evaluated it',
    effect_routed:'An effect moved along a declared route',
    observation_delivered:'Someone received an observation',
    state_committed:'The world state changed',
  }[event.kind] || event.kind.replaceAll('_', ' ')
  if (narration) {
    const momentNumber = narration.moment || narration.turn || narrations.indexOf(narration) + 1
    const participants = narration.participants || [narration.person || 'system']
    $('#step-account-title').textContent = `Moment ${momentNumber} · ${causalTime(narration, momentNumber)} · ${participants.map((item) => String(item).replaceAll('_', ' ')).join(' + ')}`
    const paragraphs = narration.detailed_paragraphs || []
    $('#step-account-body').innerHTML = paragraphs.length
      ? paragraphs.map((paragraph) => `<span>${html(paragraph.text)}</span>`).join('')
      : html(narration.concise_narrative || narration.narrative)
    const context = narration.evidence_context
    $('#step-account-source').textContent = context
      ? `Evidence supplied to the narrator · current exact events: ${(context.current_event_ids || []).join(', ')}; earlier narrated accounts: ${(context.prior_narrative_record_ids || []).join(', ') || 'none'}. This records what the narrator could use, not proof that the prose is entailed by it.`
      : paragraphs.length
        ? `Live LLM narrator · concise account grounded in ${(narration.concise_source_event_ids || narration.source_event_ids || []).join(', ')}; each detailed paragraph retains its own evidence citations.`
        : `Live LLM narrator · grounded in ${(narration.source_event_ids || []).join(', ')}. This older run retained only its concise account.`
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
  document.querySelectorAll('.detailed-narrative-moment').forEach((card) => {
    card.classList.toggle('active', card.dataset.activation === event.activation)
  })
}

function readableNarrative(text) {
  return String(text || '')
    .replace(
      /The exact workflow recorded meeting snapshot delivered\./gi,
      'The next meeting snapshot was delivered to the team.',
    )
    .replace(
      /The local liaison recorded relied_on for the local source\./gi,
      'The local liaison recorded that information from the local source influenced the decision.',
    )
    .replace(/\b[a-z0-9]+(?:_[a-z0-9]+)+\b/g, (identifier) => identifier.replaceAll('_', ' '))
}

function narrativeStoryMoments(moments) {
  const storyMoments = []
  let leadingMechanisms = []
  for (const moment of moments) {
    const isMechanism = (moment.participants || []).includes('exact_mechanisms')
    if (isMechanism) {
      if (storyMoments.length) storyMoments.at(-1).consequences.push(moment)
      else leadingMechanisms.push(moment)
      continue
    }
    storyMoments.push({moment, consequences:leadingMechanisms})
    leadingMechanisms = []
  }
  if (leadingMechanisms.length && storyMoments.length) {
    storyMoments.at(-1).consequences.push(...leadingMechanisms)
  }
  return storyMoments
}

function renderTurnNarratives() {
  const narration = current.narration || {}
  const container = $('#turn-narratives')
  const detailed = $('#detailed-narrative')
  const moments = narration.moments || narration.turns || []
  if (narration.status === 'completed' && moments.length) {
    const storyMoments = narrativeStoryMoments(moments)
    const readableMoments = storyMoments.length ? storyMoments : moments.map((moment) => ({moment, consequences:[]}))
    $('#narrative-count').textContent = `${readableMoments.length} story moment${readableMoments.length === 1 ? '' : 's'} · Detailed mode explains what each action changed.`
    container.innerHTML = readableMoments.map(({moment}) => {
      const momentNumber = moment.moment || moment.turn || moments.indexOf(moment) + 1
      const participants = moment.participants || [moment.person || 'system']
      return `
      <button class="turn-narrative" data-activation="${html(moment.activation)}">
        <p>${html(readableNarrative(moment.concise_narrative || moment.narrative))}</p>
        <small class="narrative-meta">${html(storyTime(moment, momentNumber))} · ${html(storyParticipants(participants))}</small>
      </button>`
    }).join('')
    detailed.innerHTML = readableMoments.map(({moment, consequences}, index) => {
      const momentNumber = moment.moment || moment.turn || index + 1
      const participants = moment.participants || [moment.person || 'system']
      const paragraphs = moment.detailed_paragraphs || []
      const context = moment.evidence_context
      const priorNarratives = (context?.prior_narrative_record_ids || []).map((recordId) =>
        `<button type="button" class="prior-narrative-link" data-narrative-record-id="${html(recordId)}">${html(recordId)}</button>`
      ).join(' · ')
      if (!paragraphs.length) {
        return `<article class="detailed-narrative-moment legacy" data-activation="${html(moment.activation)}">
          <p>${html(readableNarrative(moment.concise_narrative || moment.narrative))}</p>
          <small class="narrative-meta">${html(storyTime(moment, momentNumber))} · ${html(storyParticipants(participants))}</small>
          <small>Detailed account was not retained for this older run.</small>
        </article>`
      }
      const consequenceParagraphs = consequences.flatMap((consequence) => consequence.detailed_paragraphs || [])
      const exactEventIds = [...new Set([...paragraphs, ...consequenceParagraphs].flatMap((paragraph) => paragraph.source_event_ids || []))]
      return `<article class="detailed-narrative-moment" data-activation="${html(moment.activation)}">
        ${paragraphs.map((paragraph) => `<p>${html(readableNarrative(paragraph.text))}</p>`).join('')}
        ${consequenceParagraphs.length
          ? `<div class="causal-result"><strong>What changed next</strong>${consequenceParagraphs.map((paragraph) => `<p>${html(readableNarrative(paragraph.text))}</p>`).join('')}</div>`
          : ''}
        <small class="narrative-meta">${html(storyTime(moment, momentNumber))} · ${html(storyParticipants(participants))}</small>
        ${context
          ? `<details class="narrative-evidence"><summary>Show narrative evidence</summary><button type="button" class="evidence-context-button" data-activation="${html(moment.activation)}">Inspect this causal step</button><small>Current exact events: ${html((context.current_event_ids || []).join(' · '))} · earlier narrated accounts: ${priorNarratives || 'none'} · provenance, not proof of entailment</small></details>`
          : `<details class="narrative-evidence"><summary>Show ${html(exactEventIds.length)} exact event${exactEventIds.length === 1 ? '' : 's'}</summary><small>${html(exactEventIds.join(' · '))}</small></details>`}
      </article>`
    }).join('')
    document.querySelectorAll('.turn-narrative').forEach((button) => {
      button.onclick = () => {
        const index = causalMoments().findIndex((moment) => moment.activation === button.dataset.activation)
        if (index >= 0) selectMoment(index)
      }
    })
    document.querySelectorAll('.detailed-narrative-moment').forEach((article) => {
      article.onclick = () => {
        const index = causalMoments().findIndex((moment) => moment.activation === article.dataset.activation)
        if (index >= 0) selectMoment(index)
      }
    })
    document.querySelectorAll('.narrative-evidence').forEach((details) => {
      details.onclick = (event) => event.stopPropagation()
    })
    document.querySelectorAll('.evidence-context-button').forEach((button) => {
      button.onclick = (event) => {
        event.stopPropagation()
        const index = causalMoments().findIndex((moment) => moment.activation === button.dataset.activation)
        if (index >= 0) selectMoment(index)
      }
    })
    document.querySelectorAll('.prior-narrative-link').forEach((button) => {
      button.onclick = (event) => {
        event.stopPropagation()
        const prior = moments.find((moment) => moment.narrative_record_id === button.dataset.narrativeRecordId)
        const index = prior ? causalMoments().findIndex((moment) => moment.activation === prior.activation) : -1
        if (index >= 0) selectMoment(index)
      }
    })
    return
  }
  const reason = narration.reason || 'No causal-moment narration was retained for this run.'
  $('#narrative-count').textContent = ''
  container.innerHTML = `<p class="muted">${html(reason)}</p>`
  detailed.innerHTML = ''
}

function publicNodeState(node, key) {
  const retained = node?.state?.[key]
  return retained && typeof retained === 'object' && Object.prototype.hasOwnProperty.call(retained, 'value')
    ? retained.value
    : retained
}

function parsedRepresentation(node) {
  const content = publicNodeState(node, 'content')
  if (typeof content !== 'string') return null
  try {
    return JSON.parse(content)
  } catch {
    return null
  }
}

function scenarioDefinitionForRun(run) {
  if (scenarioCatalog[run.scenario]) return scenarioCatalog[run.scenario]
  const templateId = run.authoring?.template_id
  if (!templateId) return null
  const templateKey = templateId.replace(/_v\d+$/, '')
  return scenarioCatalog[templateKey] || null
}

function renderInitialSituation(run) {
  const scenario = scenarioDefinitionForRun(run)
  const arm = scenario?.arms?.find((item) => item.id === run.arm)
  const summary = scenario?.representation_summary || run.authoring?.description || run.authoring?.title
    || 'The retained run did not include a readable initial-situation summary.'
  const people = (run.nodes || []).filter((node) => node.kind === 'person')
  const roles = people.map((person) => ({
    label:person.label,
    description:String(person.description || '').replace(/\.$/, ''),
  }))
  const goal = (run.nodes || []).find((node) => node.kind === 'goal_record')
  const proposal = (run.nodes || []).map(parsedRepresentation).find((item) => item?.document_kind === 'deployment_proposal')
  const concerns = (run.nodes || []).map(parsedRepresentation).filter((item) => item?.document_kind === 'source_message' && item.claim)
  const decision = [
    proposal?.scope ? `The starting proposal is a ${String(proposal.scope).replaceAll('_', ' ')} deployment.` : '',
    goal?.description || '',
  ].filter(Boolean).join(' ')
  const condition = arm?.description
    ? `${arm.label || run.arm}: ${arm.description}`
    : run.arm
      ? `${String(run.arm).replaceAll('_', ' ')} condition`
      : ''
  $('#initial-situation').innerHTML = `
    <span class="eyebrow">Initial situation</span>
    <h3>The situation</h3>
    <p>${html(summary)}</p>
    ${decision ? `<p><strong>The decision:</strong> ${html(decision)}</p>` : ''}
    ${roles.length ? `<div class="initial-people"><strong>The people:</strong><ul>${roles.map((role) => `<li><strong>${html(role.label)}</strong> — ${html(role.description)}</li>`).join('')}</ul></div>` : ''}
    ${concerns.length ? `<p><strong>What may change the decision:</strong> ${html(concerns.map((item) => item.claim).join(' '))}</p>` : ''}
    ${condition ? `<p><strong>Starting condition:</strong> ${html(condition)}</p>` : ''}
  `
}

function readableMeasureValue(value) {
  if (value === null || value === undefined) return 'No retained value'
  if (typeof value === 'string') return value.replaceAll('_', ' ')
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2)
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (Array.isArray(value)) return `${value.length} retained item${value.length === 1 ? '' : 's'}`
  if (typeof value !== 'object') return String(value)
  if (Number.isFinite(value.count) && Number.isFinite(value.proportion)) {
    return `${value.count} (${Math.round(value.proportion * 100)}%)`
  }
  if (Number.isFinite(value.scenario_days)) return `${Number(value.scenario_days).toFixed(1)} scenario days`
  if (Number.isFinite(value.scenario_minutes)) return `${value.scenario_minutes} scenario minutes`
  const preferred = ['total', 'count', 'distinct_risks', 'final_open_count', 'message_count', 'meeting_cycles', 'external_action_attempts', 'edge_count', 'final_threshold']
  const parts = preferred
    .filter((key) => value[key] !== undefined)
    .map((key) => `${key.replaceAll('_', ' ')}: ${readableMeasureValue(value[key])}`)
  return parts.length ? parts.join(' · ') : `${Object.keys(value).filter((key) => !key.includes('event_id')).length} retained fields`
}

function measurementEvidenceButtons(eventIds = [], evidenceLabel = 'Review supplied evidence') {
  const unique = [...new Set(eventIds)]
  if (!unique.length) return '<p class="muted">No single event citation is retained for this value; its required event types remain in the exact trace.</p>'
  return `<details class="measurement-evidence"><summary>${html(evidenceLabel)} · ${unique.length} exact event${unique.length === 1 ? '' : 's'}</summary><div>${unique.slice(0, 12).map((eventId) => {
    const event = exactEvent(eventId)
    const label = event?.summary || event?.kind?.replaceAll('_', ' ') || eventId
    return `<button type="button" class="measurement-evidence-button" data-measure-event-id="${html(eventId)}">Show on map · ${html(label)}</button>`
  }).join('')}${unique.length > 12 ? `<small>${unique.length - 12} more cited exact events remain available in Advanced evidence.</small>` : ''}</div></details>`
}

function codedIndicatorQuestion(indicatorId, fallback) {
  return {
    conditional_trust_episode: 'Did trust become conditional?',
    precautionary_hedging_episode: 'Did participants hedge against risk?',
    relevance_classification: 'How directly did the concern matter?',
  }[indicatorId] || fallback
}

function exactMeasureCard(measure, compact = false) {
  return `<article class="exact-measure-card${compact ? ' compact' : ''}">
    <span class="provenance-badge exact">Recorded by the simulator</span>
    <h4>${html(measure.label)}</h4>
    <p class="measure-value">${html(readableMeasureValue(measure.value))}</p>
    ${compact ? '' : `<small>${html(measure.construct_name.replaceAll('_', ' '))} · ${html(measure.unit.replaceAll('_', ' '))}</small>
      ${measurementEvidenceButtons(measure.source_event_ids, measure.evidence_basis === 'embedded_citation' ? 'Review cited evidence' : 'Review exact events of the required types')}
      <details><summary>Retained value and limitation</summary><pre>${html(JSON.stringify(measure.value, null, 2))}</pre><p>${html((measure.limitations || []).join(' '))}</p></details>`}
  </article>`
}

function renderCoordinationMeasurement(run) {
  const section = $('#coordination-measurement-section')
  const readout = run.coordination_measurement_readout
  section.hidden = run.scenario !== 'coordination_decision' || Boolean(run.theory_analysis)
  if (section.hidden) return
  const status = readout?.status || 'not_measured'
  $('#coordination-measurement-headline').textContent = readout?.headline || 'This run has not been measured'
  $('#coordination-measurement-explanation').textContent = readout?.explanation || 'No retained assay is available.'
  $('#coordination-measurement-content').hidden = status !== 'available'
  $('#coordination-measurement-status').innerHTML = status === 'invalid'
    ? `<article class="measurement-state invalid"><strong>Analysis needs attention</strong><p>The completed simulation and its outcome are unchanged. ${html(readout?.error_type ? `Failure class: ${readout.error_type}.` : '')}</p></article>`
    : status === 'measuring'
      ? '<article class="measurement-state"><strong>Post-run analysis is finishing</strong><p>The simulation outcome is fixed. One model call is classifying only its retained evidence.</p></article>'
      : status === 'not_measured'
      ? '<article class="measurement-state"><strong>No post-run model call was made</strong><p>This is expected for a reference run. Its exact story, maps, outcome, and participant accounts remain available.</p></article>'
      : ''
  if (status !== 'available') return
  const exact = readout.exact_measures || []
  const exactById = new Map(exact.map((item) => [item.measure_id, item]))
  const snapshotIds = ['final_deployment_status', 'final_approved_scope', 'partners_retained', 'unresolved_risk_load', 'decision_latency']
  $('#measurement-snapshot').innerHTML = snapshotIds.map((measureId) => exactById.get(measureId)).filter(Boolean).map((item) => exactMeasureCard(item, true)).join('')
  $('#exact-measure-count').textContent = `· ${exact.length} exact trace values`
  $('#exact-measures').innerHTML = exact.map((item) => exactMeasureCard(item)).join('')
  $('#coded-indicators').innerHTML = (readout.coded_indicators || []).map((item) => `
    <article class="coded-indicator ${html(item.direction)}">
      <div><span class="provenance-badge coded">Model interpretation</span><span class="direction-badge">${html(item.direction.replaceAll('_', ' '))}</span></div>
      <h4>${html(codedIndicatorQuestion(item.indicator_id, item.label))}</h4>
      <p>${html(item.explanation)}</p>
      ${measurementEvidenceButtons(item.source_event_ids)}
      <details><summary>Interpretation limits and trace references</summary><p><strong>Formal measure:</strong> ${html(item.label)}</p><p>${html((item.limitations || []).join(' '))}</p><small>${html((item.source_trace_ids || []).join(' · '))}</small></details>
    </article>`).join('')
  $('#measurement-limitations').innerHTML = (readout.limitations || []).map((item) => `<li>${html(item)}</li>`).join('')
  const provenance = readout.coder_provenance
  $('#measurement-call-provenance').innerHTML = provenance ? `
    <strong>Model interpretation call</strong>
    <span>${html(provenance.model)} · ${html(provenance.reasoning_effort)} reasoning</span>
    <span>Per-call request budget $${Number(provenance.max_budget).toFixed(2)} · observed ${provenance.observed_cost === null ? 'cost unavailable' : `$${Number(provenance.observed_cost).toFixed(6)}`}</span>
    <small>${html(provenance.task)} · ${html(provenance.prompt_version)} · ${html(provenance.trace_id)}${provenance.cost_covers_all_attempts ? '' : ' · cost coverage incomplete'}</small>` : ''
  section.querySelectorAll('.measurement-evidence-button').forEach((button) => {
    button.onclick = () => {
      const index = current.timeline.findIndex((event) => event.event_id === button.dataset.measureEventId)
      if (index >= 0) selectEvent(index)
    }
  })
  applyButtonTooltips(section)
}

const theoryFindingLabels = {
  waltzman_final_deployment_status:'Final decision',
  waltzman_final_approved_scope:'Approved scope',
  waltzman_partners_retained:'Partners retained',
  waltzman_modeled_time_to_terminal:'Time to decision',
  waltzman_verification_requests:'Verification activity',
  waltzman_source_reliance_topology:'Information-source reliance',
  waltzman_intermediary_bypass:'Information that bypassed intermediaries',
  waltzman_risk_register_expansion:'Newly recorded risks',
  waltzman_action_threshold_change:'Changes to the decision threshold',
  waltzman_unresolved_risk_load:'Unresolved risk at the end',
  waltzman_decision_latency:'Final-decision processing time',
  waltzman_deliberation_load:'Deliberation load',
  waltzman_issue_reopening:'Issues reopened',
  waltzman_informal_alignment:'Informal alignment',
  waltzman_disengagement:'Partner disengagement',
  waltzman_authority_divergence_scope:'Authority divergence',
  levin_goal_progress:'Did this run satisfy the candidate goal?',
  levin_boundary_activity:'What crossed the group boundary',
  levin_collective_glue:'What connected the group',
  levin_error_correction:'Observed error correction',
  levin_persistence_adaptation:'Persistence and adaptation',
  levin_scale_scope:'Scope of the observation',
  levin_not_tested:'Collective capacities not tested',
}

function theoryFindingValue(finding) {
  const value = finding?.value
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return readableMeasureValue(value)
  }
  if (finding.finding_id === 'levin_goal_progress') {
    const status = String(value.terminal_status || 'No terminal status').replaceAll('_', ' ')
    return value.acceptable_outcome
      ? `Yes · ${status} was configured as a goal-satisfying outcome`
      : `No · the run ended with ${status}`
  }
  if (finding.finding_id === 'levin_boundary_activity') {
    return `${value.incoming_crossings || 0} incoming crossing${value.incoming_crossings === 1 ? '' : 's'}, ${value.outgoing_crossings || 0} outgoing crossing${value.outgoing_crossings === 1 ? '' : 's'}, and ${value.completed_coordination_episodes || 0} completed coordination episode${value.completed_coordination_episodes === 1 ? '' : 's'}`
  }
  if (finding.finding_id === 'levin_collective_glue') {
    return `${value.people || 0} people coordinated through ${value.connections || 0} configured connections, ${value.records || 0} records, and ${value.exact_mechanisms || 0} exact mechanisms`
  }
  if (finding.finding_id === 'levin_error_correction') {
    return value.correction_observed
      ? `${value.error_signal_events || 0} error signal event${value.error_signal_events === 1 ? '' : 's'} and ${value.correction_events || 0} correction event${value.correction_events === 1 ? '' : 's'} were observed`
      : 'No correction event was observed in this trajectory'
  }
  if (finding.finding_id === 'levin_persistence_adaptation') {
    return `${value.meeting_cycles || 0} meeting cycle${value.meeting_cycles === 1 ? '' : 's'} and ${value.adaptation_events || 0} recorded adaptation event${value.adaptation_events === 1 ? '' : 's'} led to ${String(value.terminal_status || 'no terminal status').replaceAll('_', ' ')}`
  }
  if (finding.finding_id === 'levin_scale_scope') {
    return `${value.spatial_places || 0} places, ${value.temporal_minutes || 0} modeled minutes, and ${value.state_revisions || 0} retained state revisions`
  }
  if (finding.finding_id === 'levin_not_tested') {
    return 'Robustness, controlled shock recovery, member replacement, and persuadability were not tested'
  }
  if (value.status === 'not_computed') return 'Not computed in a single run'
  return readableMeasureValue(value)
}

function theoryEvidenceButtons(refs = []) {
  const eventIds = refs
    .filter((ref) => String(ref).startsWith('event:'))
    .map((ref) => String(ref).slice('event:'.length))
  if (eventIds.length) return measurementEvidenceButtons(eventIds, 'Inspect supporting events')
  return '<small class="theory-config-evidence">Supported by the reviewed configuration, retained state, or run completion record. Exact records remain available in Advanced evidence.</small>'
}

function theoryFindingCard(finding, compact = false) {
  const method = finding.method_class === 'llm_coded'
    ? 'Model interpretation'
    : finding.method_class === 'calculated'
      ? 'Calculated from retained evidence'
      : 'Recorded by the simulator'
  const visibleMethod = compact
    ? finding.method_class === 'llm_coded' ? 'Model interpreted' : finding.method_class === 'calculated' ? 'Calculated' : 'Exact record'
    : method
  return `<article class="theory-finding${compact ? ' compact' : ''}">
    <span class="provenance-badge ${finding.method_class === 'llm_coded' ? 'coded' : 'exact'}">${html(visibleMethod)}</span>
    <h4>${html(theoryFindingLabels[finding.finding_id] || finding.construct_id?.replaceAll('_', ' ') || finding.finding_id)}</h4>
    <p>${html(theoryFindingValue(finding))}</p>
    ${compact ? '' : `${theoryEvidenceButtons(finding.evidence_refs)}
      <details><summary>Uncertainty and limitations</summary><p>${html(finding.uncertainty)}</p><ul>${(finding.limitations || []).map((item) => `<li>${html(item)}</li>`).join('')}</ul></details>`}
  </article>`
}

function renderTheoryModule(moduleId, selector, headlineIds) {
  const module = current.theory_analysis?.modules?.[moduleId]
  const container = $(selector)
  if (module?.status === 'not_selected') {
    container.innerHTML = '<article class="measurement-state"><strong>Not selected for this run</strong><p>This analysis was not part of the approved scenario configuration. The completed simulation and any other selected analysis remain available.</p></article>'
    return
  }
  if (!module || module.status !== 'available') {
    container.innerHTML = `<article class="measurement-state invalid"><strong>Analysis unavailable</strong><p>The completed simulation, narrative, maps, and other analysis remain valid. ${module?.error_type ? `This module failed retained validation (${html(module.error_type)}).` : 'No retained readout is available.'}</p></article>`
    return
  }
  const findings = module.readout?.findings || []
  const headline = headlineIds.map((id) => findings.find((item) => item.finding_id === id)).filter(Boolean)
  container.innerHTML = `
    <div class="theory-snapshot">${headline.map((item) => theoryFindingCard(item, true)).join('')}</div>
    <details class="theory-all-findings">
      <summary>Review all ${html(findings.length)} findings and their evidence</summary>
      <div>${findings.map((item) => theoryFindingCard(item)).join('')}</div>
    </details>
    <details class="theory-limitations">
      <summary>Limits of this analysis</summary>
      <ul>${(module.readout?.limitations || []).map((item) => `<li>${html(item)}</li>`).join('')}</ul>
    </details>`
  container.querySelectorAll('.measurement-evidence-button').forEach((button) => {
    button.onclick = () => {
      const index = current.timeline.findIndex((event) => event.event_id === button.dataset.measureEventId)
      if (index >= 0) selectEvent(index)
    }
  })
  applyButtonTooltips(container)
}

function renderTheoryAnalysis(run) {
  const section = $('#theory-analysis-section')
  section.hidden = !run.theory_analysis
  if (section.hidden) return
  renderTheoryModule(
    'decision_environment',
    '#decision-environment-content',
    [
      'waltzman_final_deployment_status',
      'waltzman_final_approved_scope',
      'waltzman_partners_retained',
      'waltzman_unresolved_risk_load',
      'waltzman_decision_latency',
    ],
  )
  renderTheoryModule(
    'collective_competence',
    '#collective-competence-content',
    [
      'levin_goal_progress',
      'levin_boundary_activity',
      'levin_error_correction',
      'levin_persistence_adaptation',
    ],
  )
}

function setNarrativeDetail(detail) {
  selectedNarrativeDetail = detail
  const concise = detail === 'concise'
  $('#narrative-concise').setAttribute('aria-pressed', String(concise))
  $('#narrative-detailed').setAttribute('aria-pressed', String(!concise))
  $('#turn-narratives').hidden = !concise
  $('#detailed-narrative').hidden = concise
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
    marker.title = `Moment ${index + 1}, ${causalTime(moment, index + 1)}: ${people}; ${causeSummary(causes)}${moment.silent ? ' (silent)' : ''}`
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
  selectedBoundaryActivities = null
  selectedBoundaryScope = 'full'
  boundaryActivityRequestSerial += 1
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
  } else if (current.authoring) {
    const authoredOption = [...$('#scenario').options].find(
      (option) => option.value === current.scenario,
    )
    if (!authoredOption) {
      const option = document.createElement('option')
      option.value = current.scenario
      option.textContent = `Authored · ${current.authoring.title || current.scenario.replaceAll('_', ' ')}`
      option.dataset.authoredRun = 'true'
      $('#scenario').append(option)
    }
    $('#scenario').value = current.scenario
    $('#arm').innerHTML = `<option value="${html(current.arm)}">${html(String(current.arm).replaceAll('_', ' '))}</option>`
    $('#scenario-title').textContent = current.authoring.title || 'Authored scenario'
    $('#scenario-description').textContent = current.authoring.description || ''
    $('#arm-help').textContent = 'This is the concrete condition retained by the approved authored scenario.'
  } else if (current.composite_assay) {
    $('#scenario-title').textContent = 'Collective capability stress test'
    $('#scenario-description').textContent = 'Five people must reach a valid deployment decision while concrete changes test member continuity, rerouting, feedback, and response to relevant outside information.'
    $('#arm').innerHTML = `<option value="${html(current.arm)}">${html(compositeRowPresentation[current.arm]?.label || String(current.arm).replaceAll('_', ' '))}</option>`
    $('#arm-help').textContent = compositeRowPresentation[current.arm]?.change || 'This is one retained row in the reviewed five-condition comparison.'
  }
  $('#result').hidden = false
  $('#result-summary-status').textContent = current.status === 'completed'
    ? 'Simulation complete'
    : String(current.status || 'Simulation').replaceAll('_', ' ')
  $('#narrative-section').hidden = false
  $('#map-section').hidden = false
  renderLifecycleControls(current)
  renderProjectionControls()
  renderGraph()
  $('#result-status').textContent = `${current.status} · ${String(current.scenario || '').replaceAll('_',' ')} · ${String(current.profile || '').replaceAll('_',' ')} · ${String(current.arm || '').replaceAll('_',' ')}`
  const costCoverage = current.cost_fully_observable === false
    ? 'known provider cost; one or more retry charges unavailable'
    : 'observed provider cost'
  $('#result-cost').textContent = `${current.model_calls} model calls (${current.agent_model_calls ?? current.model_calls} agent, ${current.narration_model_calls ?? 0} narrator, ${current.measurement_model_calls ?? 0} evidence coder) · $${Number(current.cost).toFixed(6)} ${costCoverage} · ${current.run_id}`
  const llm = current.llm_configuration
  const retainedBilling = retainedBillingMode(current, llm)
  $('#run-config-readout').innerHTML = llm ? `
    <strong>Effective live configuration</strong>
    <span>${html(llm.model)}</span>
    <span>${html(llm.agent_reasoning_effort)} agent reasoning · ${html(llm.narrator_reasoning_effort)} narrator reasoning</span>
    <span>${retainedBilling === 'subscription_included' ? 'ChatGPT Codex subscription included' : `$${(Number(llm.max_total_cost) + (current.scenario === 'coordination_decision' ? Number(runtimeConfig.coordination_measurement?.coder_per_call_ceiling || 0) : 0)).toFixed(2)} retained planning amount`} · $${Number(current.cost).toFixed(6)} ${html(costCoverage)}</span>
    <small>${html(String(llm.selection_basis).replaceAll('_',' '))} · llm_client ${html(llm.llm_client_revision)}</small>
  ` : `
    <strong>Reference execution</strong>
    <span>Fixed zero-call policies · $0 observed</span>
  `
  if (current.run_control) {
    const terminal = current.run_control.terminal_conditions?.map((item) => item.public_description).join(' ') || 'Compiled terminal condition.'
    $('#run-config-readout').innerHTML += `<span><strong>Run end:</strong> ${html(terminal)} Horizon: ${html(current.run_control.modeled_time_horizon?.logical_time ?? 'none')} modeled seconds.</span>`
  }
  if (current.completion) {
    $('#run-config-readout').innerHTML += `<span><strong>Ended:</strong> ${html(current.completion.public_summary)}</span>`
  }
  $('#story-headline').textContent = current.story.headline
  $('#story-summary').textContent = current.story.summary
  renderScaleControls()
  renderInitialSituation(current)
  renderTurnNarratives()
  renderCoordinationMeasurement(current)
  renderTheoryAnalysis(current)
  setNarrativeDetail(selectedNarrativeDetail)
  const participants = [...new Set(current.traces.map((entry) => entry.person))].map((person) => ({
    person,
    kind:current.traces.find((entry) => entry.person === person)?.participant_kind,
  }))
  const people = participants.filter((participant) => participant.kind === 'person')
  const processes = participants.filter((participant) => participant.kind !== 'person')
  const participantButton = ({person}) => `<button data-person="${html(person)}">${html(refLabel(person))}</button>`
  const compositeTabs = (current.boundaries || []).map((boundary) =>
    `<button data-person="${html(boundary.id)}" title="Show what entered, happened inside, and left this group">${html(boundary.label)}</button>`
  )
  const traceGroups = [
    ['People', people.map(participantButton)],
    ['Processes and sources', processes.map(participantButton)],
    ['Group views', compositeTabs],
  ].filter(([, buttons]) => buttons.length)
  $('#trace-tabs').innerHTML = traceGroups.map(([label, buttons]) => `
    <section class="trace-tab-group">
      <strong>${html(label)}</strong>
      <div class="tabs">${buttons.join('')}</div>
    </section>
  `).join('')
  $('#trace').style.minHeight = ''
  document.querySelectorAll('#trace-tabs button').forEach((button) => {
    button.onclick = () => showTraceInPlace(button.dataset.person)
  })
  const defaultParticipant = people.find(({person}) => person === 'mission_coordinator')?.person
    || people[0]?.person
    || (current.boundaries || [])[0]?.id
    || processes[0]?.person
  if (defaultParticipant) showTrace(defaultParticipant)
  else $('#trace').innerHTML = '<p class="muted">No completed participant traces were retained.</p>'
  renderTimeline(current)
  $('#raw').textContent = JSON.stringify(current, null, 2)
}

function retainedBillingMode(run, llm) {
  if (llm?.billing_mode) return llm.billing_mode
  const calls = [...(run.model_call_summaries || []), ...(run.narration?.calls || [])]
  if (calls.length && calls.every((call) => call.cost_source === 'subscription_included')) {
    return 'subscription_included'
  }
  return (runtimeConfig.live_options?.models || []).find(
    (choice) => choice.model === llm?.model
  )?.billing_mode
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
$('#narrative-concise').onclick = () => setNarrativeDetail('concise')
$('#narrative-detailed').onclick = () => setNarrativeDetail('detailed')
$('#history-tab').onclick = () => setWorkspaceView('history')
$('#readme-tab').onclick = () => setWorkspaceView('readme')
$('#run-composite-assay').onclick = async () => {
  const button = $('#run-composite-assay')
  button.disabled = true
  $('#assay-status').textContent = 'Running five fixed reference conditions and retaining their exact evidence…'
  try {
    const assay = await request('/api/composite-assays', {method:'POST'})
    compositeAssayCache.set(assay.assay_id, assay)
    await loadHistory()
    $('#assay-status').textContent = 'Comparison complete. Select a row to see what changed and step down to its exact run.'
    renderCompositeAssaySelection(assay.assay_id, assay.rows[0].row_id)
  } catch (error) {
    $('#assay-status').textContent = error.message
  } finally {
    button.disabled = false
  }
}
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
  renderScaleControls()
  renderProjectionControls()
  renderGraph()
}
$('#causal-layout').onclick = () => {
  if (!current) return
  selectedGraphView = 'causal'
  selectedNodeId = null
  selectedEdgeId = null
  renderScaleControls()
  renderProjectionControls()
  renderGraph()
}

$('#trajectory-layout').onclick = () => {
  selectedGraphView = 'trajectory'
  selectedNodeId = current?.timeline?.[selectedEventIndex]?.event_id || null
  selectedEdgeId = null
  renderScaleControls()
  renderProjectionControls()
  renderGraph()
}
$('#analytical-boundary').onchange = () => {
  if (selectedScale !== 'exact') selectedScale = $('#analytical-boundary').value
  renderScaleControls()
  if (selectedGraphView !== 'trajectory') renderGraph()
}
$('#analytical-scale-toggle').onclick = () => {
  if (selectedGraphView === 'trajectory') return
  const boundaryId = $('#analytical-boundary').value
  selectedScale = selectedScale === 'exact' ? boundaryId : 'exact'
  selectedNodeId = null
  selectedEdgeId = null
  renderScaleControls()
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
$('#authoring-model').onchange = () => configureAuthoringReasoningChoices()
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
  liveProgressSequence = 0
  liveProjection = null
  liveActivity = null
  $('#live-evidence').hidden = false
  $('#live-evidence-title').textContent = 'Live run started'
  $('#live-evidence-body').textContent = 'Waiting for the first retained causal update.'
  const pausable = ['service_desk', 'coordination_decision'].includes($('#scenario').value)
  $('#pause').hidden = !pausable
  $('#stop').hidden = !pausable
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
        ...($('#scenario').value === 'service_desk' ? {
          run_control:{modeled_time_horizon:Number($('#modeled-horizon').value)},
        } : {}),
        ...($('#live').checked ? {
          llm_options:{
            model:$('#model').value,
            agent_reasoning_effort:$('#reasoning').value,
            max_total_cost:Number($('#max-cost').value),
          },
        } : {}),
      }),
    })
    if (body.status === 'running' && $('#live').checked) {
      $('#result').hidden = false
      $('#narrative-section').hidden = true
      $('#result-status').textContent = `running · ${String(body.scenario || '').replaceAll('_',' ')}`
      $('#result-cost').textContent = 'Waiting for the first retained causal update…'
      renderLifecycleControls(body)
      void pollLiveRun(body.run_id)
    } else {
      render(body)
    }
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
    if (!$('#live').checked) {
      $('#pause').hidden = true
      $('#stop').hidden = true
    }
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

$('#stop').onclick = async () => {
  if (!activeRunId) return
  $('#stop').disabled = true
  try {
    await request(`/api/runs/${activeRunId}/stop`, {method:'POST'})
    $('#run-status').textContent = 'Stop requested; finishing this causal step…'
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
    if (['running', 'narrating'].includes(body.status) && current.execution === 'live') {
      activeRunId = body.run_id
      liveProgressSequence = Number.isInteger(body.progress_sequence) ? body.progress_sequence : 0
      liveProjection = null
      liveActivity = null
      current = {...current, ...body}
      $('#result').hidden = false
      $('#narrative-section').hidden = true
      $('#live-evidence').hidden = false
      const narrationOnly = body.status === 'narrating'
      $('#live-evidence-title').textContent = narrationOnly
        ? 'Writing the missing narrative'
        : 'Live run resumed'
      $('#live-evidence-body').textContent = narrationOnly
        ? 'The completed causal trace is unchanged; waiting for its readable account.'
        : 'Waiting for the next retained causal update.'
      $('#result-status').textContent = `${body.status} · ${String(body.scenario || '').replaceAll('_', ' ')}`
      $('#result-cost').textContent = narrationOnly
        ? 'Participant execution is complete; narrator calls are in progress…'
        : 'Waiting for the next retained causal update…'
      renderLifecycleControls(body)
      void pollLiveRun(body.run_id)
    } else {
      render(body)
      $('#run-status').textContent = 'Completed'
    }
    $('#resume').hidden = true
    await loadHistory()
  } catch (error) {
    $('#run-status').textContent = error.message
  } finally {
    $('#resume').disabled = false
  }
}

$('#authoring-load-coordination').onclick = async () => {
  const button = $('#authoring-load-coordination')
  button.disabled = true
  $('#authoring-status').textContent = 'Loading the reviewed typed example…'
  try {
    authoringDraft = await request('/api/authoring/reviewed-coordination-drafts', {
      method:'POST',
    })
    await loadAuthoringPreview()
    syncAuthoringUrl()
    renderAuthoring()
  } catch (error) {
    $('#authoring-status').textContent = error.message
  } finally {
    button.disabled = false
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
    activeRunId = run.run_id
    liveProgressSequence = 0
    liveProjection = null
    liveActivity = null
    current = {
      nodes: [], snapshots: {}, edges: [], boundaries: [], timeline: [], moments: [], traces: [],
      trajectory: {nodes: [], edges: []},
      ...authoringPreview,
      ...run,
    }
    selectedGraphView = current.world ? 'world' : 'causal'
    $('#map-section').hidden = false
    $('#result').hidden = false
    $('#narrative-section').hidden = true
    $('#result-status').textContent = 'running · approved authored scenario'
    $('#result-cost').textContent = 'Waiting for the first retained causal update…'
    $('#live-evidence').hidden = false
    $('#live-evidence-title').textContent = 'Live run started'
    $('#live-evidence-body').textContent = 'Waiting for the first retained causal update.'
    renderProjectionControls()
    renderGraph()
    void pollLiveRun(run.run_id)
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
    const assayId = search.get('assay')
    if (retainedId) await openRetained(retainedId)
    else if (draftId) await openAuthoringDraft(draftId)
    else if (assayId && compositeAssayCache.has(assayId)) {
      setWorkspaceView('history')
      renderCompositeAssaySelection(assayId, compositeAssayCache.get(assayId).rows[0].row_id)
    }
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
