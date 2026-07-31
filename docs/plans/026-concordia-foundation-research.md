---
doc_role: research_execution_plan
authority: bounded_design
status: selected
created: 2026-07-31
updated: 2026-07-31
supersedes: further Slice 25 expansion before a foundation decision
---

# Slice 26: Foundation decision for a generalized cybernetic simulator

## Outcome

Decide, from source-level evidence, whether the generalized Cybernetic
Influence product should be built on Concordia, remain on its current runtime,
use Concordia for cognition around one Cybernetic Influence causal
environment, or remain independent behind an adapter boundary. Record the
decision, rejected alternatives, migration consequences, and next smallest
implementation slice before expanding the component catalog.

This is a research and architecture-decision slice. It does not authorize a
production integration, runtime rewrite, new scenario family, or live model
spend.

## Corrected premise

The frameworks must not be compared as though Concordia were fundamentally
string-based and Cybernetic Influence fundamentally typed:

- Concordia entities and game-master components can maintain arbitrary Python
  state and enforce exact rules while using natural language at other seams.
- Cybernetic Influence can use LLM interpretation and narrative context around
  typed entities, mechanisms, and evidence.
- Both can represent a hybrid of open-world language and exact causal state.

The real question is how the same implementation is shaped: where authoritative
state lives, where prose becomes a typed action, who advances time, where
invariants are enforced, how evidence is retained, how much framework machinery
must be replaced, and whether upgrades preserve the product's guarantees.

The representation boundary also remains a design question. A prose-only world
makes exact state and provenance hard to audit; a universal ontology creates
authoring burden, ontology explosion, and false precision. The working
hypothesis is question-relative typed causal islands for material facts and
mechanisms, surrounded by narrative or explicitly coarse context. Research
must test this hypothesis rather than assume it proves one framework superior.

## Product goal held constant

The target is a generalized product competitive with agent-simulation
frameworks and differentiated by inspectable cybernetic and multiscale
analysis. An analyst should be able to:

1. conversationally specify a bounded world with people, devices, records,
   information, places, mechanisms, timing, and analytical boundaries;
2. review and correct the compiled model before execution;
3. run autonomous LLM and non-LLM processes on appropriate timescales;
4. inspect spatial topology, configured pathways, realized causality,
   narratives, and exact evidence;
5. analyze composite agency without inventing an organization mind; and
6. later compare perturbations without presenting simulation as ground truth.

## Non-negotiable invariants

- **One authoritative world state.** Facts cannot silently diverge between an
  agent prompt, game-master narrative, and exact mechanism.
- **Interpretation is not adjudication.** LLMs may interpret intent or fill a
  reviewed schema; exact mechanisms own declared invariants.
- **Information has lineage.** The system can explain which representation
  reached whom, by which mechanism, and what later behavior used it.
- **Capability, permission, and success differ.** Possible effectors, policy
  representations, authorization decisions, and world outcomes stay distinct.
- **Autonomous multirate evolution.** People, devices, transport, markets, and
  coarse processes may evolve at different cadences without an LLM call for
  every microscopic update.
- **Positive causal time.** Distinct cause-and-effect steps cannot collapse
  into one timestamp; atomic bookkeeping may share a time.
- **Organizations are analytical boundaries.** Members and mechanisms act;
  boundary-crossing inputs and outputs support coarse-grained accounts.
- **Question-relative fidelity.** Typed depth, coarse processes, assumptions,
  and omissions are explicit and replaceable.
- **Replayable evidence.** A retained run can be reopened and inspected without
  re-execution or reliance on narrator prose.
- **Provider-independent cognition.** LLM calls use shared `llm_client` and do
  not determine the runtime architecture.
- **No scenario-specific product fork.** A new bounded scenario uses reviewed
  components when it introduces no genuinely new primitive.

## Baselines to pin and inspect

