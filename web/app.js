const $ = (selector) => document.querySelector(selector)
let current = null

async function loadConfig() {
  const config = await fetch('/api/config').then((response) => response.json())
  $('#cost-details').textContent =
    `${config.model} · ${config.reasoning_effort} reasoning · up to ${config.maximum_live_calls} calls · $${config.maximum_live_cost.toFixed(2)} cap. Scripted reference runs cost $0.`
  $('#live').disabled = !config.live_authorized
  if (!config.live_authorized) $('#live').parentElement.title = 'Start the server with CYBERNETIC_INFLUENCE_LIVE=1 to enable live agents.'
}

function showNode(node) {
  $('#inspector').innerHTML = `<span class="eyebrow">${node.kind}</span><h2>${node.label}</h2><p>${node.description}</p><pre>${JSON.stringify(node.state, null, 2)}</pre>`
}

function showTrace(person) {
  document.querySelectorAll('.tabs button').forEach((button) => button.classList.toggle('active', button.dataset.person === person))
  const entries = current.traces.filter((entry) => entry.person === person)
  $('#trace').innerHTML = entries.map((entry) => `
    <article class="trace-step">
      <strong>${entry.activation} · time ${entry.logical_time} · ${entry.status}</strong>
      <p>${entry.orientation || 'No private orientation was recorded.'}</p>
      <details><summary>${entry.observations.length} observations · ${entry.actions.length} actions</summary><pre>${JSON.stringify({observations:entry.observations,actions:entry.actions}, null, 2)}</pre></details>
    </article>`).join('')
}

function render(run) {
  current = run
  $('#result').hidden = false
  $('#result-status').textContent = `${run.status} · ${run.profile.replaceAll('_',' ')} · ${run.arm.replaceAll('_',' ')}`
  $('#result-cost').textContent = `${run.model_calls} model calls · $${run.cost.toFixed(6)}`
  $('#story-headline').textContent = run.story.headline
  $('#story-summary').textContent = run.story.summary
  $('#story-steps').innerHTML = run.story.steps.slice(0, 8).map((step) => `<li>${step}</li>`).join('')
  $('#routes').innerHTML = run.edges.map((edge) => `
    <span class="route ${edge.enabled ? '' : 'disabled'}">
      <strong>${edge.source.replaceAll('_',' ')}</strong> → ${edge.target.replaceAll('_',' ')}
    </span>`).join('')
  $('#graph').innerHTML = ''
  run.nodes.forEach((node) => {
    const button = document.createElement('button')
    button.className = 'node'
    button.dataset.kind = node.kind
    button.innerHTML = `<span>${node.kind}</span><strong>${node.label}</strong><small>${node.description}</small>`
    button.onclick = () => showNode(node)
    $('#graph').append(button)
  })
  const people = [...new Set(run.traces.map((entry) => entry.person))]
  $('#trace-tabs').innerHTML = people.map((person) => `<button data-person="${person}">${person.replaceAll('_',' ')}</button>`).join('')
  document.querySelectorAll('#trace-tabs button').forEach((button) => button.onclick = () => showTrace(button.dataset.person))
  if (people.length) showTrace(people[0])
  $('#raw').textContent = JSON.stringify(run, null, 2)
  $('#result').scrollIntoView({behavior:'smooth', block:'start'})
}

$('#run').onclick = async () => {
  $('#run').disabled = true
  $('#run-status').textContent = 'Running…'
  try {
    const response = await fetch('/api/runs', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        cognition_profile:$('#profile').value,
        arm_id:$('#arm').value,
        execution:$('#live').checked ? 'live' : 'scripted',
      }),
    })
    const body = await response.json()
    if (!response.ok) throw new Error(body.detail || `Run failed (${response.status})`)
    render(body)
    $('#run-status').textContent = 'Completed'
  } catch (error) {
    $('#run-status').textContent = error.message
  } finally {
    $('#run').disabled = false
  }
}

loadConfig().catch((error) => { $('#run-status').textContent = error.message })
