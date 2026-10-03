---
doc_role: navigation
authority: navigation
status: active
updated: 2026-09-09
---

# Implementation Plans

[The roadmap](../ROADMAP.md) is the canonical authority for project direction;
[the goal](../GOAL.md) defines the accepted MVP outcome.

## Active execution

[Slice 38: Living replay for generated worlds](038-living-replay-generated-worlds.md)
is implemented as the next presentation layer. It adapts the existing compact retained-run summary into a
World-Substrate-style living replay for generated `general_world_v2` simulations while keeping
the current graph/evidence replay as deeper inspection. No new runner or backend contract.

[Slice 37: Waltzman outreach funnel](037-waltzman-outreach-funnel.md)
is implemented and turns the already-capable public workbench into a stakeholder acquisition path for
Rand Waltzman and adjacent experts: a recognizable coordination question and retained
result in the initial journey, natural-language authoring on that same path,
and one configure-first action before any deep methodology or configuration burden.
It reuses the V2 authoring/run pipeline; World Substrate is a living-presentation donor,
not a new runtime dependency in this slice.

[Slice 36: Open the human project, not a repository maze](036-human-project-picker-pilot.md)
pilots the canonical Cybernetic project composition and its operator-facing VS
Code picker. The project-local manifest identifies V3 as the primary
implementation, `llm_client` as claim-activated support, and V1/V2 as hidden
lineage. Project Meta validates the pointer and repository identities; Ecosystem
Ops projects the composition into one generated workspace and Quick Pick. Its
installed exact-session hook now adds and removes a real claimed `llm_client`
worktree automatically; the remaining acceptance observation is the final
operator-visible Quick Pick selection/open.

[Slice 35: Give the perturbation assay its own timeline](035-restore-the-perturbation-assay-timeline.md)
repairs an experiment that had been inert for three weeks without anything
failing. `54394e0` compressed the coordination world for demo pacing; the assay
reused that scenario but expressed its own timing as absolute day counts, so
every perturbation landed exactly on the deadline, after the last meeting. Four
of its five rows became indistinguishable and its control stopped deciding. The
assay now derives its timing from the scenario's meeting cadence, so re-pacing
the world re-paces the experiment instead of silently emptying it.

[Slice 34: Keep the demo correct without anyone watching it](034-demo-quality-system.md)
installs the review system the demo has been missing. Every defect found on
2026-08-23 got past every check in place, because each check confirmed a
mechanism worked and none confirmed the result was true: a chapter described an
experiment the run was not performing, in well-rendered prose, and nothing
noticed. A claims-versus-evidence check now fails the deploy when the page
states something the retained runs do not support, and a nightly audit runs it
alongside asset resolution, control visibility and certification margin. No
model calls, so the cadence costs nothing to keep.

[Slice 33: Test threshold-managed under-classification](033-evasion-space-case.md)
implements one bounded section-7 pair. The planned no-detection endpoint did not
occur: the shaped arm was classified `degrading` rather than `blocked`, and
`process_delay` rather than `incompatible_requirements`, while still reaching a
lower outright-support floor. The retained result is therefore
under-classification/misdiagnosis, not a detector miss and not proof of equal
pressure dose. The next research question is detector calibration against benign
controls and independently defined coordination impairment; no new live batch is
authorized by this correction.

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