| System | Starting revision | Required inspection |
|---|---|---|
| Cybernetic Influence v3 | `e7faf25e21abb8950a18955600bbbf7a36b76104` | runtime, scheduler, mechanisms, compiler, evidence, authoring, maps, boundaries, Slice 25 seams |
| Concordia | `bdb449ab384adf203b09004049184b9176be808f` | entities, components, game master, engines, state, scheduling, checkpointing, logs, server/UI, exact-state examples |
| shared `data_contracts` | `d845be0c5813ab26e9bf2f1eaf4473a262ac541b` | composition manifests, bindings, compiler/resolver, facts, transitions, conformance, and consumer-owned runtime boundary |
| Generative Agents | pin during 26B | memory, reflection/planning, space, scheduling, separable reuse |
| AgentVille | pin during 26B | source-backed capabilities, maturity, and separable reuse |

Primary sources, source code, tests, and executable examples outrank product
positioning. Final claims must cite immutable revisions.

## Candidate architectures

### A — Concordia foundation

Use Concordia's entities, components, engine, game master, scheduling, logging,
checkpointing, and server foundation. Implement Cybernetic Influence's typed
mechanisms, lineage, graph projections, analytical boundaries, and analyses as
Concordia components or extensions.

### B — Concordia cognition around a Cybernetic Influence environment

Keep one Cybernetic Influence causal runtime authoritative. Use Concordia
entities/components for cognition, memory, or social machinery through a narrow
adapter. Cybernetic Influence owns scheduling, exact effects, evidence, and
replay.

### C — Cybernetic Influence foundation with compatibility adapters

Keep the current runtime and make cognition/components pluggable behind a small
interface that can host Concordia-compatible entities when valuable. Reuse
selected libraries or patterns without making Concordia's engine authoritative.

### D — Independent product

Continue without a Concordia dependency. Reuse only separable libraries and
accept ownership of runtime, agent, checkpoint, server, and product surfaces.

Evaluate `data_contracts.composition` as a compile-time contract and
conformance substrate under any candidate. Do not presume it discovers, loads,
or executes implementations.

## Three canonical architecture walkthroughs

For each case, trace the same facts through A–D. Identify the owning object,
call boundary, transition, evidence, and framework replacement—not merely that
an extension is theoretically possible.

### Case 1 — Physical access

Alice attempts to enter an equipment room. She can present a credential and
operate a door, but entry may fail because the credential is invalid,
authorization is absent, or the latch is jammed. Trace memory and perceived
policy, credential presentation, separate authentication/authorization, latch
and door state, traversal and elapsed time, attempted versus committed effects,
and the evidence explaining the result.

### Case 2 — Hidden microphone and copied information

Alice speaks to Bob in a room containing a microphone she may not know about.
The microphone, recorder, storage, and later listener create distinct copies.
Trace speech and emitted sound, spatial reach and sensing, recording and stored
representation, later access/delivery/perception, possibility versus permission
versus success, and provenance from utterance to later action.

### Case 3 — Organization under heterogeneous influence

Several people and mechanisms produce an external decision after receiving
different technical, political, safety, and incentive signals. The organization
is an analytical boundary, not a mind. Trace heterogeneous delivery and
person-local interpretation, meetings/records/commitments/feedback/gates,
autonomous timing, boundary-scale compression, external inputs/outputs, and
Waltzman- and Levin-informed findings grounded in lower-level evidence.

## Required source questions

For every framework and walkthrough, answer with file, symbol, test, or trace
citations:

1. What owns authoritative state?
2. What is the action type at the agent/environment seam?
3. Where does natural language become a typed or exact operation?
4. Who adjudicates attempts and enforces invariants?
5. How are observations selected, copied, and delivered?
6. How are time, autonomous wakes, simultaneous activity, and fast processes
   scheduled?
7. What is checkpointed, replayed, or reconstructed?
8. Can evidence distinguish intent, attempt, decision, commit, and observation?
9. How are space, configured pathways, and realized causality represented?
10. What needs custom code, and does it use public seams or replace ownership?
11. Can reviewed scenarios be authored without generated executable code?
12. What maintenance and upgrade coupling results?

## Capability classification and decision criteria

Classify each material requirement as `native`, `ordinary_configuration`,
`custom_component`, `engine_replacement`, `architectural_conflict`, or
`not_yet_known`. “Possible” is not a classification. Custom components are
acceptable; accumulating engine replacements count against a foundation.

