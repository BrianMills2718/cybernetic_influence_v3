# Project: cybernetic_influence_v3 (Cybernetic Influence V3)

Layout and status words: agent-skills `contracts/client-config/agents/project-brain.md`.
Each claim is `working` (understood, not agreed), `approved` (current source of
truth) or `needs_resolution`.

- **What it is** (`approved`, `AGENTS.md` "Product Framing", `README.md` top): a
  general, reviewable simulator for bounded socio-technical worlds. An analyst
  describes a world in conversation, reviews and edits the compiled setup, runs
  LLM and deterministic entities, then inspects the trajectory, state,
  assumptions, provenance and chosen analyses. Wargaming, economic and
  organizational analysis are examples, not the product. It explores
  conditional pathways under stated assumptions; it is not a prediction engine.
- **Current direction: replacement first** (`approved`, ADR-017 accepted
  2026-09-30, `docs/GOAL.md` "Current override", `docs/ROADMAP.md` "Current
  frontier"): before any more general-simulator work, test whether Simudyne
  Nexus + its Python SDK can replace the generic platform on the retained
  regional-outbreak coordination case. If it can, retire the overlapping local
  code instead of porting it. ADR-013 (Concordia as foundation) stays as the
  open-source fallback.
- **The running app is a baseline, not the product architecture** (`approved`,
  `AGENTS.md` "Product Framing", `README.md`): the current application,
  including the public Waltzman workbench, is the pre-migration
  capability-parity baseline and evidence, not yet on the Concordia foundation.
- **Which doc wins** (`approved`, `AGENTS.md` "Documentation Authority"):
  `docs/ROADMAP.md` is current truth, `docs/GOAL.md` the accepted outcome,
  `docs/adr/` binding decisions. If a handoff's `status` disagrees with the
  roadmap's Artifact Dispositions table, the roadmap wins.
- **Who decides** (`approved`, `~/code/AGENTS.md`, `docs/ROADMAP.md`
  "Capability Map"): Brian owns the repo (GitHub `BrianMills2718/cybernetic_influence_v3`)
  and makes product, spend and outward calls, including the stakeholder
  judgment that `MVP-C6` still waits on and any paid Simudyne trial. Agents
  make technical calls.
- **Rules before changing behavior** (`approved`, `AGENTS.md` "Required Before
  Implementation"): runtime, API, UI, scenario, prompt or evidence changes need
  a governing plan (`docs/plans/`) or handoff (`docs/handoffs/`); architecture
  changes need an ADR; a slice is done only when `docs/ROADMAP.md` says so.
- **How work lands** (`approved`, `AGENTS.md` "Testing" and "Worktree And Lane
  Hygiene", PR #15): one claimed worktree per lane via `make worktree`, closed
  with `make worktree-remove`. Run `make check` (mypy strict, pytest, UI build,
  bundle check, deploy check) before calling work done. The CI copy of that
  gate is not running now (`needs_resolution`, `state.md` item 5).
  For unplanned docs work, `make worktree` also needs
  `WORKTREE_EXECUTION_PROFILE=light ALLOW_UNPLANNED=1 SESSION_WRITE_PATHS="<files>"`
  (`working`, observed when this brain was seeded, 2026-10-03).
- **Instructions** (`approved`, PR #37, 2026-09-23): `AGENTS.md` is the only
  instruction file for Claude Code and Codex; `CLAUDE.md` was removed.
- **Hosting** (`approved`, ADR-015, ADR-016): the public demo is
  https://brianmills.dev/waltzman/ on Cloudflare; live authoring and runs go to
  Docker on Brian's personal VPS (operations in `BrianMills2718/personal-vps`
  `apps/waltzman/`).
- **Related repos** (`approved`, `project-membership.yaml`, `docs/ROADMAP.md`
  "Repository Lineage Disposition", `AGENTS.md` "Testing"): live LLM runs need
  the shared `llm_client`.
  `cybernetic_influence_v2` was archived on 2026-09-01 and is evidence only; no
  V2 imports. `world-substrate` supplies a pinned presentation sidecar (see
  `state.md`).
