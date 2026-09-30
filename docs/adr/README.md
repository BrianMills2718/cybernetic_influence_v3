---
doc_role: navigation
authority: navigation
status: active
updated: 2026-08-14
---

# Architectural Decisions

These ADRs are the binding decision record. The
[roadmap](../ROADMAP.md) owns current project direction, while implementation
plans provide scoped execution and historical evidence.

| ADR | Decision | Status |
|---|---|---|
| [001](001-clean-v3-repository.md) | Clean V3 repository | accepted |
| [002](002-durable-local-runs.md) | Durable local runs before hosting | accepted |
| [003](003-private-mac-development-host.md) | Private Mac development host | accepted |
| [004](004-analyst-evidence-boundary.md) | Visibility-safe temporal analyst projection | accepted |
| [005](005-local-representation-reads.md) | Mechanisms read only declared representations | accepted |
| [006](006-boundaries-are-derived-coarse-grainings.md) | Analytical boundaries are derived and execution-inert | accepted |
| [007](007-borrow-react-flow-for-multiscale-canvas.md) | React Flow multiscale canvas | accepted |
| [008](008-separate-spatial-topology-from-routing-and-permission.md) | Spatial topology is separate from routing and permission | accepted |
| [009](009-causal-moments-not-round-robin-turns.md) | Causal moments replace round-robin turns | superseded in part by ADR 010 |
| [010](010-autonomous-multirate-process-time.md) | Autonomous multirate process time | accepted; implemented in Service Desk and purchase-to-payment |
| [011](011-declared-representation-depth.md) | Declared subsystem representation depth | accepted direction; general framework deferred |
| [012](012-decision-environment-measures-are-derived.md) | Trust, risk, coordination, and directional patterns are derived evidence-bound analyst views | accepted |
| [013](013-generalized-simulator-foundation.md) | Concordia owns the generalized simulation foundation; selected Cybernetic Influence capabilities migrate through public component and projection seams | accepted |
| [014](014-separate-simulation-and-analysis-authority.md) | Scenario and run contracts own causal execution; analysis remains a separately attachable read-only authority over retained evidence | accepted |
| [015](015-cloudflare-public-hosting.md) | Cloudflare owns the public request path; retained review ships first and stateful execution requires durable storage | accepted; amended by ADR 016 |
| [016](016-vps-live-execution-backend.md) | Live authoring and execution run on the personal VPS behind the Cloudflare tunnel, bounded by sign-in-free spend controls | accepted |
| [017](017-replacement-first-simulation-platform.md) | Off-the-shelf replacement testing precedes further generalized-simulator implementation; Simudyne is the primary replacement trial | accepted |
