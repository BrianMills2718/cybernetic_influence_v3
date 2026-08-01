---
doc_role: architecture_research
authority: evidence_record
status: complete_decision_adopted
created: 2026-07-31
updated: 2026-07-31
---

# Slice 26 foundation comparison

## Product-owner disposition

On 2026-07-31, after reviewing the technical recommendation and clarifying the
product goal, the product owner adopted **A — Concordia foundation**. The target
is a generalizable simulation system for bounded socio-technical worlds;
wargaming is one exemplar rather than the product definition. Simulation is an
exploratory instrument for conditional pathways, mechanisms, and sensitivities,
not a claim to decision-grade prediction of chaotic social systems.

The owner explicitly judged that preserving every Cybernetic Influence runtime
invariant as a foundational requirement may cost more than it contributes to
that broader goal. Selected Cybernetic Influence mechanisms and analytical
ideas remain candidates for reuse as Concordia components or projections. The
accepted decision is recorded in [ADR-013](../adr/013-generalized-simulator-foundation.md).

## Research recommendation under the frozen Slice 26 contract

Recommend **C — Cybernetic Influence foundation with compatibility adapters**.
Keep the existing typed causal runtime as the sole authority for world state,
time, exact effects, observations, evidence, replay, and analysis. Retain its
existing provider-neutral active-system protocol as the cognition port. Add a
narrow Concordia-compatible entity adapter where its component ecosystem has
concrete value, but Concordia's
engine, game master, scheduler, checkpoint, and log are not product authorities.

The strongest rejected alternative is **B — Concordia cognition around a
Cybernetic Influence environment**. It preserves the causal authority, and it
could reuse more cognition machinery immediately. It is rejected because making
Concordia's entity/component lifecycle a privileged product layer creates two
state and checkpoint models, string-to-typed translation at every participant
action, and upstream/provider coupling before a demonstrated product need.
Candidate C preserves the same future option behind an adapter without making
that dependency architectural.

This was the technical recommendation under the original frozen comparison
contract, which treated all Cybernetic Influence invariants as non-negotiable.
It remains evidence, not the adopted product decision. The owner's clarified
outcome changed the tradeoff rather than invalidating the source audit.

## 26A — Frozen comparison contract

### Pinned evidence

