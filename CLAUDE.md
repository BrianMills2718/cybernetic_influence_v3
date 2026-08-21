# Cybernetic Influence V3 Repository Rules

`AGENTS.md` is a generated Codex-oriented projection of this file plus
`scripts/relationships.yaml`, rendered by `scripts/meta/render_agents_md.py`.
Edit this file, not `AGENTS.md` directly; `scripts/meta/check_agents_sync.py
--check` verifies they are in sync.

## Product Framing

This is a general reviewable simulation system: an analyst describes a bounded
socio-technical world conversationally, reviews and edits the compiled
configuration, runs interacting LLM and deterministic entities through a
Concordia-owned simulation lifecycle, and inspects the trajectory, state,
assumptions, provenance, and selected analyses. Wargaming, economic modeling,
and organizational analysis are exemplar uses, not the product definition. The
system explores conditional pathways and sensitivities under declared
assumptions; it is not a prediction engine.

The current application (public Waltzman workbench included) is the
pre-migration capability-parity baseline, not yet migrated to the general
Concordia foundation. Do not mistake it for the general product architecture.

## Accepted Working Model

- ADR-013 is the accepted foundation: Concordia owns entity/component
  lifecycle, actor selection, environment/game-master loop, scheduling, and
  checkpoint invocation. A project-owned canonical-world component owns typed
  world truth, transitions, and atomic commit; it must not recreate
  `CausalSession`/`ActiveRuntimeSession` as a second engine.
- ADR-014 is accepted: scenario/run execution and analysis are separately
  owned authorities. Analysis is read-only over retained evidence and must
  never mutate simulation state or affect model-call count or evidence digest.
- ADR-006/ADR-008: analytical/organizational boundaries and spatial adjacency
  are derived and execution-inert, never a hidden executor or an implicit
  communication/authorization channel.
- ADR-010/ADR-011: multirate process time and declared representation depth
  are accepted directions; a general framework for representation depth
  remains deferred outside the migrated verticals.
- ADR-012: trust, risk, coordination, and directional measures are derived,
  evidence-bound analyst views, never hidden causal state.
- V2 (`cybernetic_influence_v2`) remains authoritative for any unmigrated
  production path referenced from there. This repository is the clean
  product/runtime line with no V2 imports.

Detailed current capability and status belong in `docs/ROADMAP.md` and
`docs/GOAL.md`, not this rule file.

## Documentation Authority

- `README.md`: orientation, start-here links, run-locally instructions.
- `docs/GOAL.md`: accepted outcome, scope, and acceptance criteria
  (`doc_role: execution_goal`, `authority: continuous_execution`).
- `docs/ROADMAP.md`: current truth and implementation sequence
  (`authority: canonical`) — the capability map and what is satisfied vs.
  pending.
- `docs/adr/README.md` and `docs/adr/*`: binding architectural decisions.
- `docs/plans/README.md` and `docs/plans/*`: active and historical
  implementation plans; runtime/application behavior changes need an active
  plan or bounded handoff.
- `docs/handoffs/*`: bounded-design implementation handoffs
  (`authority: bounded_design`). A handoff's own `status` frontmatter is
  authoritative for whether it is still gating; if it conflicts with
  `docs/ROADMAP.md`'s Artifact Dispositions table, treat the roadmap as
  current truth and fix the handoff's frontmatter rather than trusting either
  silently.
- `docs/research/*`: research basis for what a source does and does not
  support.
- `docs/operations/*`: host/runbook operational detail (e.g. the Mac Mini
  runbook), linked from `README.md` rather than duplicated.
- `docs/archive/README.md` and `docs/archive/*`: completed, superseded, or
  dated evidence preserved for provenance and recovery, not the current
  execution path.

Do not rewrite historical evidence, move established evidence paths, or treat
a completed plan or archived handoff as next-step authority.

## Required Before Implementation

Before runtime, API, UI, scenario, prompt, or evidence behavior changes:

1. identify the governing plan (`docs/plans/`) or bounded handoff
   (`docs/handoffs/`) that authorizes the change; if none exists, that gap is
   the first blocker to resolve, not a reason to proceed informally;
2. add or amend an ADR (`docs/adr/`) if the change affects architecture,
   authority boundaries, or the Concordia/canonical-world seam;
3. keep `docs/ROADMAP.md`'s capability map and Artifact Dispositions table
   truthful as work lands — a slice is not "done" until the roadmap says so.

Documentation-only changes still require identifying which authority surface
they update. Generated artifacts and formatting-only rewrites do not create a
new capability by themselves.

## Testing And Verification

- `make check` runs `typecheck test ui-build deploy-check` in that order —
  `mypy` (strict, `files = ["src", "tests"]`), then `pytest -q tests`, then the
  frontend build, then the deploy-script syntax check. Run it before treating
  work as complete; do not report success from a partial subset.
