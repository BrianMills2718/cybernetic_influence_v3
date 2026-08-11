---
doc_role: external_review_dossier
authority: synthesis
status: current_snapshot
created: 2026-08-11
source_revision: a57cf1bc74965a31164c132fbd9868055bcad1e0
---

# Ontology and Execution Machinery of Cybernetic Influence V3

## A self-contained technical dossier for reviewing gaps in a general-purpose sociotechnical simulator

## Abstract

Cybernetic Influence V3 is an experimental, traceable simulator for bounded
sociotechnical decision environments. Its central architectural choice is to
separate what exists, what can act, what can be attempted, what is permitted,
what physically or computationally succeeds, what information is represented,
and what an analyst later infers. A person, vehicle, document, software service,
resource, organization, and message are therefore not treated as interchangeable
“agents.” Instead, a canonical causal world contains persistent entities,
typed interfaces, routed effects, exact mechanisms, information carriers,
representations, observations, places, and explicit state. Optional active-system
implementations—currently scripted policies or LLM policies—give selected
entities autonomous behavior. Exact mechanisms, not LLM narration, validate and
commit world changes. Organizations are execution-inert analytical boundaries
over concrete components rather than additional minds or executors.

This document explains that ontology, the machinery that uses it, the path from
conversational authoring to retained evidence, and the places where the current
implementation is narrower than the intended general-purpose product. It is
written for an external reviewer with no prior knowledge of the project. Its
purpose is not to defend the current architecture. Its purpose is to make the
architecture legible enough to challenge.

The most important conclusion is that the project has two different kinds of
gap:

1. **Ontology and runtime gaps:** concepts or dynamics the canonical substrate
   cannot yet represent or execute cleanly.
2. **Adoption gaps:** capabilities that exist in the substrate but are bypassed,
   simplified, or reimplemented by scenario-specific authoring, fixtures, or UI.

Conflating those categories would lead to the wrong redesign. Adding a new
ontology primitive will not repair a scenario that simply bypasses an existing
one. Conversely, forcing every phenomenon into the existing primitives could
produce false precision and an unmanageable universal ontology.

---

## 1. Review question, scope, and epistemic status

### 1.1 Question for the external reviewer

The principal question is:

> Does the current combination of typed causal islands, open-ended semantic
> context, bounded autonomous processes, exact world mechanisms, and derived
> analytical views provide a sound foundation for a general-purpose
> sociotechnical simulator? Which important phenomena are impossible or
> misleading under the present ontology, and which apparent gaps are instead
> failures of composition, adoption, cognition, authoring, or presentation?

The reviewer should especially assess whether the architecture can support
exploratory wargaming and mechanism discovery in complex systems without
pretending to predict those systems. The target is conditional insight—“under
these assumptions and interaction rules, this pattern or failure mode becomes
possible”—rather than point prediction of human or institutional behavior.

### 1.2 Repository and time boundary

This dossier describes the repository at Git revision
`a57cf1bc74965a31164c132fbd9868055bcad1e0` on 2026-08-11. It distinguishes:

- accepted architecture decisions;
- behavior directly implemented in typed contracts and executable code;
- behavior demonstrated in focused tests or retained examples;
- accepted but only partially adopted direction; and
- unresolved generalization questions.

Historical plans are not treated as current implementation merely because they
exist. The current goal, roadmap, accepted architectural decision records,
runtime contracts, and tests take precedence over archived aspirations.

### 1.3 What this document does not claim

This paper does not claim:

- predictive validity for people, organizations, institutions, or crises;
- empirical validation of Waltzman-inspired trust, risk, or coordination
  measures;
- that an LLM persona is a faithful human model;
- that a detailed simulation is automatically more faithful than a coarse one;
- that an analytical boundary is a real unified mind;
- that typed state is inherently superior to natural-language state; or
- that the current runtime should necessarily remain the product foundation.

The selected architecture question involving Concordia remains unresolved in
the canonical roadmap. This dossier describes Cybernetic Influence V3 well
enough for that and broader foundation questions to be reviewed; it does not
silently settle them.

---

## 2. Product intent

The current product goal is a general executable laboratory for bounded
sociotechnical decision environments. An analyst should eventually be able to:

1. describe a situation conversationally;
2. review and edit the resulting simulation configuration;
3. execute autonomous LLM and non-LLM processes at appropriate timescales;
4. inspect configured pathways, spatial topology, realized causality, retained
   evidence, and narrative explanations;
5. inspect a system at more than one analytical scale without inventing a
   higher-level executor;
6. compare controlled environments, interventions, and perturbations; and
7. derive theory-specific readouts from evidence without inserting those
   readouts into the simulated world as hidden causes.

Waltzman's *From Minds to Coordination* is the first substantial theory module
over this workflow, not the definition of the product. Its motivating insight
is that heterogeneous local interactions can produce aligned directional
changes in a collective decision environment without a uniform message or
shared false belief. That motivates the simulator's emphasis on local
information paths, person-local interpretation, dependencies, timing, and
macro-level effects. The simulator should also be capable of representing
traditional homogeneous influence, ordinary disagreement, legitimate external
events, resource failures, organizational friction, and stabilizing responses.

The project is also influenced by multiscale or composite-agency questions:
when is a higher-level system description useful, and when does it wrongly
reify an organization as another agent? The current answer is observational:
model concrete components and mechanisms, then construct reversible aggregate
views. Stronger claims about higher-scale agency require perturbation evidence,
not a node labeled “organization.”

Canonical product boundaries are recorded in the [current goal](../GOAL.md),
[roadmap](../ROADMAP.md), and [foundation decision plan](../plans/026-concordia-foundation-research.md).

---

## 3. The governing ontological commitments

The simulator's ontology is best understood through commitments rather than
through a flat class list.

### 3.1 One authoritative world state

Canonical facts live in one validated `CausalState`. An agent prompt, narrator,
graph, and analysis are projections or consumers of that state and its event
history. They are not independent mutable worlds. This is intended to prevent a
fact from being true in prose, false in a mechanism, and unknowably different
in retained evidence.

### 3.2 Existence does not imply agency

`EntityState` records that a persistent referent exists. Its `entity_kind` is an
open semantic identifier; it does not grant cognition or action. A person,
truck, generator, record, court filing, source process, software service, or
resource may all be entities. An entity becomes an autonomous scheduled process
only when separately associated with an `ActiveSystemSpec` and trusted
implementation binding.

This is how the model handles a car that can be used but does not act by itself:

- the car is an entity with state and possibly a placement;
- ports and mechanisms represent operations involving it;
- a person or controller may attempt actions through owned interfaces;
- exact mechanisms determine whether the car moves or has an effect; and
- the car receives its own active-system binding only if the scenario actually
  represents autonomous onboard behavior.

### 3.3 Attempt, capability, authorization, and success are distinct

An output interface is an available path through which an actor can propose an
attempt. It is not proof of legal permission, physical capability, or success.
Policy information, authorization decisions, equipment state, topology, and
mechanism outcomes can separately block the attempt.

