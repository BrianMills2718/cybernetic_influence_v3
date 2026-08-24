---
doc_role: session_handoff
authority: bounded_design
status: active
created: 2026-08-23
updated: 2026-08-23
---

# Handoff: the Waltzman demo, 2026-08-23

The goal is one thing: a demo of this repository Brian can send to Rand
Waltzman, the author of *From Minds to Coordination*, and feel good about.
Everything below serves that.

## Send this URL

`https://brian-mac-mini.tail9c321e.ts.net/waltzman/`

**With the trailing slash.** Without it the page used to render unstyled with
dead navigation; it now redirects itself, but the slash form is what the deploy
prints and what `ui/registry.yaml` records.

## What is ready

The **flagship case study** is the strong half and is unaffected by every bug
found today. Six steps, zero console errors, verified in a browser after each
change. It reads `outcome.round_history` directly (`scripts/build_cso_case_public.py`),
a different path from the analysis lenses, and raises if the run is not the
expected condition.

**Create your own simulation** works end to end: describe -> configure ->
review -> approve -> run -> replay. Verified by generating and running one
("Storm-Damaged Relief Port", `run_012aa6971e69`, draft `draft_93a507449f73`).

## Merged this session

| Commit | What |
| --- | --- |
| `464ee78`, `4a4e58d`, `e9ef709` | The shared link works without its trailing slash; `check_public_assets.py` resolves the page's own asset references at the exact shared URL and the deploy fails on a broken one |
| `e5b0541` | Walkthrough handoff into the builder; missing-evidence explained in plain words; Luna/CSO/Levin named so a first-time reader can place them |
| `8e7d499` + follow-up | Advancing the case study scrolls to the step you advanced to, clear of the sticky bar |
| `ad84624` | Sensing rules count as information, not "0 Information items" |
| `9f79ca4`, `35d6ba8` | Sensing rules retained as `information_lineage`; unsatisfiable analysis requirements rejected where work is created |
| `fb1b39c` | The analysis reads the runtime's two-call actor shape |
| `f66034b`, `071e51f` | Nightly authoring-certification refresh, installed on the Mac (03:30) |

## What I was wrong about

- **"That run committed no world operations, nothing changed."** False. My
  survey script read `payload.proposal.operations`; operations live at
  `payload.transaction.operations`. The run committed 5 then 2, all accepted,
  revisions 0->4. The zeros were a real bug, not a quiet simulation.
- **"participant_activation is never emitted."** It is, from actor model calls;
  my grep missed a conditional expression.
- **"The draft deep link is broken."** It is not. I hand-built a URL without
  `view=create`; the app writes both together and restores correctly.
- **Enforcing a new invariant on the shared typed model** made every retained
  draft unopenable (HTTP 422). A new rule governs what may be created, never
  what is already on disk.
- **I took the demo down for four minutes** by restarting the service without
  the settle delay the deploy path already had, and by trusting a bootstrap
  exit code instead of checking the port.

## Open items

1. **The generated analysis on old drafts still asks for `boundary_activity`**,
   which nothing emits, so it stays unsupported. New proposals are rejected;
   drafts authored before `35d6ba8` keep the stale requirement.
2. **Authoring takes ~5 minutes and silently retries** while the UI says
   "typically 2-3 minutes". Honest but unexplained.
3. **Two pre-existing test failures**, unrelated to this work and unexplained by
   anyone: `test_reviewed_coordination_example_runs_reopens_and_isolates_analysis_corruption`
   and `test_rows_exercise_distinct_concrete_paths`.
4. **Six learning entries are uncommitted in project-meta.** Several sessions
   write it concurrently, a rebase aborts on untracked files, and the writer
   reports success while the commit fails. Needs a dedicated lane.
5. **The outreach email is unsent and stale** — it still describes the fork
   study, which is no longer the flagship.

## Decisions not to relitigate

- The flagship is the **CSO stabilization run** (`run_5010214f2466`), not the
  four-way resource fork. Two independent reviews converged on this.
- **Fidelity means plausibility, as in a wargame** — not empirical validity.
- Waltzman's name stays on screen; he is the reader. Luna, Sol, CSO and Levin
  do not, unless defined.
- Evidence is immutable: a fix does not retroactively change a retained run's
  analysis. Re-attach a lens to recompute.

## The rule that produced most of today's findings

Payload checks, status codes and passing tests all reported healthy while the
page was visibly broken and while every coordination number was zero.
Screenshots caught the first in one minute; running the product caught the
second. For any surface a human will open, look at it and use it before
reporting it works.
