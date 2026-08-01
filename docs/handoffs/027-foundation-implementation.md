---
doc_role: implementation_handoff
authority: bounded_design
status: ready_awaiting_execution_authorization
created: 2026-07-31
updated: 2026-07-31
depends_on: docs/adr/013-generalized-simulator-foundation.md
---

# Slice 27 handoff: Concordia-owned physical-access parity proof

## Gate

ADR-013 is adopted. This handoff is structurally ready, but the architecture
approval did not authorize implementation. Begin only after an explicit
instruction to execute Slice 27.

## Outcome

Reproduce the current physical-access capability on pinned Concordia with
Concordia actually owning entity/component state, simulation control, and
checkpoint continuation. Preserve the current analyst-visible distinctions
among credential validity, authorization, latch success, traversal, modeled
time, and explaining evidence. Do not invoke the existing `CausalSession` or
`ActiveRuntimeSession` behind the new path.

This is a direct migration blocker, not proof that the whole product has been
ported or generalized.

## Decision readout

- **Pass:** Concordia can own one exact current capability without a hidden CI
  runtime; return for judgment on the next capability-parity slice.
- **Fail:** if the old runtime, a private Concordia fork, or loss of an
  indispensable distinction is required, stop and reconsider ADR-013's
  Candidate C fallback before broader migration.

## Canonical behavioral example

Use the existing provider-free physical-access arms and current readout as the
parity oracle:

1. a valid credential, authorization, and working latch allow entry;
2. a valid credential without policy authorization denies entry before latch
   release; and
3. a valid authorized credential with a jammed latch denies entry for the
   physical reason.

Also preserve the existing forged-credential negative control, which fails at
authentication before authorization, latch release, or traversal.

The inspectable result must expose the initial condition, the technician's attempted
action, each material adjudication, final room/door/latch state, elapsed modeled
time, and evidence explaining the outcome. The existing API or presentation
readout may be reused; no new UI is required.

## Foundation boundary

| Concern | Slice 27 owner |
|---|---|
| Entity/action lifecycle | Pinned Concordia `Entity` and simulation/game-master path |
| Exact access state | A Concordia game-master/component state object using public state/apply seams |
| Credential, authorization, latch, traversal rules | Deterministic component operations, not an LLM judgment |
| Simulated time | Concordia time/scheduling component used by the selected engine path |
| Checkpoint/restore | Concordia component/checkpoint state with fail-loud JSON serialization |
| Evidence projection | Narrow retained records sufficient to build the current physical-access readout |
| Presentation | Existing physical-access readout/API adapter where compatible |
| Forbidden authority | Existing CI causal/active sessions, generated mechanism code, narrator prose as state truth |

The component may reuse small CI types or pure rule functions after their
ownership is made explicit. It may not wrap the old runtime and call that
Concordia integration.

## Ordered work

### 27A — Freeze parity inputs and outputs

Capture the current three arm configurations and exact public readout fields at
the execution baseline. Map each required field to Concordia entity input,
component state, transition, or evidence. Record which current internal fields
are intentionally not part of parity. Retain the forged-badge authentication
test as a separate negative control rather than inventing a fourth public arm.

**Pass:** the parity fixture is executable without a live model and can detect
a Concordia surface that merely returns a hand-authored answer.

### 27B — Run one successful Concordia-owned path

Create the smallest Concordia simulation configuration with a provider-free
technician entity and one deterministic access component. Execute the successful arm
through Concordia's public entity, game-master, component-state, and engine
seams. Project the result into the existing analyst-visible readout.

**Pass:** entry succeeds for the same reasons and modeled ordering as the
baseline, and an execution probe proves neither old CI session class ran.

### 27C — Preserve the failure distinctions and continuation

Run the policy-denial and jammed-latch arms, plus the forged-credential negative
control, through the same component and configuration seam. Checkpoint after the attempt boundary,
restore into a fresh simulation instance, finish execution, and compare the
terminal readout with uninterrupted execution.

**Pass:** policy and physical failures remain distinguishable; checkpoint
round-trip loses no material component/evidence state; invalid state or
serialization fails visibly.

### 27D — Expose one human-reviewable parity artifact

Present the three results through the existing API/readout surface or a simpler
existing review page. Link the exact baseline and Concordia outputs so a human
can inspect the same starting conditions, outcomes, reasons, and limitations.

**Pass:** the product owner can directly judge whether this current capability
was reproduced. Tests support but do not replace that judgment.

## Acceptance

| ID | Pass condition | Evidence |
|---|---|---|
| P27-1 | All three baseline arms produce the same analyst-visible outcome and reason distinctions | Frozen baseline/Concordia readout comparison |
| P27-2 | Concordia owns the entity, component state, engine/game-master loop, time path, and checkpoint | Exact execution trace and source review |
| P27-3 | `CausalSession` and `ActiveRuntimeSession` do not execute on the new path | Instrumented negative control that fails if either constructor/restore/advance path is called |
| P27-4 | Exact credential, authorization, latch, and traversal rules are deterministic component operations | Positive and failure fixtures plus component-state inspection |
| P27-5 | Checkpoint/restore into a fresh instance preserves the terminal result and evidence; unsupported state fails loudly | Round-trip and non-serializable/corrupt-state negative tests |
| P27-6 | One current API/readout surface exposes the Concordia result with assumptions and non-predictive limitations | Direct human inspection plus focused API/presentation test |
| P27-7 | No live LLM call, new scenario family, generalized authoring rewrite, retained-run migration, or broad UI redesign enters the slice | Diff/dependency review |

## Failure behavior

- Invalid actions, component state, or checkpoint content stop the run and
  retain enough context to diagnose the boundary; no productive fallback
  invents a different action or state transition.
- If Concordia's generic checkpoint would silently drop material state, replace
  serialization at the component boundary or stop. Do not accept lossy parity.
- If parity requires the old CI runtime as an executor, stop and return to the
  ADR-013 fallback decision rather than hiding dual authority.
- If a private or unstable Concordia seam is required, record the exact seam
  and stop for an upgrade/maintenance judgment.

## Non-goals

- porting the other scenarios, conversational authoring, theoretical analysis,
  comparison workflow, or all existing UI surfaces;
- adding provider-backed cognition or judging model quality;
- proving predictive fidelity or cross-domain generality;
- migrating or rewriting historical retained runs;
- optimizing scale, concurrency, security, or deployment; or
- deleting the existing runtime before parity is observed and accepted.

## Verification

Run focused Concordia component/engine/checkpoint tests, the existing physical-
access regression tests, the no-old-runtime negative control, JSON/checkpoint
validation, and direct inspection of the exact parity artifact. Run the broader
suite only at the terminal slice claim or when an affected shared boundary
cannot be isolated.

## Reset boundary

Reassess after the successful arm and again after the two failure arms. Reset
the design if the Concordia path needs a second hidden engine, loses a required
reason distinction, or cannot produce a faithful checkpoint. Do not broaden
into full parity before this result is observed.

## Required authority

- accepted [ADR-013](../adr/013-generalized-simulator-foundation.md);
- [Slice 26 source evidence](../research/026-foundation-comparison.md);
- [Goal](../GOAL.md) and [roadmap](../ROADMAP.md); and
- explicit implementation authorization after this handoff.
