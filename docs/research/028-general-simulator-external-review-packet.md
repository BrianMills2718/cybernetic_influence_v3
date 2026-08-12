---
doc_role: external_review_packet
authority: synthesis
status: current_snapshot
created: 2026-08-11
updated: 2026-08-11
source_revision: d5f22594fe2f82160b846b18c43746e3c95f9944
depends_on:
  - docs/GOAL.md
  - docs/ROADMAP.md
  - docs/adr/013-generalized-simulator-foundation.md
  - docs/research/027-concordia-architecture-revisit.md
  - docs/research/general-purpose-simulator-ontology-and-machinery.md
---

# External review packet: architecture of a general-purpose exploratory simulator

## Instructions to the reviewer

This packet is intended to be self-contained. You should not need the prior
conversation or earlier review memoranda to understand the product, the current
implementation, the adopted architectural direction, the evidence supporting
it, or the unresolved questions.

Please assess the following central question:

> Does the adopted architecture—Concordia owning the outer simulation lifecycle
> while project-owned components own canonical world state, bounded context,
> semantic intent, transition adjudication, validated patches, and evidence—form
> a credible foundation for a general-purpose exploratory simulator? Which
> capabilities are genuinely supported, which remain speculative, and what is
> the smallest high-value change needed before broader implementation?

The intended product is closer to an extensible wargaming environment than to a
predictive digital twin. Do not evaluate it primarily by forecast accuracy.
Relevant standards include mechanism plausibility, diagnostic value,
exploratory usefulness, internal coherence, inspectability, and sensitivity to
plausible assumptions.

This is an architecture review request, not an instruction to implement a broad
rewrite. Please distinguish:

- implemented behavior;
- behavior observed only in a disposable probe;
- an accepted architectural decision;
- a designed but unimplemented production contract;
- an inference or recommendation; and
- a genuinely unresolved question.

If repository access is available, inspect the cited files and symbols. If it
is not, treat the code descriptions below as the evidence boundary and identify
any conclusion that would require direct source confirmation.

## Executive summary

The product goal is a reviewable simulator in which an analyst can describe a
bounded sociotechnical world in ordinary language, edit the resulting
configuration, run autonomous LLM and non-LLM processes, and inspect what
happened, why it happened under the declared assumptions, and which evidence
supports or limits an interpretation.

Waltzman's *From Minds to Coordination* supplies the first substantial theory
module and motivates attention to local information paths, heterogeneous
interactions, perceived risk, trust structure, dependencies, and collective
coordination readiness. It does not define the whole product. The simulator
must also be able to represent traditional homogeneous influence, ordinary
disagreement, logistics, infrastructure, software, resources, markets,
technical failures, organizations at different resolutions, and other bounded
worlds.

The existing Cybernetic Influence runtime contains several strong ideas:

- one authoritative canonical world state;
- separation of existence from agency;
- separation of attempt, capability, authorization, feasibility, and success;
- explicit information carriers, representations, delivery, and provenance;
- bounded actor observations and private memory;
- declared exact transition mechanisms and invariant validation;
- multirate scheduling and checkpoint continuation;
- replayable state patches and causal evidence; and
- theory analyses derived from evidence rather than inserted as hidden causes.

Its principal limitation is not that it cannot represent anything interesting.
It is that its richest capabilities are difficult to compose generally and are
repeatedly bypassed by scenario-specific Python, prompts, execution loops, and
interfaces. The current free-text authoring system still compiles into four
closed workflow families. The nominal component-composition path maps a fixed
component pattern into an existing information-campaign fixture. The regional
outbreak demonstration uses the richer shared person model but still bypasses
the general authoring/composition path.

The accepted direction is to use Google DeepMind's Concordia as the outer
simulation foundation rather than continue growing a second complete agent
framework. Concordia would own entity/component lifecycle, actor selection,
time, simulation-engine/game-master invocation, component assembly, and
checkpoint invocation. Project-owned Concordia components would supply the
canonical world, actor and adjudicator contexts, semantic action intents,
transition authorities, structured patches, validation, atomic commit,
information boundaries, and retained evidence.

The intended common path is:

```text
canonical world truth
    -> actor-authorized context
    -> open semantic action intent
    -> declared transition authority
    -> structured world patch proposal
    -> generic and subsystem-declared validation
    -> atomic commit or visible rejection
    -> actor-specific observation and retained evidence
```

A transition authority may be deterministic code, a stochastic model, an LLM
game master, an external simulator, a script, or a replayed trace. An LLM game
master is a legitimate first-class coarse model, not a shameful fallback. It
does not directly edit canonical state: it proposes a patch that is validated
and committed through the same authority boundary as other transition models.

A disposable probe exercised the most discriminating part of this design on
stock Concordia. A destroyed bridge blocked a fuel delivery; a temporary depot
and route were created; state was checkpointed and restored; a Luna-backed
worker proposed an open semantic action; a separate Luna-backed adjudicator
proposed a structured patch; generic validation checked references, scope,
topology, placement, and a narrow hidden-information condition; and the worker
and truck reached the port. Fifty-nine focused upstream Concordia tests also
passed. The probe did not call the old Cybernetic Influence runtimes.

That evidence supports the public extension seam. It does not establish a
production architecture, general authoring, cross-domain reuse, reliable LLM
adjudication, general information noninterference, safe live creation/removal
of autonomous entities, concurrent transaction semantics, scale, or behavioral
fidelity. The probe source was deliberately disposable and is not product code.

The current recommendation is therefore:

1. retain the Concordia-first decision;
2. do not fork Concordia yet;
3. implement one production bridge/port vertical through public Concordia
   seams and domain-neutral project contracts;
4. route one real product consumer through those contracts immediately after
   the vertical works, so the new machinery cannot become another unused path;
5. reconsider a private fork or the independent-runtime fallback only when a
   concrete required capability cannot be implemented through stable public
   seams or an upstream-compatible extension.

## Status vocabulary used in this packet

| Label | Meaning |
|---|---|
| **Implemented** | Present in repository product code. |
| **Observed** | Executed with focused evidence at the named boundary. |
| **Accepted** | Current product-owner architectural decision. |
| **Designed** | Contract or vertical is specified but not implemented. |
| **Indicated** | One probe supports the possibility but does not establish general capability. |
| **Unknown** | Decision-relevant evidence is absent or insufficient. |
| **Deferred** | Deliberately outside the current vertical, not claimed impossible. |

## 1. Product objective and epistemic position

### 1.1 Desired analyst workflow

The mature workflow is:

```text
describe a bounded world
    -> review and edit its executable configuration
    -> run autonomous and non-autonomous processes
    -> inspect trajectory, state, evidence, and assumptions
    -> compare conditions or interventions when useful
    -> derive replaceable theory-specific analyses
```

The product should eventually allow an analyst to:

- construct a world from people, artifacts, software, places, resources,
  relationships, channels, topology, mechanisms, and active processes;
- decide which subsystems need detailed explicit models and which can use
  coarse LLM or statistical surrogates;
- observe how information and action propagate through local pathways;
- inspect individual actions and emergent macro-patterns without turning an
  organization or coalition into a hidden omniscient mind;
- fork checkpoints, apply perturbations, and compare possible continuations;
- inspect exactly what was configured, model-selected, inferred, validated,
  committed, observed, and later analyzed; and
- understand the questions the chosen representation cannot answer.

### 1.2 What “fidelity” means here

Fidelity is question-relative. More detail is not automatically more faithful.
The useful standard is whether the representation preserves the structures,
information boundaries, choices, dependencies, constraints, timing, and
consequences material to the analytical question.

The product does not claim that generated trajectories predict chaotic human or
institutional systems. A useful result has the conditional form:

