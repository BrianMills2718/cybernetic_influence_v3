---
doc_role: historical_evidence
authority: evidence
status: archived_completed
created: 2026-07-25
updated: 2026-07-25
---

# Slice 19: Live authored people

## Outcome

After reviewing and approving an authored scenario, an analyst can run its
concrete people as autonomous LLM-driven participants. Each person receives
only their reviewed descriptive profile, committed private memory, newly
delivered observations, and currently exposed output interfaces. Existing exact
mechanisms alone deliver information and commit world effects.

The canonical example is the information-campaign draft: the source decides
whether to publish its retained claim, the recipient activates only if the
configured route delivers it, and the recipient decides whether and how to
record an assessment. The retained trace exposes each orientation, proposed
action or silence, provider receipt, exact mechanism decision, and resulting
world state.

## Boundary

This slice changes person bindings and the approved-run control. It does not:

- generate mechanism code or new workflow templates;
- let a person read canonical world state, hidden provenance, another person's
  memory, or same-moment proposals;
- turn positions, capabilities, policies, or analytical boundaries into
  permissions or executors;
- claim that a profile field caused an action merely because it appeared in
  the person's context;
- add pause/resume to the small synchronous authored-run endpoint;
- infer persuasion, truth, virality, or geopolitical outcomes.

## Packet contract

| Boundary | Input | Output | Failure behavior |
|---|---|---|---|
| Reviewed person context | Approved `PersonDraft` | Declarative persona plus typed private-memory entries | Empty/invalid profile remains rejected by the existing draft contract |
| Live policy binding | Compiled active-system spec, selected model/reasoning, run trace prefix | Configuration-bound `NativeLlmActiveSystem` and matching spec identity | Provider/schema failure fails loudly with retained call evidence |
| Grounded action | Frozen `ActiveSystemInput` | Zero or more intents through exposed ports and permitted representation IDs | Invented ports or inaccessible representations are rejected before world mutation |
| Exact adjudication | Validated intent | Existing delayed delivery or exact state transition | Disabled routes dissipate; malformed mechanism payloads fail rather than silently guessing |
| Operator control | Approved draft plus `execution` and `llm_options` | Reference or live retained run | Live disabled, unavailable model, stale approval, concurrent live run, or invalid options return explicit errors |

## Person projection

The LLM persona is rendered from the person's label, position, disposition, and
the eight reviewed behavioral-profile categories. Every entry remains a direct
declarative statement. Authored memories and concrete retained information
needed at scenario start are separate private-memory entries.

Described capabilities and limitations are context only. The active-system
spec and current causal state determine which interfaces and representations
are actually available.

Template-specific payloads remain narrow exact contracts. In the information
campaign template, the full assessment rationale stays in the person's
orientation trace while the committed disposition is one of `accepted`,
`contested`, `uncertain`, or `deferred`.
Representation-only send interfaces require an empty payload; the selected
retained representation remains the sole authoritative content.

## Acceptance

Pass when:

- focused tests show the exact reviewed profile in a person's provider prompt;
- source and recipient/reviewer calls receive only their private memory,
  delivered observations, and owned action surfaces;
- a live two-person authored run completes through existing exact mechanisms,
  retains two provider calls, and replays to the same final state;
- an inaccessible representation or undeclared output is rejected before any
  corresponding world effect commits;
- the approved-draft UI offers explicit reference and live controls using the
  existing advertised model, reasoning, and hard-cost contract;
- one bounded OpenRouter canary is inspected at full trace depth;
- focused tests, the full regression suite, frontend checks, and production
  build pass.

## Stop conditions

Stop and report rather than adding a workaround if:

- the generic active-system schema cannot express a reviewed template's action;
- a provider requires canonical hidden state or procedural commands to complete
  the canonical example;
- the selected route cannot return the existing structured decision schema;
- exact mechanisms must be modified to make a preferred LLM decision succeed.

## Implementation evidence

- Focused provider fakes exercised both approved templates. They confirmed that
  exact reviewed profile statements enter the person prompt, a recipient can
  reference only the representation delivered to its observation port, and
  replay reconstructs the exact final state.
- Negative controls reject an undelivered source representation and reject
  extra content beside a representation-only publication action.
- DeepSeek V4 Flash with `none` reasoning passed the current exact
  `LlmDecision` and `CausalMomentNarration` schemas through OpenRouter.
  Observations `routeobs1_76e1763c917ae41ae9fc42a3` and
  `routeobs1_c0ac07f8684af54274adaa64` retain that route evidence.
- The first integrated canaries exposed and drove two contract repairs: a
  free-form paragraph could become an outcome status, and an unused action
  payload could duplicate retained claim content. The final contracts use four
  assessment dispositions and require empty payloads on representation-only
  sends.
- Final canary `run_5eb7eee74628` completed with two person calls and four
  sequential narrator calls for a total observed cost of `$0.001019117`. The
  source selected `claim_copy` with `{}`; the recipient received only
  `delivered_event_000003`, selected `contested`, and the exact mechanism
  committed `assessed_contested`.
- Full trace inspection covered all six calls in
  `~/projects/data/llm_observability.db`: exact prompts, profile context,
  memories, observations, action interfaces, parsed outputs, model route,
  reasoning, costs, exact events, prior-narrative chaining, and cited event
  IDs. No call used canonical hidden state or an analytical boundary as an
  executor.
- The rendered 1440×1100 authoring screen showed both run actions, the
  DeepSeek/no-reasoning/cost controls, two editable people, and the compiled
  graph before execution. The new live action has an accessible tooltip.
  Mobile verification was explicitly excluded by the operator.
- A forced provider-failure check confirmed that the authored endpoint retains
  the failed run, observed cost, and attached provider evidence for later
  inspection. The live-spend lock covers both participant execution and live
  narration.
- `101` repository tests passed. Full strict typing, JavaScript syntax,
  deployment-script syntax, diff checks, and the production React Flow build
  passed.
