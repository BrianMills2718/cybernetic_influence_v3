---
doc_role: architecture_research
authority: evidence_record
status: complete_recommendation
created: 2026-08-11
updated: 2026-08-11
depends_on: docs/adr/013-generalized-simulator-foundation.md
---

# Concordia foundation revisit: current source and bridge/port probe

## Decision readout

Reaffirm **ADR-013's Concordia foundation**, but make the boundary more precise:

- Concordia should own the outer entity/component lifecycle, actor selection,
  simulation loop, and invocation of game-master components.
- A project-owned canonical-world component should hold the modeled world's
  persistent records, topology, placements, resources, and transition evidence.
- Project-owned context and transition components should implement the common
  path `world truth -> bounded actor context -> semantic intent -> transition
  authority -> structured patch -> generic validation -> atomic commit ->
  observation`.
- Deterministic mechanisms, stochastic mechanisms, LLM adjudicators, external
  models, scripts, and replay should all implement the same transition-authority
  contract. They differ in fidelity and provenance, not in whether their output
  bypasses validation.
- A person or other autonomous process may be a Concordia entity. A truck,
  bridge, document, route, warehouse, or resource is normally a record in the
  canonical world, not a pretend actor merely because Concordia's base `Entity`
  interface can represent inanimate objects.

This is layered integration, but it is **not Candidate B** as that candidate was
defined. The old `CausalSession` and `ActiveRuntimeSession` do not remain a
second environment, scheduler, checkpoint, or execution authority. The world
kernel is a normal game-master component invoked by Concordia's engine.

Do **not fork Concordia now**. The current public seams were sufficient for the
probe. A fork becomes justified only if a specific required capability cannot
be implemented through a stable public component, entity, simulation, or engine
extension and an upstream-compatible change is not viable.

## Question tested

The prior physical-access parity plan mainly tested whether exact rules could be
ported. The architecture-review questions require a more discriminating test:

> Can Concordia remain the actual simulation foundation while a general world,
> evolving topology, strict information boundary, open semantic action, LLM
> game master, validated structured patch, and checkpoint continuation are
> implemented through public extension seams rather than a hidden second
> simulator?

The bridge/port probe used this trajectory:

1. A worker tries to move a fuel truck to a port over a destroyed bridge.
2. The world rejects the attempt and tells the worker only that the bridge is
   impassable; the hidden cause remains world truth.
3. A temporary depot and route are created during the run.
4. The state is checkpointed and restored into a fresh simulation.
5. A Luna-backed worker proposes its next action from local observations.
6. A separate Luna-backed transition authority converts the open intent into a
   structured patch.
7. Generic code validates identities, write scope, route topology, and hidden
   information before committing the patch.

## Evidence boundary

### Source inspected

The current local Concordia checkout was clean at shallow revision
`131ed0d2ea14754539a3feb9dfd3717d11e859df`. Because the checkout is shallow,
this review could not compute a trustworthy diff from the earlier pinned
`bdb449ab384adf203b09004049184b9176be808f` audit. Findings below describe the
current checkout, not every intervening upstream change.

Source-confirmed current capabilities:

- `EntityAgent` runs component `pre_act`, action, `post_act`, and update phases;
  component state is exposed through public `get_state`/`set_state` seams.
- The generic simulation has public `add_entity` and `add_game_master` methods.
  Checkpoint loading can instantiate a missing entity when its prefab is already
  registered in the configuration.
- The simultaneous engine collects multiple actor actions and presents one
  joint string to the game master for resolution.
- The interrupt scheduler has serializable simulated time, event queues, masks,
  timers, and per-entity pending observations.
- `InteractiveDocumentWithTools` provides an LLM tool loop and records tool
  calls/results in the document.

Focused current-source tests passed:

```text
59 passed in 2.49s
```

The set covered generic checkpoint tests, the simultaneous engine, interrupt
scheduling, and interrupt response parsing. This establishes those focused
behaviors at the inspected revision; it does not certify the full framework.

### Disposable bridge/port execution

The research probe used Concordia's stock `generic.Simulation`, stock
`Sequential` engine, public prefab/component interfaces, and a project-owned
game-master world component. It did not import or execute the Cybernetic
Influence causal or active runtimes.

Observed provider-free path:

```text
destroyed north bridge -> fuel move blocked
temporary depot + route created during execution
checkpoint after two transitions -> fresh simulation restore
fuel truck reaches port on the restored continuation
hidden sabotage cause absent from worker observations
corrupt world checkpoint -> ValueError, not a fallback state
```

