---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-08-23
updated: 2026-09-07
depends_on:
  - docs/plans/031-cso-stabilization-flagship.md
  - docs/research/001-from-minds-to-coordination.md
plan_id: "cybernetic_influence_v3#33"
dependencies: ["cybernetic_influence_v3#31"]
dependency_evidence:
  "cybernetic_influence_v3#31": "- docs/plans/031-cso-stabilization-flagship.md"
dependencies_reviewed: "2026-09-15"
---

# Slice 33: test threshold-managed under-classification

## Why

The flagship case covers sections 1, 3, 4 and 6 of the source paper: the opening
bio-surveillance scenario, the three state variables, an invariant read through
effects rather than content, and a detect/diagnose/stabilize chain.

Section 7 asks whether pressure can preserve a directional effect while changing
how that effect appears. A synthetic environment adds one thing field data rarely
provides cleanly: the analyst can author the pressure policy and hold the
monitoring system fixed. That makes a miss, under-classification, or
misdiagnosis inspectable as a property of this detector configuration rather
than an inferred hidden cause.

## What was implemented

One paired comparison uses the flagship scenario:

- **Arm A — overt expression.** Retained run `run_5010214f2466`. The monitor
  reports readiness `blocked`; the diagnostician reports
  `incompatible_requirements`; the planner proposes `cross_domain_compact`.
- **Arm B — threshold-managed expression.** Retained run `run_76dae6d4a9a7`.
  The same four source roles act on the same coalition while their expression
  policy is constrained to narrow verification requests rather than escalation
  or cross-source reference. The detection cell, its personas, categories, and
  trigger are unchanged.

This is a controlled change in expression policy. It is **not** an independently
calibrated equal-dose pressure manipulation, so the result must not be described
as proving that "the same pressure" was merely hidden.

## Observed result

The original no-detection endpoint did not occur. The threshold-managed arm was
seen by the monitor: readiness was classified `degrading`, the diagnostician
reported `process_delay`, and the same `cross_domain_compact` intervention was
proposed.

The comparative result is under-classification and different mechanism labeling,
not non-detection. On the exact outright-support count, the threshold-managed arm
reached a lower floor at its worst round: 0 support / 26 conditional, versus
6 support / 20 conditional in the overt arm. Yet the monitor assigned the less
severe readiness category (`degrading` rather than `blocked`) and a different
mechanism (`process_delay` rather than `incompatible_requirements`). Both runs
ended approved, but recovery was less complete in the threshold-managed arm:
14 support / 11 conditional / 1 defer versus 26 support.

## Original pass/fail criteria

- **Comparable degradation:** partially supported on the exact stance trajectory;
  the shaped arm reached zero outright support, but no independent coordination
  impairment scale was defined.
- **Arm A blocked while Arm B is not detected:** **failed.** Arm B was detected
  as `degrading`.
- **Detector reading visible in the paired presentation:** satisfied.
- **Authored-evasion and single-pair nonclaims retained:** satisfied.

The failed primary endpoint is retained as a result rather than rewritten into a
success criterion after observation.

## Next calibration question

The next useful assay is not another scenario showcase. It should separate an
independent impairment measure from the monitor's categorical judgment and add
benign controls.

Primary research question:

> Holding world truth, coalition, source objectives, decision rule, and
> monitoring system fixed, can changing only the temporal and presentational
> form of heterogeneous pressure produce equal or greater independently measured
> coordination impairment while the monitor assigns a less severe state?

Calibration question:

> Across benign variation and genuinely impaired synthetic decision
> environments, what sensitivity/false-positive tradeoff results as an explicit
> detection boundary changes?

A bounded design should predeclare exact outcome measures such as approval-margin
trajectory, unconditional-support count, unresolved prerequisite count, modeled
decision latency, and issue reopening; include benign routine-verification and
legitimate-constraint controls; keep the detector read-only; sweep an explicit
trigger or boundary rather than treating one LLM category as a calibrated
threshold; and use checkpoint-paired continuations or repeated runs to expose
sampling variability.

## Not in scope

The other section-7 strategies, real-world prevalence, hostile attribution, a
validated detector, or a claim that a more sensitive threshold is better. A
boundary that catches this authored pattern may also produce more false alarms;
that tradeoff is exactly what the follow-up must measure.

## Cost

This correction uses retained evidence and requires no model calls. Any live
calibration batch remains separately gated and requires explicit authorization.
