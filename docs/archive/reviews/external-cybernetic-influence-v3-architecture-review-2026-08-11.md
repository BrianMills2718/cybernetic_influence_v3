---
title: "Architecture Review Memorandum for Cybernetic Influence V3"
subtitle: "Recommendations, questions, uncertainties, concerns, and requested code audit for a general-purpose sociotechnical/world simulator"
author: "Prepared for the coding agent"
date: "August 11, 2026"
---

*Source basis: Ontology and Execution Machinery of Cybernetic Influence V3, revision `a57cf1bc74965a31164c132fbd9868055bcad1e0`, snapshot dated August 11, 2026.*

*Status: architecture audit request; repository verification required before broad implementation.*

# Contents

- [Document status and instructions](#document-status-and-instructions)
- [Executive summary](#executive-summary)
- [Priority map](#priority-map)
- [Corrections and refinements to the earlier review](#corrections-and-refinements-to-the-earlier-review)
- [1. Audit the actual free-text authoring path](#1-audit-the-actual-free-text-authoring-path)
- [2. Replace scenario-family architecture with general world composition, if necessary](#2-replace-scenario-family-architecture-with-general-world-composition-if-necessary)
- [3. Make structural endogeneity a first-class runtime requirement](#3-make-structural-endogeneity-a-first-class-runtime-requirement)
- [4. Clarify the irreducible atoms of the general simulator](#4-clarify-the-irreducible-atoms-of-the-general-simulator)
- [5. Recover the capability, competency, effector, and affordance model](#5-recover-the-capability-competency-effector-and-affordance-model)
- [6. Decide explicitly between exact mechanisms, LLM adjudication, and a common transition-authority model](#6-decide-explicitly-between-exact-mechanisms-llm-adjudication-and-a-common-transition-authority-model)
- [7. Retain a canonical state engine, but keep the mandatory kernel small](#7-retain-a-canonical-state-engine-but-keep-the-mandatory-kernel-small)
- [8. Make context management a first-class architecture component](#8-make-context-management-a-first-class-architecture-component)
- [9. Support open-ended semantic actions through structured world patches](#9-support-open-ended-semantic-actions-through-structured-world-patches)
- [10. Represent organizations and other subsystems at explicit resolution](#10-represent-organizations-and-other-subsystems-at-explicit-resolution)
- [11. Preserve the strong information model and prevent omniscient leakage](#11-preserve-the-strong-information-model-and-prevent-omniscient-leakage)
- [12. Generalize simultaneous-action and conflict semantics](#12-generalize-simultaneous-action-and-conflict-semantics)
- [13. Strengthen component contracts beyond nominal effect types](#13-strengthen-component-contracts-beyond-nominal-effect-types)
- [14. Use evidence carefully: execution lineage is not external causal proof](#14-use-evidence-carefully-execution-lineage-is-not-external-causal-proof)
- [15. Preserve the experiment seam while deferring a general experiment product](#15-preserve-the-experiment-seam-while-deferring-a-general-experiment-product)
- [16. Align the UI with the actual ontology and resolution choices](#16-align-the-ui-with-the-actual-ontology-and-resolution-choices)
- [17. Add adoption governance so scenarios cannot silently bypass canonical seams](#17-add-adoption-governance-so-scenarios-cannot-silently-bypass-canonical-seams)
- [18. Reframe the framework-foundation decision around these requirements](#18-reframe-the-framework-foundation-decision-around-these-requirements)
- [19. Requested repository-audit deliverable](#19-requested-repository-audit-deliverable)
- [20. Required answer format for each issue](#20-required-answer-format-for-each-issue)
- [21. High-value acceptance scenarios](#21-high-value-acceptance-scenarios)
- [22. Decision recommendations](#22-decision-recommendations)
- [Appendix A. Source mapping](#appendix-a-source-mapping)
- [Appendix B. Conceptual schemas](#appendix-b-conceptual-schemas-for-discussion-not-implementation-mandates)
- [Appendix C. Compact question inventory](#appendix-c-compact-question-inventory)

# Document status and instructions

This memorandum is an architecture-audit request, not an instruction to begin a broad rewrite. The first requested deliverable is a repository-grounded report that establishes what the current code actually does, where the dossier is accurate or incomplete, and which limitations are deliberate vertical slices rather than intended product boundaries.

The memorandum distinguishes three kinds of statement:

- **Source-supported finding:** directly stated or strongly supported by *Ontology and Execution Machinery of Cybernetic Influence V3*, revision `a57cf1bc74965a31164c132fbd9868055bcad1e0`, dated August 11, 2026.
- **Design-intent clarification:** supplied by the product owner during review and therefore authoritative for intended direction even where the dossier or implementation differs.
- **Reviewer recommendation or uncertainty:** an architectural inference that must be tested against the repository before implementation.

Do not silently resolve contradictions between these categories. Report them explicitly.

# Executive summary

The current architecture contains several unusually strong foundations: one authoritative world state; separation of entity existence from active agency; separation of attempt, authorization, feasibility, and success; explicit information lineage; bounded agent observations; retained causal/event evidence; and question-relative representation depth. These should not be discarded casually.

The principal uncertainties are no longer primarily about whether the causal substrate can represent a port, an organization, a logistics system, or a social system. They are about whether the implemented product can *author, mutate, adjudicate, and inspect* such worlds generally.

The highest-priority questions are:

1. **What does the free-text authoring tab actually compile?** The product owner believes an analyst can describe a simulation in programmer-free prose and then edit it. The dossier, however, says the authoring proposal is limited to four closed workflow families and that the nominal component-composition path maps to a fixed information-campaign fixture. This may be a documentation error, a temporary implementation slice, or a real architectural constraint. Trace the code before drawing a conclusion.
2. **Can runtime execution change world structure, not merely predefined values?** A general simulator must be able to create or retire entities, routes, places, capabilities, active processes, relationships, carriers, and other structural elements during a run. Bridge destruction, depot construction, coalition formation, company creation, delegation, and new communication channels are all structural mutations.
3. **Should the fundamental transition abstraction be broader than an exact mechanism?** The likely target is a common `TransitionAuthority` contract supporting an LLM game master, exact code, stochastic models, external simulators, scripts, and replayed traces. The key invariant is not that exact code owns every transition. It is that every committed transition has an identifiable authority, relevant context, a structured patch, validation, fidelity limits, and evidence.
4. **How does an LLM adjudicator obtain the relevant world context?** An intelligent model cannot reject travel over a destroyed bridge unless the context system retrieves the bridge state. The dossier describes bounded context for active agents and declared read surfaces for exact mechanisms, but it does not establish a comparable context-management system for an open-ended game master.
5. **How should capabilities, competencies, and affordances be represented?** The intended design is more general than a list of action-specific ports. An actor may have general physical-manipulation or computer-use capabilities, with varying competency; an object and its current environment expose affordances. Exhaustively enumerating every action is impossible, especially for computers and general tools.
6. **How should representation scale be managed?** An organization may be modeled as a detailed sociotechnical network or as a coarse active surrogate when its internals are irrelevant. The same principle applies to computers, markets, logistics, and other subsystems. A coarse executor must not independently duplicate the same causal scope as the fine-grained system it replaces.
7. **What remains mandatory if LLM adjudication is the default?** A canonical state engine remains valuable even if most domain transitions are LLM-adjudicated. It should own identity, history, visibility, lifecycle, scheduling, reference integrity, information boundaries, declared invariants, and replayable patches. It should not attempt to formalize every ordinary causal judgment.
8. **Experiment semantics may be deferred, but the seam must remain clean.** Scenario, run, analysis, and future experiment specifications should remain distinct. Checkpoints and intervention seams should not be designed away.

## Recommended architectural north star

```text
ANALYST AUTHORING OR ACTIVE-SYSTEM INTENT
                    |
                    v
           GENERAL WORLD COMPOSITION
              OR SEMANTIC INTENT
                    |
                    v
             CONTEXT ASSEMBLER
          actor view / umpire view
                    |
                    v
            TRANSITION AUTHORITY
      LLM | exact | stochastic | external | replay
                    |
                    v
          STRUCTURED WORLD PATCH
     value changes + structural mutations
                    |
                    v
       GENERIC AND DECLARED VALIDATION
                    |
                    v
          CANONICAL VERSIONED WORLD
                    |
                    v
      OBSERVATIONS + EVIDENCE + ANALYSIS
```

This preserves the strongest current guarantees without requiring exact mechanisms for every ordinary action.

# Priority map

| Priority | Topic | Immediate objective |
|---|---|---|
| P0 | Free-text authoring trace | Establish whether arbitrary prose compiles to a genuinely general world or is forced into four workflow schemas/fixtures. |
| P0 | Structural endogeneity | Determine and generalize which world structures can be created, retired, rebound, or disabled during execution. |
| P0 | Transition authority | Decide whether `MechanismSpec` should be generalized so LLM adjudication is a first-class implementation rather than a fallback. |
| P0 | Adjudicator context | Design a first-class context assembler and query interface for world-aware LLM adjudication. |
| P0 | Actor/umpire information separation | Ensure an omniscient adjudicator cannot leak hidden state into an actor's knowledge without an observation path. |
| P0 | Structured patch model | Extend patches to cover lifecycle and topology changes while retaining replay and historical references. |
| P1 | General composition intermediate representation | Make templates compile into a generic world specification rather than making scenario families the primary architecture. |
| P1 | Capability/competency/affordance model | Recover the general effector concept without exhaustively enumerating every possible action. |
| P1 | Representation resolution | Support coarse surrogates and fine-grained subsystems with explicit scope and no double execution. |
| P1 | Simultaneous-action semantics | Eliminate accidental canonical-order bias in resource races, negotiation, voting, and structural conflicts. |
| P1 | Component behavioral contracts | Define semantic compatibility beyond matching `effect_type` strings. |
| P1 | Adoption governance | Make scenario use of canonical seams visible and testable. |
| P2 | Dynamic and overlapping analytical boundaries | Support changing, nested, overlapping, and contested groupings without inventing a hidden group mind. |
| P2 | Optional claim/proposition layer | Consider claim-level information analysis only if representation-level lineage proves insufficient. |
| P2 | Analyst UI fidelity | Show transition authority, resolution, actor perception, world truth, and topology history clearly. |
| Deferred but protected | General experiment specification | Preserve checkpoints, forks, interventions, repetitions, and comparison metadata for later implementation. |
| Deferred pending audit | Framework foundation decision | Compare Concordia or alternatives against the required ownership, context, mutation, adjudication, and evidence contracts. |

# Corrections and refinements to the earlier review

Several earlier criticisms require correction or qualification.

## The free-text tab prevents a confident claim that general authoring is absent

The dossier states that conversational authoring produces a `ScenarioDraftProposal` but is not open-ended; it lists four workflow families and describes a fixed component-composition adapter. Source basis: dossier sections 7.1-7.3, approximately lines 638-700.

The product owner states that the application already has a free-text tab intended to let an analyst describe simulations without programming and then edit the result.

These statements may both be true if the UI is open-ended while the compiler beneath it is closed-ended. They may also indicate that the dossier is incomplete or stale. The coding agent must trace the actual path rather than assuming either interpretation.

## A port crisis is not a fundamental scenario type

The model should represent a port and its environment: ships, people, storage, roads, fuel, software, weather, customs procedures, contracts, communications, and other relevant entities and processes. "Crisis" may be an actor's belief, an analyst's interpretation, a derived condition, or a narrative label. It should not automatically become a special `PortCrisisScenario` ontology.

This distinction matters because a general product should model worlds and processes, not accumulate named scenario applications.

## Organizations may be coarse active surrogates

The dossier's categorical statement that organizations are analytical boundaries and not executors is too strong if the intended product permits question-relative coarse-graining. An organization can be represented as one LLM active system when its internals are deliberately omitted. It can also be represented as a detailed sociotechnical network. The error is not coarse organizational agency; the error is allowing coarse and fine representations to generate the same causal behavior simultaneously without an explicit coupling rule.

## Deterministic LLM reproduction is not a primary requirement

The target is exploratory wargaming and mechanism discovery, not a high-fidelity deterministic digital twin. Exact regeneration of the same LLM choices is not necessary. What matters is retained provenance, coherent state, explicit assumptions, replay of committed trajectories, and future ability to test sensitivity across repeated runs and alternative models.

## "Synthetic society" is too narrow a label for the target

The intended product is broader: a general sociotechnical/world simulator in which social relationships may evolve, but so may logistics networks, infrastructure, software, resources, markets, physical topology, and information systems. Social constructs should not dominate the irreducible kernel unless they prove necessary across domains.

# 1. Audit the actual free-text authoring path

## Source-supported finding

The dossier says:

- conversational authoring calls an LLM with a strict consumer schema;
- the result is a `ScenarioDraftProposal`;
- current authoring supports four workflow families: resource request, information campaign, a narrow component composition, and one coordination-decision template;
- the authoring model cannot supply arbitrary executable Python or implementation identities;
- the compiler maps proposals to reviewed fixtures and trusted mechanism implementations; and
- the current component-composition vertical requires a fixed pattern and projects into an existing information-campaign fixture.

Source basis: sections 7.1-7.3 and 10.1, approximately lines 638-700 and 976-1000.

## Design-intent clarification

The product owner expects the free-text tab to support programmer-free creation of general simulations followed by editing.

## Concern

A user interface can accept arbitrary prose while the compiler silently narrows the request to a small union of supported workflows. This is **open input with closed compilation**. It can look general while being architecturally specialized.

The opposite is also possible: the dossier may understate newer or separate general authoring machinery.

## Required code trace

Trace an arbitrary free-text request from UI submission to executable scenario. Identify:

1. the UI component and endpoint;
2. the prompt and response schema supplied to the authoring LLM;
3. all union/discriminator types in the response model;
4. compiler dispatch logic;
5. component-registry lookups;
6. fixture/template selection;
7. creation of ports, carriers, mechanisms, active systems, places, and connections;
8. unsupported-content handling;
9. edit and approval persistence; and
10. tests demonstrating general or restricted behavior.

## Questions for the coding agent

1. Must every free-text request ultimately select one of the four documented workflow families?
2. Is there another authoring path not described in the dossier?
3. Can the authoring LLM emit an arbitrary graph of existing reviewed primitives?
4. Can it bind arbitrary compatible ports or transition authorities from a registry?
5. Does it merely configure a prebuilt fixture?
6. What happens when the request contains constructs outside the selected workflow?
7. Are unsupported constructs surfaced as unresolved questions, silently dropped, or approximated?
8. Can the user edit the generated graph itself, or only template-specific fields?
9. Which new worlds require scenario-specific Python today?
10. Was the workflow union deliberately temporary, or is it treated as the long-term product architecture?

## Acceptance probe

Use the existing free-text tab to request a world containing:

- a port and two storage areas;
- ships, trucks, fuel stocks, containers, roads, and a bridge;
- workers, a customs authority, a shipping company, and a municipal authority;
- communications and information carriers;
- a queue for loading;
- weather as an external or endogenous process;
- autonomous participants with different observations and goals; and
- no predeclared "crisis" workflow.

Report exactly what compiles, what is approximated, what is rejected, and whether new Python is required.

# 2. Replace scenario-family architecture with general world composition, if necessary

## Recommendation

The primary authoring target should be a general world-composition intermediate representation. Workflow templates should compile into this representation as convenience macros.

The architecture should resemble:

```text
GeneralScenarioComposition
    <- information-campaign template
    <- resource-request template
    <- coordination template
    <- analyst-authored world
```

It should not resemble:

```text
if resource request: build fixture A
if information campaign: build fixture B
if coordination: build fixture C
```

## Candidate composition contents

A general composition contract should be able to declare:

- persistent entities and initial lifecycle state;
- typed or semantically described state;
- places, placements, and topology;
- carriers, representations, and initial information;
- capabilities, competencies, and affordance-relevant properties;
- interfaces and connections where explicitly modeled;
- active-system bindings;
- transition-authority bindings;
- clocks, schedules, and initial pending work;
- fidelity declarations;
- hard invariants and protected state;
- analytical boundaries or views; and
- unresolved semantics that require analyst confirmation.

## Important boundary

General composition does not mean allowing the authoring LLM to invent arbitrary executable code. The LLM may:

- instantiate known components;
- bind compatible interfaces;
- configure semantic state;
- select an LLM adjudicator for open-ended transitions;
- choose among reviewed exact/stochastic/external models; and
- flag unsupported high-fidelity requirements.

New Python should ordinarily be required only when adding a new reusable exact subsystem, a new external-model adapter, or a new validator - not for every new scenario.

## Questions

1. What is the smallest composition IR that can express existing scenarios without template-specific branches?
2. Can all current workflow families compile into it without loss?
3. Which scenario-specific payload schemas are genuinely reusable domain contracts, and which are fixture artifacts?
4. Can the compiler create a world whose structure was not anticipated by a named scenario module?
5. Can the same component be reused in social, logistical, software, and physical contexts?
6. Can unknown but semantically ordinary actions be delegated to an LLM transition authority rather than forcing a new fixture?
7. How will the editor expose component bindings, unsupported assumptions, and selected representation depth?

# 3. Make structural endogeneity a first-class runtime requirement

## Source-supported uncertainty

The dossier lists runtime patch/output types for facts, placements, representations, observations, effects, and movements. It does not establish that runtime execution can create or retire entities, connections, ports, mechanisms, active-system bindings, places, or persistent relationships. It also says analytical boundaries are authored, flat, and static.

Source basis: sections 4.3, 7.8, and 10.12, approximately lines 355-371, 767-787, and 1170-1188.

## Design-intent clarification

The world structure should be able to evolve endogenously. External inputs after initialization are optional; the simulation must support internally generated changes to both values and structure.

## Required structural operations

Determine whether the runtime can already perform each operation. If not, propose a coherent generalization.

### Entity lifecycle

- create entity;
- activate entity;
- deactivate, destroy, retire, or decommission entity;
- retain historical identity after retirement;
- split or merge entities where meaningful.

### Topology lifecycle

- create, disable, re-enable, and retire connections;
- create, destroy, and repair spatial links;
- create and retire places;
- change containment or placement rules;
- create new communication or transportation paths.

### Interface and capability lifecycle

- add or remove ports/interfaces;
- grant, revoke, or alter capabilities;
- change competency;
- expose or withdraw affordances based on state;
- transfer control or access.

### Process lifecycle

- create or retire active-system bindings;
- start, suspend, resume, or terminate autonomous processes;
- change implementation or transition-authority bindings under declared rules;
- create new scheduled processes without inventing arbitrary untrusted code.

### Relationship and institution lifecycle

- create, revise, and terminate persistent relationships;
- form and dissolve coalitions, companies, task forces, households, or other structures;
- delegate and revoke authority;
- create and terminate commitments;
- change membership in actor-recognized groups and analyst boundaries.

### Information and resource lifecycle

- create and retire carriers;
- create representations and derivation lineages;
- create, consume, transform, divide, merge, or destroy resources;
- create new records, contracts, credentials, and artifacts.

## Lifecycle rather than erasure

Literal deletion can break replay because historical events retain references. Prefer versioned lifecycle status such as:

```text
planned -> active -> impaired -> destroyed -> retired
```

Historical projections should reconstruct whether an entity or route existed at the selected revision.

## Structural patch requirements

Structural changes should be:

- explicit patch operations;
- atomic where required;
- validated against reference integrity and topology rules;
- recorded with causal parents and transition authority;
- reversible for historical reconstruction;
- included in checkpoints and digests;
- visible to context indexes immediately after commit; and
- unable to rewrite prior history.

## Concrete probes

1. A bridge is destroyed, eliminating the only road route.
2. A temporary depot is created and connected to a transport network.
3. Two actors establish a coalition, create a shared communication channel, and later dissolve it.
4. A company purchases a truck, changing ownership and transport affordances.
5. An actor delegates purchasing authority to another actor for a limited interval.
6. A software administrator creates a new account and VPN route.
7. A new active process is started to monitor a sensor and later terminated.

For each probe, show whether the current runtime can represent the change as executable topology rather than merely as an opaque fact.

# 4. Clarify the irreducible atoms of the general simulator

## Recommendation

Keep the kernel small and cross-domain. Do not make specifically social categories the universal base merely because social simulation is an important use case.

A plausible kernel includes:

- identity and lifecycle;
- addressable state;
- time and scheduling;
- place, containment, placement, and topology;
- information carriers, representations, observations, and provenance;
- capabilities/interfaces and connections;
- transition authorities;
- active processes;
- structured patches;
- events, causal/execution lineage, and evidence;
- visibility and access control; and
- fidelity/representation declarations.

Resources, queues, markets, norms, contracts, software services, epidemiology, and other domains can be reusable subsystems or records above the kernel.

## Entity kinds versus behavioral contracts

The dossier correctly identifies that open `entity_kind` strings are semantically weak. A complex class hierarchy may not be the solution. Interoperability is more likely to depend on behavioral and interface contracts:

- what state is required;
- what capabilities and affordances are exposed;
- what transition authorities understand the component;
- what units and invariants apply;
- what context must be retrieved;
- what fidelity and omissions are declared; and
- what substitutions are valid.

## Generic relationship record

A first-class relationship record may be useful for structures that are neither simple facts nor executable mechanisms, especially temporally qualified and n-ary relations such as delegation. Any such record should remain generic enough to support logistics and technical dependencies as well as social ties.

Possible fields include:

```text
relationship_id
relationship_type
role bindings
validity interval
status/lifecycle
provenance
confidence or contestation
supporting artifacts
constraints
visibility
```

Do not introduce this merely because natural-language facts feel untidy. Introduce it only if it materially improves selection, validation, mutation, context retrieval, or analysis.

## Questions

1. Which current state is trapped in arbitrary JSON and therefore cannot be validated or queried reliably?
2. Which concepts recur across multiple scenario families?
3. Which concepts need lifecycle, provenance, role bindings, or independent selection?
4. Can generic relationship/dependency records support social, contractual, logistical, and technical links?
5. Are ports and `effect_type` values acting as an accidental type system for too many concepts?
6. Which primitives are genuinely cross-domain, and which should remain optional modules?

# 5. Recover the capability, competency, effector, and affordance model

## Definitions

- **Capability:** a general ability possessed by an actor or process, such as locomotion, physical manipulation, language communication, or computer operation.
- **Competency:** the degree of proficiency with which a capability can be exercised.
- **Effector:** an actor-controlled means of producing an effect. In the original concept, this may be general rather than action-specific.
- **Affordance:** an action made possible by the relation among an actor's capabilities, an object's properties, and current environmental conditions.
- **Authorization:** whether an available attempt is permitted by policy, law, role, access control, or another rule.
- **Feasibility:** whether the attempt can physically, computationally, or procedurally succeed.
- **Outcome:** what actually happens after adjudication.

These distinctions should not collapse into a single exposed action list.

## Design-intent example

Alice may possess:

```text
physical manipulation: ordinary competency
computer operation: advanced competency
network administration: novice competency
```

A computer may have properties and coarse affordances related to reading, creating, transforming, and transmitting information. Whether Alice can use it depends on location, access, credentials, power, software, and selected model resolution.

The intended architecture is more general than:

```text
Alice has use_computer_1 port
```

and much more general than:

```text
Alice has crop_screenshot_and_email_Bob port
```

## The open affordance problem

Affordances cannot be exhaustively enumerated. A chair can be sat on, moved, used as a barrier, or wedged under a door. A computer is programmable and has an effectively open action space. Humans invent novel uses for ordinary objects.

Therefore, capabilities and object properties should constrain and inform adjudication, not define the complete action vocabulary.

## Recommended hybrid

- Use explicit affordances and requirements where the subsystem is central or well understood.
- Use general semantic properties and an LLM adjudicator for ordinary open-ended uses.
- Allow the adjudicator to query capabilities, competency, object state, access, and local topology.
- Preserve separate checks for actor-perceived possibility, simulator-admitted attempt, authorization, feasibility, and outcome.
- Permit capabilities and affordances to change structurally during execution.

## Questions

1. Does the current port model preserve the original effector concept or replace it with action-specific interfaces?
2. Is a port an actor capability, a currently exposed affordance, a routing interface, or all three?
3. How are competency and skill represented today?
4. Can an actor attempt a novel action that lacks a predeclared port?
5. Can an LLM adjudicator infer an affordance from general object properties?
6. How are access, ownership, authorization, and physical feasibility kept distinct?
7. Can acquisition of a new object create new affordances without manually adding scenario-specific actions?
8. Can training or injury change competency or capability dynamically?

# 6. Decide explicitly between exact mechanisms, LLM adjudication, and a common transition-authority model

## The false binary

"Exact mechanisms everywhere" and "mechanisms nowhere" are not the only choices.

If a mechanism is defined broadly as any rule that maps state and intent to consequences, an LLM game master is itself a mechanism. The meaningful question is whether every domain transition must be represented by preauthored exact code.

## Option A: exact mechanisms are the default

### Advantages

- strong declared read/write authority;
- straightforward invariants;
- predictable computational semantics;
- efficient repeated execution;
- clear failure reasons;
- easier unit testing.

### Costs

- scenario-specific Python proliferates;
- open-ended human action is difficult;
- affordance enumeration becomes unmanageable;
- ordinary peripheral behavior receives disproportionate engineering effort;
- the authoring system remains narrower than the substrate.

## Option B: an LLM game master owns reality and state directly

### Advantages

- maximal semantic flexibility;
- rapid scenario creation;
- natural handling of novel actions and ordinary common-sense causality.

### Costs

- the model becomes both judge and database;
- state can drift or contradict itself;
- hidden information can leak into actor knowledge;
- long-run context becomes unmanageable;
- conservation, identity, topology, and timing are fragile;
- audit and replay become weak;
- unsupported assumptions may be concealed in prose.

This option is not recommended.

## Option C: common transition authority with canonical state and structured patches

This is the recommended direction.

```text
intent + relevant context
        -> TransitionAuthority
        -> proposed structured patch
        -> generic and declared validators
        -> canonical state commit
```

Implementations may include:

- `LlmAdjudicator`;
- `ExactFunction`;
- `StochasticModel`;
- `ExternalSimulatorAdapter`;
- `ScriptedProcess`; and
- `ReplayTrace`.

## Default selection policy

Use an explicit model when:

- the phenomenon is central to the analytical question;
- accounting, conservation, or legal/technical constraints matter;
- a trusted computational model exists;
- the transition repeats often enough that LLM calls are wasteful;
- small differences among alternatives are analytically important;
- the analyst explicitly selects high resolution; or
- a formal invariant must be guaranteed.

Use an LLM adjudicator when:

- the behavior is semantically open-ended;
- common-sense plausibility is sufficient at the selected resolution;
- the subsystem is peripheral;
- no trustworthy formal model exists;
- exhaustive affordance enumeration would be artificial; or
- rapid scenario composition is more valuable than fine mechanization.

## Common `TransitionAuthority` contract

Every transition authority should declare or retain:

- implementation identity and version;
- authority type;
- permitted read and write surfaces;
- context-acquisition policy;
- accepted intent/effect schema;
- patch schema;
- timing semantics;
- stochastic or model configuration;
- fidelity declaration;
- assumptions and invalid questions;
- validators and invariants;
- resource/token/cost bounds;
- confidence or insufficiency output where relevant; and
- evidence linking input context, decision, and committed patch.

## Terminology concern

"Exact mechanism" is exact only in execution, not necessarily in empirical truth. Consider "explicit transition mechanism" or "code-defined transition authority" if the current wording may imply real-world correctness.

## Questions

1. Which current `MechanismSpec` guarantees should apply to all transition authorities?
2. Which guarantees depend specifically on reviewed Python handlers?
3. Can the current engine accept a structured patch proposed by an LLM without creating a bespoke mechanism per action?
4. Can an LLM authority create structural mutations safely?
5. How will unsupported or insufficiently contextualized actions be represented?
6. Can the same subsystem switch from LLM to exact resolution without changing surrounding contracts?
7. Can an exact subsystem call an LLM for a bounded semantic subdecision, and vice versa?
8. How will the UI and evidence distinguish exact, stochastic, external, scripted, and LLM-adjudicated outcomes?

# 7. Retain a canonical state engine, but keep the mandatory kernel small

## Source-supported strength

The dossier's one-authoritative-world-state principle is sound. It prevents prose, mechanisms, visualizations, and evidence from becoming independent mutable worlds. Source basis: section 3.1, approximately lines 148-154.

## Why retain it even if LLM adjudication dominates

The state engine is not mainly a defense of determinism. It is a defense of coherent bookkeeping and information control.

The engine is better suited than an LLM context window to retain:

- stable identity;
- current and historical existence;
- locations and topology;
- ownership and custody;
- quantities and declared conservation constraints;
- representation lineage;
- who observed what and when;
- pending delays and scheduled work;
- active and retired processes;
- event history and causal/execution ancestry;
- visibility and protected state; and
- checkpoint/replay integrity.

## Small protected kernel

The mandatory engine layer may only need to enforce:

- identity and reference validity;
- state revision and event ordering;
- lifecycle validity;
- declared exclusive placement or cardinality rules;
- information/provenance boundaries;
- protected history;
- scheduling and pending work;
- topology consistency;
- registered invariants; and
- authority/read/write scope.

It should not attempt to encode every common-sense causal rule.

## Questions

1. Which current invariants are universal and which are scenario-specific?
2. Can validators be registered independently of exact mechanisms?
3. Can a subsystem choose very permissive LLM adjudication while retaining only a few hard invariants?
4. Does canonical state contain epistemic status for disputed, latent, assumed, or unknown values?
5. How are state schemas versioned when structural mutations add new kinds of records?
6. Can historical projections reconstruct topology and lifecycle at any selected event?

# 8. Make context management a first-class architecture component

## Source-supported foundation

The dossier already uses bounded projections:

- an active LLM receives its persona, private memory, delivered observations, exposed interfaces, accessible representations, activation cause, time, and bounds;
- it does not receive the canonical world, hidden provenance, another actor's private state, or same-moment proposals;
- exact mechanisms receive defensive copies of declared facts, representations, placements, links, and triggering data.

Source basis: sections 6.2, 7.5, and 7.8, approximately lines 550-575, 724-739, and 767-783.

## Missing or unclear capability

The dossier does not establish an equivalent context-management system for a general LLM game master that must adjudicate open-ended world transitions.

This is a central problem. Model intelligence cannot compensate for missing state.

## Bridge example

Canonical state:

```text
Alice is in Town A.
Truck 7 is available.
Bridge 7 was destroyed yesterday.
Bridge 7 is the only route to Town B.
```

Actor intent:

```text
Alice attempts to drive Truck 7 to Town B.
```

If the adjudicator receives only Alice, the truck, and the destination, it may reasonably return success. The architecture must retrieve the route and bridge state.

## Two distinct context projections

### Actor context

What the acting entity is entitled to know:

- delivered observations;
- private memory;
- beliefs and interpretations;
- exposed interfaces or perceived affordances;
- accessible representations.

### Adjudicator context

What is required to determine what actually happens:

- canonical entity and resource state;
- relevant topology and routes;
- hidden infrastructure conditions;
- applicable policies and constraints;
- pending work and recent structural changes;
- relevant implementation/fidelity information.

The adjudicator may be omniscient for ruling purposes. The actor must not become omniscient as a consequence.

## Recommended context architecture

### Deterministic initial projection

From the intent and directly referenced entities, retrieve:

- actor and target state;
- current placements;
- ownership/access/control relations;
- local topology;
- directly applicable capabilities and constraints;
- relevant representations;
- recent changes involving those entities; and
- pending scheduled effects.

### Typed query tools

The adjudicator should be able to request additional information, conceptually including:

```text
get_entity_state(id)
get_relationships(id, type?)
get_capabilities(actor)
get_competency(actor, capability)
get_place_and_local_topology(id)
find_routes(origin, destination, mode?)
get_route_component_state(route)
get_resource_state(id)
get_pending_events(scope)
get_recent_events(scope, time_window)
get_representation_lineage(id)
get_applicable_constraints(intent, entities)
get_fidelity(scope)
```

### Semantic retrieval

Unstructured facts, policies, contracts, and narrative state may require semantic search. This should complement, not replace, typed retrieval.

### Domain/component context hooks

Reusable components should declare what context is ordinarily relevant to actions involving them.

### Context provenance

Retain which records and queries were supplied to the adjudicator. This allows later inspection of whether a poor ruling resulted from bad judgment or missing context.

### Insufficient-context outcome

The adjudicator must be allowed to return:

```text
cannot adjudicate confidently because required state is missing or ambiguous
```

It should not be forced to invent a ruling.

## Context risks to test

- stale caches after structural mutation;
- distant but causally relevant constraints;
- hidden information leakage;
- excessive retrieval that overwhelms the model;
- semantic search returning obsolete facts;
- conflicting records;
- temporal qualification;
- circular tool calls;
- prompt injection from world content;
- cost and latency growth;
- inconsistent context across simultaneous adjudications.

## Questions

1. Does any current game-master or narrator code already query canonical state?
2. Is context assembled by graph traversal, explicit declarations, prompt templates, or ad hoc scenario code?
3. Can the adjudicator request follow-up state?
4. How is relevant history selected?
5. How is current state distinguished from historical or superseded state?
6. Can component authors provide context hooks?
7. Is context provenance retained with the ruling?
8. How does context update after a topology mutation in the same causal moment?
9. How are actor-visible and adjudicator-visible information separated in code?
10. Can the adjudicator produce an observation without automatically revealing the hidden reason for an outcome?

# 9. Support open-ended semantic actions through structured world patches

## Recommendation

An actor should be able to propose:

```text
I crop this screenshot and send it to Bob.
```

The product should not require a preauthored action named `crop_screenshot_and_email_Bob`.

A general pathway is:

```text
semantic intent
    -> context assembly
    -> selected transition authority
    -> structured proposed patch
    -> validation
    -> commit
    -> observations and evidence
```

## Avoid unnecessary decomposition

If computer use is peripheral, the LLM adjudicator may directly propose:

- a new representation derived from the original screenshot;
- a time cost;
- a communication effect or delivery; and
- relevant public/private summaries.

The engine does not need to simulate an image editor or email client.

If cybersecurity is the analytical subject, replace the coarse computer representation with accounts, credentials, services, network routes, software, and explicit technical models.

## Candidate patch families

### Value/state patches

- update fact;
- update lifecycle status;
- update quantity or condition;
- update ownership/control;
- update private state where authorized.

### Spatial/resource patches

- move entity or resource;
- consume, create, divide, merge, or transfer resource;
- create or retire storage/custody relation.

### Information patches

- create carrier;
- create representation;
- derive representation from parents;
- deliver observation;
- alter apparent source while retaining actual provenance;
- revoke or destroy access where modeled.

### Structural patches

- create/retire entity;
- create/disable/retire connection;
- create/destroy spatial link;
- create/retire place;
- add/remove interface;
- grant/revoke capability;
- create/retire active-system binding;
- create/terminate relationship;
- change group membership;
- bind/unbind a reviewed transition authority.

## Structured LLM output

The adjudicator's result should be machine-readable and minimally sufficient. A conceptual result might include:

```text
status: success | partial | failure | insufficient_context
summary: human-readable ruling
modeled_duration: ...
patches: [...]
observations_to_emit: [...]
follow_up_work: [...]
assumptions_used: [...]
confidence: ...
invalid_question_warning: ...
```

The LLM should not supply canonical IDs unless the engine has allocated or validated them.

## Questions

1. Can the current engine accept generic patch operations independent of a named mechanism handler?
2. Which patch types require stronger validators?
3. Can the adjudicator propose partial success and delayed consequences?
4. Can it schedule follow-up work?
5. How are new identities allocated?
6. How are structural patches ordered and made atomic?
7. How does the system recover when one patch in a multi-step ruling is invalid?
8. Can a user inspect and override a disputed ruling before commit in manual wargame mode?

# 10. Represent organizations and other subsystems at explicit resolution

## Design-intent clarification

Organizations can be treated as minds when they are intentionally coarse-grained representations, especially for marginal actors whose internal sociotechnical structure is irrelevant. They should not simultaneously be represented as a detailed network and as an independent unitary executor for the same causal function.

## Recommendation

Do not make `Organization` a mandatory fundamental atom. Organizationhood may be:

- an analyst's boundary;
- an actor-recognized identity;
- a set of persistent relationships and artifacts;
- a detailed sociotechnical subsystem; or
- a coarse entity with an active surrogate.

These are different modeling choices.

## Resolution exclusivity principle

```text
One causal scope -> one active representation
```

A coarse surrogate and its fine-grained internals may coexist only when an explicit coupling contract assigns distinct responsibilities and prevents double counting.

## Candidate subsystem representation record

```text
subsystem_id
represented_scope
active_resolution
implementation_type
replaces_or_abstracts_members
preserved_inputs_outputs
omitted_internal_dynamics
state_transfer_on_resolution_change
coupling_rules
fidelity_note
invalid_questions
```

## Layering, overlap, and hierarchy

The same person or artifact may participate in multiple organizations. Organizations may be nested, overlapping, temporary, contested, or differently perceived by actors. Therefore:

- analytical boundaries should support overlap and time-varying membership;
- actor-recognized group identity should not be conflated with analyst grouping;
- detailed institutional state can live in agents, artifacts, software, procedures, resources, and relationships;
- a coarse active surrogate should be explicitly labeled as a model resolution, not an ontological claim about a group mind.

## Dynamic resolution

Longer term, the simulator may support replacing a coarse surrogate with a detailed subsystem during a run or fork. This requires a state-transfer contract and should not be attempted casually.

## Questions

1. Can any entity, regardless of semantic kind, receive an active-system binding today?
2. Does the current prohibition apply only to `AnalyticalBoundary`, or to organization-like entities generally?
3. How would a coarse organizational surrogate declare what it abstracts?
4. How can the engine prevent duplicate execution by coarse and fine representations?
5. Can analytical boundaries overlap or change over time?
6. Can actors disagree about whether an organization exists or who belongs to it?
7. Can a new coalition form endogenously and acquire a decision process or resources?
8. Is dynamic resolution switching needed now, or is static per-run resolution sufficient initially?

# 11. Preserve the strong information model and prevent omniscient leakage

## Source-supported strength

The carrier/representation/observation distinction, actual versus apparent source, and derivation lineage are among the strongest parts of the architecture. Delivery is separated from truth, attention, belief, agreement, and action. Source basis: section 3.4, approximately lines 198-214.

## Requirements under LLM adjudication

An omniscient game master may know why an action failed. That does not mean the actor knows.

Example:

```text
Canonical reason: bridge destroyed.
Actor observation: road blocked ahead.
Actor inference: uncertain; perhaps accident, closure, or destruction.
```

The adjudicator should emit only observations justified by the event and modeled sensors/channels.

## Actual-source ambiguity

Clarify whether `actual_source` means:

- the creator of the representation token;
- the originator of the semantic claim;
- the immediate transmitter;
- the causal source of the underlying event; or
- another defined provenance role.

These differ materially in rumor, copying, edited media, and contested evidence.

## Optional claim layer

Representation-level lineage may be insufficient when one document contains many claims or when different representations express equivalent claims. A claim/proposition layer may eventually support contradiction, corroboration, rumor convergence, and belief revision. This should remain optional until a concrete analysis requires it.

## Questions

1. Can an LLM transition authority create representations while retaining protected lineage?
2. Can it alter apparent source without altering actual provenance?
3. Can it emit different observations to different actors?
4. Is every private-state update tied to delivered observations or authorized internal processes?
5. How are semantic transformations such as cropping, paraphrasing, summarizing, or selective quotation represented?
6. Does the current model distinguish creation, transmission, endorsement, and subject of a claim?
7. What hard tests prevent world truth from appearing in actor prompts?

# 12. Generalize simultaneous-action and conflict semantics

## Source-supported concern

The runtime evaluates due processes from a frozen pre-moment state, then applies proposals to a trial session in canonical order and commits atomically. The dossier acknowledges that there is no general conflict-resolution language for incompatible writes, resource races, market clearing, voting, or negotiation. Source basis: section 10.9, approximately lines 1130-1140.

## Why this matters

Canonical order can create an accidental priority rule. Atomic commit does not make conflicting actions semantically simultaneous.

Examples:

- two actors claim one truck;
- two buyers spend the same funds;
- two processes create incompatible routes;
- one actor destroys a bridge while another begins crossing;
- simultaneous votes or offers interact;
- two administrators modify the same permission state.

## Possible approaches

1. **Moment-level adjudicator:** one transition authority receives the full simultaneous proposal set and resolves it jointly.
2. **Generic transaction resolver:** proposals declare read/write sets, priorities, exclusivity, and conflict rules.
3. **Domain-specific resolver:** markets, votes, queues, and negotiations use dedicated models.
4. **Explicit serial order:** accepted only when the modeled process really has priority/order and that order is evidence, not an arbitrary implementation detail.

These approaches can coexist.

## Questions

1. Does current canonical ordering produce observable bias in tests?
2. Can the engine detect overlapping write sets before execution?
3. Can an LLM moment adjudicator resolve open-ended conflicts?
4. How are structural mutations included in conflict detection?
5. Can exact domain resolvers override the generic policy?
6. How are priority, preemption, cancellation, and partial success represented?
7. How are simultaneous outcomes explained in retained evidence?

# 13. Strengthen component contracts beyond nominal effect types

## Concern

Matching `effect_type` strings is not sufficient for safe composition. Two components can both accept `resource_transfer` while disagreeing about units, conservation, timing, ownership, or failure semantics.

## Recommended behavioral contract

A reusable component or interface should declare, as applicable:

- semantic identity and version;
- input/output schema;
- units and dimensional meaning;
- preconditions and postconditions;
- read/write surface;
- invariants;
- timing and delay semantics;
- cardinality and exclusivity;
- side effects;
- failure modes;
- uncertainty;
- context-retrieval hooks;
- fidelity and invalid questions;
- substitution compatibility; and
- evidence produced.

## Component kinds

Do not choose between semantic class, behavior contract, and port signature prematurely. They serve different purposes:

- semantic class helps humans and search;
- port/interface signature supports structural compatibility;
- behavior contract supports meaningful substitution and validation.

## Questions

1. Is there a global registry for effect-type semantics?
2. Can components from different scenario modules interoperate safely?
3. How are units represented today?
4. Can a component declare context dependencies for LLM adjudication?
5. How is contract version drift detected?
6. Can a coarse LLM surrogate and an exact model expose the same external contract?
7. What constitutes proof that two components are substitutable for a given question?

# 14. Use evidence carefully: execution lineage is not external causal proof

## Source-supported objective

The project targets conditional insight and exploratory mechanism discovery rather than point prediction. Source basis: section 1.1, approximately lines 55-68.

## Terminology concern

Explicit event-parent links support **execution lineage** or **model-internal token causation**: within the simulated rules, one event generated another. They do not establish that the same relationship holds in the external world.

The system should distinguish:

- execution lineage;
- model-implied causality;
- counterfactual evidence from controlled simulation comparisons; and
- empirical causal validity outside the simulation.

## Wargaming validity standard

Appropriate standards include:

- mechanism plausibility;
- diagnostic value;
- traceability;
- explicit assumptions;
- sensitivity to plausible alternatives;
- robustness across models/prompts/runs;
- analyst usefulness; and
- clear invalid questions.

Forecast accuracy and deterministic reproduction are not mandatory.

## LLM evidence

For LLM-adjudicated transitions, retain enough evidence to determine:

- the intent;
- the actor-visible context;
- the adjudicator-visible context or query trace;
- the selected transition authority and configuration;
- the structured ruling;
- assumptions and uncertainty;
- validators applied;
- committed patches; and
- observations emitted.

Do not rely on narrator prose as measurement truth.

## Questions

1. Should `causal_parent` terminology be changed or qualified in analyst-facing views?
2. Can the evidence bundle distinguish exact computation from LLM judgment?
3. Is adjudicator context retained without exposing protected content to unauthorized viewers?
4. Can analysts identify which outcomes depend on one LLM ruling?
5. Can fidelity notes be attached to individual transitions or only subsystems?
6. What constitutes a replay when the LLM is not re-invoked?
7. Can the system fork from a retained checkpoint and substitute a different transition authority?

# 15. Preserve the experiment seam while deferring a general experiment product

## Design-intent clarification

A general experiment specification is desired but can be deferred.

## Recommendation for current work

Do not block general composition, structural mutation, or LLM adjudication on a full experiment workbench. However, preserve clear distinctions among:

- scenario specification: what world and initial situation exist;
- run specification: how one execution is configured;
- analysis specification: which findings are derived and how; and
- experiment specification: how runs are forked, varied, repeated, and compared.

## Minimum seams to protect now

- checkpoints can be restored and forked;
- initial and runtime interventions are representable as explicit patches or authorized actions;
- model/LLM/transition-authority configurations are retained;
- stochastic seeds and external model versions can be retained where available;
- outcomes and mechanism/evidence measures can be computed later;
- scenario state is not entangled with analysis labels;
- structural mutations replay correctly across forks.

## Future experiment capabilities

- controlled variable changes;
- random or adversarial interventions;
- repeated models/prompts/seeds;
- condition matching;
- outcome measures;
- mechanism-occurrence measures;
- falsification conditions;
- sensitivity analysis;
- robustness labels; and
- comparison-validity declarations.

## Questions

1. Do current checkpoints include all structural state and context-relevant indexes?
2. Can a run be forked before an LLM adjudication and rerun with a different authority?
3. Are scenario, run, analysis, and experiment identities already distinct in storage?
4. Could future experiments change representation resolution between forks?
5. Are analyst-derived labels prevented from becoming hidden causes in later runs?

# 16. Align the UI with the actual ontology and resolution choices

## Source-supported concern

The dossier says the public guide uses simplified/hard-coded vocabulary, calls mechanisms "Process" inconsistently, and does not clearly distinguish causal routes, undirected adjacency, containment, ownership, and analytical grouping. Source basis: sections 5.1-5.2 and 10.15.

## Recommendations

The authoring and inspection UI should expose:

- which elements were generated from free text;
- which requests were unsupported, approximated, or unresolved;
- whether a transition is LLM-adjudicated, exact, stochastic, external, scripted, or replayed;
- the selected resolution/fidelity of each subsystem;
- actor-visible versus canonical state;
- current versus historical topology;
- attempt, authorization, feasibility, and outcome as separate stages;
- structural creation/retirement events;
- context used by an adjudicator, subject to access controls; and
- scenario compliance/adoption information.

Do not display "port crisis" as a world object merely because the analyst used that phrase. Display the port world and, separately, actor beliefs or derived analyst classifications.

## Questions

1. Does the free-text editor display the actual compiled graph or a template abstraction?
2. Can users inspect and edit transition-authority selections?
3. Can users see that a subsystem is coarse and what questions it cannot support?
4. Can users distinguish actor belief from canonical state?
5. Can users inspect topology at a prior revision?
6. Can users review or override LLM rulings in a human-umpired mode?
7. Are unsupported authoring requests made visible before approval?

# 17. Add adoption governance so scenarios cannot silently bypass canonical seams

## Source-supported concern

The dossier distinguishes ontology/runtime gaps from adoption gaps and notes that scenario modules can bypass the authoring compiler, component registry, shared person machinery, or evidence bundle. Source basis: introduction and section 10.2, approximately lines 36-47 and 1002-1020.

## Recommendation

Each scenario or world should retain a machine-readable implementation/adoption manifest stating:

- how it was authored;
- whether it uses the general composition IR;
- which components and contracts were instantiated;
- which transition authorities are used;
- whether the shared person/active-system context path is used;
- whether information lineage is canonical;
- whether structural mutation uses the standard patch path;
- whether evidence bundles are standard;
- which bespoke exceptions exist; and
- why each exception is bounded.

## Tests

- a new scenario cannot claim general composition while being built by a private fixture path;
- the receipt maps authoring selections to actual runtime references;
- bespoke handlers declare their scope and fidelity;
- regression tests detect bypass of actor-context or information-provenance boundaries;
- public examples are generated from executable scenarios where practical.

## Questions

1. Is `CompositionReceiptV1` sufficient to prove construction, or does it only describe already-built surfaces?
2. Can CI enforce use of canonical seams?
3. How should bounded exceptions be registered?
4. Can scenario-specific UIs be generated from the general schema rather than maintaining separate semantics?
5. Which existing scenarios would fail a strict adoption manifest today?

# 18. Reframe the framework-foundation decision around these requirements

The Concordia or alternative-framework decision should not be reduced to prose versus typed state. Evaluate whether a framework can support or coexist with:

- one authoritative world state;
- structural mutation and versioned topology;
- actor-specific and adjudicator-specific context projection;
- first-class LLM transition authorities;
- information/provenance boundaries;
- multirate scheduling;
- checkpoint/fork semantics;
- representation resolution;
- standard evidence; and
- general composition.

Questions:

1. Would adopting the framework create two authoritative worlds?
2. Who owns scheduling and pending work?
3. Who owns context retrieval?
4. Can framework agents propose structured patches rather than narratively changing state?
5. Can the framework support dynamic creation and retirement of agents and world structures?
6. Can current evidence and replay guarantees be preserved?
7. Which current systems are differentiating and which duplicate mature infrastructure?
8. Can adapters preserve a single source of truth during gradual integration?

Do not generalize large amounts of current machinery merely to match a framework before answering these questions. Conversely, do not adopt a framework that weakens the required contracts.

# 19. Requested repository-audit deliverable

Before implementing broad changes, return an architecture-gap report with evidence.

## Part A: code-path inventory

Trace and cite files/classes/tests for:

1. free-text authoring;
2. proposal schemas and workflow unions;
3. compilation and fixture dispatch;
4. component registry/composition receipts;
5. world-state model;
6. patch types;
7. structural topology mutation;
8. active-system creation and scheduling;
9. mechanism/transition execution;
10. any LLM game-master or narrator adjudication;
11. context assembly and retrieval;
12. information/observation projection;
13. checkpoint and replay;
14. simultaneous proposal handling;
15. analytical boundaries; and
16. evidence bundles.

## Part B: capability matrix

For every requested capability, report one of:

- implemented and generally exposed;
- implemented but only through scenario-specific code;
- implemented but bypassed by current authoring/UI;
- partly implemented;
- not implemented;
- intentionally prohibited.

Include at least:

- arbitrary free-text world composition;
- generic component binding;
- entity creation/retirement;
- dynamic connections and spatial links;
- dynamic ports/capabilities;
- dynamic active-system bindings;
- persistent relationship lifecycle;
- dynamic organizations/coalitions;
- LLM adjudication of open-ended actions;
- generic structured patches from an LLM;
- adjudicator context queries;
- actor/umpire information separation;
- coarse/fine resolution declarations;
- exact/stochastic/external transition authorities;
- simultaneous conflict resolution;
- adoption receipts; and
- future experiment forks.

## Part C: dossier accuracy report

For each material mismatch:

- quote or identify the dossier claim;
- identify current code evidence;
- classify the dossier as accurate, incomplete, stale, or ambiguous;
- propose corrected wording.

The free-text authoring/general-composition discrepancy is the first required item.

## Part D: minimal architecture proposals

Do not produce one large redesign. Produce small RFC/ADR candidates, likely including:

1. General Scenario Composition IR;
2. Structural Mutation and Lifecycle Patches;
3. Transition Authority Abstraction;
4. Adjudicator Context and Query Service;
5. Capability/Competency/Affordance Semantics;
6. Subsystem Representation and Resolution Exclusivity;
7. Simultaneous Proposal Resolution; and
8. Scenario Adoption Manifest.

For each candidate include:

- problem;
- current behavior;
- minimum contract;
- alternatives;
- migration path;
- backward compatibility;
- tests;
- risks; and
- deferred questions.

## Part E: prioritized implementation plan

Classify each change as:

- required for the intended general-purpose product;
- required only if LLM adjudication becomes the default;
- desirable but deferrable;
- experimental; or
- unnecessary complexity.

Favor small vertical proofs over broad speculative ontology work.

# 20. Required answer format for each issue

For every major issue in this memorandum, answer using this template:

```text
Issue:

Current code behavior:
- concrete files/classes/functions/tests

Dossier accuracy:
- accurate / incomplete / stale / ambiguous

Product-intent fit:
- aligned / narrower than intended / contradictory / unresolved

Existing abstractions that already solve part of the problem:

Missing capability, if any:

Smallest viable change:

Alternative approaches and tradeoffs:

Backward-compatibility/migration implications:

Acceptance tests:

Priority:
- P0 / P1 / P2 / deferred

Recommendation:
```

# 21. High-value acceptance scenarios

These scenarios are intended to expose architectural capability, not provide domain realism.

## Scenario A: free-text port world

From analyst prose, construct a port world with people, organizations, ships, storage, trucks, fuel, roads, a bridge, software, communications, queues, and weather. Do not select a named `PortCrisis` type. Confirm whether the general authoring path can compile it without new scenario-specific Python.

## Scenario B: destroyed bridge and context retrieval

1. Bridge 7 is destroyed at time 10.
2. At time 100, Alice attempts to drive from A to B.
3. The adjudicator retrieves that Bridge 7 is the only route and is destroyed.
4. The attempt fails or is redirected.
5. Alice receives only an observation justified by her sensors and location.
6. Evidence shows which context was used.

## Scenario C: endogenous coalition

1. Alice and Bob begin unaffiliated.
2. They create a coalition and a shared communication channel.
3. The coalition acquires a warehouse and resource stock.
4. Carol joins and receives delegated authority.
5. Bob later leaves.
6. The coalition dissolves.
7. Historical projections show membership and topology at each revision.

## Scenario D: novel affordance

Alice wedges a chair under a door handle. No action-specific port exists. The LLM adjudicator uses physical-manipulation capability, chair/door properties, and local state to propose an outcome and structured patch.

## Scenario E: coarse versus fine organization

Run one condition with a ministry as a coarse LLM active system and another with people, records, software, and procedures. Verify that the coarse surrogate cannot independently execute in the detailed condition unless an explicit coupling rule gives it a separate role.

## Scenario F: coarse versus fine computer

In a diplomatic scenario, ordinary screenshot editing is LLM-adjudicated. In a cyber scenario, the same external action is resolved by detailed accounts, permissions, services, and network paths behind a compatible boundary.

## Scenario G: simultaneous resource race

Two actors attempt to acquire the same truck in one causal moment. Confirm that outcome is determined by a declared conflict policy or joint adjudication, not incidental canonical application order.

## Scenario H: edited information lineage

Alice creates an edited screenshot from an existing representation and transmits it through an apparent source that differs from actual provenance. Bob observes only the delivered surface. Lineage remains protected and inspectable by authorized analysis.

## Scenario I: insufficient adjudication context

An actor attempts an unusual action for which required state is missing. The adjudicator returns `insufficient_context` or requests clarification/state rather than inventing a confident outcome.

## Scenario J: adoption manifest

Create a new scenario through the intended general authoring path. Verify that its manifest proves use of canonical composition, context projection, transition authority, patch, information, checkpoint, and evidence seams, while listing any bounded exceptions.

# 22. Decision recommendations

## Recommendation 1: do not adopt "mechanisms nowhere" literally

Removing preauthored exact domain mechanisms as the mandatory default is plausible and may be desirable. Removing explicit transition authority, structured patches, validation, canonical state, context management, and evidence is not.

Recommended principle:

> LLM adjudication may be the default transition model at coarse resolution; explicit models are opt-in refinements. Every committed world transition still passes through a common authority, context, patch, validation, and evidence contract.

## Recommendation 2: place structural endogeneity above additional ontology refinement

Before adding many social primitives, establish whether the world can create and retire its own entities, routes, relationships, capabilities, processes, and structures. A fixed graph with changing JSON values will not satisfy the intended general simulator.

## Recommendation 3: make context management coequal with state and adjudication

The success of an LLM game master depends less on generic intelligence than on reliable retrieval of relevant current state. Context assembly should be a first-class runtime service with evidence, access boundaries, and tests.

## Recommendation 4: model worlds, not named crises

Scenario templates may be useful onboarding devices, but the general product should compose the underlying world. Crisis, stability, legitimacy, coalition, and similar concepts may exist in actor cognition or analysis rather than as mandatory world types.

## Recommendation 5: treat representation resolution as an explicit contract

The system should support detailed and coarse representations across organizations, computers, markets, logistics, and other subsystems. It must prevent accidental double execution of the same causal scope.

## Recommendation 6: keep the information boundary comparatively strict

Even a powerful omniscient game master must not silently give actors hidden information. Preserve representation lineage, observation paths, apparent versus actual provenance, and actor-local interpretation.

## Recommendation 7: defer general experiments without foreclosing them

Do not prioritize the full experiment workbench over general composition, structural mutation, and context-aware adjudication. Preserve checkpoint, fork, intervention, configuration, and evidence seams now.

# Appendix A. Source mapping

| Dossier topic | Approximate source location | Use in this memorandum |
|---|---|---|
| Ontology/runtime versus adoption gaps | lines 36-47 | Distinguishes missing abstractions from bypassed capabilities. |
| General-purpose wargaming objective | lines 55-68 | Establishes conditional insight rather than prediction. |
| Authoritative world state | lines 148-154 | Supports retaining a canonical state engine. |
| Entity versus active system | lines 156-172 | Supports flexible coarse surrogates without making kinds intrinsically agentic. |
| Attempt, authorization, and success | lines 174-194 | Supports capability/affordance distinctions. |
| Information lineage | lines 198-214 | Supports strict actor information boundaries. |
| Exact mechanisms | lines 216-233 | Basis for questioning whether a broader transition-authority abstraction is needed. |
| Organizations as analytical boundaries | lines 245-262 | Basis for revising the categorical organization rule. |
| Question-relative representation depth | lines 277-290 | Basis for mixed LLM/exact/stochastic/external models and coarse/fine resolution. |
| Runtime ontology and patch records | sections 4.1-4.4 | Basis for structural-mutation audit. |
| Person input projection | sections 6.2 and 7.5 | Basis for actor-context architecture. |
| Closed authoring workflows | lines 638-660 | Basis for free-text authoring audit. |
| Compiler and fixed composition adapter | lines 662-700 | Basis for general-composition concern. |
| Active runtime and declared mechanism context | sections 7.4-7.8 | Basis for context and transition design. |
| General composition gap | lines 976-1000 | Basis for testing whether authoring is narrower than the substrate. |
| Adoption gap | lines 1002-1020 | Basis for scenario manifests and CI enforcement. |
| Roles, relationships, and world-physics gaps | sections 10.4-10.7 | Basis for optional relationship records and reusable subsystems. |
| Interface vocabulary | section 10.8 | Basis for separating attempt exposure from in-world permission. |
| Simultaneous conflicts | lines 1130-1140 | Basis for conflict-resolution work. |
| Static analytical boundaries | lines 1170-1188 | Basis for structural endogeneity and dynamic grouping. |
| Experiment gap | section 10.14 | Basis for deferred but protected experiment seam. |
| UI mismatch | section 10.15 | Basis for analyst-facing ontology fidelity. |
| Foundation decision | section 10.16 | Basis for framework evaluation questions. |

# Appendix B. Conceptual schemas for discussion, not implementation mandates

## General scenario composition

```text
ScenarioCompositionSpec
    id
    semantic_description
    initial_entities[]
    initial_places[]
    initial_state[]
    initial_carriers_and_representations[]
    capabilities_and_competencies[]
    topology_and_connections[]
    active_system_bindings[]
    transition_authority_bindings[]
    validators_and_invariants[]
    schedules_and_initial_work[]
    subsystem_representations[]
    fidelity_notes[]
    analytical_views[]
    unresolved_questions[]
```

## Transition authority

```text
TransitionAuthoritySpec
    authority_id
    authority_type
    implementation_identity
    accepted_intent_schema
    context_policy
    read_scope
    write_scope
    patch_types
    timing_semantics
    validators
    fidelity_note
    uncertainty_policy
    cost_and_budget
    evidence_policy
```

## Structured world patch

```text
WorldPatch
    patch_id
    parent_event_ids[]
    transition_authority_id
    modeled_time
    operations[]
    observations[]
    scheduled_follow_up[]
    assumptions[]
    confidence_or_insufficiency
    validation_results[]
```

## Context request and receipt

```text
AdjudicationContextReceipt
    intent_id
    initial_projection_refs[]
    tool_queries[]
    returned_state_refs[]
    omitted_or_redacted_refs[]
    temporal_revision
    context_digest
    access_policy
```

## Subsystem representation

```text
SubsystemRepresentationSpec
    subsystem_id
    represented_scope
    active_resolution
    implementation_type
    abstracted_members[]
    preserved_inputs_outputs
    omitted_dynamics
    coupling_rules
    state_transfer_policy
    fidelity_note
    invalid_questions
```

# Appendix C. Compact question inventory

## Authoring and composition

1. What exactly does the free-text tab compile?
2. Are the four workflow families still binding?
3. Can the current authoring LLM compose arbitrary reviewed primitives?
4. Is the fixed component-composition adapter still the only general-looking path?
5. Which requests are silently lost or approximated?
6. Can current templates compile into one generic IR?
7. What requires new Python per scenario?
8. Can a scenario be created without a named scenario class?

## Structural endogeneity

9. Can entities be created and retired during a run?
10. Can places and spatial links be created, destroyed, and repaired?
11. Can connections and ports change?
12. Can capabilities and competency change?
13. Can active processes be created and terminated?
14. Can transition-authority bindings change?
15. Can relationships and organizations form and dissolve?
16. Can structural changes be replayed and projected historically?

## LLM adjudication

17. Is there a current game-master implementation that changes world state?
18. Can it propose structured patches?
19. Does it have typed state-query tools?
20. Is its context provenance retained?
21. Can it return insufficient context?
22. Can it schedule delayed consequences?
23. Can it make structural mutations?
24. How are its read/write permissions constrained?

## Context and information

25. How is relevant state discovered?
26. How are current and superseded facts distinguished?
27. How are actor and adjudicator projections separated?
28. How are distant dependencies such as destroyed bridges retrieved?
29. Can world content prompt-inject the adjudicator?
30. How are hidden provenance and mechanism-only facts protected?
31. Can observations reveal only local surfaces rather than omniscient explanations?

## Capabilities and affordances

32. What remains of the original effector model?
33. Are ports too action-specific?
34. How is competency represented?
35. Can affordances be inferred from object properties and context?
36. Can actors attempt novel actions without declared ports?
37. Can new objects grant new affordances dynamically?
38. How are authorization and feasibility separated?

## Resolution and organizations

39. Can an organization-like entity receive an active-system binding?
40. Can coarse and fine representations be declared explicitly?
41. How is double execution prevented?
42. Can boundaries overlap and change?
43. Can actor-recognized groups differ from analyst boundaries?
44. Can resolution be changed between experimental forks?

## Execution and evidence

45. Can validators apply independently of exact mechanisms?
46. Does canonical ordering bias simultaneous conflicts?
47. Can a moment-level adjudicator resolve proposal sets jointly?
48. Does the evidence bundle distinguish LLM, exact, stochastic, and external rulings?
49. Is execution lineage clearly distinguished from empirical causality?
50. Can a committed run be replayed without re-invoking the LLM?

## Governance and future work

51. Can CI prove that scenarios use canonical seams?
52. Is the composition receipt evidence of actual composition or only post hoc classification?
53. Which experiment seams already exist?
54. Does a framework integration preserve one authoritative world?
55. Which changes are required now and which are avoidable simulation-engine ambition?

# Final instruction to the coding agent

Do not respond with a general agreement or a broad redesign narrative. Return repository evidence, contradictions, capability classifications, minimal alternatives, and acceptance tests. The most important immediate outputs are:

1. the true free-text authoring/compilation trace;
2. the structural-mutation capability matrix;
3. the current status of any LLM game-master adjudication and its context path;
4. a minimal proposal for `TransitionAuthority` plus structured patches;
5. a minimal proposal for adjudicator context retrieval with strict actor-information separation; and
6. a prioritized distinction between capabilities that already exist, capabilities that are merely bypassed, and capabilities that are genuinely absent.
