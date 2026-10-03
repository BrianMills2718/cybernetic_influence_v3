# Now (2026-10-03, seeded from git history)

**Stopped at:** the newest commit (PR #42, 2026-10-02) only synced the shared
doc-coupling checker. The last direction-setting work is PRs #40-#41
(2026-09-30): ADR-017 put a replacement-first gate in front of all further
simulator work, Slice 39 froze the Simudyne trial case, and an access request
went to Simudyne. No reply is recorded.

**Next step** (`approved`, `docs/GOAL.md` "Exact next action"): get real
Simudyne trial access, then build the regional-outbreak case on it without
calling the Cybernetic Influence runtime. Follow "First command after access
arrives" in `replacement_trials/simudyne_regional_outbreak/README.md`.

- Waiting on: Simudyne's reply to the 2026-09-30 request. The AWS Marketplace
  route auto-converts to a paid plan; it needs Brian's explicit yes.
- If access fails (`approved`, plan 039 "Comparative fallback"): record an
  access failure, not a semantic one; run the same case on Concordia; evaluate
  GAMA before expanding Concordia if LLM residents are not needed, and AnyLogic
  before adding local capability if conventional multi-method simulation is
  the real need.
- Until then (`approved`, ADR-017 "Consequences"): demo and evidence surfaces
  may be maintained, but maintenance must not turn into platform development.

**Other open threads** (all `working`):
1. Stakeholder judgment for `MVP-C6` and the `POST-C1`/`C2` readouts (ROADMAP).
2. Four unmerged PRs: #39, #30, #20 and #19 (see `state.md`).
3. Waltzman outreach email, unsent, needs Brian's approval of the exact text
   (`docs/WALTZMAN_OUTREACH_DRAFT.md`). What the repo says about Waltzman and
   World Substrate: `state.md` "Waltzman in this repo".
4. The four docs that disagree, listed at the bottom of `state.md`. (Item 5,
   CI, was resolved 2026-10-03: the local `make check` is the merge gate.)

**Reading tip:** `docs/GOAL.md` "Active Plan" and the README's Slice 27 link
describe the Concordia track; both sit under the 2026-09-30 override, which
supersedes them. Read them as the fallback path.

**Rule for every agent:** read this file first. When your change moves where
the project stands, update `now.md` (and `state.md` if needed) in the same pull
request. `python3 ~/code/agentic-engineering-system-canonical/scripts/hive/brain_fresh.py .`
exits 1 when this brain is stale.
