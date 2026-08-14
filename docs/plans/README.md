---
doc_role: navigation
authority: navigation
status: active
updated: 2026-08-14
---

# Implementation Plans

[The roadmap](../ROADMAP.md) is the canonical authority for project direction;
[the goal](../GOAL.md) defines the accepted MVP outcome.

## Active execution

[Slice 29: Separate scenario, run, analysis, and experiment authority](029-separate-simulation-run-analysis.md)
is the approved current-to-target refactor. It preserves one conversational
authoring experience while preventing analyst purpose from entering actor or
transition-authority contexts, makes run evidence theory-neutral, and permits
post-run analysis attachment without simulation effects.

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
