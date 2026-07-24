---
doc_role: active_plan
authority: implementation_plan
status: active
created: 2026-07-23
updated: 2026-07-24
predecessor: 012-event-driven-purchase-payment.md
---

# Slice 13: Configurable, Explainable Runs

**Status: Implemented; deployed acceptance remains open.**

## Current implementation and acceptance state

The configurable-run vertical is implemented and deployed at simulator
`00ea2342a6c5e3125366e59820f1e49b12dec17c` with shared `llm_client`
`07b168ffc10ab28834d8571fdf48aa9b775d57bc`.

- Linux and Mac gates pass: mypy, 57 tests, production graph build, and launcher
  syntax.
- Terra is the only advertised route. Its exact current-revision participant
  and narrator observations are `routeobs1_a7a692e9a6893e15d36f30ab` and
  `routeobs1_8d61ca73ab6c08249e5cdf59`.
- The exact-revision deployed canary `run_feb8ed10258d` reached
  `closed_confirmed` across eight causal moments. Seven participant calls used
  Terra at medium reasoning and eight narrator calls used Terra at low
  reasoning for a fully observed `$0.103861875`.
- All 15 provider records completed through native structured output with zero
  retries, warnings, or validation errors. Each narrated moment cites only its
  retained moment events or, for the one silent moment, its validated synthetic
  silence marker.
- DeepSeek V4 Flash remains unadvertised. Final-revision high-reasoning probes
  repeatedly returned empty structured content at both 384 and 512 output
  tokens.
- Current-revision rendered desktop verification is unproven because the
  available browser-automation paths hung from the SSH session. Mobile is not
  an acceptance target for this private PoC.

Two shared-client defects found by deployment certification were fixed and
tested: malformed received JSON now produces a complete validation-retry
lifecycle (`4e0780d`), and the public certification schema helper now exactly
matches the runtime provider schema (`07b168f`).

The remaining acceptance packet is one current-revision desktop browser pass.
A second model is not a blocker to honest single-route use; it becomes
selectable only after its own exact schema and complete canary evidence pass.

## UX correction: readable run flow

The current Service Desk review exposed a presentation defect, not a runtime
one: API metadata incorrectly said the scenario had no authored spatial
topology, and the screen put an audit-style moment inspector ahead of the
human-readable account. The PoC's analyst flow is now:

1. choose a scenario and see its bounded representation summary immediately;
2. inspect one map with spatial/causal projections and one in-place analytical
   scale control for execution-inert composites;
3. read the sequential LLM narrative and its outcome directly below the map;
4. inspect people, exact processes, and composites; then optionally open the
   causal-moment evidence inspector before advanced evidence.

The narrator contract favors one or two plain-English sentences over repeated
mechanism vocabulary and generic omission disclaimers. It remains constrained
to current-moment evidence and prior accounts. The Read me tab defines the
projection and composite terms without competing with the run flow.

## Route and Outcome

Request mode: plan and implement the approved documentation direction; runtime
implementation begins only after this packet is accepted as the sole active
plan.

Design depth: Standard. Execution profile: PoC on a private, single-operator
development host. Overlays: runtime state, LLM, UI, and the existing strict JSON
API. The change is reversible and does not alter shared world state outside
retained simulator runs.

For an analyst using an authored scenario, replace one fixed, unexplained live
LLM policy with a run they can configure and understand:

- choose an advertised model, agent reasoning level, and maximum total spend;
- see what those controls affect before dispatch;
- see scenario assumptions, omissions, and fidelity questions without
  mistaking them for editable world state;
- run the existing simulation;
- recover the effective configuration, spend, graph, narratives, and exact
  evidence from the retained run.

This is a representative vertical of the existing analyst workflow and a direct
prerequisite for conversational scenario authoring. If work stopped after this
slice, the operator would still have a more useful version of the current
simulator rather than an isolated settings component.

## Frozen Target and Critical Flow

Starting state: the deployed Service Desk baseline, live authorization enabled,
and at least one structured-output route that has passed the same simulator
agent/narrator schemas in the deployment environment.

Operator flow:

1. Select Service Desk and baseline.
2. Expand **Model, cost, and simulation assumptions**.
3. Choose one advertised model, `medium` agent reasoning, and a maximum total
   spend.