> Under these assumptions, representations, and transition authorities, this
> pathway or failure mode is possible and these dependencies appear important.

The appropriate evaluation questions are therefore:

- Is the mechanism plausible under the modeled assumptions?
- Does the run reveal a dependency, failure mode, tradeoff, or intervention
  consequence the analyst can reason about?
- Can every material conclusion step down to retained evidence?
- Does the insight survive reasonable changes in assumptions, prompts, models,
  seeds, or representation depth?
- Is the simulator exposing uncertainty or merely producing persuasive prose?

### 1.3 Relation to Waltzman

Waltzman's paper argues that an influence operation need not produce a uniform
narrative or shared false belief. Heterogeneous, individually plausible, and
adaptive interactions may still move a decision environment in a common
direction by changing credibility structures, perceived risk, verification
burden, action thresholds, coordination timing, and expectations about other
participants.

For this product, that yields a micro-to-macro hypothesis:

```text
source, message, channel, timing, and local context
    -> person-local observation and interpretation
    -> memory, requests, commitments, delays, withdrawal, or action
    -> changing relationships, dependencies, and interaction patterns
    -> derived trust-, risk-, and coordination-related findings
    -> collective outcome
```

Heterogeneous interaction is a particularly important modern influence pattern,
not a restriction on the simulator. The same machinery should represent a
traditional repeated homogeneous message, legitimate external information,
real resource shortages, ordinary bureaucratic conflict, or non-adversarial
uncertainty.

The paper proposes trust structure, perceived risk, and coordination readiness
as decision-environment dimensions. It supplies no validated measurement scale,
threshold, detector, intervention policy, or empirical dataset. These constructs
must remain derived analyses with stated methods and limitations. They may not
be inserted into the world as hidden global variables that manufacture the
desired result.

## 2. Four layers that must not be confused

| Layer | Current status | What it means |
|---|---|---|
| Existing Cybernetic Influence causal/active runtime | **Implemented** | A substantial typed simulator and evidence system that remains the capability baseline but is not the adopted long-term lifecycle authority. |
| Regional outbreak/Waltzman demonstration | **Implemented, scenario-specific** | A rich 26-role world with person profiles, exogenous sources, CSO roles, exact resource allocation, and retained evidence; it still uses bespoke configuration and scenario mechanisms. |
| Concordia bridge/port research probe | **Observed, disposable** | Evidence that stock Concordia public seams can host one canonical-world/context/intent/patch flow with authentic Luna calls. It is not retained production code. |
| Concordia-first general product architecture | **Accepted and designed, not implemented** | The intended product boundary and next vertical. No current public demo should be described as already using it. |

This separation is essential. The old runtime demonstrates capabilities the new
architecture may selectively preserve. The outbreak demonstrates a substantive
simulation, not general composition. The disposable probe reduces foundation
risk, not product risk. The accepted ADR establishes direction, not completion.

## 3. Current Cybernetic Influence ontology and machinery

### 3.1 One authoritative world

The current runtime places canonical facts in one validated `CausalState`.
Prompts, memories, narratives, graphs, and analyses are projections or consumers
of that state and its event history. They are not independent mutable worlds.

Primary source:

- `src/cybernetic_influence/causal_core/models.py`
- `CausalState`
- `StatePatch`
- state and cross-reference validators

This prevents a fact from being true in narrator prose, false in the mechanism
state, and absent from retained evidence.

### 3.2 Existence is separate from agency

`EntityState` records that a persistent referent exists. Its open
`entity_kind` label does not grant cognition or action. A person, truck, court
filing, bridge, software service, message carrier, or fuel stock may all exist
as entities. Only a separately registered `ActiveSystemSpec` gives an entity a
scheduled autonomous process.

This is how an ordinary car is represented:

- the car exists, has state, and may have a placement;
- people or controllers may attempt to use it;
- its current state and environment expose possible affordances;
- transition authority decides whether an attempted use succeeds; and
- it receives an active-system binding only if autonomous onboard behavior is
  inside the selected representation.

The adopted Concordia architecture keeps this conceptual separation even though
Concordia's base `Entity` interface provides `act` and `observe` methods. Active
or externally driven processes become Concordia entities. Inert things normally
remain records inside the canonical-world component rather than fake actors.

### 3.3 Current persistent records

The existing runtime uses strict Pydantic collections rather than treating the
world as an unrestricted generic property graph.

| Record | Current function |
|---|---|
| `FactState` | Addressable value with public, analyst, or mechanism visibility. |
| `EntityState` | Persistent referent; kind does not imply agency. |
| `ContainerState` | Typed routing or broadcast locus, distinct from spatial location. |
| `PlaceState` | Spatial locus in an acyclic containment hierarchy. |
| `PlacementState` | Entity's current immediate place. |
| `SpatialLinkState` | Undirected adjacency; not automatically traversable. |
| `PortState` | Typed input or output interface owned by an entity or mechanism. |
| `ConnectionState` | Directed compatible route with delay and enabled state. |
| `MechanismSpec` | Declared exact transition authority and read/write surface. |
| `CarrierState` | Stateful information-holding surface. |
| `RepresentationToken` | Content revision with hash, encoding, source, lineage, and visibility. |
| `ObservationRecord` | Actor-visible delivered surface, distinct from hidden provenance. |
| `AnalyticalBoundary` | Nonexecuting analyst-selected grouping. |

These records have provided useful precision but are not all proposed as an
irreducible universal ontology. The generalized architecture instead seeks a
small kernel plus registered subsystem contracts. Exactness is selected when a
question requires it.

### 3.4 Attempt, capability, authorization, feasibility, and outcome

The current physical-access example separates:

```text
badge presentation attempt
    -> authentication
    -> policy authorization
    -> latch actuation
    -> physical threshold crossing
    -> observation of the result
```

A valid badge may fail authorization. Authorization may coexist with a jammed
latch. Neither changes the person's location unless the movement transition
commits successfully.

The general product should preserve the conceptual distinctions:

- **Capability:** an actor-side ability, such as physical manipulation,
  locomotion, communication, or computer use.
- **Competency:** degree or reliability with which the actor can exercise a
  capability.
- **Affordance:** an action made possible by the relationship among actor
  capability, object/system properties, and current environmental conditions.
- **Attempt interface:** a simulator path through which an actor may propose an
  action now.
- **Authorization:** an in-world policy, legal, social, or technical permission.
- **Feasibility:** whether material and causal conditions permit success.
- **Outcome:** the canonical consequence actually committed.

These concepts should not collapse into a long list of action-specific ports.
An exposed simulator interface also must not be described to an actor as though
it were necessarily legal or institutionally legitimate.

### 3.5 Information is a lineage

The current information model separates:

- world truth;
- an information carrier;
- a representation revision on that carrier;
- actual protected provenance;
- an apparent source visible to a recipient;
- delivery through a channel/interface;
- an observation received by a particular actor; and
- the actor's interpretation or memory.

Delivery does not make content true. Observation does not imply attention,
belief, agreement, or action. Copying creates a new representation with parent
lineage rather than moving a free-floating message object.

This boundary should remain comparatively strict even when an omniscient LLM
game master adjudicates reality. Adjudicator access to hidden truth must never
automatically place that truth in the actor's cognition.

### 3.6 Relations, direction, and arity

The current runtime contains several distinct relationship forms:

- directed port connections and effect routes;
- undirected spatial adjacency;
- containment and placement;
- ownership and component binding;
- representation derivation;
- observation delivery;
- causal-parent edges; and
- analytical-boundary membership.

A configured route is only a possible pathway. A retained routed-effect event
is evidence that something used it. A state commit is evidence of the resulting
world change.

