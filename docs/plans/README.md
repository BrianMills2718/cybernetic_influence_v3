---
doc_role: navigation
authority: navigation
status: active
updated: 2026-08-16
---

# Implementation Plans

[The roadmap](../ROADMAP.md) is the canonical authority for project direction;
[the goal](../GOAL.md) defines the accepted MVP outcome.

## Active execution

[Slice 32: The authoring route stays certified without a human](032-authoring-route-stays-certified.md)
closes the gap that has repeatedly taken the public Create surface dark.
Producing a route certification was automated; installing one was not, so the
ids had to be pasted into the service plist by hand and the service restarted by
hand. Nothing reported a problem until the button was already disabled. The
refresh now certifies when the margin is short, installs it, restarts, and
re-checks that the margin grew — preferring the free subscription route, and
falling back to the metered one only inside two days rather than going dark. It
shares the deploy path's in-flight-work gate rather than keeping a second copy.

[Slice 31: Make the flagship the run that exercises the paper's framework](031-cso-stabilization-flagship.md)
points the public case study at `run_5010214f2466`, the adaptive-CSO
stabilization run, instead of the four-way resource fork. Two reviews in fresh
contexts converged that the fork was the weakest of three available results: it
varies a package delivered identically to all 26 officials, which is the
broadcast logic the source paper defines adaptive interaction against, and its
four arms end identically. The stabilization run instead moves 26 support → 20
conditional → 26 support with no false claim in it, and carries a
detect/diagnose/stabilize chain that implements the paper's section 6 by name.
Public projection only: no runtime, scenario, prompt or execution change, and
no new model calls.

[Slice 30: Unify the two frontends, add Experimentation, add a real Levin lens](030-unified-frontend-experimentation-and-levin-analysis.md)
audited `web/` (the older, general surface) against `public/waltzman/` (the
actively-developed one) and found two real, specifiable gaps — RunSpec-level
experimentation and a genuine post-hoc Levin analysis profile — plus two
explicitly blocked items (graph-projection/boundary-collapse pending a
product decision; pause/resume pending an execution-loop exploration pass).
Designs A and B are implemented, tested, and deployed; C is not silently
dropped, just not yet unblocked.

[Slice 29: Separate scenario, run, analysis, and experiment authority](029-separate-simulation-run-analysis.md)
has completed its selected public V2 vertical and authentic isolation proof.
Its active follow-up records the still-partial V1 retirement and the audited
boundaries between structural compiler validity, causal-closure verification,
progressive editing, and substantive post-run analysis.

[Slice 28: Natural-language general simulation demo](028-natural-language-general-simulation-demo.md)
is the implemented general-authoring foundation. Its monolithic
`GeneralSimulationProposalV1` contract is superseded in part by Slice 29; its
Concordia world, trusted compiler, evidence, generic graph, and replay seams
remain the implementation baseline to extend rather than replace.

[Slice 24: Configurable theory-informed simulation MVP](024-configurable-theory-analysis-mvp.md)
remains the MVP authority. Packets 24A0–24D are technically complete. Its only
active boundary is the M7 stakeholder readout of the retained canonical run;
do not launch another provider run to satisfy it.

[Slice 22: Composite-agency perturbation assay](022-composite-agency-perturbation-assay.md)
has three technically completed provider-free packets: 22A0 implements strict
contracts, 22A1 compiles and retains five zero-call scripted rows, and 22A2
groups them into one analyst comparison with exact run and boundary step-down.
Its stakeholder readout is pending. Packet 22B live repetitions remain a
separate, unauthorized continuation.

## Historical foundations

Completed and superseded execution plans are preserved in the
[plan archive](../archive/plans/README.md). They document reusable foundations
such as typed authoring, person review, live authored people, multi-episode
coordination, and subscription-backed providers, but they are not independent
instructions. The archive index records their source revision, content hash,
and current disposition.