4. Read concise help for scenario condition, live execution, model, reasoning,
   budget, fidelity assumptions, map projection, analytical scale, causal
   moment, narrative, and exact evidence.
5. Review a preview that separates maximum participant calls, maximum narrator
   calls, per-call ceilings, and total authorized spend.
6. Play the live simulation.
7. Reopen it from Run history and confirm the effective model, reasoning,
   budget, call counts, and observed cost.

Human-reviewable target artifact: the existing run screen with one compact
advanced-settings panel, inline accessible help, a pre-run authorization
summary, and retained configuration evidence. The machine-readable target is
the `RunRequest`/retained-run configuration contract below.

Negative case: a model outside shared policy, an unavailable advertised route,
or a malformed/over-ceiling budget is rejected before any provider dispatch.
If an accepted low budget is exhausted during execution, the run stops
explicitly and retains the effective configuration, completed call summaries,
observed cost, and exact budget failure boundary.

Non-claims:

- configuration does not make the scenario assumptions editable;
- a model appearing in a registry is not by itself proof that its exact route
  and schemas currently work;
- budget enforcement cannot prevent an upstream provider from misreporting or
  belatedly reporting cost, though no further call may be authorized after the
  retained ceiling is reached;
- this slice does not create scenarios, calibrate fidelity, compare model
  quality, or establish analytical usefulness.

## Current and Target Delta

Design-time current:

- `RunRequest` selects only scenario, condition, cognition profile, and
  scripted/live execution;
- each scenario binds hard-coded model and reasoning constants;
- narration always binds the Service Desk model at low reasoning;
- participant and narrator budgets are separate hard-coded envelopes;
- `/api/config` reports one display model and aggregate conservative ceiling;
- the UI uses one prose paragraph for settings and assumptions;
- retained documents do not expose one normalized effective run-LLM
  configuration;
- the original design began with divergent shared-client revisions; both
  environments now use
  `07b168ffc10ab28834d8571fdf48aa9b775d57bc`.

Implemented target:

- one strict `RunLlmOptions` object is accepted by the API and threaded through
  every human binding and sequential narrator call;
- one server-owned catalog exposes only operator-configured choices that also
  satisfy the shared client's current allowlist, configured-credential,
  structured-output, and simulator-advertisement gates;
- one total authorization is enforced sequentially across participant and
  narrator calls;
- selected and effective options are retained from the initial running record
  through completion or failure;
- scenario explanation comes from API-owned metadata and canonical fidelity
  contracts, not duplicated JavaScript prose;
- the existing screen remains the only simulator workspace.

## Target Derivation

| Target behavior | Required source/state | Owning rule/operation | Contract/check |
|---|---|---|---|
| Select only eligible models | Shared registry and execution allowlist, deployment model choices, configured credential, structured-output requirement | API model-catalog projection | Positive advertised models; disallowed/unconfigured models rejected before run creation or dispatch |
| Apply one selected model | Effective run options | Scenario binding factories and narrator | Every retained agent/narrator call names the selected model; exact processes have zero calls |
| Apply agent reasoning | Effective run options and shared model reasoning policy | Native human binding factory and model catalog | Every human call snapshot records a model-supported selected effort; narrator uses the route-specific retained effort |
| Bound total authorization | Scenario call ceilings, observed cumulative cost, requested total | Run budget coordinator | No next call starts unless its full per-call ceiling fits inside remaining authorization |
| Explain configuration | API-owned field help and scenario fidelity metadata | Existing run screen | Mouse, touch, and keyboard users can reveal help without leaving the control |
| Preserve provenance | Requested/effective options, call evidence, observed cost | Run store document | Running, completed, and failed records retain configuration and cost |
| Preserve scripted mode | Existing zero-cost bindings | API and UI | Scripted run makes zero calls; live settings are disabled and omitted from its request |

## Boundaries and Owned Rules

### Shared `llm_client`

Owns canonical model identifiers, the global execution allowlist and hard model
bans, configured-credential availability, model capability metadata, provider
routing, reasoning normalization, structured decoding, per-call cost evidence,
and route-certification observations.

The simulator imports public shared-client APIs; it does not copy the model
matrix or weaken model policy. Before implementation evidence is interpreted,
the Mac editable dependency must advance to an approved clean revision
containing the current execution policy. That revision is an execution input and
must be recorded in canary evidence.