This proves that structural changes *inside canonical world component state*
can survive Concordia checkpoint continuation. It does not prove that a new
autonomous Concordia entity can safely be spawned or removed in the middle of
an already-running engine loop.

### Authentic Luna continuation

The final retained model receipts each contain one completed call, no model
error, and subscription-included cost:

| Role | Trace | Observed output |
|---|---|---|
| Worker | `concordia-foundation-revisit/luna/bridge-port-continuation-v3-final` | Open intent `move_fuel_truck` using `temporary_depot_route` |
| Transition authority | `concordia-foundation-revisit/luna/semantic-adjudicator-v3-final` | Two proposed place replacements moving the truck and worker to the port |

The transition authority proposed paths rooted at `/world/entities/...`. The
generic validator accepted `/world` as a declared root alias, canonicalized the
paths, verified that both source placements matched the enabled route, limited
writes to the declared entities' placement fields, checked the public result
against hidden values, and only then committed. The final fuel-truck placement
was `port`.

The successful result is evidence for the extension seam, not for action
quality, realism, robustness, or cross-domain generality.

## The failed attempts were decision-relevant

Two preceding authentic iterations failed at useful boundaries:

1. The actor initially received “a temporary depot is available” without its
   and the truck's current placements. Luna proposed going to the depot rather
   than moving the fuel. The omission was in the observer/context contract.
2. After local placement and route identifiers were made visible, Luna used
   semantically reasonable verbs such as `travel` and `move_fuel_truck`, while
   the exact handler recognized only `deliver_fuel`. The mismatch was in the
   enumerated action interface.
3. The first semantic patch used `/world/entities/...` while the validator
   expected `/entities/...`. The refusal exposed an underspecified patch-root
   convention.

These failures support three architecture requirements:

- local context must expose the current actor-relevant state, not merely the
  last narrative event;
- actors need an open semantic-intent seam rather than a growing catalogue of
  scenario verbs; and
- patch addressing, authority, validation, and atomic commit need one explicit
  contract.

## What Concordia supplies versus what the product must supply

| Concern | Concordia now supplies | Project-owned work still required |
|---|---|---|
| Outer execution | Entity/component lifecycle and sequential, simultaneous, and asynchronous engines | Select and constrain the supported execution profiles |
| Cognition | Reusable memory, perception, planning, and action components | `llm_client` adapter, richer person configuration, bounded context inputs, and adoption in real scenarios |
| World state | Arbitrary serializable component state | General world composition/state contract and validators |
| Semantic action | String action seam | Typed semantic intent and transition-authority contract |
| LLM game master | Generative resolver patterns | Structured patch output, read/write authority, provenance, invalid-question declarations, and generic invariant gate |
| Information | Observation strings and queues | World truth/representation/delivery/interpretation separation and actor-specific context projection |
| Structural change | Mutable component state; runtime entity addition API | General topology patch operations, active-system binding semantics, safe spawn/removal, and resolution consistency |
| Time/concurrency | Multiple engines plus interrupt scheduler | Transaction/conflict semantics for simultaneous world patches |
| Checkpoint | Generic component snapshots and prefab-based restoration | Strict lossless codec/validation for canonical state and failure propagation |
| Authoring | Prefab/config assembly | LLM-authored general composition contract compiling only to registered implementations |
| Evidence | Component and structured logs | Retained intent, context, proposed patch, validation, commit, observation, and model-call lineage |

## Material defects or limitations in the current public defaults

These are source-confirmed and must not be described as solved:

1. `Entity.act` and `Entity.observe` still cross the framework boundary as
   strings. Structured intent and observation envelopes must be implemented by
   product components and validated at their boundaries.
2. Generic checkpoint conversion silently drops values it cannot make JSON
   serializable. That behavior is explicitly tested upstream.
3. `EntityAgent.set_state` catches component restore exceptions, logs them, and
   continues. The probe required a strict subclass so corrupt canonical-world
   state actually failed the restore.
4. The stock generative `WorldState` stores LLM-selected string variables; it
   is not a canonical typed world or patch authority.
5. Stock interrupt scheduling adds unmatched events to non-polled entities'
   pending queues for later delivery. That is attention scheduling, not the
   required information-access boundary.
6. `InteractiveDocumentWithTools` returns tool failures to the model as error
   strings. It is useful for cognition, but it is not by itself a fail-loud
   trusted world-query boundary.
7. The simultaneous engine offers one joint resolution opportunity, but it
   does not provide typed patch conflicts, isolation, ordering, or transaction
   semantics.
