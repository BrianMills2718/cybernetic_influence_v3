---
doc_role: session_handoff
authority: bounded_design
status: active
created: 2026-08-25
updated: 2026-08-25
---

# Handoff: repository review and the assay's broken control, 2026-08-25

The session began as "review `cybernetic_influence_v3` and advise" and turned
into one substantive defect: the perturbation assay's control condition has
been failing since 2026-08-03 and nobody knew why.

## The demo is fine and is the thing to send

Verified in a real browser against the deployment, not inferred:

- `https://brian-mac-mini.tail9c321e.ts.net/waltzman/` loads, and all seven
  case-study steps advance with zero console errors and zero page errors.
- The Create surface is live and enabled — two authoring routes certified,
  roughly 5.6 days of margin at the time of checking.
- Both nightly launchd jobs are firing. Read their logs: the certification
  refresh ran 03:30 on 08-24 and 08-25 and correctly did nothing (above its
  3-day margin); the demo audit ran and passed all four checks both mornings.
- Retained runs `run_012aa6971e69` and `run_702e57f9accc` both populate
  `visible_edge_ids` on their event scenes on the live deployment.

## Merged this session

| Commit | What |
| --- | --- |
| `0302e80` | The outreach email no longer offers section 7 as unbuilt; the roadmap gains slices 31–34, the CSO flagship correction, and evasion moved off the fully-deferred list |
| `923e141` | `test_config_and_static_ui_are_operator_first` knows about the `threshold_managed_evasion` arm |
| `d0d2cde` | Both long-standing failures diagnosed and written into the roadmap |
| `64eb640` | The assay control failure bisected to `54394e0` with its mechanism |

## The finding that matters

`54394e0` (2026-08-03, "Remove inert gaps from Waltzman demo timeline") moved
`MEETING_DAYS` from `(0, 3, 6, 9)` to `(0, 1, 2, 3)` and `DECISION_DEADLINE_DAY`
from 10 to 4. Sensible for a demo. But the composite perturbation assay reuses
that same scenario constant. Its `matched_control` row decided at modeled minute
12998 under the day-10 deadline; against the day-4 deadline of 5760 it lands at
5768. Eight minutes late, every run since.

Consequences: `capability_satisfied` is false for the control while
`member_replacement` passes, so every Packet 22A2 contrast published after
2026-08-03 is measured against a control that never reaches a decision. Nothing
failed loudly, because the assay's own assertions still ran — only its meaning
changed.

Bisected across 354 commits in a disposable clone under the scratchpad. No
worktree, no claim, nothing touched in the canonical checkout.

## What I was wrong about

- **"The suite takes about two hours."** It takes 16–18 minutes. I projected
  from its first 44 tests, which are the slow ones.
- **"3 failures, then 13, then the 3 was load-corrupted."** Wrong twice. Three
  full runs gave 3, 13, 3. The ten extra all pass in isolation, so the suite
  has order-sensitive tests and its count is not a single-run measurement. I
  should not have quoted a number from one run of a suite I had not
  characterised, and should not have blamed concurrent load without testing it.
- **"The replay's missing edges might affect authored runs."** They do not. The
  V2 runs the site serves populate them; only the V1 path is affected.

## Open items

1. **The assay repair itself.** The right fix is to give the assay its own
   declared deadline rather than inheriting the demo's pacing constant, which
   restores the meaning its retained evidence already assumes. A scenario
   behavior change needs a governing plan first; that plan is the active work.
2. **The V1 replay gap.** The scene builder reads
   `transitions[].transaction.operations`, which the `reviewed-coordination-drafts`
   path never retains, so its event scenes have one node and no edges. Belongs
   to the V1 retirement track, harmless to the demo.
3. **Two learning entries are owed and cannot be written.** The register
   directory is read-only under the Codex lane `observer-panel-learning`
   (claim expires 2026-08-27T00:36Z). Owed: the single-run failure-count
   self-correction, and this shared-constant coupling.
4. **`docs/plans/CLAUDE.md` is stale scaffolding** injected into every session
   touching that directory. It names `01_example.md` and
   `scripts/meta/complete_plan.py`, neither of which exists, and a `NN_name.md`
   convention the repo does not use.
5. **The builder's progress line still says "typically 2–3 minutes"**
   (`public/waltzman/app.js:2749`) while the intro copy correctly says several
   minutes.

## Decisions not to relitigate

- The flagship is the CSO stabilization run `run_5010214f2466` with its
  `threshold_managed_evasion` counterpart, decided 2026-08-23.
- The deadline is not the thing to move. Fitting it to 5768 so the control
  passes would make the experiment agree with whatever the schedule happens to
  do, which is the opposite of what a control is for.
- Send the email before building more. The demo holds its own quality nightly.