### Simulator configuration API

Owns which shared-client-eligible models this deployment chooses to advertise,
the server maximum total cost, scenario defaults and call ceilings, request
validation, default resolution, and configuration projection.

Deployment advertisement is an additional intersection, not a competing
capability database:

```text
advertised model
  = deployment-selected
  ∩ llm_client allowed
  ∩ configured credential available
  ∩ structured-output capable
  ∩ simulator-schema canary passed
```

The deployment-selected set is operator configuration. Treat Terra and
DeepSeek V4 Flash as candidates, but advertise each independently only after it
passes the exact simulator schemas on the Mac. Currently only Terra passes. Do
not expose an arbitrary model text box in this slice.

### Scenario binding factories

Own the construction of LLM-modeled human implementations from effective run
options. Persona, task, interfaces, memory, mechanisms, and initial state remain
scenario-authored. Exact state-machine bindings ignore LLM options and make no
model call.

### Run budget coordinator

Owns remaining authorization across the sequential agent phase and narration
phase. Existing scenario per-call ceilings remain fixed safety bounds:
participants currently authorize at most `$0.05` per call and narration at most
`$0.02` per moment.

Before each call, require:

```text
remaining_total_authorization >= applicable_per_call_ceiling
```

After each call, add provider-observed cost to the retained total. Participant
execution receives the configured total as its per-run ceiling. Narration
receives only the observed remainder after participants. Budget exhaustion is
explicit; narration never silently substitutes a programmatic summary for a
requested live account.

### Presentation and run store

Own the analyst-safe projection and durable requested/effective configuration.
On an execution failure, they retain the effective configuration, completed
model-call summaries available from the raised execution evidence, observed
cost, and error boundary. This slice does not add resumable causal checkpoints
or promise a full analyst graph for a partially executed run. Presentation does
not decide model eligibility or budget authorization.

### Existing web client

Owns control rendering, local form state, preview formatting, accessible
show/hide behavior, and submission of the typed request. It does not own model
policy, budget eligibility, fidelity truth, or cost accounting.

## Domain Model and Contracts

### `RunLlmOptions`

Strict Pydantic request value:

```text
model: nonempty canonical model identifier
agent_reasoning_effort: low | medium | high
max_total_cost: finite positive number
```

`RunRequest.llm_options` is optional for backward compatibility:

- omitted on a live request: resolve current server/scenario defaults;
- present on a live request: validate and use it;
- present on a scripted request: reject with 422 rather than imply it matters;
- unknown fields remain forbidden.

The server maximum is configuration-owned and defaults to the current
conservative Service Desk envelope. Scenario defaults may be lower, but no
request may exceed the server ceiling.

### `EffectiveRunLlmConfiguration`

Persist before dispatch:

```text
model
agent_reasoning_effort
narrator_reasoning_effort
max_total_cost
participant_per_call_ceiling
narrator_per_call_ceiling
maximum_participant_calls
maximum_narrator_calls
selection_basis
llm_client_revision
```

`selection_basis` distinguishes `server_default` from `operator_selected`.
The effective object is present on running, completed, and failed live records.
Scripted records retain `llm_configuration: null` and zero cost.
`llm_client_revision` uses the shared client's existing
`LLM_CLIENT_REVISION` deployment binding, falling back to its installed package
version only in local development.

### `ModelChoice`

API projection:

```text
model
label
default
agent_reasoning_efforts
default_agent_reasoning_effort
narrator_reasoning_effort
structured_output
availability_basis
certification_basis
```

`availability_basis` describes configured credentials, not health.
`certification_basis` names the exact retained simulator-schema canary or is not
advertised. Do not label a route “working,” “available,” or “certified” from
registry membership alone.

### Scenario explanation

Each scenario catalog item adds:

```text
representation_summary
assumptions[]
known_omissions[]
fidelity_questions[]
help
```

Mechanism-specific fidelity continues to come from `FidelityNote`. The catalog
may add scenario-level cognition and timing statements that have no mechanism
owner. Every explanation is read-only in this slice.

### API compatibility

`GET /api/config` adds the model catalog, live-option defaults/limits, scenario
explanation, and help text. Existing fields remain through this PoC slice.

