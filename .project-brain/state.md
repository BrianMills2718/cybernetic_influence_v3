# State (2026-10-03)

Detail: `docs/ROADMAP.md` ("Current Truth", "Capability Map", "Artifact
Dispositions"), `docs/plans/039-simudyne-replacement-trial.md`. Short version:

- **Simudyne replacement trial, Slice 39** (`working`, plan status
  `access_gated`, PRs #40-#41, 2026-09-30): an access request went to
  `support@simudyne.com` on 2026-09-30. The trial package is ready in
  `replacement_trials/simudyne_regional_outbreak/` (frozen 12-person case,
  result template, validator). No reply or trial result is recorded. The AWS
  Marketplace trial turns into a paid subscription after 7 days; do not start
  it without Brian's explicit approval (package `README.md`).
- **MVP** (`approved`, ROADMAP "Capability Map"): `MVP-C0`-`C5` satisfied. The
  only open MVP item is the stakeholder judgment part of `MVP-C6`.
  `POST-C1`/`POST-C2` experiments: technically done, stakeholder readout pending.
- **Concordia foundation** (`approved`, ROADMAP "Capability Map"): `GEN-C0`
  satisfied by Slice 28; `GEN-C1` parity substantially satisfied on the public
  V2 path. Paused as fallback by ADR-017; no new general-simulator work.
- **Public demo** (`approved`, ADR-016, PRs #34, #38): retained cases on
  Cloudflare, live runs on the personal VPS, no sign-in, spend capped by
  `public_spend_controls`. PR #38 says it was verified live on 2026-09-24. Not
  re-checked for this page.
- **Slices 37-38** (`approved`, `docs/plans/README.md`, PRs #23-#24): the
  Waltzman outreach funnel and living replay are implemented.
- **Slice 36 project picker** (`working`, ROADMAP "Artifact Dispositions"):
  active; the remaining check is the final Quick Pick selection/open.
- **Open PRs, unmerged** (`working`, GitHub): #39 archive external architecture
  review (2026-09-29); #30 Waltzman paper-fidelity gap analysis (2026-09-14);
  #20 and #19, drafts (2026-09-08). No open issues.

## Waltzman in this repo

- `docs/research/001-from-minds-to-coordination.md` (`approved` as source
  note): Rand Waltzman's paper is the research basis. It is a conceptual
  framework with no dataset or validated scale.
- The public workbench (https://brianmills.dev/waltzman/) shows a
  bio-surveillance partnership case with a Waltzman readout of trust, perceived
  risk and coordination readiness (`MVP-C4`, `docs/GOAL.md`).
- `/waltzman/world-substrate/` serves a World Substrate artifact pinned to an
  exact `BrianMills2718/world-substrate` revision; this repo owns only that
  hosting seam (ROADMAP "Outcome", PRs #28, #36). Slice 37 reuses this repo's
  authoring/run pipeline "rather than rebuilding it inside World Substrate".
- `docs/WALTZMAN_OUTREACH_DRAFT.md`: "draft, not sent"; needs Brian's approval.
- No comparison of a Waltzman route across this repo and world-substrate is
  recorded here. ADR-017 lets demo surfaces be maintained, not grown.

## Docs that disagree (`needs_resolution`)

1. `docs/plans/README.md` "Active execution" (updated 2026-09-09) lists Slices
   36-38 and omits Slice 39 and the ADR-017 gate.
2. `README.md` "Lineage" says V2 branches "still require disposition"; ROADMAP
   says the whole V2 checkout was archived on 2026-09-01 (PR #8).
3. `project-membership.yaml` lists `CLAUDE.md` as an entry point; PR #37
   removed it.
4. `wiki/index.md` claims "no declared roadmap or current-state authority";
   `docs/ROADMAP.md` declares `authority: canonical`.
5. `AGENTS.md` "Testing" says CI runs `make check` on every PR and `main`
   requires it. GitHub (checked 2026-10-03): Actions disabled for the repo, no
   required status checks, last run 2026-09-14, so PRs #32-#42 merged
   without a CI run. Re-enabling is Brian's call (Actions may cost money).
