# Cybernetic Influence V3

Cybernetic Influence is becoming a generalizable, reviewable simulator for
bounded socio-technical worlds. Concordia is the adopted simulation foundation;
the current Cybernetic Influence application is the capability-parity baseline
and a source of selected exact mechanisms, evidence projections, authoring,
analysis, and presentation features.

Wargaming, economic modeling, and organizational analysis are exemplar uses,
not separate product definitions. The system explores conditional pathways and
sensitivities under declared assumptions; it is not a prediction engine.

## Start here

- [Current goal](docs/GOAL.md) — outcome, scope, and acceptance criteria.
- [Roadmap](docs/ROADMAP.md) — current truth and implementation sequence.
- [Foundation decision: ADR-013](docs/adr/013-generalized-simulator-foundation.md)
  — accepted Concordia-first authority boundary.
- [Next bounded design: Slice 27](docs/handoffs/027-foundation-implementation.md)
  — Concordia-owned physical-access parity proof, awaiting explicit
  implementation authorization.
- [Retained MVP design: Slice 24](docs/plans/024-configurable-theory-analysis-mvp.md)
  — completed technical baseline with a separate stakeholder readout pending.
- [Post-MVP perturbation design: Slice 22](docs/plans/022-composite-agency-perturbation-assay.md)
  — completed scripted assay foundation and separately gated next packets.
- [Architectural decisions](docs/adr/README.md) — binding ontology and runtime
  constraints.
- [Research basis](docs/research/001-from-minds-to-coordination.md) — what the
  Waltzman source does and does not support.
- [Historical archive](docs/archive/README.md) — completed plans and dated host
  evidence, preserved for recovery rather than normal execution.

## Run locally

```bash
make install
make check
make serve
```

Open <http://127.0.0.1:8620>.

Scripted reference runs are zero-cost. Live LLM execution requires the shared
`llm_client` integration and explicit live authorization; model availability,
reasoning options, and observed spend are shown by the running application.
Do not infer current route availability from historical documentation.

## What the application shows

The current application is the pre-migration parity baseline. It shows:

- a pre-run spatial topology and configured interaction-pathway map;
- a realized causal graph after retained events exist;
- concise and detailed causal narratives grounded in retained evidence;
- person, process, and execution-inert composite accounts;
- a retained five-condition composite-capability comparison with exact row,
  boundary, graph, narrative, measurement, and event step-down; and
- scenario assumptions, exact mechanisms, and analyst-safe trace step-down.

For a private Mac development host, use the concise
[host runbook](docs/operations/mac-mini.md). It links dated deployment and
capacity records only when they are needed for diagnosis.

## Lineage

- `cybernetic_influence`: original research implementation.
- `cybernetic_influence_v2`: governed architecture and evidence work.
- this repository: clean product/runtime line with no V2 imports.

The earlier repositories and archived V3 slices are historical sources, not
runtime dependencies or current instructions.