There is no general arbitrary n-ary relation object. Exact n-ary causal rules
are usually reified as mechanism nodes with multiple inputs and outputs.
Membership uses multiple binary edges. Temporally qualified relations such as
delegation, commitments, contested authority, and witnessed agreements remain
largely scenario-specific facts or artifacts.

The open question is not whether to turn every semantic relation into a typed
edge. It is which recurring relations require identity, parties, roles,
provenance, validity intervals, and lifecycle to support the questions analysts
actually ask.

## 4. The current person model

The implemented person model is substantially richer than:

```text
LLM + role mandate + country context
```

That simplified characterization described an earlier scenario shortcut, not
the shared person contract now used by the outbreak scenario.

### 4.1 Authored person description

`PersonDraft` contains:

- stable identity and name;
- position;
- disposition;
- autobiographical or situational memories; and
- a `BehavioralProfileDraft` with natural-language lists of:
  - values;
  - goals;
  - beliefs, which may be mistaken;
  - decision tendencies;
  - social perceptions;
  - current affect, attention, confidence, fatigue, or intent;
  - capabilities; and
  - limitations.

Primary sources:

- `src/cybernetic_influence/authoring/models.py`
- `src/cybernetic_influence/authoring/live.py`
- `src/cybernetic_influence/authoring/prompts/scenario_draft.yaml`
- `src/cybernetic_influence/scenarios/regional_outbreak.py`

These are descriptive semantic statements, not numeric psychological variables
or action scripts. The person renderer explicitly separates:

```text
personal values and preferences
    != position expectations
    != technically available attempts
    != in-world authorization
    != physical success
```

A position supplies responsibilities, information access, controlled artifacts,
resource dependencies, accountability, and expected conduct. These are
institutional “oughts,” not automatically the person's own values, commands the
person must obey, or proof that an action is impossible.

### 4.2 Runtime cognition

At activation, the current LLM person receives only:

- its rendered person profile;
- committed private memory;
- newly delivered observations from declared paths;
- currently exposed attempt interfaces and accessible representations;
- activation reason and modeled time; and
- action, memory, and provider bounds.

It does not receive the complete canonical world, hidden provenance,
mechanism-only facts, another person's private state, same-moment proposals,
analytical boundary definitions, or engine-owned identifiers.

The person returns structured private orientation, optional memory updates,
zero or more bounded action attempts, or an explicit reason for silence. Memory
updates commit only if the activation succeeds.

### 4.3 Person-fidelity gaps

The system has no validated computational model of human behavior. Important
limitations include:

- no independent attention stage deciding what a person notices;
- no generic belief object with confidence, provenance, contradiction, and
  decay;
- limited psychologically meaningful forgetting;
- no general persistent plan representation;
- no generic relationship-dependent credibility update;
- no calibrated stress, workload, or cognitive-load dynamics;
- limited self-scheduling by generic LLM people;
- substantial dependence on the LLM to maintain cross-context consistency; and
- no empirical evidence that the same profile behaves stably or human-plausibly
  across scenarios.

The preferred direction is not to turn every subjective relationship into a
typed global value. A statement such as “I trust Ana's technical judgment but
fear her ministry's political incentives” can remain in personal memory.
Concrete facts—who communicated, what was delivered, which commitment was made,
which resource someone controlled—belong in world and event evidence. An
analyst may derive a relationship or reliance network from those observations
without using that network to dictate behavior.

The reviewer should identify the smallest explicit cognitive machinery needed
to prevent the LLM from implicitly controlling perception, memory update,
belief revision, and action all at once, without imposing a rigid theory of
mind.

## 5. Organizations, institutions, and sociotechnical networks

The ontology should not treat “organization” as a universal primitive that
automatically thinks or acts. At detailed resolution, an organization may be a
sociotechnical network containing:

- people and offices;
- documents, records, procedures, and software;
- authority claims and controlled artifacts;
- resource ownership and dependencies;
- communication channels;
- sanctions and enforcement processes;
- routines and histories; and
- technical infrastructure.

Organization-like effects then emerge from patterns such as:

- whose statements are accepted;
- which artifacts are required;
- who can interrupt a resource flow;
- which commitments are enforced;
- which pathways become reliable;
- which actors become bottlenecks or intermediaries; and
- which repeated routines stabilize.

The current Cybernetic Influence runtime represents organizations as
execution-inert `AnalyticalBoundary` groupings over concrete components. That is
useful for avoiding a duplicate group mind, but current boundaries are flat,
authored, static, and not inferred from behavior.

The adopted generalized architecture adds a question-relative qualification. A
subsystem the analyst describes as a ministry, firm, market, computer, or
logistics network may be represented by one coarse active surrogate when its
internals are deliberately outside the research question. The same subsystem
may instead be represented as detailed components. The architecture must prevent
the coarse surrogate and fine-grained subsystem from independently producing
the same causal behavior unless an explicit coupling contract assigns them
different responsibilities.

Therefore:

- organizationhood does not intrinsically imply agency;
- analytical boundaries do not execute;
- a declared coarse subsystem surrogate may execute;
- representation depth and causal responsibility must be explicit; and
- dynamic, overlapping, nested, contested, or emergent boundaries remain open
  analytical capabilities rather than governing ontology.

## 6. Current authoring and why it is not yet general

### 6.1 Actual free-text code path

The application has a free-text authoring interface. An LLM produces a strict
`ScenarioDraftProposal`, the proposal is retained by revision, a user can edit
supported fields, and approval precedes compilation.

The exact executable union is currently closed:

- `ResourceRequestWorkflowDraft`;
- `InformationCampaignWorkflowDraft`;
- `ComponentCompositionWorkflowDraft`; and
- `CoordinationDecisionWorkflowDraft`.

Primary sources:

- `src/cybernetic_influence/authoring/models.py`
- `src/cybernetic_influence/authoring/service.py`
- `src/cybernetic_influence/authoring/compiler.py`
- `src/cybernetic_influence/authoring/component_composition.py`

`ScenarioDraftProposal.workflow` is the union of those four types. Compiler
dispatch selects a family-specific fixture. The current
`component_composition_v1` vertical requires a fixed reviewed delivery and
recording pattern and projects it into the existing information-campaign
fixture.

Therefore the interface accepts free text, but the executable authoring system
is not open-ended. A request for a port containing ships, storage, workers,
fuel, road transport, customs procedures, communications, queues, weather, and
autonomous decision-makers cannot currently compile into an arbitrary world
without new scenario-specific Python.

### 6.2 Intended general authoring seam

The target is:

```text
analyst prose
    -> semantic GeneralWorldSpec proposal
    -> human review and direct editing
    -> reference and contract validation
    -> binding only to registered implementations
    -> executable Concordia configuration
```

The minimum semantic composition should be able to name:

- persistent referents and state;
- active and inert things;
- places, placement, topology, and routes;
- carriers, representations, channels, and observations;
- capabilities and interfaces;
- resources and declared constraints;
- relationships and dependencies where material;
- registered transition authorities;
- active-system bindings;
- initial conditions and timing;
- representation depth, fidelity assumptions, and invalid questions;
- relevant generic and subsystem invariants; and
- evidence and analysis selections.

The authoring LLM may generate semantic configuration. It may not invent Python
implementations, unreviewed executable semantics, or implementation identities.
Exact, stochastic, external, scripted, replay, and LLM authorities must already
be registered and declare their contracts. Open-ended behavior may be delegated
to a registered LLM adjudicator rather than requiring generated code.

Convenience templates such as “outbreak response” or “port logistics” may
compile into this same representation. They must not become the foundational
runtime architecture.

### 6.3 Relationship to the shared data-contracts repository