8. Generic entity/component membership is construction-oriented. Public
   `add_entity` exists, but live endogenous spawning, removal, component
   rebinding, and checkpoint-consistent scheduler updates are not established.

## Explicit uncertainty register

### Resolved enough for the foundation decision

- **Can exact and coarse world state coexist in Concordia components?** Yes.
- **Can the stock Concordia engine invoke a project-owned canonical world and
  transition component without the old runtime?** Yes, in the bounded probe.
- **Can topology records change during a run and survive checkpoint restore?**
  Yes, for records inside one canonical component.
- **Can an authentic actor and authentic LLM game master use the same path?**
  Yes, once, using Luna and `llm_client`.
- **Is a private Concordia fork required for this path?** No evidence says so.

### Indicated but not established

- **General composition:** the world component shape appears compatible with a
  general composition contract, but no analyst-authored port world compiled
  through one reusable contract in this probe.
- **Cross-domain reuse:** the context/intent/patch sequence is domain-neutral in
  form, but only one logistics movement was executed.
- **Information safety:** a hidden cause did not leak in this case, but the
  validator only checked one narrow class of literal leak. It is not a general
  noninterference proof.
- **LLM adjudication:** Luna produced a valid patch once after two interface
  defects were corrected. This does not establish reliability or appropriate
  judgment across ordinary actions.
- **Checkpoint adequacy:** strict restoration is possible with a custom entity
  subclass and JSON-safe state. The correct production codec and how much of
  Concordia's generic checkpoint to retain remain undecided.
- **Cognition reuse:** Concordia has richer person components than the current
  outbreak scenario uses, but no migration proves that they preserve the
  previously reviewed values, goals, beliefs, tendencies, memories, and local
  information contract.

### Unknown and decision-sensitive

- Whether live engine loops safely notice a newly added autonomous entity.
- How to remove, replace, suspend, or rebind active entities and components
  without stale scheduler, game-master, or checkpoint references.
- Whether active system creation should occur immediately inside a commit or at
  a defined safe boundary between engine moments.
- The smallest generic conflict language for simultaneous incompatible patches.
- The correct transaction boundary when exact mechanisms, LLM adjudicators,
  and external simulators jointly affect one moment.
- How open an LLM patch authority may be before generic invariant protection
  becomes either unsafe or so elaborate that it defeats rapid wargaming.
- Which context queries actors and adjudicators need, how they are authorized,
  and how query results retain provenance without flooding prompts.
- Which representations, resources, custody, conservation laws, and historical
  records deserve universal kernel invariants versus optional subsystem rules.
- How coarse and fine representations declare causal responsibility so both do
  not execute the same function simultaneously.
- How to compile arbitrary analyst prose into the general composition contract
  without inventing executable Python, binding unsupported implementations, or
  falling back to scenario families.
- Scale, latency, cost, and behavioral stability for many active systems,
  multirate processes, or long runs.
- Upstream API stability and whether the inspected shallow revision is the
  right long-lived pin.

## Candidate comparison after the probe

| Candidate | Current judgment | Reason |
|---|---|---|
| A — Concordia foundation plus project world components | **Reaffirm** | Stock engine and public components executed the discriminating path; no old runtime or fork was required |
| B — Concordia cognition around the old CI environment | **Reject for now** | Preserves dual lifecycle, state, checkpoint, and scheduling authorities without a demonstrated need |
| C — independent/CI foundation with adapters | **Fallback** | Stronger existing exact semantics, but higher framework ownership and less Concordia reuse; reconsider only on a concrete A blocker |
| Private Concordia fork | **Defer** | No public-seam blocker was found; a fork would add merge and upgrade cost before necessity |

## Recommended next implementation slice

Replace the old physical-access-only parity handoff with one general
bridge/port vertical:

1. Define the minimum composition, actor-context, semantic-intent,
   transition-authority, patch, validation, and evidence contracts.
2. Host them as public Concordia entity/game-master components under a stock
   engine; do not call the old causal/active runtime.
3. Represent the worker as active and the truck, bridge, route, fuel, and depot
   as world records.
4. Execute deterministic and Luna-backed transitions through the same patch
   gate, including the failed bridge move, dynamic depot/route creation, and
   successful continuation.
5. Checkpoint before the continuation and restore strictly.
6. Compile the case from the general composition contract rather than a
   `PortScenario` Python class.
7. Only after this works, route one existing public simulation path through the
   same adopted seam so the machinery cannot become another unused subsystem.

This is the smallest path that tests the architecture the product now needs. A
physical-access port would still be useful later as an exact-mechanism example,
but it no longer owns the foundation decision's critical path.