The physical-access example deliberately separates:

```text
badge presentation
    -> authentication
    -> policy authorization
    -> latch operation
    -> physical threshold crossing
    -> observed entry result
```

A valid badge can fail authorization; authorization can coexist with a jammed
latch; and neither condition changes a person's placement unless the crossing
mechanism commits a valid spatial transition. See the executable
[physical-access scenario](../../src/cybernetic_influence/scenarios/physical_access.py)
and its [negative and replay tests](../../tests/test_causal_runtime.py).

### 3.4 Information is a material or technical lineage, not a free-floating fact

The model separates:

- a **carrier**, which can retain an encoded pattern;
- a **representation**, which is a particular encoded content revision on a
  carrier;
- an **actual source**, retained as protected provenance;
- an **apparent source**, visible to the recipient and possibly wrong;
- an **observation**, which records that an apparent content surface reached a
  particular entity through a particular input interface; and
- a person's private interpretation or memory of that observation.

Delivery does not make content true. Receiving a message does not guarantee
attention, belief, agreement, or action. Copying information creates a new
representation with declared parent lineage rather than teleporting a single
abstract message.

### 3.5 Mechanisms own declared world transitions

An exact mechanism is an executable transition authority with an explicit
contract:

- typed input and output ports;
- facts, representations, placements, and spatial links it may read;
- facts, placements, and carriers it may write;
- observation targets it may notify;
- physical or computational substrates it uses;
- registered invariant checks; and
- a fidelity declaration.

The handler receives defensive copies of only its declared read surface. Its
proposed updates, emitted effects, representations, observations, and movements
are validated against the declared write surface and independent invariant
checkers before commit. The mechanism cannot search the entire world for a
convenient explanation or state value.

### 3.6 Space, routing, and permission are separate

Places form an acyclic containment hierarchy. A placement records an entity's
current immediate place. A spatial link records topological adjacency and its
physical substrate. None of these imply traversability, visibility,
communication, permission, or successful movement. Connections and ports own
information or effect routing; mechanisms own movement and authorization.

This separation is binding under [ADR 008](../adr/008-separate-spatial-topology-from-routing-and-permission.md).

### 3.7 Organizations are analytical boundaries, not additional executors

The canonical runtime has no ontologically fundamental `OrganizationAgent`.
An `AnalyticalBoundary` names a reversible grouping of concrete entities,
mechanisms, interfaces, carriers, or representations. It has `executor=false`,
cannot own an action interface, and never enters the active-system registry.

At the analytical scale, an effect crossing into the selected membership can be
described as a boundary input; an effect crossing out can be described as a
boundary output; internal routed effects can be described as coordination. Each
aggregate event must step down to exact members, ports, effects, and causal
parents. The boundary does not thereby become the source of the action.

This is a deliberately sociotechnical view of institutions. Institutional
effects should arise from concrete dependencies: people, artifacts, software,
records, resource control, sanctions, routines, and repeated reliance. The
current runtime does not yet infer institutions from those patterns; it only
supports authored analytical boundaries over them. [ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md)
defines this boundary.

### 3.8 Analysis is not world state

Aggregate trust structure, perceived risk, coordination readiness, and
candidate composite agency are derived from retained evidence after or during
execution. They do not execute, route effects, or enter every person's prompt.
A person can have a local trust judgment or perceived risk in memory; the world
cannot contain a hidden global `trust_fragmentation=0.82` that manufactures the
desired result.

[ADR 012](../adr/012-decision-environment-measures-are-derived.md) records this
separation.

### 3.9 Representation depth is question-relative

The intended product may use exact implementations, LLM policies, stochastic
models, learned surrogates, authored external processes, or replayed traces
behind compatible typed boundaries. These are implementation strategies, not
new species of actor. A coarse market process can be useful for a scenario that
only needs prices, but it cannot support claims about omitted traders or order
flow.

Every nontrivial subsystem should declare what it preserves, what it omits,
its inputs, outputs, timing, provenance, uncertainty, and invalid questions.
The current `FidelityNote` is the implemented minimum. A general registry and
runtime for all representation strategies is accepted direction but not yet
implemented; see [ADR 011](../adr/011-declared-representation-depth.md).

---

## 4. The canonical runtime ontology

The canonical world is not fundamentally a generic property graph. It is a
strict Pydantic state contract containing several typed record collections.
Graph views are derived later.

### 4.1 Persistent state records

| Record | Function | Important semantics |
|---|---|---|
| `FactState` | One addressable attribute value | Has `public`, `analyst`, or `mechanism` visibility. |
| `EntityState` | One persistent referent | `entity_kind` is open-ended and does not assert agency. |
| `ContainerState` | A typed broadcast-routing locus | Membership is not authoritative spatial location. |
| `PlaceState` | One spatial locus | Places form an acyclic parent hierarchy. |
| `PlacementState` | Current immediate place of an entity | Movement requires a validated mechanism transition. |
| `SpatialLinkState` | Undirected topological adjacency | Existence does not imply traversability. |
| `PortState` | Typed input or output interface | Owned by an entity or mechanism; has one `effect_type`. |
| `ConnectionState` | Directed route from output port to input port | Requires matching effect types; may have delay and enabled state. |
| `MechanismSpec` | Declared exact transition authority | Restricts reads, writes, outputs, substrates, and observations. |
| `CarrierState` | Stateful information-holding surface | Has an owner, medium, locator, revision, and visibility. |
| `RepresentationToken` | Content at one carrier revision | Retains hash, actual source, encoding, parents, and visibility. |
| `ObservationRecord` | Delivered agent-visible surface | Separates apparent content/source from hidden causal lineage. |
| `AnalyticalBoundary` | Nonexecuting analyst grouping | Exists on `CausalScenario`, not in active world state. |

The source contract is [causal_core/models.py](../../src/cybernetic_influence/causal_core/models.py).
Unknown fields and implicit coercions are rejected at durable boundaries.
Cross-references, disjoint identities, place trees, port ownership, effect-type
compatibility, mechanism authority, information lineage, inbox membership, and
checkpoint digests are validated as a whole.

### 4.2 Agency records are deliberately separate

`ActiveSystemSpec` associates one scheduled process with one entity and one
implementation identity. It declares:

- observation ports the process can perceive;
- output ports through which it can attempt actions;
- representation tokens available on each output;
- exact world conditions that can withdraw an interface;
- initial private state;
- an optional next scheduled update; and
- limits on observations, actions, state size, and provider spend.

The active-system implementation is replaceable behind a small protocol. The
repository currently provides:

- `ScriptedActiveSystem`, a deterministic or conventional controller; and
- `NativeLlmActiveSystem`, a structured LLM policy using the shared
  `llm_client`.

An implementation identity is bound to nonsecret policy configuration,
including persona, model, reasoning effort, prompt template, response schema,
memory bound, and token bound. A retained run can therefore detect configuration
drift rather than treating every invocation of an implementation family as
identical.

