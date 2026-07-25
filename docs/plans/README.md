---
doc_role: navigation
authority: navigation
status: active
updated: 2026-07-24
---

# Implementation Plans

[The roadmap](../ROADMAP.md) is the canonical authority for project direction
and current truth. This directory preserves one bounded design and its evidence
per completed slice; completed plans are historical evidence, not independent
instructions to continue their former “next slice” sections.

## Active packet

[Slice 14: Pausable live runs](014-pausable-live-runs.md) is the sole active
packet. Its runtime implementation is deployed, and a real DeepSeek run has
completed from a retained live checkpoint. The remaining work is the integrated
demo completion gate: obtain the operator's short usability judgment. The
resumed trace has passed duplicate/cost/narrative-continuity inspection, and the
operator-requested unique causal timestamp correction is deployed and has
passed its API, legacy-readback, rendered desktop, console/network, and backend
log checks.

[Slice 13: Configurable, explainable runs](013-configurable-explainable-runs.md)
is implemented and retained as completed design evidence. Its remaining
desktop acceptance is consolidated into Slice 14's integrated demo gate rather
than advertised as a second active packet. Conversational scenario authoring is
post-demo roadmap direction and has no active implementation plan.

## Completed evidence

| Slice | Outcome |
|---|---|
| [001](001-first-vertical-slice.md) | Clean V3 service-desk vertical |
| [002](002-durable-temporal-inspection.md) | Durable temporal inspection |
| [003](003-private-mac-host.md) | Private Mac development host |
| [004](004-evidence-boundary-repair.md) | Visibility-safe analyst evidence |
| [005](005-physical-access-generalization.md) | Physical-access ontology probe |
| [006](006-reversible-multiscale-graph.md) | Reversible analytical boundaries |
| [007](007-spatial-multiscale-canvas.md) | React Flow multiscale canvas |
| [008](008-topological-world-substrate.md) | Spatial topology substrate |
| [009](009-event-driven-causal-moments.md) | Observation-driven causal moments |
| [010](010-autonomous-multirate-substrate.md) | Autonomous multirate process time |
| [011](011-purchase-payment-representation-boundary.md) | Coarse processor and representation depth |
| [012](012-event-driven-purchase-payment.md) | Event-driven purchase-to-payment causal chain |
| [013](013-configurable-explainable-runs.md) | Configurable model, reasoning, spend, and fidelity explanation |

No completed plan is archived or deleted: each contains unique acceptance
evidence and design lineage, while this index and explicit completion statuses
remove current-authority ambiguity.