The current Cybernetic Influence code does not import the shared
`data_contracts` package. `data_contracts.composition` was evaluated as a
possible compile-time authoring substrate, not a runtime authority. The accepted
ADR deliberately defers that dependency until the production composition seam
reveals a concrete duplication or interoperability need.

The reviewer should decide whether the project should:

- define the minimum Pydantic contracts locally first and later align them;
- adopt shared composition contracts immediately; or
- use an adapter boundary while preserving Cybernetic Influence-specific
  runtime semantics.

It should not assume that a shared manifest library discovers implementations,
owns simulation state, or executes transitions.

## 7. Current execution machinery and retained evidence

The existing pre-migration runtime path is:

```text
reviewed proposal
    -> family-specific compiler and trusted registry
    -> CausalScenario + ActiveSystemSpec bindings
    -> multirate active-system activation
    -> bounded actor input projection
    -> structured ActionIntent
    -> routed EffectEnvelope
    -> exact MechanismSpec handler
    -> validated MechanismOutcome
    -> atomic StatePatch
    -> observations and future work
    -> checkpoint, replay, graphs, narrative, and theory analysis
```

Key implementation locations:

| Concern | Current code |
|---|---|
| Canonical state and records | `src/cybernetic_influence/causal_core/models.py` |
| Routing, exact transition execution, validation, commit | `src/cybernetic_influence/causal_core/engine.py` |
| Active systems and action intents | `src/cybernetic_influence/active_runtime/models.py` |
| Active scheduling and moment commit | `src/cybernetic_influence/active_runtime/engine.py` |
| Native LLM cognition | `src/cybernetic_influence/active_runtime/llm.py` |
| Authoring schemas | `src/cybernetic_influence/authoring/models.py` |
| Compilation | `src/cybernetic_influence/authoring/compiler.py` |
| Component receipt | `src/cybernetic_influence/authoring/composition.py` |
| General run retention | `src/cybernetic_influence/run_store.py` |
| Graphs and analyst projection | `src/cybernetic_influence/causal_core/projection.py` |
| Narrative/presentation | `src/cybernetic_influence/presentation.py` |
| Evidence bundle and theory modules | `src/cybernetic_influence/analysis/theory_analysis.py` |
| Coordination measures | `src/cybernetic_influence/analysis/coordination_measurement.py` |
| Scenario-specific experiments | `src/cybernetic_influence/experiments/coordination_experiment.py` |

The event model distinguishes intent, attempt, emission, routing, mechanism
execution, state commit, observation, and completion. Checkpoints retain
scenario and execution fingerprints, state, event history, pending work,
private active-system state, calls, budgets, and implementation identities.
Completed runs can reopen without model execution. Narration and analysis can
fail independently without erasing a successful world trajectory.

These are valuable capability precedents. They are not automatically universal
requirements for every Concordia component. Migration should preserve a
distinction only when it contributes observable value or protects the current
question.

## 8. The regional outbreak example: what is autonomous and what is authored

The outbreak case should not be described as merely “26 AI agents voting.” It
contains:

- 26 reviewed participant configurations;
- values, goals, beliefs, tendencies, social perceptions, current state,
  capabilities, limitations, memories, positions, and private institutional
  context;
- separate exogenous source processes;
- optional CSO monitor, diagnostician, and planner roles;
- a deterministic allocation authority;
- typed stance, message, intervention, and resource interfaces;
- exact round, decision-gate, source-delivery, CSO, and allocation mechanisms;
- resources with custody, quantity, availability, dependencies, and evidence;
  and
- coalition and national-delegation analytical boundaries.

Different process types have different authority surfaces. Coalition
participants cannot emit source or CSO actions. Source and CSO roles cannot
emit coalition stances. The planner does not directly move resources. Exact
allocation authority owns resource custody and quantities.

| Element | Model-selected | Scenario- or system-authored |
|---|---|---|
| Person configuration | An authoring LLM may propose descriptive content | Schema, reviewed fields, approved profile, position, and initial world |
| Coalition action | Stance, rationale, concern, request, and other permitted semantic output | Available attempt interfaces, response schema, delivered evidence, and decision gate |
| Source behavior | A source model may select among its authorized responses | Source role, objectives, available interface, mapping, and world consequences |
| CSO monitor/diagnostician/planner | Classification, diagnosis, or action-class selection | Taxonomies, action catalogue, context, and registered consequences |
| Resource movement | None unless a relevant authority proposes it | Deterministic allocation rules, stocks, custody, dependency checks, and validation |
| Collective outcome | No model directly sets the gate | Fixed deterministic decision rule over participant outputs |
| Analysis | Some findings may be LLM-coded | Evidence bundle, method labels, source data, and limitations |

Historical reviewers correctly identified that selecting a response class is
not the same as inventing an effective intervention. In some retained runs, the
scenario maps a model-selected action class to a comprehensive preauthored fact
package. That demonstrates taxonomy routing and participant reassessment more
than difficult intervention design. The retained evidence should always expose
this authorship boundary.

The outbreak currently reuses the richer shared person context. It still uses
scenario-specific Python, closed action catalogues, and dedicated authoring and
public surfaces. It is a capability baseline and research case, not proof of
the general product architecture.

## 9. Adopted Concordia-first architecture

### 9.1 Why use Concordia if the project already has a runtime?

Concordia provides mature reusable infrastructure for:

- entity/component composition;
- actor memory and cognition components;
- agent and game-master interaction;
- sequential, simultaneous, and asynchronous execution engines;
- actor selection and simulated time;
- prefab/configuration assembly;
- checkpoint-oriented component state;
- extensible game-master components; and
- a broader ecosystem of reusable agent/simulation patterns.

The strategic argument is that Cybernetic Influence should specialize in the
world, information, transition, evidence, authoring, and analysis contracts that
differentiate the product rather than maintain a second complete outer agent
framework indefinitely.

### 9.2 Authority boundary

| Concern | Adopted owner |
|---|---|
| Entity/component lifecycle | Concordia |
| Actor selection and outer execution loop | Concordia engine/game master |
| Simulated time and scheduling | Concordia components/engine, extended through public seams if required |
| Actor cognition, planning, and memory | Concordia entities/components configured by project person contracts |
| Provider calls and trace custody | Shared `llm_client` |
| Canonical world truth | Project-owned Concordia game-master component |
| Actor context | Project-owned bounded projection/query service |
| Adjudicator context | Project-owned authority-scoped projection/query service |
| Semantic action intent | Project-owned typed boundary over Concordia's action string seam |
| Transition adjudication | Registered project `TransitionAuthority` implementations |
| Patch validation and atomic commit | Project-owned canonical-world component |
| Information/provenance boundaries | Project-owned canonical-world/context contracts |
| Strict canonical-state checkpoint codec | Project-owned component codec invoked through Concordia lifecycle |
| Evidence and analysis projections | Project-owned retained evidence plus selected Concordia logs |
| General authoring | Project-owned semantic composition and implementation registry |
| UI and theory modules | Adapted Cybernetic Influence projections and readouts |

This is layered integration, but it is not the rejected “Concordia cognition
wrapped around the old Cybernetic Influence environment” design. The old
`CausalSession` and `ActiveRuntimeSession` may not run as a hidden second
environment, scheduler, checkpoint, or transition authority.

### 9.3 Common transition-authority contract

Each transition authority should declare or retain:

- stable implementation identity and version;
- kind: deterministic, stochastic, LLM, external, scripted, or replay;
- semantic scope and accepted intent/effect contract;
- permitted read paths and context-acquisition policy;
- permitted patch/write paths;
- timing semantics;
- model, stochastic, or external configuration;
- assumptions, fidelity, uncertainty, and invalid questions;
- generic and subsystem validators;
- budget or resource limits; and
- evidence linking supplied context, decision, patch, validation, and commit.