The relevant contracts are
[active_runtime/models.py](../../src/cybernetic_influence/active_runtime/models.py),
[active_runtime/protocol.py](../../src/cybernetic_influence/active_runtime/protocol.py),
and [active_runtime/llm.py](../../src/cybernetic_influence/active_runtime/llm.py).

### 4.3 Attempt and transition records

The execution ontology distinguishes:

| Record | Meaning |
|---|---|
| `ActionIntent` | An active system's proposed output port, optional representation, payload, and public summary. |
| `ActionAttempt` | Engine-materialized attempt with canonical actor, action ID, and time. |
| `EffectEnvelope` | Typed effect emitted from an output port and queued for routing. |
| `EffectDraft` | A mechanism's proposed downstream effect. |
| `FactUpdate` | A proposed write to one declared fact. |
| `PlacementDraft` | A proposed movement across one declared spatial link. |
| `RepresentationDraft` | A proposed information copy on a writable carrier. |
| `ObservationDraft` | A proposed delivery to a declared target. |
| `MechanismOutcome` | The complete proposed result of a mechanism execution. |
| `StatePatch` | Replayable before/after state changes committed at one revision. |
| `CausalEvent` | Typed event with exact causal parents and relevant identifiers. |

The event vocabulary currently includes run start/completion, action attempt,
effect emission, effect routing or dissipation, mechanism execution, state
commit, and observation delivery. A non-root event requires one or more causal
parents. Event sequence supplies replay order; explicit parent links—not
adjacent timestamps or narrative prose—supply causal ancestry.

### 4.4 Time

The architecture distinguishes:

- scenario time in a scenario-declared integer unit;
- causal moments that batch processes due from the same frozen pre-moment
  state;
- exact events within a moment;
- future active-system wakes; and
- delayed effects and deliveries.

Processes can be activated by scenario start, observation delivery, internal
wake, or manual scheduling. The scheduler jumps to the earliest due work rather
than invoking every process on every tick. Processes due together decide from
the same frozen checkpoint and cannot observe one another's same-moment
proposals.

New positive-duration scenarios require every causal descendant world event to
occur later than its parent. Some older workflows retain legacy zero-time
cascades, so positive causal duration is an accepted and partly implemented
contract rather than a universal property of every retained scenario. See
[ADR 010](../adr/010-autonomous-multirate-process-time.md).

---

## 5. Relations, directionality, and arity

### 5.1 There are several relation vocabularies

It is important not to confuse three layers:

1. **Runtime relations**, encoded in typed records such as ports,
   connections, placements, spatial links, mechanism read/write surfaces,
   representation parents, and boundary membership.
2. **Graph projection relations**, derived for analyst selection and display.
3. **Walkthrough language**, simplified labels such as Person, Thing, Message,
   Process, `operates`, or `requires_route`.

The public guided example currently uses four friendly node categories:
`person`, `thing`, `information`, and `mechanism`. It displays the mechanism
category as “Process,” creating an avoidable terminology mismatch. The guide is
hard-coded explanatory data in
[public/waltzman/app.js](../../public/waltzman/app.js); it is not itself a
compiled canonical `CausalScenario`.

The canonical analyst graph permits these projected node kinds:

- `entity`
- `container`
- `place`
- `port`
- `mechanism`
- `carrier`
- `representation`
- `boundary`

Its projected edge kinds are:

- `owns`
- `contains`
- `connects`
- `binds_input`
- `declares_output`
- `uses_substrate`
- `reads_representation`
- `carries`
- `derived_from`
- `located_in`
- `within`
- `spatially_connected`
- `derived_member`

These contracts live in
[causal_core/projection.py](../../src/cybernetic_influence/causal_core/projection.py).

### 5.2 Directionality

Every serialized graph edge has source and target fields, but not every
relation has the same directional semantics.

- A `ConnectionState` is genuinely directed from one output port to one input
  port.
- Effect emission, routing, observation delivery, representation derivation,
  and causal-parent links are directed.
- `within`, `located_in`, ownership, and boundary membership are oriented for
  interpretation but are not necessarily causal-flow arrows.
- A `SpatialLinkState` is semantically undirected. Its graph projection stores
  endpoint A and endpoint B but explicitly sets `directed=false` and states
  that adjacency does not imply traversability.

The current visual graph does not communicate these distinctions as clearly as
the contracts do. A general-purpose UI should not use one undifferentiated line
style for directed causal possibility, undirected adjacency, containment,
ownership, and analytical grouping.

Configured direction also does not prove realized flow. A connection is a
possible route. A retained `effect_routed` event proves that a particular effect
actually used it. A later mechanism execution or state commit proves what
happened next.

### 5.3 N-ary relations

There is no generic first-class hyperedge or arbitrary n-ary relation object.
The runtime uses three patterns instead:

1. **Reified causal relation:** a mechanism is a node with many input and output
   bindings. For example, release, routing, transport, and receipt can all feed
   a delivery-readiness mechanism. The mechanism owns the joint rule, state,
   timing, evidence, and failure behavior.
2. **Membership collection:** a container or analytical boundary stores many
   members, projected as several binary membership edges.
3. **Multi-valued attribute:** facts such as commitments, dependency IDs, or
   parent representation IDs may contain lists, but those entries are not
   automatically first-class selectable relations.

Mechanism reification is useful for causal n-ary dependencies because the
joint rule becomes inspectable and executable. It is less satisfactory for a
descriptive n-ary social relation whose identity, temporal validity, roles,
provenance, or uncertainty should be queried independently. The external
reviewer should decide whether such relations warrant a general relation
record, a narrowly scoped artifact pattern, or continued scenario-specific
representation.

---

## 6. The current person model

### 6.1 Authored person description

The reviewed authoring model is richer than a role label. A `PersonDraft`
contains:

- name and stable entity identity;
- position;
- disposition;
- autobiographical or situational memories; and
- a `BehavioralProfileDraft` containing lists of:
  - values;
  - goals;
  - beliefs, which may be wrong;
  - decision tendencies;
  - social perceptions;
  - current affect, attention, confidence, fatigue, or intent;
  - capabilities; and
  - limitations.

These fields are descriptive natural-language statements, not numeric latent
variables or commands. The authoring prompt instructs the model not to turn
them into action scripts. The renderer further states that described
capabilities and limitations do not grant or remove interfaces. See
[authoring/models.py](../../src/cybernetic_influence/authoring/models.py),
[authoring/live.py](../../src/cybernetic_influence/authoring/live.py), and the
[authoring prompt](../../src/cybernetic_influence/authoring/prompts/scenario_draft.yaml).

This implements an important distinction:

```text
personal oughts and preferences
    != position expectations
    != technical action interfaces
    != legal or institutional authorization
    != physical success
```

The regional outbreak scenario makes the distinction especially explicit. It
combines the shared `PersonDraft` profile with a role mandate and private
institutional context, then tells the LLM that position expectations are
institutional “oughts,” not commands, personal values, or granted
capabilities. See
[regional_outbreak.py](../../src/cybernetic_influence/scenarios/regional_outbreak.py).

### 6.2 Runtime cognition

