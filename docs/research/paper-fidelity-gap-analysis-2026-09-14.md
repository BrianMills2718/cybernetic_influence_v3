---
doc_role: source_evidence
authority: evidence
status: active
created: 2026-09-14
---

# Paper fidelity gap analysis: *From Minds to Coordination* vs. current implementation

Brian's direction, 2026-09-14: the Waltzman demo should match the paper as
closely as possible, or go beyond it. This note is a dispositioned checklist
so that direction survives past this conversation — not a restatement of
[`001-from-minds-to-coordination.md`](001-from-minds-to-coordination.md),
which paraphrases the paper itself. Read that note (or the source PDF at
`~/code/_docs/From Minds to Coordination Paper.pdf`) first for the framework;
this note only tracks fidelity, gaps, and next actions.

## What already matches well

- **Three state variables** (trust structure, perceived risk, coordination
  readiness) — implemented as the Waltzman analysis module (`MVP-C4`,
  satisfied) and measured with the paper's own named indicators.
- **Heterogeneous, adaptive, individualized pressure** (paper §5) — the
  `ExperimentSpec` vertical (Slice 27) explicitly builds "heterogeneous
  influence sources that can adapt to local reactions while retaining a shared
  objective," matching §5.1–5.3 directly.
- **Condition-blind matched trajectories** — a 2026-08-05 audit found the
  original twelve-agent outbreak probe disclosed its condition identifier to
  participants before round one, invalidating matched-condition inference.
  This was already corrected: `run_8924342b56ce` / `run_946a10a820fc` /
  `run_05acbaea1137` are the clean replacement, reproducing baseline
  approval / pressure non-approval / restored approval without that leak.
  **Use these three runs, not the disclosed-condition ones, in any demo
  content going forward.**
- **The 26-agent cross-border compact fork** (`outbreak_resource_forks_20260810214211`)
  is, on inspection, the single most paper-faithful piece of evidence in the
  repo, and it is *not yet surfaced as the headline result* anywhere I found.
  It shows that supplying resources alone does **not** restore joint approval
  (all four resource-package variants ended `no_joint_response`), and that
  the real driver is a shift in named concerns — from capacity (24/26) to a
  mixed evidence-quality / sovereignty / legitimacy profile once resources
  arrive. Sovereignty and legitimacy concerns are trust-structure phenomena
  in the paper's own terms (§3.1), not perceived-risk or resource phenomena.
  **This is a stronger demonstration of the paper's actual thesis** — that
  influence operates on decision-environment conditions, not on resolvable
  material objections — than the simpler twelve-agent probe, and should be
  the one led with if going for maximum fidelity.

## Real gaps

1. **The stabilization intervention doesn't match the paper's own three
   measures.** §6.3 names exactly three: clarify authoritative sources/
   decision processes, bound perceived risk by defining thresholds, reinforce
   coordination readiness via timelines/commitments. The twelve-agent probe's
   intervention is "supply a verified resource allocation package" — not one
   of these three. *(Partially mitigated by the 26-agent finding above, which
   shows resources alone don't work — but no run yet demonstrates one of the
   paper's actual three stabilization measures succeeding or failing.)*
   **Action:** run one condition using an authority-clarification or
   commitment-reinforcement intervention (matching §6.3 literally) and
   compare against the resource-only result.

2. **The evasion space (paper §7 — time, structure, signal, distribution,
   context) is explicitly deferred**, per `REGIONAL_OUTBREAK_COORDINATION_PROBE.md`:
   "These are later challenge conditions. They should not be implemented
   before a basic baseline/pressure/stabilization assay produces an
   inspectable trajectory." That baseline assay now exists (see above) — the
   deferral's own precondition is met. **This is the clearest "go beyond the
   paper" opportunity**: the paper itself frames evasion as an open,
   unresolved analytic frontier ("no validated detector, intervention policy,
   or measurement formula" — see `001-from-minds-to-coordination.md`, "What
   the paper does not establish"). A working demonstration of even one
   evasion dimension (segmented targeting/incompatible local equilibria is
   the most demo-legible) would be a genuine contribution, not just a
   faithful reproduction.

3. **CSO's Detect/Diagnose functions are implicit, not modeled as separate
   steps.** The current pipeline measures state variables per-run and reports
   them; it doesn't yet show a detection threshold being crossed or a
   diagnosis step ("which dimension is shifting, is it local or propagating")
   as a distinct, inspectable stage. Lower priority than #1 and #2, but worth
   naming since CSO's three-function cycle (§6) is as central to the paper as
   the three state variables themselves.

4. **No run yet demonstrates the paper's own invariant definition precisely**
   — "diverse interactions produc[ing] the same directional shift" (§4) —
   because the existing multi-condition work varies *pressure* across
   conditions, not the *diversity of inputs within one condition*. A cleaner
   invariant demonstration would hold the outcome direction fixed while
   varying message content/source/tone within a single pressure condition,
   showing convergent effect despite divergent expression. This is closer to
   the paper's central claim ("the signal is not in what is said, but in what
   consistently changes") than anything currently built.

## Recommended order

Given a bounded amount of time before a demo needs to be shown: (2) is the
highest-leverage "go beyond the paper" move and reuses existing
infrastructure; (1) is the cheapest fidelity fix; (4) is the most
conceptually important but requires new scenario design; (3) is real but
lower priority. Lead the demo narrative with the 26-agent compact-fork result
regardless of what else lands — it is already the strongest evidence in the
repo and is currently under-surfaced.

## What this note does not establish

This is a documentation/evidence note, not an implementation plan. It does
not itself change `docs/ROADMAP.md`'s capability map, and none of the actions
above are yet backed by a governing plan or bounded handoff per this
repository's `CLAUDE.md`. Whoever picks this up should open one before
touching runtime/scenario/analysis code.