`POST /api/runs` accepts optional `llm_options`. Existing callers that omit it
retain current behavior. Invalid eligibility or request shape returns 422 before
a provider call. Live-lock conflict remains 409 and unauthorized live execution
remains 403.

## UI Contract

- **User:** the analyst about to run and inspect one authored scenario.
- **Decision:** which bounded LLM execution policy to authorize and what the
  resulting simulation does and does not represent.
- **Hypothesis:** the operator can configure a run without confusing execution
  settings with world assumptions and can later identify exactly what ran.
- **Smallest surface:** extend the existing run card and its current details
  panel; do not create a settings screen.
- **Machine equivalent:** `GET /api/config`, `POST /api/runs`, and retained
  `GET /api/runs/{run_id}`.

Compact layout:

```text
Scenario          Condition          [ ] Live LLM agents

[Model, cost, and assumptions ▾]
  Model [?]          Agent reasoning [?]     Maximum spend [?]
  <choice>           <low|medium|high>        <$>

  Preview: participants ≤ N calls · narrator ≤ M calls
           per-call ceilings · total authorized spend

  What this scenario represents
  summary · assumptions · known omissions · fidelity questions

[Play simulation]
```

Help uses visible buttons with accessible names and inline/popover content that
works with mouse, keyboard, and touch; native hover-only `title` text is
insufficient. Map projection, analytical scale, causal moment, narrative, and
exact-evidence help may be concise adjacent disclosures rather than permanent
paragraphs.

States:

- configuration loading;
- scripted mode with live controls disabled and explicit `$0` explanation;
- live defaults;
- operator-modified live options;
- invalid/unavailable selection before dispatch;
- running with controls disabled;
- completed with requested/effective settings and observed spend;
- failed or budget-exhausted with retained partial evidence.

## Fixtures and Acceptance

Implement contract fixtures before UI wiring:

1. Positive explicit live options pass the same selected model/reasoning into
   every mocked human structured call and narration call; retained effective
   configuration matches.
2. Omitted live options reproduce the current default behavior.
3. Scripted execution remains zero-cost and rejects supplied live options.
4. Unknown, shared-policy-disallowed, deployment-unadvertised,
   credential-unconfigured, non-structured, blank, nonfinite, nonpositive, and
   over-ceiling inputs fail before dispatch.
5. A low accepted total stops before the next call whose ceiling cannot fit,
   retains completed call summaries and observed cost, and never starts
   narration without authorization.
6. A participant result above its per-call ceiling fails loudly with observed
   cost evidence.
7. Running, completed, and failed live records preserve the same effective
   configuration.
8. Scenario help contains nonempty assumptions, omissions, and fidelity
   questions; browser controls expose their help accessibly.

End-to-end acceptance:

- each advertised model completes one bounded Service Desk baseline on the
  exact deployed simulator and shared-client revisions;
- every agent and narrator trace records the selected model and expected
  reasoning; exact remediation makes no call;
- total observed cost is within the selected authorization;
- reopening either run shows the effective settings and exact evidence;
- a disallowed-model request and an underfunded continuation prove fail-closed
  behavior without an unauthorized next call;
- desktop flow passes normal input, keyboard access, screenshot
  inspection, zero horizontal overflow, console/network checks, and backend-log
  inspection;
- `make check` passes on Linux and the Mac.

Stakeholder review handoff:

```text
URL: private Mac simulator
Starting state: Service Desk baseline, Live enabled
Actions: expand settings → choose model/reasoning/budget → Play
Expected insight: distinguish run policy from scenario fidelity, then recover
  the effective settings from Run history
Known limitation: the scenario itself remains authored and fixed
```

## Failure, Compatibility, and Recovery

- Resolve and validate all defaults before creating a running record; malformed
  or ineligible requests spend nothing.
- Save effective configuration before the first call so provider/runtime
  failure remains interpretable.
- Propagate a typed failure evidence object containing completed call summaries,
  observed cost, and the precise budget or execution error into the failed run
  record. Do not manufacture a completed causal result from partial state.
- Never fall back to another model, reasoning level, scripted policy, or
  programmatic narration unless the operator explicitly selected such a policy;
  this slice exposes no fallback selector.
- Preserve the current one-live-run lock and recoverable run deletion.
- Keep existing no-options API callers compatible.
- A failed deployment restores the prior simulator commit and LaunchAgent
  configuration. Retained documents are additive and older documents continue
  to render when `llm_configuration` is absent.