At activation, an LLM person receives only:

- its persona/profile rendering;
- committed private memory;
- newly delivered observations from declared input ports;
- currently exposed action interfaces and accessible representations;
- the reason it is active;
- the current modeled time; and
- action and spend bounds.

It does not receive the canonical world, mechanism-only facts, actual hidden
provenance, another person's private state, same-moment proposals, analytical
boundaries, or engine-assigned identities.

The LLM returns a structured decision with:

- a private orientation;
- an optional memory update;
- zero or more bounded action intents; or
- an explicit reason for silence.

Observations, orientation, memory updates, and own action summaries are appended
to bounded private memory only if the activation commits successfully. The
generic memory implementation is an ordered natural-language list, truncated
to a configured maximum.

### 6.3 What is not yet a person model

The current design should not be mistaken for a validated computational model
of human behavior. In particular:

- values, beliefs, relationships, attention, confidence, and goals are text,
  not independently evolving state variables with explicit update equations;
- no generic belief object retains confidence, provenance, contradiction, or
  decay;
- no generic attention mechanism determines which delivered observations are
  noticed;
- memory loss is mainly bounded-list truncation, not psychologically grounded
  forgetting;
- interpersonal trust and obligations may appear in memory but are not
  canonical relationship states;
- the LLM is responsible for much of the consistency between profile, memory,
  interpretation, and action;
- the generic LLM decision schema cannot currently choose a new wake time, even
  though the active runtime supports scheduled updates; scenario wrappers and
  scripted processes currently own most scheduling; and
- the project has no empirical calibration showing that a profile produces
  stable or human-plausible behavior across contexts.

Some of these omissions may be deliberate. Encoding every semantic human
relationship as a typed global variable could dictate behavior and impose a
premature theory of mind. A promising distinction for review is:

- keep subjective semantic content—“I trust Ana's technical judgment but fear
  her ministry's political incentives”—inside personal memory; while
- retain concrete observable structure—who communicated, what artifact was
  received, which resource was controlled, which commitment was attempted—in
  world and event evidence from which an analyst may derive a relationship
  network.

The open question is which minimal cognitive state must become explicit to
prevent the LLM from implicitly controlling both the person model and its own
update rule.

---

## 7. How the machinery uses the ontology

The complete intended path is:

```text
analyst description
  -> bounded authoring model
  -> typed reviewable draft
  -> deterministic validation and compilation
  -> canonical scenario + trusted implementation registries
  -> active-system scheduling and bounded cognition
  -> typed action attempts
  -> local effect routing
  -> exact mechanism adjudication
  -> validated state patches and observations
  -> checkpoints, replay, and retained evidence
  -> analyst-safe graphs and narratives
  -> replaceable theory analyses and experiments
```

### 7.1 Conversational authoring

The authoring service calls an LLM with a strict consumer schema and asks it to
populate one reviewed workflow. The result is a `ScenarioDraftProposal`
containing people, objects, information, places, topology, placements, timing,
one workflow, analytical boundaries, fidelity questions, and unresolved
questions.

The draft is retained by revision. A user can edit a person or supported
scenario configuration directly without another model call. Approval binds the
reviewed proposal before execution. Provider failures preserve the prior valid
revision rather than silently applying a partial fallback.

Current authoring is not open-ended. The proposal union supports four workflow
families:

- resource request;
- information campaign;
- a narrowly reviewed component composition; and
- one coordination-decision template.

The authoring model cannot supply Python, arbitrary predicates, mechanism
implementation identities, or an organization executor.

### 7.2 Compilation

The compiler is the boundary between reviewed semantic input and executable
runtime identity. It validates references, reserved IDs, required participants,
timing agreement, placements, spatial links, boundaries, goal validity, and
template-specific constraints. It then maps the proposal onto a reviewed
fixture and trusted exact-mechanism registry.

The compiler deliberately owns ports, carriers, mechanism identities, handler
bindings, and invariant checkers. A proposal can configure supported semantics
but cannot invent behavior the runtime will execute.

The relevant implementation is
[authoring/compiler.py](../../src/cybernetic_influence/authoring/compiler.py).

### 7.3 Component registry and composition receipt

The repository contains a small reviewed registry with component kinds for:

- person participant;
- stateful object;
- information carrier;
- place;
- directed connection;
- exact mechanism; and
- analytical boundary.

Compilation retains a `CompositionReceiptV1` that maps selected reviewed
components to concrete runtime references and registry digest. This makes it
possible to inspect which runtime surfaces were used.

However, the current composition vertical is not a general composer. Its eight
selected components must match one fixed delivery-and-recording pattern, and
the adapter projects that configuration into the existing information-campaign
fixture. The receipt can also classify a scenario's already-built surfaces
after compilation. It does not yet prove that general scenarios are assembled
from components rather than constructed by bespoke fixture code.

See [authoring/composition.py](../../src/cybernetic_influence/authoring/composition.py)
and [authoring/component_composition.py](../../src/cybernetic_influence/authoring/component_composition.py).

### 7.4 Active-system activation

The active runtime combines one causal-core session with active-system specs,
private state, implementation bindings, budget limits, and checkpoints. It
finds the earliest due time across:

- unconsumed delivered observations;
- scheduled internal wakes; and
- pending exact effects or deliveries.

All processes due at that time are collected against one frozen causal
checkpoint. They may execute sequentially or concurrently, but their inputs are
the same pre-moment state. Each implementation receives a defensive copy of its
bounded input.

Participant proposals are validated before world mutation. The runtime assigns
canonical action identities, applies all proposals to a trial causal session in
canonical order, validates the resulting aggregate checkpoint, and commits the
moment atomically. A failed collection or transition retains failure evidence
without partially committing the moment.

### 7.5 Input projection

For each active system, the runtime projects only:

- observations delivered to its entity through declared observation ports and
  not already consumed;
- output ports owned by that process and currently available;
- representation IDs allowed on each output;
- private state;
- activation causes; and
- budget limits.

This is a core fidelity and integrity boundary. A person does not receive a
global dictionary of all facts and choose which ones to mention. A mechanism
credential or hidden actual source remains outside the person's prompt unless
an explicit observation pathway exposes it.

### 7.6 Action materialization

An implementation proposes an `ActionIntent`. The active runtime checks:

- that the active system used its own exposed output port;
- that the payload matches the selected scenario-specific response schema or
  later mechanism validation;
- that any representation ID was accessible through that interface;
- that action and memory bounds are respected; and
- that implementation identity matches the registered specification.

The engine then constructs an `ActionAttempt` with actor, action ID, modeled
time, and causal ancestry. The implementation never invents those identities.

### 7.7 Structural effect routing

The causal core emits a typed effect from the selected output port. It finds
compatible local routes through:

- explicitly directed connections; or
- compatible input ports in the same typed routing container.

Connections may be disabled or delayed. If no valid route exists, the effect
dissipates and that outcome is retained. Routing uses declared topology, not an
LLM or a global semantic search.

### 7.8 Mechanism execution and commit