- `make test` runs `pytest -q tests` specifically — always scope pytest to
  `tests/` (or use `make test`). Do not run a bare `pytest` from the repo
  root: `worktrees/` can contain other lanes' checkouts with duplicate test
  basenames and no path isolation, which produces spurious collection errors
  unrelated to this repository's own test suite.
- Live LLM execution requires the shared `llm_client` integration and
  explicit live authorization; model availability, reasoning options, and
  observed spend are shown by the running application. Do not infer current
  route availability from historical documentation.
- Never turn a failed, partial, or stale check into a passing claim in a plan,
  handoff, or roadmap update.

## Worktree And Lane Hygiene

This repository uses the standard worktree-per-lane pattern:
`worktrees/<branch>/`, one bounded mission and plan/handoff per worktree.

- Create lanes with the sanctioned `make worktree` entrypoint once installed;
  do not improvise `git worktree add` against ad hoc paths.
- A finished lane needs one disposition (`merged`, `active`, `handoff`,
  `superseded`, `abandoned`, `archived`, `migrated`) and must be closed with
  the atomic `session-close` / `make worktree-remove` flow — claim release and
  worktree/branch cleanup happen together, never as two separate manual steps.
- Worktree lifetime and branch lifetime are separate: a worktree can be
  removed while its branch is preserved when a lane's disposition is
  uncertain, but a stale, no-longer-truthful `active` claim should still be
  resolved (resume, hand off, or abandon) rather than left indefinitely — see
  `enforced-planning`'s `docs/guides/WORKTREE_COORDINATION_OPERATOR_GUIDE.md`
  for the full lifecycle and stale-claim diagnostics.
- Before trusting `worktrees/` as healthy, check `git worktree list` against
  the claim registry (`~/.claude/coordination/claims/*.yaml` filtered to this
  project) rather than assuming every checkout on disk has a live owner.

## Commands

```bash
# Setup
make install
make serve

# Verification
make check        # typecheck (mypy --strict) + test (pytest -q tests) + ui-build + deploy-check
make test          # pytest -q tests
make typecheck     # mypy --strict
make ui-smoke       # scripts/verify_demo_ui.py against a running server
make ui-visibility  # every primary control is inside the viewport, at ten widths

# Worktree and session lifecycle (governed-repo tooling)
make worktree BRANCH=... TASK="..." SESSION_GOAL="..." SESSION_PHASE="..." [PLAN=N]
make worktree-list
make worktree-remove BRANCH=...
make session-status
make session-close BRANCH=...
make status         # repository authority freshness and branch status
```

## Repository Hygiene

- Preserve unrelated user changes and generated job artifacts.
- Keep secrets, prompts, private memory, and protected content out of public
  projections (`public/waltzman/`); retain typed redacted lineage where
  required.
## Principles

- Concordia owns entity/component lifecycle and the game-master loop; this
  repository owns typed world truth, transitions, and evidence. Do not
  recreate a second simulation engine to work around that boundary.
- Scenario/run execution and analysis are separately owned authorities
  (ADR-014). A change that lets analysis mutate simulation state or affect
  model-call count/evidence digest is a regression, not a convenience.
- A slice is "done" when `docs/ROADMAP.md`'s capability map and Artifact
  Dispositions table say so, not when code exists. Code presence is not
  promotion.
- Every worktree lane gets an explicit disposition and atomic closeout
  (claim + worktree + branch together); do not leave a lane's physical
  cleanup as a manual follow-up step.
- Prefer the documentation authority surface that already owns a fact over
  creating a second place to state it.

## Workflow

1. Find the governing authority: `docs/ROADMAP.md` for current direction,
   `docs/GOAL.md` for the accepted outcome, `docs/plans/README.md` for the
   active plan, `docs/adr/README.md` for binding decisions.
2. Create a claimed worktree for bounded work: `make worktree BRANCH=...
   TASK="..." SESSION_GOAL="..." SESSION_PHASE="..." [PLAN=N]`.
3. Implement against the active plan or bounded handoff; keep
   `docs/ROADMAP.md` truthful as work lands.
4. Run `make check` before treating work as complete.
5. Merge/push from a clean root-anchored control session, then close the lane
   with `make worktree-remove BRANCH=...` (or `make session-close`) — never as
   a separate manual worktree deletion after the claim is already released.

## References

- `README.md` — orientation and run-locally instructions.
- `docs/GOAL.md` — accepted outcome and acceptance criteria.
- `docs/ROADMAP.md` — current truth and capability map.
- `docs/adr/README.md` — binding architectural decisions.
- `docs/plans/README.md` — active and historical implementation plans.
- `docs/handoffs/` — bounded-design implementation handoffs.
- `docs/archive/README.md` — historical evidence, not current direction.
- `enforced-planning`'s
  `docs/guides/WORKTREE_COORDINATION_OPERATOR_GUIDE.md` — worktree, claim,
  and lane lifecycle definitions used by the `make worktree*`/`session-*`
  commands above.