Use an explicit deterministic or external model when accounting, conservation,
legal/technical rules, repetition, or small outcome differences are central to
the analytical question. Use an LLM adjudicator when common-sense plausibility
at coarse resolution is sufficient, behavior is open-ended, no trustworthy
formal model exists, or exhaustive affordance enumeration would be artificial.

An authority may return insufficient context or reject adjudication. It should
not be forced to manufacture a confident consequence.

### 9.4 Context is coequal with state and adjudication

Two contexts are deliberately different.

**Actor context** contains what the active system may know or perceive:

- delivered observations;
- private memory and interpretation;
- perceived or exposed affordances;
- accessible representations;
- modeled time and activation reason; and
- permitted attempt channel and bounds.

**Adjudicator context** contains what a transition authority needs to determine
what actually happens:

- canonical actor, target, and resource state;
- relevant placements, topology, routes, and hidden infrastructure;
- applicable policies and constraints;
- recent changes and pending work;
- relevant subsystem models and fidelity declarations; and
- authorized query results.

The context layer should support deterministic initial projection, typed
follow-up queries, optional semantic retrieval, subsystem-specific context
hooks, and retained provenance. Poor judgment and missing context must be
distinguishable after the run.

### 9.5 Structured patches and a small protected kernel

The target `WorldPatch` needs to cover more than scalar fact changes. Candidate
operations include:

- create, retire, replace, or reactivate a persistent record;
- add, disable, remove, or rebind a route or connection;
- change placement or resource custody;
- create or derive a representation and record delivery;
- add or end a temporally qualified relationship;
- bind or unbind an interface, capability, or subsystem implementation;
- schedule, cancel, or complete pending work; and
- request active-system creation or retirement at a safe lifecycle boundary.

The generic mandatory kernel should remain small. Likely invariants include:

- valid identities and references;
- revision and event ordering;
- lifecycle validity and protected history;
- declared read/write authority;
- topology consistency;
- exclusive placement or cardinality where declared;
- representation/provenance and observation boundaries;
- pending-work and timing validity;
- declared custody or conservation constraints; and
- atomic commit or complete rejection.

The kernel should not attempt to mechanize all ordinary causality or encode a
universal social ontology. Subsystems may register stronger invariants when the
question requires them.

### 9.6 Capabilities and open semantic affordances

The actor should be able to propose:

> I crop this screenshot and send it to Bob.

without a preauthored `crop_screenshot_and_email_bob` action. The semantic
intent should name the actor, referents, target or purpose, and relevant detail.
The context and transition authority then determine whether the actor's
capabilities, competency, object properties, software, permissions, network,
and current conditions afford the action.

The design should not require exhaustive enumeration of every affordance. It
may use explicit action components for analytically central behavior and broad
semantic adjudication for peripheral ordinary behavior.

## 10. Concordia source evidence

### 10.1 Inspected boundary

The current local Concordia checkout was inspected at shallow revision:

```text
131ed0d2ea14754539a3feb9dfd3717d11e859df
```

The earlier comparison used revision
`bdb449ab384adf203b09004049184b9176be808f`, but the current shallow checkout
did not contain enough history for a trustworthy source diff. Findings below
describe the current inspected revision only.

Relevant source surfaces included:

- `concordia/typing/entity.py`;
- `concordia/typing/entity_component.py`;
- `concordia/agents/entity_agent.py`;
- `concordia/prefabs/simulation/generic.py`;
- `concordia/environment/engines/simultaneous.py`;
- interrupt scheduling and response components;
- `concordia/document/interactive_document_tools.py`; and
- the stock generative world-state component.

Focused upstream tests covered generic checkpointing, the simultaneous engine,
interrupt scheduling, and interrupt response parsing:

```text
59 passed in 2.49 seconds
```

### 10.2 Source-confirmed useful seams

- `EntityAgent` executes component pre-action, action, post-action, and update
  phases.
- Public component `get_state` and `set_state` seams allow project-owned state.
- Generic simulation exposes public `add_entity` and `add_game_master` methods.
- Checkpoint loading can instantiate a missing entity when its prefab is already
  registered.
- Sequential, simultaneous, and interrupt-oriented scheduling paths exist.
- Simulated time, timers, queues, masks, and pending observations are
  serializable.
- An interactive-document tool loop can call model tools and log tool
  calls/results.

### 10.3 Source-confirmed defaults that are not sufficient

1. `Entity.act` and `Entity.observe` cross the framework boundary as strings.
   Structured intent and observation remain product responsibilities.
2. Generic checkpoint conversion silently drops values that cannot be made JSON
   serializable.
3. `EntityAgent.set_state` catches component restore exceptions, logs them, and
   continues. Strict canonical state cannot accept that failure policy.
4. The stock generative `WorldState` stores LLM-selected string variables. It
   is not a typed canonical world or patch authority.
5. Interrupt scheduling may queue unmatched events for later delivery. That is
   attention scheduling, not a strict information-access boundary.
6. Interactive tool failures are returned to the LLM as error strings. The tool
   loop is not itself a fail-loud trusted world-query boundary.
7. The simultaneous engine presents joint actions for one resolution but does
   not supply typed patch conflicts, transaction isolation, or general resource
   contention semantics.
8. Public entity addition exists, but safe live endogenous spawning, removal,
   component rebinding, scheduler updates, and checkpoint consistency are not
   established.

These limitations justify project components and possibly upstream-compatible
extensions. They do not currently justify maintaining a private fork.

## 11. The bridge/port probe

### 11.1 Trajectory

The disposable research probe used stock Concordia `generic.Simulation`, the
stock `Sequential` engine, public prefab/component interfaces, and one
project-owned game-master world component.

```text
worker and fuel truck begin outside port
    -> worker attempts delivery over north route
    -> destroyed bridge blocks movement
    -> worker learns only that route is impassable
    -> hidden sabotage cause remains world truth
    -> temporary depot and replacement route are created
    -> state checkpoints
    -> a fresh simulation restores the checkpoint
    -> Luna worker proposes an open semantic action
    -> Luna adjudicator proposes placement patches
    -> generic validator checks and commits
    -> worker and truck reach port
```

The provider-free part also verified that corrupt canonical-world state raised
`ValueError` rather than restoring a fallback world.

### 11.2 Authentic model receipts

| Function | `llm_client` trace | Observed output |
|---|---|---|
| Worker continuation | `concordia-foundation-revisit/luna/bridge-port-continuation-v3-final` | `move_fuel_truck` using `temporary_depot_route` |
| Semantic transition authority | `concordia-foundation-revisit/luna/semantic-adjudicator-v3-final` | Replace truck and worker placements with `port` |

Each trace contained one completed `codex/gpt-5.6-luna` call, no model error,
and subscription-included observed cost.

The adjudicator used `/world/entities/...` paths while the validator initially
expected `/entities/...`. A declared `/world` root alias canonicalized the
paths. The validator then checked identities, source placements, enabled route,
write scope, and a narrow hidden-value condition before atomic commit.

### 11.3 Decision-relevant failed attempts

1. The first actor context omitted the worker and truck placements. Luna
   sensibly proposed moving toward the newly mentioned depot rather than
   delivering fuel. This was a context-contract defect, not evidence that Luna
   was too weak.
2. After local state was exposed, Luna used reasonable verbs such as `travel`
   and `move_fuel_truck`, while the exact handler accepted only
   `deliver_fuel`. This exposed the failure of a closed scenario verb registry.
3. The first structured patch used a different root convention and was refused.
   This exposed an underspecified patch-addressing contract.

These failures produced the current requirements for actor-relevant context,
open semantic intent, and one explicit patch-addressing/authority/commit seam.

### 11.4 What the probe establishes