Each input port is bound to exactly one mechanism. When an effect reaches that
port, the engine constructs a `MechanismContext` containing only declared facts,
representations, placements, links, triggering data, and protected accessors.
The registered handler proposes a `MechanismOutcome`.

Before commit, the engine verifies:

- input and output effect types;
- handler and implementation identity;
- declared read and write authority;
- legal placement movement across declared link endpoints;
- carrier revision and representation lineage;
- observation targets and ports;
- independently registered invariants; and
- propagation and zero-time limits.

Valid changes become a versioned `StatePatch`; downstream effects and
observations are scheduled. Invalid changes fail loudly and roll back the
attempt.

The implementation is in
[causal_core/engine.py](../../src/cybernetic_influence/causal_core/engine.py).

### 7.9 Checkpoint, replay, and retention

A checkpoint contains scenario and execution fingerprints, canonical state,
state digest, complete event prefix, event-tail digest, metrics, accepted
actions, counters, and pending scheduled work. Restore re-derives topology and
validates retained references rather than trusting serialized future work.

The active checkpoint additionally retains private active-system state,
activation attempts, call evidence, exact-work records, budgets, and
implementation identities. A completed run binds the final causal result to
all active-system evidence.

The local `RunStore` writes one complete JSON document per run through atomic
replacement. Completed runs can be reopened without model re-execution.
Narration or analysis can fail independently without invalidating a completed
world trajectory.

### 7.10 Analyst projections

The application derives several different views:

- **spatial topology:** places, placements, and spatial links;
- **configured interaction pathways:** entities, ports, mechanisms, carriers,
  representations, and possible routes;
- **realized causal trajectory:** events and their causal-parent edges;
- **analytical boundary view:** reversible coarse-graining with member
  step-down; and
- **timeline and narrative:** selected-revision accounts grounded in retained
  events.

Analyst projection redacts mechanism-only values and content. Selecting an
earlier event reconstructs the state at that revision rather than pairing early
events with final state. The UI has no authority to mutate canonical state.

See [causal_core/projection.py](../../src/cybernetic_influence/causal_core/projection.py),
[presentation.py](../../src/cybernetic_influence/presentation.py), and
[ADR 004](../adr/004-analyst-evidence-boundary.md).

### 7.11 Analysis machinery

After a completed configured run, the system can build a theory-neutral
`RunEvidenceBundleV1` containing:

- approved scenario configuration;
- separate run and analysis specifications;
- initial and terminal state identities;
- causal events and mechanism decisions;
- information lineage;
- participant activations;
- boundary activity;
- completion evidence;
- fidelity assumptions and omissions; and
- run/model integrity metadata.

Separate Waltzman and Levin readouts consume the immutable bundle. Every
finding declares whether it is exact, calculated, or LLM-coded and cites bundle
evidence. Narrator prose is explicitly excluded as measurement source truth.

The implemented contracts are in
[analysis/theory_analysis.py](../../src/cybernetic_influence/analysis/theory_analysis.py)
and [analysis/coordination_measurement.py](../../src/cybernetic_influence/analysis/coordination_measurement.py).

### 7.12 Experiment machinery

The repository has scenario-specific experiment contracts for coordination and
composite-agency probes. They define conditions, retained run references,
replicates, contrasts, and evidence-linked readouts. These demonstrate that
matched conditions and checkpoint forks are possible, but there is not yet a
general `ExperimentSpec` authoring and execution layer usable across arbitrary
scenario families.

---

## 8. Two concrete examples

### 8.1 Physical access: a compact exact-world example

The physical-access scenario is the clearest demonstration of the canonical
ontology.

**World:** a technician, badge, written policy, access controller, secure door,
pump, hallway, equipment room, threshold, and record carriers.

**Person:** the technician has an active-system binding and private memory. The
door, policy, and badge exist but do not think.

**Information:** the badge and policy are separate representations on separate
carriers. Badge secret content is mechanism-visible and excluded from the
person prompt and analyst graph.

**Action:** the technician may attempt badge presentation through an owned
output interface.

**Mechanisms:** authentication reads the badge credential; authorization reads
the stored policy representation; latch actuation reads door state; crossing
reads lock state, technician placement, and the threshold link.

**Outcomes:** three controlled arms distinguish authorized entry,
authentication followed by policy denial, and authorization followed by a
jammed latch. Only authorized and physically operable execution changes the
technician's placement.

This example demonstrates strong causal and institutional-mechanism separation,
but it is a hand-built fixture rather than evidence that an analyst can compose
an arbitrary access system through the general authoring UI.

### 8.2 Regional outbreak: a richer but bespoke sociotechnical example

The outbreak example contains:

- twenty-six autonomous participant configurations;
- reviewed person profiles with values, goals, beliefs, tendencies, social
  perceptions, state, capabilities, limitations, and memories;
- position mandates and private institutional contexts;
- separate exogenous source processes;
- optional defensive CSO monitor, diagnostician, and planner roles;
- a deterministic allocation authority;
- typed stance, message, intervention, and resource interfaces;
- exact round, decision-gate, source-delivery, CSO, and resource-allocation
  mechanisms;
- concrete resources with custody, quantity, availability, dependencies, and
  verification evidence; and
- coalition and national-delegation analytical boundaries.

This is more than “twenty-six LLM agents voting.” It is a case-specific causal
world in which different process types have different authority surfaces.
Coalition participants cannot use source or CSO ports; source and CSO roles
cannot use coalition stance ports; an allocation authority, not the planner,
owns resource movement; and exact mechanisms own the gate and resource facts.

However, it remains substantially authored:

- the roster and allowable conditions are closed;
- typed payloads and mechanism handlers are scenario-specific Python;
- source and CSO action catalogues are predefined;
- some intervention classes map to preauthored world consequences;
- the public workbench uses a dedicated configuration and run surface rather
  than the general `ScenarioDraftProposal` compiler; and
- the public guided generator example is illustrative JavaScript, not the
  executable outbreak ontology.

The outbreak now reuses the shared `PersonDraft`/`person_context` machinery; it
does not currently bypass the richer person profile. It still bypasses the
general authoring and component-composition path. That distinction is exactly
why adoption gaps must be reviewed separately from missing ontology.

Focused evidence appears in
[tests/test_regional_outbreak.py](../../tests/test_regional_outbreak.py),
including checks that reviewed person configuration reaches private memory and
native policy, participant prompts are blind to experiment condition, resources
move as conserved objects, and false claims do not change custody.

---

## 9. Current implementation and adoption status