| System | Inspected revision | Status |
|---|---|---|
| Cybernetic Influence v3 | `e7faf25e21abb8950a18955600bbbf7a36b76104` | Product baseline; source is unchanged at the Slice 26 planning revision `a11b68658bec0f71815bd9b2220d72c0cad24f18` |
| Concordia | [`bdb449ab384adf203b09004049184b9176be808f`](https://github.com/google-deepmind/concordia/tree/bdb449ab384adf203b09004049184b9176be808f) | Detached clean checkout inspected |
| `data_contracts` | [`d845be0c5813ab26e9bf2f1eaf4473a262ac541b`](https://github.com/BrianMills2718/data-contracts/tree/d845be0c5813ab26e9bf2f1eaf4473a262ac541b) | Detached content of the clean local revision inspected |
| Generative Agents | [`fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4`](https://github.com/joonspk-research/generative_agents/tree/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4) | Detached clean checkout inspected |
| AgentVille candidate | [`d11679a03b172aa0d1d2b5000cacecc15fcffb13`](https://github.com/pranayjoshi/Agentville/tree/d11679a03b172aa0d1d2b5000cacecc15fcffb13) | Detached clean checkout inspected; see identity limitation below |

The invariants, three cases, six-value capability taxonomy, and twelve decision
criteria are exactly those in the [Slice 26 plan](../plans/026-concordia-foundation-research.md).
No candidate receives credit for theoretical expressiveness alone. `custom_component`
means a supported public extension; replacing state, scheduling, adjudication,
observation, or evidence ownership is `engine_replacement` even if Python makes
the replacement possible.

### Existing product inventory

Cybernetic Influence already has one strict `CausalState`, typed mechanisms,
carrier/representation lineage, typed action attempts, committed events and
observations, positive causal time, checkpoints, retained runs, derived
analytical boundaries, multirate active participants, reviewed authoring, and
analyst step-down. The source anchors are [causal models](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/causal_core/models.py),
[causal execution](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/causal_core/engine.py),
[active runtime](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/engine.py),
[active-system protocol](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/protocol.py),
[composition](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/authoring/composition.py), and
[retained run storage](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/run_store.py).

Its bespoke burden is also real: the compiler and component registry are still
product-specific; no external-framework cognition adapter exists; scenario
families are limited; and the project owns its runtime, checkpoint, server,
evidence, and product surfaces. Slice 25 proves a bounded composition path, not
a broad component ecosystem or a generalized world builder.

## 26B — Source audit

### Concordia

Concordia is not merely prose state. `EntityWithComponents` serializes component
state and restores it through public `get_state`/`set_state` methods
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/typing/entity_component.py#L118-L227)).
The inventory game-master component maintains exact Python quantities and has a
public, validated `apply` operation
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/inventory.py#L55-L69),
[source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/inventory.py#L376-L403)).
That corrects the motivating premise: exact components are supported.

The default agent/environment seam is nevertheless textual. `ActionSpec`
offers free text, choices, or floats, while `Entity.act` returns a string and
`observe` receives a string
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/typing/entity.py#L73-L120),
[source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/typing/entity.py#L204-L247)).
The sequential engine asks the game master for the next actor/action spec,
obtains an entity string, and asks the game master to resolve that putative
event into another string
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/environment/engines/sequential.py#L93-L170)).
The stock event resolver uses a language-model chain both to resolve events and,
optionally, select observers
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/event_resolution.py#L40-L104)).
Exact adjudication can be installed, but the product would own that replacement.

The interrupt-driven prefab supplies useful scheduling machinery: per-entity
masks and timers, a sorted event queue, monotonic datetime, and serializable
scheduler state
([scheduler](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_scheduling.py#L157-L288),
[time model](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_time_model.py#L178-L242)).
Its observation semantics do not supply the product's information boundary:
the next-actor component puts an event into every non-polled entity's pending
queue, and the observation component later renders all pending events as prose
([selection](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_next_acting.py#L102-L190),
[delivery](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_make_observation.py#L63-L109)).
The event record has time, tag, source, and description, but not copy lineage,
permissions, causal parents, attempts, decisions, and commits
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_scheduling.py#L42-L67)).

Concordia checkpoints entity/game-master component state and its raw log
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/prefabs/simulation/generic.py#L333-L380)).
Its structured log is content-addressed and component-oriented
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/utils/structured_logging.py#L15-L22)),
but it does not natively encode the required causal distinctions. More
importantly, checkpoint conversion deliberately drops non-JSON-serializable
values, behavior covered by a test
([implementation](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/prefabs/simulation/generic.py#L382-L404),
[test](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/prefabs/simulation/checkpoint_test.py#L133-L150)).
The inventory inference path and interrupt resolver also contain fallback
behavior rather than the product's fail-loud boundary
([inventory](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/inventory.py#L265-L281),
[interrupt resolution](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/components/game_master/interrupt_resolution.py#L163-L180)).

The simulation server is useful reusable product inspiration—HTTP state,
server-sent events, play/pause/step, and paused component editing—but is a
generic visualization server rather than parity with the current analyst flow
([source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/utils/simulation_server.py#L32-L39),
[source](https://github.com/google-deepmind/concordia/blob/bdb449ab384adf203b09004049184b9176be808f/concordia/utils/simulation_server.py#L117-L176)).

### Cybernetic Influence end-to-end path

1. Reviewed authoring resolves registered selections and emits a composition
   receipt; implementation dispatch remains product-owned
   ([composition](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/authoring/composition.py)).
2. A scenario validates one strict `CausalState`, typed mechanisms, topology,
   routing, lineage, analytical boundaries, timing, and fidelity declarations
   ([models](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/causal_core/models.py)).
3. `ActiveRuntimeSession` owns one `CausalSession`; `core_state` is the sole
   canonical world state. Due exact work settles before participant activation,
   and a participant proposal is trial-run and committed atomically
   ([active runtime](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/engine.py)).
4. The causal engine validates actor and output ownership, routes
   representations explicitly, constrains mechanism reads/writes, validates
   invariants, and records attempt, decision, positive-time commit,
   observations, and downstream work
   ([causal engine](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/causal_core/engine.py)).
5. Full typed checkpoints and run artifacts are written atomically and validated
   on load; analysis consumes retained evidence rather than narrator prose
   ([run store](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/run_store.py),
   [theory analysis](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/analysis/theory_analysis.py)).

This path natively answers the twelve source questions. `ActiveSystemImplementation`
is already a provider-neutral protocol over strict `ActiveSystemInput` and
`ActiveStepResult`; `ActiveSystemState` protects JSON private state, and failed
steps are retained before any causal commit
([protocol](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/protocol.py),
[models](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/models.py),
[atomic collection](https://github.com/BrianMills2718/cybernetic_influence_v3/blob/e7faf25e21abb8950a18955600bbbf7a36b76104/src/cybernetic_influence/active_runtime/engine.py)).
The missing seam is therefore a concrete external-framework compatibility
adapter, not a new cognition port. Candidate C retains and proves this existing
boundary without moving world authority.

### `data_contracts.composition`

The shared package supplies typed manifests, bindings, resolution/compilation,
facts, transitions, and deterministic conformance over a caller-injected pure
callable. It explicitly does **not** discover implementations, dispatch,
persist, retry, reconcile, or execute effects
([contracts](https://github.com/BrianMills2718/data-contracts/blob/d845be0c5813ab26e9bf2f1eaf4473a262ac541b/src/data_contracts/composition/contracts.py#L1-L6),
[conformance](https://github.com/BrianMills2718/data-contracts/blob/d845be0c5813ab26e9bf2f1eaf4473a262ac541b/src/data_contracts/composition/conformance.py#L1-L6)).
Its conformance runner rejects effectful descriptors and checks repeated pure
execution for declared deterministic behavior
([source](https://github.com/BrianMills2718/data-contracts/blob/d845be0c5813ab26e9bf2f1eaf4473a262ac541b/src/data_contracts/composition/conformance.py#L99-L184)).

Disposition: **adapt**, not adopt as runtime. Use it later as the shared
compile-time manifest/binding/conformance substrate after a small projection
from causal component declarations is proven. Cybernetic Influence must retain
implementation discovery, exact effect execution, state, scheduling, evidence,
and replay. Do not migrate Slice 25 merely for schema uniformity.

### Separable prototype machinery

Generative Agents' durable idea is the persona cognition sequence—perceive,
retrieve, plan, reflect, execute—around spatial and associative memories
([persona](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/persona/persona.py#L81-L224)).
Its retrieval ranks memory by recency, importance, and relevance
([source](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/persona/cognitive_modules/retrieve.py#L199-L280)).
The implementation is coupled to its maze, scratch/associative memory files,
and direct model helpers; execution maps plan strings directly to maze paths
([source](https://github.com/joonspk-research/generative_agents/blob/fe05a71d3e4ed7d10bf68aa4eda6dd995ec070f4/reverie/backend_server/persona/cognitive_modules/execute.py#L15-L159)).
Reuse the cognitive decomposition as a pattern, not the runtime code.

“AgentVille” was ambiguous: several unrelated GitHub repositories use the
name. The pinned `pranayjoshi/Agentville` revision was selected because it is
the source that matches an autonomous multi-agent town. This identity choice
is an explicit research assumption, not evidence of ecosystem maturity. Its
README describes Gemini function calling, SQLite state, server-sent events,
and fair scheduling
([README](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/README.md#L13-L34)).
Source confirms a direct Gemini client and function-call-to-SQLite handlers
([runtime](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/server/engine/agentRuntime.js#L479-L597),
[tools](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/server/engine/tools.js#L82-L129)).
Its scheduler uses wall-clock intervals, randomized tie breaks, and in-memory
last-tick data
([source](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/server/engine/agentRuntime.js#L609-L696)).
Failed or absent model actions invoke unrecorded productive world mutations,
and several exceptions are ignored
([source](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/server/engine/agentRuntime.js#L556-L605),
[source](https://github.com/pranayjoshi/Agentville/blob/d11679a03b172aa0d1d2b5000cacecc15fcffb13/server/engine/agentRuntime.js#L698-L826)).
Only the function-tool UX and live town visualization are separable product
references; no runtime, evidence, scheduling, or cognition code should be
adopted.

## Evidence-linked comparison matrix

Each classification is followed by its evidence anchor. “CI” refers to the
end-to-end product path above; “CC” to Concordia's component/state seam; “CE”
to its engine/resolution seam; “CS” to interrupt scheduling/observation; “CP”
to checkpoint/log behavior; and “DC” to the shared compile-time contracts.

| Requirement | A — Concordia foundation | B — Concordia cognition / CI environment | C — CI + compatibility adapters | D — independent CI product |
|---|---|---|---|---|
| Single state/invariants | `engine_replacement` — CC can hold exact state, but CE/CS must be replaced for one typed authority | `native` — CI owns state and adjudication; Concordia state is cognition-only | `native` — CI owns both; adapter cannot mutate world | `native` — CI |
| Reusable stable machinery | `ordinary_configuration` for entities/components/server; `custom_component` for exact rules — CC/CE | `ordinary_configuration` for entity components plus a `custom_component` adapter — CC | `custom_component` compatibility adapter; otherwise CI | `native` CI only; external patterns are not dependencies |
| Cognition/environment translation | `custom_component` at typed mechanism seam plus `engine_replacement` for resolution — Entity strings/CE | `custom_component` on every observe/act boundary — Entity strings | `custom_component` at one optional adapter boundary — Entity strings/CI | `native` local participant seam, but no cross-framework compatibility |
| Authoring/composition | `custom_component` — Concordia prefab/component assembly plus product compiler | `custom_component` — two component models plus DC later | `custom_component` — current Slice 25 seam; DC projection later | `custom_component` — same as C without compatibility contract |
| Multirate/concurrency | `custom_component` for scheduling; `engine_replacement` for visibility/causal ordering — CS | `native` CI; Concordia scheduler unused | `native` CI | `native` CI |
| Evidence/replay | `engine_replacement` — CP cannot express required semantics and may drop values | `native` CI; cognition state needs explicit snapshot adapter | `native` CI; adapter state is an explicit checkpoint payload | `native` CI |
| Spatial/information model | `engine_replacement` — CS broadcasts pending prose without lineage/permission | `native` CI; translated observations only | `native` CI | `native` CI |
| Waltzman–Levin fit | `custom_component` plus `engine_replacement` for evidence step-down — CE/CP | `native` CI analysis over CI evidence | `native` CI analysis over CI evidence | `native` CI analysis over CI evidence |
| Migration from current product | `engine_replacement` of runtime, scheduler, checkpoint, and evidence | `custom_component` cognition adapter and state snapshot | `custom_component` external-framework adapter on the existing stable port; no data migration | `ordinary_configuration`/refactor only, but closes compatibility option |
| Maintenance/upgrades | `architectural_conflict` — most foundational defaults are replaced | `custom_component` — dependency and dual lifecycle remain | `ordinary_configuration` — optional adapter version boundary | `native` local ownership; maximum product code ownership |
| Differentiation vs reimplementation | `architectural_conflict` — differentiated causal core becomes replacement engine | `custom_component` — reuses cognition while retaining differentiation | `native` differentiated core; opt-in reuse | `native` differentiation, but reimplements all agent ecosystem seams |
| Materially different scenario | `not_yet_known` until product compiler and replacements are proven | `custom_component` for new exact mechanisms; cognition reusable | `custom_component` for genuinely new mechanisms; reviewed components otherwise | `custom_component`; highest risk of bespoke cognition work |

The matrix does not manufacture a score. Candidate A loses because preserving
the fixed invariants repeatedly changes Concordia's foundational ownership,
not because Concordia lacks expressive power. Candidates B and C both preserve
the product contract. C wins the narrower architectural claim because no
current canonical scenario requires Concordia-specific lifecycle authority.

## 26C — Same-case walkthroughs

### Case 1: physical access

| Candidate | Owning object and call path | Transition and evidence | Replacement/duplication |
|---|---|---|---|
| A | Concordia entity memory produces a string action; a custom game-master component parses credential/door intent; exact inventory/access/latch components own Python state | A replacement resolver must record authentication, authorization, latch decision, traversal attempt, positive-time commit, and observations as typed linked records | Replace CE resolution, CS observation, and CP evidence/checkpoint semantics; otherwise prose event is the only common authority |
| B | Concordia entity observes a rendered, authorized CI observation and returns a string; adapter emits a typed `ActionAttempt`; CI `CausalSession` owns credential, policy, latch, door, and location | Existing mechanism calls separately decide authentication, authorization, physical success, and positive-time traversal; retained CI evidence explains failure | Duplicate cognition/component checkpoint state; no world-state duplication if adapter is read-only |
| C | Provider-neutral cognition receives typed input; an optional Concordia-compatible adapter alone renders/decodes it; CI owns the same physical-access path | Existing typed attempt/decision/commit/observation and checkpoint remain canonical | One adapter and reviewed translation schema; no engine replacement |
| D | Current participant implementation calls CI directly | Existing physical-access scenario and run artifacts remain canonical | No translation, but product owns every future cognition integration |

### Case 2: hidden microphone and copied information

| Candidate | Owning object and call path | Transition and evidence | Replacement/duplication |
|---|---|---|---|
| A | Custom spatial/sensing, recorder, storage, and access components must intercept a speech string and create distinct representations | Replacement engine must route utterance→sound→recording→stored copy→later delivery, checking capability, permission, and success at each edge and retaining causal parents | CS pending-event broadcast is semantically wrong for hidden sensing; CE and CP must be replaced for lineage and evidence |
| B | Concordia supplies only Alice/Bob cognition; CI creates sound and each representation copy and delivers only authorized observations | CI representation IDs, source IDs, mechanism events, decisions, commits, and later observations retain the complete chain | Adapter must prevent raw world context from bypassing CI visibility; cognition snapshot remains secondary |
| C | Same CI path; any cognition adapter receives only the already-selected observation envelope and returns an intent | CI alone owns copies, storage, permissions, timing, evidence, and replay | One enforceable adapter contract; Concordia-specific behavior is optional |
| D | Current CI participants consume authorized observations directly | Same native CI causal chain | No external lifecycle, but all memory and social cognition remain local work |

### Case 3: organization under heterogeneous influence

| Candidate | Owning object and call path | Transition and evidence | Replacement/duplication |
|---|---|---|---|
| A | Concordia entities/components model each person; custom meeting, record, feedback, gate, and boundary components operate under a replaced scheduler/environment | Replacement evidence must retain heterogeneous deliveries, person-local attempts, mechanism commits, boundary crossings, and derived Waltzman/Levin readouts | Organizations can be analytical, but default game-master narration/logs cannot support lower-level step-down; scheduler and evidence replacement recur |
| B | Concordia cognition holds person-local memory/social components; CI schedules people and mechanisms, routes representations, commits meetings/records/gates, and derives analytical boundaries | CI run bundle grounds boundary compression and Waltzman/Levin analysis in lower-level state/events | Strong reuse option, but two component/state lifecycles and mandatory string translation for every person |
| C | Pluggable cognition implementations receive the same authorized CI inputs; CI schedules all participants/mechanisms and owns the boundary/readout path | Existing run-evidence bundle and analytical step-down remain authoritative regardless of cognition backend | Adapter can later host Concordia memory/social components if evidence shows value; no privileged dependency now |
| D | CI owns cognition interface and all implementations | Same CI evidence/analysis path | Clean authority, highest ongoing cost for memory, reflection, social components, and ecosystem interop |

### Spike decision

No 26C spike was triggered. Source establishes the decision-changing seams:
Concordia exact component state is possible, its public agent seam is textual,
its stock engines own prose resolution/observation, and CI already owns the
required exact transition/evidence path. A production integration would not
answer a remaining architectural unknown more safely than these sources.

## 26D — Ownership and migration

### Proposed authority map

| Concern | Authority under Candidate C |
|---|---|
| Cognition/memory/planning | Existing provider-neutral `ActiveSystemImplementation` protocol; implementations may be native or compatibility adapters |
| LLM invocation | Shared `llm_client`, always outside exact adjudication |
| World state | One CI `CausalState` inside one active causal session |
| Scheduling/time | CI active runtime and causal queue |
| Interpretation | Cognition adapter may propose a reviewed typed intent; invalid translation fails visibly |
| Adjudication/effects | CI mechanisms with declared reads, writes, invariants, and positive time |
| Observation/lineage | CI routing, representations, observations, and causal parents; adapters receive only authorized envelopes |
| Checkpoint/replay/evidence | CI checkpoint and retained run bundle; adapter state is an explicitly versioned payload within it |
| Authoring/composition | CI reviewed compiler/registry now; evaluate a narrow projection to `data_contracts.composition` later |
| Analysis | CI derived analytical views over retained evidence; never cognition or organization state authority |

### Existing artifact disposition

| Existing work | Disposition | Reason |
|---|---|---|
| Causal models, engine, and active runtime | **keep** | They implement the non-negotiable state, time, adjudication, and evidence contract |
| Checkpoints, run store, retained runs/traces | **keep** | No migration is needed; historical evidence remains readable and authoritative for its revision |
| Theory analysis and analytical boundaries | **keep** | Correctly derived from lower-level evidence and execution-inert |
| Current participant implementations and protocol | **keep** | They already use the typed provider-neutral port and protected private state |
| Slice 25 registry/composition receipt | **keep**, then evaluate **adapt** | Do not migrate until a concrete `data_contracts` projection reduces duplication |
| Scenario compiler/templates | **adapt incrementally** | Remove scenario-family assumptions only when a materially different case reproduces them |
| Concordia engine/game master/scheduler/checkpoint/server | **do not adopt** | Their ownership conflicts with the product contract; source remains design reference |
| Concordia entities/components | **optional adapter target** | Adopt only for a demonstrated component need and through the same cognition port |
| Generative Agents code | **do not adopt**; reuse pattern | Cognitive decomposition is useful, implementation is tightly coupled |
| AgentVille candidate code | **do not adopt**; reuse UI/tool ideas | Direct provider/runtime coupling and silent productive fallbacks violate the contract |

### Uncertainties and bounded claims

- A future Concordia component may justify a compatibility adapter. This
  research does not claim that no such component will be useful.
- Candidate C does not prove that current authoring generalizes to every world.
  A materially different scenario remains the correct test.
- The AgentVille repository identity was inferred from the handoff's label and
  public description. No decision depends on that prototype.
- This architecture supports inspectable simulation; it does not establish
  predictive validity, empirical calibration, or model quality.
- The separate MVP stakeholder-comprehension judgment remains open and is not
  advanced by this architecture research.

## Acceptance evidence

| Criterion | Result |
|---|---|
| R1 capability-equivalent premise | Pass — exact Concordia state and hybrid representation are explicitly credited |
| R2 identical invariants/cases | Pass — one frozen matrix and all three A–D walkthroughs |
| R3 immutable evidence | Pass — external claims link pinned commits; CI claims link pinned-baseline source paths |
| R4 fixed taxonomy | Pass — every matrix cell uses one of the six values |
| R5 authority boundaries | Pass — the original authority map supported the research recommendation; accepted ADR-013 now owns the revised foundation boundary |
| R6 strongest rejection | Pass — Candidate B is stated and represented fairly |
| R7 migration disposition | Pass — keep/adapt/do-not-adopt dispositions cover current code and retained evidence |
| R8 smaller-than-rewrite next slice | Pass after owner revision — the original Candidate C handoff was replaced by a Concordia-foundation parity proof after Candidate A adoption |
