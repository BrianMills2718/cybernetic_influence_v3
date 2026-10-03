# Decisions and rejected alternatives

Only decisions the repo records. ADRs: `docs/adr/` (index `docs/adr/README.md`).
Rejected alternatives are the point of this page.

- **Replacement testing comes before more simulator building** (`approved`,
  ADR-017, 2026-09-30): trial Simudyne Nexus + Python SDK first; if it fails,
  Concordia; GAMA if LLM residents are not needed; AnyLogic for conventional
  commercial multi-method work. Rejected as reasons to keep local
  infrastructure: novelty, sunk cost, style, "tighter control in the abstract",
  features ordinary model code can reproduce, and compatibility no live user
  needs. Emulating Nexus locally and calling it the trial is ruled out (plan 039).
- **Concordia owns the simulation lifecycle** (`approved`, ADR-013; now the
  fallback under ADR-017). Rejected: C, a Cybernetic Influence foundation with
  compatibility adapters (the Slice 26 recommendation), because it leaves
  Concordia an optional edge around a bespoke runtime; it stays the fallback if
  a Concordia parity proof fails. B, Concordia cognition around a CI
  environment, because it carries two lifecycle/state models forever. D, an
  independent CI product, for the least ecosystem leverage.
- **Simulation and analysis are separate authorities** (`approved`, ADR-014):
  analysis reads retained evidence only and must never change simulation
  state, model-call count or evidence digest.
- **Boundaries, spatial adjacency and trust/risk measures are derived views**
  (`approved`, ADR-006, ADR-008, ADR-012): never hidden executors, channels or
  causal state.
- **Cloudflare is the public host** (`approved`, ADR-015, 2026-09-13), with no
  origin or SPA fallback, so missing `api/*` routes fail visibly. Rejected:
  moving the SQLite/file run store into a Cloudflare Container, whose disk is
  ephemeral.
- **Live runs on the personal VPS** (`approved`, ADR-016, 2026-09-15), amending
  ADR-015. Rejected: a Cloudflare durable-storage adapter, which "would be a
  rewrite of the storage layer, not a deployment".
- **React Flow for the multiscale canvas** (`approved`, ADR-007). Rejected:
  extending the hand-rolled SVG grid, and restoring the whole V2 workbench.
  Inferring composite agents is deferred.
- **Clean V3 line, no V2 imports** (`approved`, ADR-001, `AGENTS.md`).
- **`make check` gates every merge** (`approved`, PR #15, `AGENTS.md`
  "Testing"): added because three merges between 2026-08-26 and 2026-09-06
  shipped a red assertion unnoticed. Polling waits use wall-clock time,
  enforced by `make test-wait-check`, after prose alone did not hold (PR #22).
- **`AGENTS.md` is the only instruction file** (`approved`, PR #37,
  2026-09-23): `CLAUDE.md` removed. PR #37 records the change, not why.
