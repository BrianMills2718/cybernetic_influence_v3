# Cybernetic Influence V3

Cybernetic Influence is a traceable multiscale-agency simulator. It represents
people, information carriers, stateful objects, interfaces, connections, and
exact mechanisms separately. An organization is an analytical boundary over
those concrete members, not another mind or world executor.

The current MVP is to configure a bounded coordination scenario and obtain
separate, evidence-bound findings relevant to Waltzman's coordination ideas
and Levin-style composite agency. It is not a prediction engine and it does not
yet make robustness or perturbation comparisons part of a normal run.

## Start here

- [Current goal](docs/GOAL.md) — outcome, scope, and acceptance criteria.
- [Roadmap](docs/ROADMAP.md) — current truth and implementation sequence.
- [Active design: Slice 24](docs/plans/024-configurable-theory-analysis-mvp.md)
  — the only executable continuation plan.
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

- a pre-run spatial topology and configured interaction-pathway map;
- a realized causal graph after retained events exist;
- concise and detailed causal narratives grounded in retained evidence;
- person, process, and execution-inert composite accounts; and
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