| Capability | Current status | Important qualification |
|---|---|---|
| Strict canonical causal state | Implemented and broadly used | Entity kinds and fact semantics remain open strings/JSON. |
| Typed ports and directed connections | Implemented and broadly used | Effect types have no global semantic registry. |
| Exact mechanism authority and invariant validation | Implemented and broadly used | Handlers are trusted, reviewed Python implementations. |
| Information carriers, copies, provenance, and observations | Implemented and used in several scenarios | Attention, belief, and credibility updates remain cognitive interpretation. |
| Places, placements, and adjacency | Implemented | No geometry, pathfinding, visibility, acoustics, or general transport model. |
| Multirate active-system scheduler | Implemented | Positive duration is not universal; generic LLM self-scheduling is limited. |
| Scripted and LLM active-system implementations | Implemented | No general stochastic, learned-surrogate, or external-trace implementation registry. |
| Rich descriptive person profile | Implemented and used in authored coordination and outbreak | Behavioral consistency and calibration are unestablished. |
| Execution-inert analytical boundaries | Implemented | Flat, authored membership; nested, overlapping, dynamic, or inferred boundaries are deferred. |
| Reversible graph, trace, and selected-revision evidence | Implemented | Public walkthrough language is simpler and partly disconnected. |
| Theory-neutral evidence bundle and separate analyses | Implemented for configured coordination | Measures are exploratory and scenario-specific. |
| Conversational authoring | Implemented for four closed workflow families | Not a general world/ontology composer. |
| Reviewed component registry and receipt | Implemented narrowly | Current composition is an adapter over a fixed existing fixture. |
| General experiment specification | Not implemented | Existing experiment contracts are scenario-specific. |
| General representation-depth registry | Accepted direction, deferred | Only exact/scripted/LLM paths are ordinary product machinery today. |
| Emergent institution inference | Not implemented | Boundaries are authored analytical choices, not learned macrostructures. |
| Concordia or other cognition-framework integration | Unresolved | Canonical plan requires a foundation decision before expansion. |

---

## 10. Gap analysis for a general-purpose simulator

The following are observed architecture gaps, not a proposed implementation
roadmap. The reviewer should challenge their severity and whether each belongs
in ontology, execution machinery, cognition, analysis, or authoring.

### 10.1 The general composition seam is much narrower than the runtime

The causal core can represent many arrangements of entities, ports,
connections, mechanisms, carriers, representations, places, and active systems.
The authoring layer cannot assemble most of them. It chooses among closed
templates, and the first component composition maps to a preexisting campaign
fixture.

Consequences:

- new scenario families still require substantial Python fixture work;
- component receipts can describe a graph without proving the graph was
  actually composed through the registry;
- an LLM author cannot select arbitrary reviewed mechanisms or bind their typed
  slots; and
- the product risks accumulating high-fidelity but isolated demonstrations.

This is probably the largest current general-purpose gap.

The limitation is visible directly in the closed workflow union in
[authoring/models.py](../../src/cybernetic_influence/authoring/models.py), the
template dispatch in
[authoring/compiler.py](../../src/cybernetic_influence/authoring/compiler.py),
and the fixed adapter in
[authoring/component_composition.py](../../src/cybernetic_influence/authoring/component_composition.py).

### 10.2 There is no enforced “use the existing capability” adoption contract

Nothing in the Python architecture prevents a new scenario module from
constructing a `CausalScenario`, active specs, personas, and bespoke UI directly
while bypassing the authoring compiler, component registry, person renderer, or
standard evidence bundle. Tests can prove that a capability exists without
proving that a later consumer adopted it.

The outbreak now uses the shared person context, demonstrating that adoption
can be repaired, but it still has a dedicated authoring/configuration path.
A general product needs a visible declaration of which canonical seams each
scenario uses and which bounded exceptions it introduces. This is partly a
lifecycle and integration-governance problem, not an ontology problem.

The contrast can be inspected between the generic
[authored-person binding](../../src/cybernetic_influence/authoring/live.py) and
the scenario-owned construction in
[regional_outbreak.py](../../src/cybernetic_influence/scenarios/regional_outbreak.py).

### 10.3 `entity_kind` is flexible but semantically weak

Open strings avoid ontology explosion, but they do not define:

- which state or capabilities a kind requires;
- whether two scenarios use a kind compatibly;
- which components can replace one another;
- which projections or analyses understand it; or
- whether a kind is merely a label over scenario-specific facts.

The component registry partially addresses this at a coarser runtime-surface
level. A reviewer should assess whether the product needs a versioned semantic
type/contract registry, or whether typed ports and behavior contracts are
sufficient while entity kinds remain descriptive.

The open `entity_kind` field and the stricter surrounding reference validation
are both visible in
[causal_core/models.py](../../src/cybernetic_influence/causal_core/models.py).

### 10.4 Roles, norms, authority claims, and commitments are mostly scenario-specific

Positions and institutional expectations are currently descriptive strings.
Concrete authority can be modeled well through controlled artifacts,
mechanisms, and resource dependencies, but there is no general representation
for:

- an office occupied by a changing person;
- a claim of authority distinct from actual technical control;
- a norm or obligation distinct from personal preference;
- delegation and revocation;
- commitments with lifecycle, parties, conditions, and enforcement; or
- contested jurisdiction.

It may be a mistake to make all these universal primitives. It may also be a
mistake to leave them buried in text in a simulator focused on coordination.
The reviewer should identify the smallest recurring contracts that deserve
first-class treatment.

### 10.5 N-ary and temporally qualified social relations are not first-class

Mechanism nodes handle n-ary causal rules well. They are less natural for
relations such as “A delegates task X to B under policy P until time T, witnessed
by C.” Such a relation has roles, provenance, validity, and lifecycle. Encoding
it as a fact dictionary may make it unselectable and hard to validate; encoding
it as a mechanism may wrongly imply executability.

The current system needs a clearer decision about when an artifact, entity,
event, mechanism, or new relation record should represent these structures.

### 10.6 World physics and resource semantics are scenario-local

The runtime validates declared state changes and spatial-link movement, but it
does not supply general machinery for:

- physical units and dimensional consistency;
- conserved stocks and flows;
- capacity and queueing;
- resource contention and allocation optimization;
- degradation, consumption, and replenishment;
- probabilistic failure and repair;
- continuous or hybrid dynamics;
- geometry and travel paths; or
- causal models such as epidemiology or logistics.

The outbreak implements concrete resource custody and quantities, but those
semantics are embedded in the scenario's exact handlers. A general simulator
needs reusable subsystem components or surrogate contracts without turning the
core into a universal physics engine.

The current spatial boundary is documented in
[ADR 008](../adr/008-separate-spatial-topology-from-routing-and-permission.md),
while the outbreak's resource semantics are implemented locally in
[regional_outbreak.py](../../src/cybernetic_influence/scenarios/regional_outbreak.py).

### 10.7 Cognition remains an LLM policy plus prose memory

The person profile is substantially richer than a role prompt, but the LLM
still owns most interpretation and psychological state transition. Missing
generic machinery includes partial attention, belief provenance and confidence,
contradiction management, forgetting, relationship-dependent credibility,
stress/cognitive load, persistent plans, and cross-context behavioral
consistency.

The architectural question is not whether to convert psychology into dozens of
numbers. It is where explicit state or conventional mechanisms are needed so
the LLM does not implicitly determine what the person noticed, believed,
remembered, valued, and did all at once.

The present generic decision and memory schemas are in
[active_runtime/llm.py](../../src/cybernetic_influence/active_runtime/llm.py).