- Stock Concordia can invoke a project canonical-world component.
- Exact and coarse state can coexist in public components.
- Inert topology records can change during a run.
- Dynamic records inside that component can survive checkpoint restore.
- A Luna actor and Luna transition authority can use a common semantic
  intent/patch path once.
- The old Cybernetic Influence runtimes are not required for this bounded path.
- No current evidence requires a private Concordia fork.

### 11.5 What the probe does not establish

- production-quality contracts or packaging;
- arbitrary analyst-authored world composition;
- safe live creation/removal of autonomous Concordia entities;
- concurrent conflicting patch semantics;
- general information noninterference;
- robust or realistic LLM adjudication;
- cross-domain reuse;
- scale, latency, cost, or long-run stability;
- behavioral fidelity of human agents; or
- adoption by any current product scenario.

## 12. Candidate architecture comparison

| Candidate | Current judgment | Principal advantage | Principal risk |
|---|---|---|---|
| A. Concordia foundation plus project world components | **Accepted; reaffirmed** | Reuses lifecycle, cognition, engine, time, and component infrastructure while preserving differentiated world/evidence contracts | Project components could quietly grow into a second engine or fail to preserve needed guarantees |
| B. Concordia cognition around the old CI environment | **Rejected for now** | Easiest preservation of current exact runtime | Permanently duplicates state, scheduling, checkpoint, and execution authority |
| C. CI foundation with compatibility adapters | **Fallback** | Strongest preservation of current semantics and lowest migration risk | Maintains a complete bespoke framework and limits ecosystem leverage/general flexibility |
| D. Independent CI product | **Rejected** | Maximum control | Highest framework ownership and least reuse |
| Private Concordia fork | **Deferred** | Could repair framework lifecycle or strictness at the source | Immediate long-term merge/upgrade burden without a demonstrated blocker |

The earlier source comparison recommended Candidate C under a frozen premise
that every current Cybernetic Influence invariant was non-negotiable. The
product owner later clarified that the goal is a flexible exploratory simulator
with selective question-relative exactness. Under that product objective,
Candidate A was selected.

A private fork should be reconsidered only if all of the following hold:

1. a required production capability has a focused failing example;
2. the capability cannot be supplied by a project component or stable public
   extension seam;
3. an upstream-compatible patch is unavailable or unacceptable;
4. an adapter would create dual authority or materially weaken the product; and
5. the value of owning the fork exceeds its continuing integration cost.

## 13. Structural endogeneity

The product requires more than changing values in a fixed graph. Relevant
world structure may evolve during a run:

- actors form or dissolve coalitions;
- people join or leave groups;
- a company or task force is created;
- a bridge is destroyed;
- a warehouse or temporary depot is established;
- a communication or transport route appears or fails;
- custody moves;
- a person delegates a capability;
- new records and representations are created;
- an actor acquires a vehicle and new affordances;
- a subsystem changes from coarse to detailed representation; or
- an autonomous process begins, suspends, or retires.

Current capability is uneven:

| Structural change | Existing CI runtime | Concordia source | Probe | General target |
|---|---|---|---|---|
| Fact/value update | Implemented | Mutable component state | Observed | Standard patch |
| Placement change | Implemented through exact mechanisms | Mutable component state | Observed | Standard patch |
| Create inert entity/place/route record | Not general across authoring/runtime | Possible inside component state | Observed for depot/route | Standard lifecycle patch |
| Disable/destroy route | Scenario-local | Possible inside component state | Observed as bridge state | Standard topology patch |
| Create/retire relationship | Mostly facts/scenario code | Possible inside component state | Not tested | Versioned relation/lifecycle patch if needed |
| Create/remove active autonomous entity | Construction-oriented | Public addition exists | Not tested live | Safe-boundary lifecycle operation |
| Rebind components or transition authority | Not general | Not established live | Not tested | Explicit binding operation and checkpoint semantics |
| Dynamic organization/coalition | Analytical or scenario-specific | Possible as records; active lifecycle unknown | Not tested | Network records, boundaries, or declared surrogate lifecycle |
| Simultaneous structural conflict | Scenario-specific canonical ordering | Joint resolution without typed transactions | Not tested | Declared conflict policy or joint authority |

The reviewer should prioritize whether structural patches and active-lifecycle
safe boundaries are sufficient, or whether a deeper engine change is needed.

## 14. Adoption governance and the recurring bypass failure

The project has repeatedly implemented richer shared machinery and later built
scenarios that bypass it. Examples include:

- simplified scenario-specific person prompts despite a richer person model;
- dedicated scenario configuration instead of general authoring;
- component receipts that describe already-built surfaces rather than proving
  the world was composed through the registry; and
- public explanatory graphs disconnected from canonical executable graphs.

The root problem is that implemented capability is mistaken for adoption. A
unit test proves that a component works. It does not prove that an intended
consumer used it.

The proposed correction is a general composition/implementation registry plus
a retained adoption manifest. Each scenario or world should declare:

- semantic composition revision;
- how it was authored;
- which canonical contracts and registered implementations were used;
- person/context path;
- transition authorities and their fidelity;
- information and provenance path;
- structural patch and checkpoint path;
- evidence/analysis path;
- active representation resolution;
- any bespoke exceptions and their bounded rationale; and
- an integration receipt showing that the intended runtime references actually
  executed.

The registry should not become a closed taxonomy of scenario names. It binds
semantic configuration to trusted implementations and rejects unsupported
references. A `PortScenario`, `OutbreakScenario`, or `ElectionScenario` class
should be a convenience layer at most, not the foundation.

The next production vertical is incomplete until one intended product consumer
uses the new contracts. This adoption proof is as important as isolated tests.

## 15. Evidence, autonomy, and authorial control

Every review should ask who selected what.

| Stage | Possible decision owner | Required evidence distinction |
|---|---|---|
| World and initial state | Analyst, template, or authoring LLM plus human review | Authored configuration and assumptions |
| Person profile | Analyst or authoring LLM plus review | Descriptive inputs, not resulting behavior |
| Actor observation | Canonical context projection | What was delivered or exposed, including provenance |
| Actor intent | Active model, script, or external process | Raw/structured output and model trace |
| Adjudication | Declared transition authority | Supplied context, authority identity, reasoning/output, insufficiency |
| Proposed consequence | Transition authority | Structured patch before validation |
| Validity and commit | Generic kernel and subsystem invariants | Checks, rejection reasons, exact committed patch |
| Actor learning | Observation path plus actor interpretation | Delivered surface separate from hidden cause |
| Aggregate interpretation | Analyst or theory module | Method, evidence, uncertainty, and nonclaims |

Autonomy does not mean the scenario author contributes nothing. Every
simulation has authored ontology, initial conditions, prompts, action surfaces,
transition authorities, and validity rules. Credibility comes from exposing
those choices, distinguishing them from model selections, varying them when
appropriate, and avoiding claims that the model independently discovered what
the author supplied.

## 16. Explicit uncertainty register

### 16.1 Resolved enough for the foundation decision

| Question | Current answer |
|---|---|
| Can exact and coarse state coexist in Concordia components? | Yes. |
| Can stock Concordia invoke a project canonical world without the old CI runtime? | Yes, in the bounded probe. |
| Can inert topology records change and survive restore? | Yes, in one canonical component. |
| Can authentic Luna actor and adjudicator calls use the path? | Yes, once. |
| Is a private fork currently required? | No evidence says so. |

### 16.2 Indicated but not established

