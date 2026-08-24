---
doc_role: implementation_plan
authority: bounded_design
status: proposed
created: 2026-08-23
updated: 2026-08-23
depends_on:
  - docs/plans/031-cso-stabilization-flagship.md
  - docs/research/001-from-minds-to-coordination.md
---

# Slice 33: show detection failing under evasion

## Why

The flagship case covers sections 1, 3, 4 and 6 of the source paper: the opening
bio-surveillance scenario, the three state variables, an invariant read through
effects rather than content, and a detect/diagnose/stabilize chain.

Section 7 has no representation at all. It names six strategies by which
influence keeps its directional pressure while changing how that pressure
*appears*: threshold management, temporal fragmentation, segmented targeting
with incompatible local equilibria, oscillation, variable switching, and
environmental masking. The paper's own summary of them is that effects are made
to seem "too gradual to detect, too fragmented to aggregate, too unstable to
interpret, too distributed to isolate, too contextual to question."

This is the part of the framework a simulator is uniquely able to demonstrate.
Evasion is unobservable in the field by construction — it is built to resemble
normal variation — so a claim that a detector missed it is unfalsifiable outside
a synthetic environment where the ground truth is authored. Here the pressure is
a scenario control, so whether the detector caught it is a fact about the
detector, not an interpretation.

## What it does

One paired comparison, from the flagship's own scenario so nothing else varies:

- **Arm A — overt.** The existing `adaptive_cso_stabilization` run. The monitor
  reports readiness blocked; the chain fires; the coalition recovers.
- **Arm B — threshold-managed.** The same four sources apply the same
  directional pressure, spread over more rounds at lower per-round amplitude,
  staying inside the monitor's variation bound. Same end state in the state
  variables, no detection.

The finding is not "the coalition broke". It is that two runs reach comparable
degradation and only one is seen, with the difference being the shape of the
pressure over time rather than its content or its size.

Start with threshold management alone. It is the cleanest to author, the easiest
to read on the existing round trajectory, and it needs no new detector.

## Pass/fail

- Both arms reach a comparable coordination-readiness floor by their final round.
- Arm A's monitor reports blocked; Arm B's does not, at the same detector
  configuration and threshold.
- The two arms are presented against each other, with the detector's own reading
  shown for both, so the miss is visible rather than asserted.
- Nonclaims state that the evasion is authored, not discovered, and that a
  detector missing an authored pattern is evidence about that detector at that
  threshold and nothing more.

## Not in scope

The other five evasion strategies, a redesigned detector, and any claim that the
detector is deficient. Whether a threshold that catches Arm B would produce
false positives elsewhere is a real question and is not answered by one pair.

## Cost

Live model spend for one additional multi-round coalition run at 26 agents; the
flagship cost 89 model calls on the subscription route. Requires explicit
authorization before execution.