### 10.8 The interface vocabulary can confuse possibility with permission

Technically, an exposed output port means “this process may attempt this typed
effect now.” Institutional permission and success may still be denied later.
The LLM prompt uses language such as “may act only through” and “permitted
representation IDs,” which describes simulator admissibility but can be read as
in-world authorization.

For coordination and institutional scenarios, the product should consistently
distinguish:

- technically exposed attempt;
- actor-perceived affordance;
- policy authorization;
- social legitimacy;
- physical feasibility; and
- realized outcome.

### 10.9 Simultaneous proposal conflict semantics are limited

Due participants decide from a frozen state, which avoids same-moment leakage.
Their actions are then applied to a trial causal session in canonical order.
The runtime validates the aggregate result atomically, but it does not expose a
general conflict-resolution language for incompatible simultaneous writes,
resource races, market clearing, voting, negotiation, or priority. Each
scenario must provide exact mechanisms that make these semantics meaningful.

The frozen-input and canonical trial-commit behavior is implemented in
[active_runtime/engine.py](../../src/cybernetic_influence/active_runtime/engine.py).

### 10.10 Time is discrete and only partly generalized

The scheduler supports future work and multirate processes, but:

- scenario time is integer-valued;
- some retained scenarios use legacy zero-delay routes;
- generic LLM policies do not independently choose their next wake;
- duration sources are not a reusable calibrated library;
- no continuous solver or hybrid-event adapter exists; and
- there is no general policy for deadlines, preemption, cancellation, or
  activities occupying resources over intervals.

This may be sufficient for many wargames, but the limits should be explicit in
claims about logistics, disease, finance, or physical processes.

The accepted and partly implemented time contract is
[ADR 010](../adr/010-autonomous-multirate-process-time.md).

### 10.11 Information delivery is stronger than attention modeling

The runtime carefully models what is delivered, when, through which port, with
what apparent source and representation. After delivery, the generic person
policy sees all newly projected observations. It does not have a separate
bounded attention stage that can miss, delay, prioritize, or misread them.

Consequently, information-topology fidelity is stronger than cognitive-attention
fidelity.

### 10.12 Analytical boundaries are flat, authored, and static

Execution-inert boundaries avoid organization reification, but the current
model does not support:

- overlapping or nested boundaries;
- membership changing over modeled time;
- alternative competing coarse-grainings;
- boundary inference from repeated interaction and dependency patterns;
- formal comparison of which boundary best compresses/control-predicts a
  trajectory; or
- explicit separation between an analyst's boundary and actors' own contested
  group identities.

These are material gaps for emergent sociotechnical institutions, although
adding them must not create a hidden aggregate executor.

The current flat boundary semantics and explicit deferrals are documented in
[ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md).

### 10.13 Analysis constructs are better separated than validated

The evidence architecture is strong: derived findings cannot mutate the world,
must declare method, and cite retained evidence. The measurement validity is
weak:

- Waltzman constructs have no empirical calibration;
- LLM coding may share model-family biases with the simulated people;
- current examples are mechanism demonstrations, not independent samples;
- robustness across scenarios, prompts, models, and assumptions is limited;
- aggregate network measures remain scenario-specific; and
- the system lacks a general sensitivity/uncertainty workbench.

For wargaming, the appropriate standard is likely mechanism plausibility,
diagnostic value, exploratory validity, and robustness to plausible assumptions—not
forecast accuracy. The product still needs machinery to expose that robustness.

The implemented evidence/readout separation is in
[analysis/theory_analysis.py](../../src/cybernetic_influence/analysis/theory_analysis.py);
its epistemic limits follow
[ADR 012](../adr/012-decision-environment-measures-are-derived.md).

### 10.14 Experiment support is not yet general-purpose

Specific modules can run matched coordination conditions and composite assays,
but an analyst cannot generally define:

- a checkpoint fork;
- controlled variable changes;
- random or adversarial authorized interventions;
- repeated seeds/models;
- outcome and mechanism measures;
- falsification conditions; and
- comparison validity labels

for any compiled scenario through one common contract.

The current experiment machinery is explicitly coordination-specific in
[experiments/coordination_experiment.py](../../src/cybernetic_influence/experiments/coordination_experiment.py).

### 10.15 The public explanatory UI is not a faithful ontology browser

The guided example is intentionally simpler, but it currently:

- calls a mechanism a “Process” in the legend while the graph labels the node
  as a mechanism;
- uses situation-specific edge kinds not present in the canonical graph
  contract;
- does not clearly distinguish directed routes from undirected adjacency or
  noncausal grouping;
- represents an n-ary readiness rule visually without explicitly teaching
  mechanism reification; and
- is hard-coded rather than generated from a canonical executable scenario.

This is a presentation/adoption gap. It should not be mistaken for proof that
the underlying runtime lacks mechanism, direction, or provenance semantics.

The guide vocabulary is defined in
[public/waltzman/app.js](../../public/waltzman/app.js), whereas the canonical
graph vocabulary is defined in
[causal_core/projection.py](../../src/cybernetic_influence/causal_core/projection.py).

### 10.16 The framework-foundation decision remains unresolved

The repository has not yet adopted whether to:

- build on Concordia;
- use Concordia cognition around the current causal environment;
- keep the current foundation with compatibility adapters; or
- remain independent.

The key comparison is not “prose versus typed state.” Both approaches can mix
natural language and exact state. The material questions are ownership of
authoritative state, scheduling, interpretation, adjudication, evidence,
checkpointing, extension seams, and maintenance. Generalizing the current
runtime before resolving that question risks duplicating machinery that could
be reused—or adopting a framework in a way that splits authority and weakens
the current evidence guarantees.

The unresolved alternatives and evaluation contract are recorded in
[Slice 26](../plans/026-concordia-foundation-research.md).

---

## 11. Questions the external reviewer should answer

The reviewer is asked to give concrete, architecture-level criticism rather
than only recommending “more agents,” longer prompts, or more realistic prose.

### 11.1 Ontology

1. Are the canonical primitives minimal and compositional, or are important
   kinds of state being forced into unvalidated JSON facts?
2. Which recurring sociotechnical concepts—role, office, authority claim,
   norm, commitment, resource, dependency, contract, relationship—deserve
   first-class versioned records, if any?
3. Is mechanism-node reification sufficient for n-ary causal relations? What
   noncausal n-ary relations require another representation?
4. Is the distinction among carrier, representation, observation, apparent
   source, and actual source adequate for misinformation, copying, provenance,
   and contested evidence?
5. Does an execution-inert analytical boundary adequately support emergent
   institutions, or is additional dynamic boundary machinery necessary?

### 11.2 Agency and cognition

6. Is separating entity existence from active-system implementation the right
   abstraction for people, vehicles, software, organizations, and tools?
7. Which parts of human cognition should remain semantic memory interpreted by
   an LLM, and which need explicit state/update mechanisms for fidelity and
   consistency?
