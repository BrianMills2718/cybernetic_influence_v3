# Cybernetic Influence V3 Repository Rules

<!-- GENERATED FILE: DO NOT EDIT DIRECTLY -->
<!-- generated_by: scripts/meta/render_agents_md.py -->
<!-- canonical_claude: CLAUDE.md -->
<!-- canonical_relationships: scripts/relationships.yaml -->
<!-- canonical_relationships_sha256: 926e29ad529a -->
<!-- sync_check: python scripts/meta/check_agents_sync.py --check -->

This file is a generated Codex-oriented projection of repo governance.
Edit the canonical sources instead of editing this file directly.

Canonical governance sources:
- `CLAUDE.md` — human-readable project rules, workflow, and references
- `scripts/relationships.yaml` — machine-readable ADR, coupling, and required-reading graph

## Purpose

`AGENTS.md` is a generated Codex-oriented projection of this file plus
`scripts/relationships.yaml`, rendered by `scripts/meta/render_agents_md.py`.
Edit this file, not `AGENTS.md` directly; `scripts/meta/check_agents_sync.py
--check` verifies they are in sync.

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

## Operating Rules

This projection keeps the highest-signal rules in always-on Codex context.
For full project structure, detailed terminology, and any rule omitted here,
read `CLAUDE.md` directly.

### Principles

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

### Workflow

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

## Machine-Readable Governance

`scripts/relationships.yaml` is the source of truth for machine-readable governance in this repo: ADR coupling, required-reading edges, and doc-code linkage. This generated file does not inline that graph; it records the canonical path and sync marker, then points operators and validators back to the source graph. Prefer deterministic validators over prompt-only memory when those scripts are available.

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