| Question | Evidence boundary |
|---|---|
| General composition | The component shape is compatible, but no arbitrary analyst-authored world compiled through a reusable contract. |
| Cross-domain reuse | The sequence is domain-neutral in form, but only one logistics movement executed. |
| Information safety | One hidden cause did not leak; this is not a general noninterference proof. |
| LLM adjudication | Luna produced one valid final patch after interface defects were corrected; reliability and realism are unknown. |
| Strict checkpoint adequacy | A strict subclass and JSON-safe state worked; production codec boundaries remain undecided. |
| Rich cognition reuse | Concordia has relevant components; no migration proves equivalence to the reviewed person contract. |

### 16.3 Unknown and decision-sensitive

1. Can a live Concordia engine safely create, remove, suspend, replace, or
   rebind autonomous entities/components without stale scheduler, game-master,
   or checkpoint references?
2. Should active-system creation occur during a patch commit or at a defined
   safe boundary between engine moments?
3. What is the smallest generic conflict language for incompatible simultaneous
   patches and resource races?
4. Where is the transaction boundary when deterministic, stochastic, LLM,
   replay, and external authorities affect the same moment?
5. How broad may an LLM adjudicator's read and write scope be before the kernel
   becomes unsafe or overengineered?
6. Which world queries do actors and adjudicators need, how are they authorized,
   and how is query provenance retained without overwhelming prompts?
7. Can general information noninterference be preserved across all transition
   authority kinds?
8. Which identity, topology, placement, representation, custody, conservation,
   and history constraints are universal kernel invariants versus optional
   subsystem rules?
9. How do coarse surrogates and detailed subsystems declare causal
   responsibility and avoid double execution?
10. Can arbitrary analyst prose compile into the general composition contract
    without generated executable code, unsupported bindings, or closed scenario
    families?
11. Can a materially different domain reuse the same composition, context,
    intent, authority, patch, validation, checkpoint, and evidence seams?
12. What latency, cost, behavioral stability, and failure patterns appear with
    many active systems, multirate processes, repeated seeds, and long runs?
13. Are the inspected public Concordia seams stable enough for a long-lived pin?
14. Which minimal cognitive mechanisms materially improve human-agent fidelity
    without hard-coding a premature semantic psychology?
15. How should dynamic, overlapping, nested, contested, or emergent analytical
    boundaries be represented and compared without becoming executors?

## 17. Designed next production vertical

The next slice is deliberately smaller than a broad migration.

### 17.1 Stable example

A worker and fuel truck begin outside a port. A destroyed bridge blocks the
initial route. A temporary depot and route are created during the run. State is
checkpointed and restored. The worker proposes its next action in ordinary
language. A Luna transition authority proposes a structured patch. Generic
validation commits or rejects it. The worker receives only an authorized
observation, not the hidden cause of the bridge failure.

### 17.2 Minimum production contracts

| Contract | Responsibility |
|---|---|
| `GeneralWorldSpec` | Persistent things, state, places, placements, representations, resources, topology, active bindings, timing, fidelity assumptions, and invariants |
| `ActorContext` | Only actor-authorized observations, memory, representations, and affordance-relevant state |
| `SemanticActionIntent` | Open-ended attempted action without a closed scenario verb union |
| `TransitionAuthoritySpec` | Kind, implementation, read/write authority, context policy, fidelity, assumptions, provenance, and invalid questions |
| `WorldPatch` | Typed value and structural mutations against canonical paths |
| `PatchValidationResult` | Acceptance/rejection and explicit generic/subsystem reasons |
| `TransitionEvidence` | Context, intent, authority call, patch, validation, commit, observation, trace IDs, and checkpoint lineage |

### 17.3 Required evidence

The production vertical should establish:

- stock Concordia owns the outer lifecycle;
- neither old CI runtime executes;
- the world is configured from domain-neutral contracts rather than a
  `PortScenario` class;
- dynamic inert topology survives strict fresh-instance restore;
- corrupt or lossy restore fails visibly;
- the actor does not receive the hidden cause without an information path;
- Luna produces an action verb not enumerated by scenario code;
- a declared Luna authority proposes a structured patch;
- generic validation, not the LLM, owns commit;
- invalid references, unauthorized writes, topology errors, and declared
  conservation violations reject without partial mutation;
- evidence separates author input, actor choice, adjudicator inference,
  deterministic validation, and outcome; and
- the two authentic calls retain complete `llm_client` lifecycle traces.

### 17.4 Explicit non-goals

- migrating the outbreak demo or every current feature;
- building a public UI;
- implementing arbitrary conversational authoring;
- solving live autonomous-entity creation;
- solving concurrent or distributed transactions;
- inventing an exhaustive social or physical ontology;
- proving cross-domain generality, scale, realism, or predictive validity;
- broad compatibility, security, or production hardening; or
- deleting the old runtime before an intended consumer adopts the new path.

## 18. High-value challenge scenarios after the first vertical

These are architecture probes, not demands to implement immediately.

### A. Free-text port world

From prose, compose people, ships, storage, trucks, fuel, roads, a bridge,
software, communications, queues, weather, and active systems without selecting
a named `PortCrisis` runtime type or adding Python.

### B. Destroyed bridge and bounded knowledge

Destroy the only bridge, then have an actor attempt travel later. The
adjudicator retrieves the hidden route state, but the actor receives only an
observation justified by local sensors or communication.

### C. Endogenous coalition

Actors create a coalition and channel, acquire a warehouse, delegate a
capability, add and remove members, and dissolve the coalition. Historical
projections show structure at each revision.

### D. Novel affordance

An actor wedges a chair under a door handle without a preauthored action verb.
Capability, object properties, local conditions, and coarse physical
adjudication produce a patch and limitations.

### E. Coarse versus detailed ministry

Run one representation with a ministry as a coarse LLM surrogate and another
with people, records, software, and procedures. Prove that the surrogate and
detailed system cannot both independently execute the same responsibility.

### F. Coarse versus detailed computer

Use LLM adjudication for ordinary screenshot editing in a diplomatic scenario,
then use accounts, permissions, services, and network paths in a cyber scenario
behind a compatible external interface.

### G. Simultaneous resource race

Two actors attempt to acquire the same truck from one frozen moment. Outcome
must come from a declared conflict policy or joint authority, not incidental
application order.

### H. Edited information lineage

An actor edits a screenshot and transmits it with apparent provenance different
from protected actual lineage. The recipient sees only the delivered surface;
authorized analysis can reconstruct derivation.

### I. Insufficient context

An unusual action lacks necessary state. The adjudicator requests more context
or returns `insufficient_context` rather than inventing a confident result.

### J. Adoption manifest

Create a new scenario and prove through a machine-readable receipt that it used
the canonical composition, person/context, transition, patch, information,
checkpoint, and evidence paths, with every exception visible.

## 19. Questions for the reviewer

### 19.1 Overall architecture

1. Should the project proceed with the adopted Concordia-plus-project-world
   architecture, amend its ownership boundary, or reverse to the independent CI
   runtime? Explain the strongest reason and strongest counterargument.
2. Does the project-owned canonical-world component remain a legitimate
   Concordia component, or is it likely to become a second hidden simulation
   engine? Give a concrete boundary test.
3. Is “do not fork yet” correct? What exact future evidence should trigger a
   private fork, upstream contribution, adapter, or foundation reversal?
4. Which existing Cybernetic Influence capabilities are genuinely
   differentiating and should migrate? Which should be discarded rather than
   preserved for compatibility?

### 19.2 World and transition contracts

5. Is the common `TransitionAuthority` abstraction sufficient for exact,
   stochastic, LLM, external, scripted, and replay behavior?
6. Which guarantees belong to every transition authority, and which belong
   only to exact implementations?
7. Is the proposed protected kernel too small, too broad, or correctly scoped?
8. What structural patch operations and lifecycle rules are missing?
9. What is the simplest credible simultaneous-conflict and transaction model?
10. Can an LLM authority safely receive broad patch discretion under generic
    invariants, or is a more constrained intermediate language required?

