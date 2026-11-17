# Testing and verification

Moved word for word from the root `AGENTS.md` on 2026-11-17 to keep that file under the
12,000-byte instruction cap. These rules bind every change in this repository.

## Testing And Verification

- `make check` runs six stages — `typecheck test-wait-check test ui-build
  assets-check deploy-check` in that order: `mypy` (strict,
  `files = ["src", "tests"]`), then the test-deadline scan described below,
  then `pytest -q tests`, then the frontend build, then the check that the
  served bundle matches `frontend/src`, then the deploy-script syntax check.
  Run it before treating work as complete; do not report success from a
  partial subset. Count the stages against the `check:` target in the
  `Makefile` rather than this list if the two ever disagree.
- Run it from a worktree, not from a canonical checkout left read-only by the
  workspace guard: only the write stages fail there, so `ui-build` reports a
  bundler crash whose real cause is `Permission denied` on `web/`.
- **The merge gate is a local `make check`, and the PR says so.** Hosted CI is
  off: GitHub Actions has not run here since 2026-09-14, and Brian does not want
  it relied on (2026-10-03: "we need to not rely on github actions because i was
  running up massive bills"). So before a merge, run `make check` from a
  worktree and paste its pass/fail counts and exit status into the PR
  description; do not merge a PR that lacks them. This matters: between
  2026-08-26 and 2026-09-06 three merges each shipped a red assertion because the
  local run was skipped. `.github/workflows/check.yml` is kept but does not run.
- If hosted CI is ever turned back on: it checks out `llm_client` with a read-only deploy key held in the
  `LLM_CLIENT_DEPLOY_KEY` secret. It is not optional there: without
  `llm_client` the suite does not skip gracefully, it fails to collect with 11
  errors. If CI starts erroring during collection, check that key before
  suspecting the tests.
- A test that exercises a Codex route must patch
  `cybernetic_influence.run_configuration.codex_subscription_available`. It
  shells out to the local `codex` CLI and reads its login status, so a test
  that leaves it real is asserting that whoever runs the suite is signed in to
  ChatGPT; the model drops out of the catalog otherwise and the run is rejected
  as "not currently advertised for simulator execution". Most tests here
  already patch it. Reproduce that environment with `PATH=/usr/bin:/bin`.
- Wait on wall-clock time, never on an iteration count, when polling for a
  background run to reach a terminal state. A fixed `for _ in range(200)` with
  a 10ms sleep is a two-second deadline on real work: it passes alone and fails
  inside the full suite and on CI. Use `wait_for` / `wait_until` from
  `tests/waiting.py`. This rule is enforced by `make test-wait-check`
  (`scripts/check_test_wait_deadlines.py`), which runs inside `make check` — it
  became a check on 2026-09-08 because as prose alone it did not hold: it was
  written on 2026-09-06 alongside a fix for two such tests, and two days later
  fourteen instances of the exact named pattern were still live across three
  test files, one of them failing `main`'s own CI.
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