Use an evidence-linked comparison table, not a manufactured scalar score:

- invariant preservation and single-state authority;
- reusable machinery and stability of its seams;
- cognition/environment translation complexity;
- authoring and composition burden;
- multirate scheduling and concurrency;
- evidence, replay, and analytical step-down;
- spatial and information modeling;
- Waltzman–Levin analysis fit;
- migration cost from the current product;
- maintenance and upstream upgrade friction;
- product differentiation versus reimplementation; and
- ability to add a materially different scenario without another bespoke
  vertical.

Defaults matter only when they cause recurring translation, split authority,
weakened guarantees, or maintenance burden. Do not conclude from labels such as
“typed,” “game master,” or “more flexible.”

## Ordered work

### 26A — Freeze the comparison contract

Confirm repository revisions and worktree state; inventory current Cybernetic
Influence capabilities and bespoke seams; freeze the invariants, cases,
taxonomy, and criteria; create a matrix with an evidence cell for every claim.

**Pass:** theoretical expressiveness alone earns no credit, and all candidates
face identical cases.

### 26B — Source audit

Trace Concordia's public interfaces and an exact-state component end to end;
trace the corresponding Cybernetic Influence authoring-to-replay path; identify
exactly what `data_contracts.composition` supplies and omits; inspect Generative
Agents and AgentVille only for relevant separable machinery.

**Pass:** every material claim cites immutable source or executable evidence;
README-only claims are labeled.

### 26C — Same-case walkthroughs

Write the complete state and call path for all three cases under A–D. Identify
duplicate state, translation boundaries, custom components, engine replacement,
and missing evidence. Existing Cybernetic Influence traces show current
behavior, not architectural superiority.

**Pass:** a reviewer can locate every material fact and causal decision under
each candidate.

### 26C-spike — Conditional disposable proof

Only if one decision-changing seam remains unknowable from source, define one
pass/fail claim and build the smallest disposable probe for one case. Do not add
UI, migrate data, generalize the probe, or merge it into the product.

### 26D — Decision and next frontier

Recommend A, B, C, or D and name the strongest rejected alternative. Assign
ownership of cognition, state, scheduling, interpretation, adjudication,
evidence, authoring, and analysis. Record keep/adapt/migrate/retire dispositions
for current code and retained runs. Decide whether `data_contracts.composition`
belongs. Create or amend an ADR, update the roadmap, and issue the next bounded
implementation handoff.

## Acceptance

| ID | Criterion | Minimum evidence |
|---|---|---|
| R1 | Capability equivalence is the premise, not erased by defaults | Comparison contract and reviewed matrix |
| R2 | All four candidates face identical invariants and cases | Complete matrix |
| R3 | Framework claims cite immutable source, tests, or observed execution | Citation audit |
| R4 | Every requirement uses the fixed capability taxonomy | Matrix review |
| R5 | The decision names authoritative state and control boundaries | ADR |
| R6 | The strongest rejected alternative is represented fairly | ADR |
| R7 | Existing work receives keep/adapt/migrate/retire disposition | Migration table |
| R8 | One smaller-than-rewrite implementation slice follows | Roadmap and validated handoff |

## Stop conditions

Stop rather than inventing a workaround if a required source cannot be pinned,
the comparison needs undocumented private behavior, state ownership remains
ambiguous, generated mechanism code becomes necessary, only production
integration could test a seam, or candidates optimize materially different
product goals. The last case requires a product-owner decision.

## Non-goals

- implementing or migrating to Concordia;
- adding components or scenarios;
- completing the separate MVP stakeholder judgment;
- running provider-backed simulations or model comparisons;
- proving predictive validity; or
- choosing based on novelty, familiarity, or code volume.

## Resume context

Begin from canonical `main` revision
`e7faf25e21abb8950a18955600bbbf7a36b76104`. Read `docs/GOAL.md`,
`docs/ROADMAP.md`, this plan, Slice 25, ADRs 006/008/010/011/012, and relevant
research notes. Work read-only across external repositories and mutate only a
claimed linked worktree. Do not resume product implementation until 26D yields
an adopted decision and a new implementation handoff.