### 19.3 Context and information

11. What is the smallest context/query architecture that reliably supplies
    relevant current state without recreating a hand-coded action decomposer?
12. How should it handle distant causal constraints, stale records, temporal
    qualification, semantic documents, and missing information?
13. Are actor context and adjudicator context sufficiently separated?
14. Which protections are necessary to prevent hidden-state leakage without
    overengineering ordinary wargaming?

### 19.4 Agency and person fidelity

15. Is the current descriptive person profile an appropriate substrate for LLM
    people?
16. Which minimal additions—attention, belief provenance/confidence,
    relationships, persistent plans, stress/workload, forgetting, or
    self-scheduling—would most improve behavioral plausibility?
17. Which subjective concepts should remain natural-language memory rather than
    canonical typed variables?
18. How should capability, competency, perceived affordance, technical attempt,
    authorization, feasibility, and outcome interact without an exhaustive
    action catalogue?

### 19.5 Organizations and representation depth

19. Is the detailed sociotechnical-network/coarse-surrogate distinction sound?
20. What minimum contract prevents coarse and fine representations from double
    executing the same causal function?
21. How should representation resolution change during a run, if at all?
22. Which organization-like structures require first-class lifecycle records,
    and which should remain artifacts, memory, or analyst projections?

### 19.6 Authoring and adoption

23. Is the proposed `GeneralWorldSpec` the correct general composition seam?
24. What should be semantic configuration, what must be a registered trusted
    implementation, and what may be left to LLM adjudication?
25. Should the project use the shared `data_contracts.composition` package now,
    later, or not at all?
26. Is an adoption manifest sufficient to stop future scenario bypass? What
    enforcement belongs in code, tests, or repository lifecycle policy?
27. What is the smallest second domain needed to establish meaningful
    generality after the port vertical?

### 19.7 Evidence and product claims

28. Does the proposed evidence chain sufficiently distinguish authored inputs,
    autonomous choices, adjudicator inference, validation, canonical outcome,
    and later interpretation?
29. What sensitivity or robustness machinery is essential for exploratory
    validity before building a general experiment workbench?
30. Which claims about Waltzman-inspired coordination mechanisms are supported
    by simulation evidence, and which remain merely executable hypotheses?

### 19.8 Priority and overengineering

31. Which three gaps have the highest expected analytical value per engineering
    hour?
32. Which proposed contracts or invariants are unnecessary complexity for an
    exploratory wargaming product?
33. Is the bridge/port production vertical still the highest-value next step?
    If not, propose a more discriminating vertical that can be completed quickly.

## 20. Requested review output

Please begin with a short verdict:

- **Proceed** with the adopted boundary;
- **Proceed with amendments**;
- **Return to the independent CI foundation**; or
- **Evidence insufficient**, naming the smallest decisive probe.

Then provide:

1. the five most consequential architectural strengths;
2. the five most consequential gaps or risks;
3. a ranked list of the next three high-value changes;
4. a specific recommendation on whether to fork Concordia;
5. a specific recommendation on the minimum person-fidelity improvement;
6. a specific recommendation on structural endogeneity and simultaneous
   conflicts;
7. a specific recommendation on general authoring and adoption enforcement;
8. anything that appears overengineered relative to exploratory wargaming; and
9. any claim in this packet that seems unsupported, ambiguous, or internally
   inconsistent.

For each major issue, please use this compact structure:

```text
Issue:

Current behavior or evidence:

Packet accuracy:
- accurate / incomplete / ambiguous / incorrect

Product-intent fit:
- aligned / narrower than intended / contradictory / unresolved

Existing abstraction that solves part of the problem:

Smallest viable change or decisive probe:

Tradeoffs:

Priority:
- P0 / P1 / P2 / defer / reject

Recommendation:
```

Please explicitly identify any uncertainty you believe the packet has
prematurely resolved and any open issue that does not need to be solved for the
intended product.

## 21. Source ledger and authority order

| Source | Role | Used for |
|---|---|---|
| `docs/GOAL.md` at `d5f2259` | Canonical active outcome | Product identity, acceptance, nonclaims |
| `docs/ROADMAP.md` at `d5f2259` | Canonical direction | Critical path and capability status |
| `docs/adr/013-generalized-simulator-foundation.md` | Accepted decision | Concordia ownership boundary and alternatives |
| `docs/research/027-concordia-architecture-revisit.md` | Primary current-source evidence | Concordia inspection, probe, traces, defects, and uncertainty register |
| `docs/handoffs/027-foundation-implementation.md` | Designed production boundary | Next vertical, contracts, acceptance, stop conditions |
| `docs/research/general-purpose-simulator-ontology-and-machinery.md` | Pre-migration architecture dossier, amended | Current CI ontology, code paths, implementation/adoption gaps |
| `docs/research/001-from-minds-to-coordination.md` | Source-evidence note | Waltzman theory scope and limitations |
| `src/cybernetic_influence/**` and focused tests | Primary implementation evidence | Current runtime behavior and authoring constraints |
| Concordia checkout at `131ed0d2...` | External framework source | Public extension seams and default limitations |
| Workspace sibling `Cybernetic_Influence_V3_Architecture_Review.md` | Prior external advisory memo | Review questions and recommendations; not canonical product authority |

Authority conflicts are resolved in this order: current goal and roadmap for
product direction, accepted ADRs for architectural decisions, primary source or
execution evidence for observed behavior, and advisory reviews for criticism.
Historical plans and retained runs remain evidence but do not override current
direction.

Excluded source classes include unrelated historical deployment notes, obsolete
UI iterations, archived plans not referenced by current authority, and old run
narratives not needed for the architecture question. They were not allowed to
reacquire authority through this synthesis.

## 22. Compact glossary

**Active system** — A scheduled autonomous or externally driven process bound
to a persistent referent and one implementation.

**Actor context** — The bounded information, memory, representations,
affordances, time, and limits available to an acting process.

**Adjudicator context** — The canonical and possibly hidden state a transition
authority is authorized to use to determine what actually happens.

**Affordance** — An action possible because of the relationship among actor
capability, object/system properties, and current environmental conditions.

**Analytical boundary** — A reversible nonexecuting grouping used to inspect a
system at a selected scale.

**Canonical world** — The sole authoritative versioned state and history against
which transitions and observations are validated.

**Capability** — An actor-side ability; it is distinct from competency,
authorization, and outcome.

**Coarse surrogate** — An active representation of a subsystem whose internal
machinery is intentionally omitted at the selected resolution.

**Exact transition authority** — Code-defined execution that deterministically
maps declared inputs to a proposed consequence. “Exact” describes execution,
not empirical truth.

**Information representation** — A particular content revision encoded on a
carrier with provenance and lineage.

**Institution** — In the detailed representation, an emergent stable pattern of
sociotechnical relationships, dependencies, artifacts, routines, authority, and
enforcement; it is not necessarily a fundamental simulator atom.

**Open semantic intent** — An actor's proposed action expressed without
requiring a scenario-specific enumerated verb for every possible behavior.

**Organization** — An analyst or actor concept that may be represented as a
detailed sociotechnical network, an analytical boundary, or a declared coarse
active surrogate depending on resolution.

**Representation depth** — The chosen internal detail and transition model for
a subsystem, together with what it preserves, omits, and cannot answer.

**Structural endogeneity** — The ability for world topology, membership,
relationships, bindings, entities, and processes—not only scalar values—to
change as consequences of the run.

**Transition authority** — A declared deterministic, stochastic, LLM, external,
scripted, or replay implementation that maps intent and authorized context to a
proposed world patch.

**World patch** — A typed, evidence-linked proposal to change canonical state or
structure, committed only after authority and invariant validation.
