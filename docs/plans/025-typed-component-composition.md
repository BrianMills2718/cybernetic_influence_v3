---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-07-31
updated: 2026-07-31
---

# Slice 25: Typed component composition

## Outcome

An analyst can author a bounded scenario from a reviewed library of people,
information carriers, places, connections, exact mechanisms, and schedules;
the compiler validates their composition, retains a human-readable composition
receipt, and runs it through the one existing causal runtime. The resulting
maps, narratives, pause/resume state, and theory evidence work without a
scenario-specific UI or a second runtime.

The first canonical proof is a scenario that combines more than one reviewed
component family, so it cannot be expressed honestly as a relabeled existing
single workflow template.

## Why this is the next architecture boundary

The current authoring language collects useful scenario facts, but its
`workflow.template_id` dispatch selects scenario-specific Python fixtures.
That limits the system to individually implemented templates. The causal core
already validates entities, interfaces, connections, mechanisms, information,
places, timing, and execution traces; Slice 25 moves the missing selection and
binding layer into typed, reviewed component contracts.

## Boundaries

- A component is a versioned, reviewed runtime capability with declared input
  slots, output slots, required entities, information/record surfaces,
  mechanism implementation IDs, timing fields, and fidelity limits.
- A composition selects component kinds and supplies only typed bindings and
  reviewed data. It never supplies Python, arbitrary predicates, interface
  implementations, model prompts, or an organization executor.
- The compiler—not an LLM—resolves IDs, interfaces, ownership, connection
  compatibility, timing, and implementation bindings. It fails with a retained
  diagnostic before a run when any declared seam is incompatible.
- Organizations remain execution-inert analytical boundaries. A composition
  may include a boundary but cannot turn one into a component executor.
- Existing authored templates remain readable and runnable while they migrate;
  no retained run is rewritten.

## Observability contract

Every approval and execution retains a `CompositionReceiptV1` containing:

1. schema/compiler version and digests;
2. selected component kinds and reviewed versions;
3. resolved slots, generated runtime IDs, interfaces, mechanisms, and timing;
4. deterministic validation checks, including failures and referent paths;
5. scenario/configuration/run identities; and
6. exact links from each receipt item to the configured map or retained event.

The receipt is visible in the normal review UI in concise form and in Advanced
evidence in full. Runtime failures retain the selected component/binding and
exact error surface; they never silently choose a template or fallback route.
LLM calls remain separately observable through `llm_client`; component
composition adds no hidden LLM call.

## Ordered packets

### 25A — Component registry and compiler receipt

**Status:** technically complete. The receipt is retained at approval/run time,
available from the preview API, and presented concisely in the authoring review.
Browser visual verification remains part of the next integrated UI pass because
this environment currently has no headless browser executable.

Implement a strict reviewed-component registry and the receipt contracts. Add
adapters for the existing resource-request and information-campaign mechanisms
without changing their behavior. Compile one manifest through the registry and
prove that incompatible slots, unknown component versions, duplicate runtime
IDs, and analytical-boundary executors fail before execution.

**Acceptance:** a compiled existing scenario exposes a receipt with every
selected reviewed component and resolved runtime seam; negative fixtures fail
loudly and retain the diagnostic. Existing run/replay tests remain green.

### 25B — First mixed-component scenario

**Status:** technically complete. The provider-free field-report composition
selects two people, information, a channel, two routes, and two exact
mechanisms; it executes/replays through the existing runtime and exposes a
semantic direct-edit form for bindings and timing. Conversational authoring of
registered composition choices remains 25C work.

Add one authored `component_composition_v1` scenario that combines reviewed
communication, recording, scheduling, and exact-gate components. It must have
people, information, a record, at least one place/route, a terminal condition,
and an analytical boundary. Reference execution, pause/resume, reopen,
narrative, three maps, and evidence-bundle creation must all work.

**Acceptance:** the scenario is authorable and directly editable without
Python, compiles and reopens through the one runtime, and one human can inspect
why each action/effect occurred through receipt-to-event step-down.

### 25C — Generic authoring and review surface

**State:** conditional on the 25B human-readable proof.

Teach the authoring conversation to choose only registered component kinds and
their typed fields. The UI presents a concise scenario description and a
composition summary before approval; Advanced evidence exposes receipt details.
No model call may invent components or executable behavior.

### 25D — Component-family expansion

**State:** deliberately deferred until a second materially different analyst
scenario exposes a real missing primitive.

Add a component family only when it supports a selected scenario that cannot be
represented with the registry. Candidate families include physical traversal,
authentication/authorization, device processes, delayed feedback, and coarse
stochastic external fields. Each is a reviewed exact or explicitly coarse
mechanism with a fidelity declaration—not an arbitrary code plugin.

## Verification and reset

Run focused unit/negative/replay checks per packet. Batch the slow full suite,
browser inspection, and any live LLM probe after the known packets are
integrated; inspect retained compiler/runtime traces before changing prompts or
models. No live spending is required for 25A or 25B.

Reset after two substantive packets or four hours without a human-visible
composition/review improvement, or immediately if the design requires arbitrary
generated mechanism code, a second runtime, or an uninspectable global rule.

## Non-goals

- a universal simulation DSL or arbitrary code execution;
- an LLM-generated game master or organization mind;
- empirical calibration, prediction, or automatic real-world timing;
- generalized perturbation authoring or live repeated experiments; and
- a separate observability dashboard disconnected from scenario review.