## Dependency Resolution

Dependency: current shared-client execution policy on the Mac.

- **Blocks:** trustworthy model catalog construction and route advertisement.
- **Known contract:** the simulator consumes public `list_models`,
  `ALLOWED_EXECUTION_MODELS`, structured-output metadata, execution-policy
  validation, and `LLM_CLIENT_REVISION`.
- **Resolved state:** Linux and Mac use clean shared-client revision
  `07b168ffc10ab28834d8571fdf48aa9b775d57bc`.
- **Resolution:** advance the Mac editable checkout to one approved clean main
  revision, install it into the simulator environment, bind
  `LLM_CLIENT_REVISION`, and run the shared-client policy tests plus simulator
  checks before catalog wiring.
- **Readout:** both environments report the same approved revision and reject a
  globally disallowed model through the public execution policy.

Dependency: initial advertised route evidence.

- **Blocks:** showing any configured candidate as selectable.
- **Known contract:** route certification binds resolved model, upstream
  endpoint, execution mode, schema class/digest, client revision, and retained
  call evidence.
- **Instrument:** run one bounded native structured probe for the Service Desk
  human decision schema and one for the narrator schema through each candidate
  on the Mac.
- **Readout:** both exact schemas for one candidate produce parseable validated
  output with retained provider/attempt evidence; any failing candidate remains
  absent from the advertised set.
- **Promotion:** record the certification basis in `ModelChoice`, then exercise
  the complete simulator canary after UI/API integration.

## Implementation Order

### Packet A — typed configuration and budget seam

**Classification:** direct blocker/enabler inside this active vertical.

- Advance and bind the Mac shared-client dependency to an approved clean
  revision containing the current model execution policy.
- Add strict request, catalog, effective-configuration, and total-budget
  contracts.
- Thread model/reasoning through all scenario native-binding factories and
  narration.
- Retain configuration on success and failure.
- Add positive and negative API/runtime fixtures.

Do not stop or declare outcome progress here; return directly to Packet B.

### Packet B — existing-screen interaction and deployed observation

**Classification:** representative vertical.

- Extend the run card, preview, help disclosures, and retained settings readout.
- Verify API parity and all UI states.
- Certify Terra and DeepSeek V4 Flash as candidates, but advertise each only
  after its own exact-schema evidence passes.
- Run bounded live canaries, inspect full traces, deploy the exact revision, and
  conduct the stakeholder handoff.

The conversational-authoring packet becomes eligible only after this packet is
technically verified and the stakeholder has used it.

## YAGNI and Deferred Work

Do not add:

- an arbitrary model text field or simulator-owned provider capability matrix;
- separate narrator model/reasoning controls;
- fallback chains, automatic model selection, model benchmarking, or pricing
  synchronization;
- editable personas, memories, timing, mechanisms, fidelity notes, or
  assumptions;
- resumable partial-run checkpoints or a full causal graph synthesized from a
  failed mid-run state;
- a scenario DSL, compiler, chatbot, mechanism marketplace, or generated code;
- multi-user presets, accounts, billing, quotas, or production operations;
- a new frontend framework or settings page.

## Landscape and Authority Disposition

Landscape disposition: **linked**.

- [Roadmap](../ROADMAP.md) owns the approved two-increment order.
- `api.py`, scenario binding factories, `active_runtime`, `narration.py`, and
  the retained analyst document are the current simulator contracts.
- Shared `llm_client` public model registry, `ALLOWED_EXECUTION_MODELS`,
  execution policy, structured runtime, budget evidence, and route
  certification are reused rather than rebuilt.
- ADRs 004, 006, 010, and 011 continue to own evidence visibility, inert
  aggregates, temporal semantics, and representation depth.

No external provider-model database is consulted because the shared client is
the accepted execution-policy boundary. Current provider behavior remains a
live certification question, not a planning assumption.

## Review Gate and Next Action

Before implementation, perform one isolated non-independent review of this
packet against the roadmap, current request/API behavior, shared-client public
surface, and YAGNI boundary. Revise any contract that cannot be implemented
without an unstated model registry, budget semantics, or fidelity source.

Then implement Packet A and Packet B as one outcome loop. Do not start a
conversational scenario-authoring plan or another ontology/runtime substrate in
parallel.