8. How should partial attention, uncertain belief, source credibility,
   relationships, planning, stress, and forgetting be modeled without imposing
   an overly rigid semantic theory?
9. Should active processes be able to schedule their own reconsideration through
   the generic decision contract?

### 11.3 World and execution

10. Are ports, effect types, connections, and exact mechanisms an adequate
    action/environment seam?
11. Does the trusted Python mechanism registry scale, or is a reviewed
    data-driven transition language needed?
12. How should reusable world subsystems—resources, queues, logistics,
    epidemiology, law, markets, software—fit behind fidelity-declared contracts?
13. What general conflict or transaction semantics are needed for simultaneous
    proposals?
14. Which timing features are necessary for credible wargaming, and which would
    be unnecessary simulation-engine ambition?

### 11.4 Authoring and adoption

15. What is the smallest general composition contract that would let an analyst
    assemble materially different scenarios without arbitrary generated code?
16. How should a scenario prove that it uses canonical person, information,
    mechanism, evidence, and analysis seams rather than bypassing them?
17. Should component kinds be defined by semantic class, behavior contract,
    port signature, or some combination?
18. How can conversational authoring remain flexible without allowing the LLM
    to invent executable semantics or conceal unsupported capability?

### 11.5 Evidence and analysis

19. Does the retained event and state model distinguish intent, attempt,
    routing, adjudication, commit, observation, and interpretation sufficiently?
20. What uncertainty, sensitivity, and perturbation machinery is needed for
    exploratory validity rather than prediction?
21. Which graph/network projections would reveal emergent authority,
    bottlenecks, reliance, coalition formation, or institutional stabilization
    without governing behavior through those derived labels?
22. What minimum evidence would justify calling a pattern robust across
    heterogeneous interactions rather than a single authored trajectory?

### 11.6 Foundation

23. Which current ownership boundaries should remain in Cybernetic Influence,
    and which could be delegated to Concordia or another framework without
    creating two authoritative worlds?
24. Which present guarantees are genuinely differentiating and which are
    expensive reimplementations of mature simulation/agent infrastructure?

---

## 12. A concise mental model

For a reader who remembers only one model, use this:

```text
WORLD SUBSTRATE
  entities + facts + places + carriers + representations

POSSIBLE PATHWAYS
  owned ports + directed connections + broadcast containers + spatial links

AUTONOMOUS PROCESSES
  selected entities + private state + bounded observations + implementation

ATTEMPT
  process proposes a typed action through an exposed interface

ADJUDICATION
  local exact mechanism reads only declared state and applies a reviewed rule

CONSEQUENCE
  validated patch, movement, representation, effect, or observation

EVIDENCE
  causal event parents + checkpoint + replayable state changes

ANALYSIS
  reversible graphs, boundaries, narratives, and theory-specific findings
```

The LLM answers a bounded question resembling:

> Given this person's descriptive context, private memory, delivered
> observations, time, and currently exposed interfaces, what might this person
> attempt or retain?

The LLM should not be authoritative for:

> What is globally true, which hidden information exists, whether an attempted
> action is permitted or physically possible, how the world changes, whether a
> message was delivered, or what aggregate theory the run proves.

---

## 13. Source ledger

| Source | Authority or evidence role | Used for |
|---|---|---|
| [GOAL.md](../GOAL.md) | Active product outcome and boundaries | Product identity, contracts, nonclaims |
| [ROADMAP.md](../ROADMAP.md) | Current direction and implementation state | Adoption status, unresolved foundation decision |
| [ADR index](../adr/README.md) and ADRs 004–012 | Binding architecture decisions | Evidence, information, boundaries, space, time, fidelity, analysis |
| [From Minds to Coordination source note](001-from-minds-to-coordination.md) | Project evidence summary of supplied paper | Waltzman theory scope and limits |
| [Causal models](../../src/cybernetic_influence/causal_core/models.py) | Primary executable contract | Canonical ontology, events, checkpoints |
| [Causal engine](../../src/cybernetic_influence/causal_core/engine.py) | Primary executable behavior | Routing, mechanism authority, validation, commit |
| [Active runtime](../../src/cybernetic_influence/active_runtime/) | Primary executable behavior | Agency, scheduling, cognition boundary, private state |
| [Authoring package](../../src/cybernetic_influence/authoring/) | Primary executable behavior | Person model, draft schema, compiler, component composition |
| [Projection and presentation](../../src/cybernetic_influence/causal_core/projection.py) and [presentation.py](../../src/cybernetic_influence/presentation.py) | Primary executable behavior | Graph semantics, redaction, temporal and boundary views |
| [Theory analysis](../../src/cybernetic_influence/analysis/theory_analysis.py) | Primary executable contract | Evidence bundle and derived readouts |
| [Physical access](../../src/cybernetic_influence/scenarios/physical_access.py) | Executable ontology example | Permission/capability/success and information separation |
| [Regional outbreak](../../src/cybernetic_influence/scenarios/regional_outbreak.py) | Executable rich scenario | Person profile adoption, organizations, sources, CSO, resources |
| [Focused tests](../../tests/) | Primary observed checks | Validation, replay, person adoption, boundaries, experiments |

Excluded source classes include archived superseded plans, old deployment
records, and historical run narratives except where current authorities
explicitly depend on them. They are useful forensic evidence but do not define
the present ontology. Concordia source is also outside this dossier's evidence
boundary; the unresolved foundation plan specifies a separate pinned source
comparison.

---

## 14. Glossary

**Active system** — A scheduled stateful process bound to an entity and one
implementation. It may be LLM-based, scripted, or eventually another declared
policy technology.

**Analytical boundary** — An execution-inert grouping used to inspect a system
at a chosen scale. It is not a mind, actor, or spatial container.

**Carrier** — A physical or digital state surface capable of retaining an
encoded representation.

**Causal moment** — A set of active systems due at the same modeled time and
evaluated from one frozen pre-moment state.

**Connection** — A directed, optionally delayed route between compatible output
and input ports.

**Container** — A typed broadcast-routing locus. It is not a place.

**Entity** — A persistent referent. Entity kind does not imply autonomy.

**Exact mechanism** — A registered transition implementation whose declared
read/write authority and invariants are enforced by the causal engine.

**Fidelity declaration** — A statement of preserved phenomena, assumptions,
omissions, validation basis, and invalid questions for a subsystem
representation.

**Observation** — The apparent content and source actually delivered to an
entity through a declared input interface.

**Port** — An owned typed input or output interface.

**Representation** — Specific encoded content on a carrier at a particular
revision, with source and derivation lineage.

**Scenario specification** — What world and situation are simulated.

**Run specification** — How one execution is configured.

**Analysis specification** — Which constructs are derived from a run and by
what evidence/method.

**Experiment specification** — Which conditions, forks, repetitions, and
comparisons are applied across runs; currently scenario-specific rather than a
general product contract.

**Typed causal island** — A deliberately explicit subsystem where state,
interfaces, transitions, evidence, and invariants matter to the research
question, embedded within a wider world that may remain natural-language or
coarsely represented.
