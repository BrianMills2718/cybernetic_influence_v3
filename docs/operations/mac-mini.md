# Mac Mini Development Host

This is a private development host, not a public deployment surface.

- private URL: <https://brian-mac-mini.tail9c321e.ts.net:8620/>
- checkout: `/Users/b/code/cybernetic_influence_v3`
- retained runs: `/Users/b/Library/Application Support/CyberneticInfluenceV3/runs`
- service: `com.cybernetic-influence.v3`
- logs: `/Users/b/Library/Logs/cybernetic-influence-v3*.log`

The service binds to `127.0.0.1:8620`; Tailscale Serve provides the private
HTTPS listener. Do not use Funnel or reset unrelated Tailscale Serve settings.

Current product direction is the [roadmap](../ROADMAP.md) and
[Slice 24](../plans/024-configurable-theory-analysis-mvp.md). Before treating
this host as ready for live work, inspect its `/api/config`, the installed
shared-client revision, and current route capability evidence. Historical route
certifications, model capacity incidents, run identifiers, and canary results
are retained separately in the [July 2026 runtime history](../archive/operations/mac-mini-2026-07.md);
they do not authorize a new run or establish present model availability.

Last verified 2026-07-30: simulator commit
`9daadbb5349fefc317cca2bd2f1a166b33474b2d` served corrected approved draft
`draft_6fbb279df69b` and zero-call reference run `run_eded0f70b15f`. The
desktop flow passed with non-overlapping launch controls, a reviewed
initial-situation account, human-centered concise and detailed stories,
separate person/process/group accounts, full-run and selected-moment group
scope, all three graph projections, both analytical composites, and
pause/resume. The run ended `scope_reduced`, retained both Waltzman and Levin
readouts, and reopened with unchanged evidence and analysis digests. The
current service started cleanly and reported the same build commit; no browser
or request error occurred. Historical live draft `draft_019c16228a62` and run
`run_e1a91d0a47e1` remain immutable Packet 24C evidence; they do not authorize
another live call.

Current demo deployment 2026-08-03: the running service uses isolated worktree
`/Users/b/code/cybernetic_influence_v3-waltzman-demo` at the implementation
commit recorded by `/api/config`, rather than the general canonical checkout.
The LaunchAgent at
`/Users/b/Library/LaunchAgents/com.cybernetic-influence.v3.plist` records that
build commit and installed shared-client revision
`28dfa9928750baefe131e25ecc97c04ede81c174`. Coordination launch is live-agent
only on the product API and UI; fixed person policies remain available only to
explicitly enabled internal verification apps. Historical scripted run
`run_f2d6bfc31ea0` remains readable but is not stakeholder product evidence.

Fresh live run `run_2250cbb74f44`, compiled from approved draft
`draft_760f90419937`, completed with 51 successful participant calls and 46
successful narrator calls through `codex/gpt-5.6-terra` at medium reasoning.
Subscription-included observed cost was `$0.00` and fully observable. Its five
people were live LLM participants; only the retained meeting clock and three
outside concern sources were deterministic world processes. Meetings opened on
modeled days 0, 1, 2, and 3, and the exact day-4 gate recorded
`no_decision_by_horizon`. Both Waltzman and Levin modules are available and
bound to the same retained run-evidence bundle. Reopening the API twice produced
the same identity-and-analysis digest without additional calls. A fresh browser
pass verified contiguous story days 0 through 4, all projections, both
analytical composites, exact-evidence step-down, and live-only coordination
launch without console or failed-request errors.

Post-audit presentation correction 2026-08-03: the Waltzman-facing surface now
renders `no_decision_by_horizon` as no deployment approved, states that
verification began on day 0 before the scheduled concern sources acted on day
1, and presents the measures as single-run observations rather than a causal
chain. It visibly states that the sources are fixed scheduled processes and
that the unmatched run does not demonstrate adaptive influence, a directional
invariant, attribution, or proportionality. The corrected private browser pass
preserved the full deep-link, evidence, projection, composite, and pause/resume
flow without console or failed-request errors.

Current outbreak-comparison deployment 2026-08-04: the same private service now
serves commit `8e43e6ec64a4661629fce9e332386aa09d05003b`. Run History exposes
the fresh authentic baseline `run_0b5e20260805`, responsive capacity-pressure
run `run_7eae20260805`, and matched allocation-stabilization replay
`run_ca9a20260805`. Their final positions are respectively 12 support;
12 defer; and 11 support plus 1 conditional. The exact outcomes are approval,
no approval, and restored approval. Each run retained 36 completed
`codex/gpt-5.6-luna` participant calls with no observed cost. A private Chromium
pass opened all three comparison rows and the stabilized deep link with no
console or failed-request errors. The live launch catalog currently advertises
the freshly eligible `codex/gpt-5.6-terra` route; retained Luna evidence remains
readable without implying present Luna launch availability. The pre-cutover
LaunchAgent is retained at
`~/Library/LaunchAgents/com.cybernetic-influence.v3.plist.pre-8e43e6e` for
rollback.

## Inspect

```bash
ssh 100.109.41.60 \
  'launchctl print "gui/$(id -u)/com.cybernetic-influence.v3"'

curl https://brian-mac-mini.tail9c321e.ts.net:8620/api/config
```

Compare `build_commit` with the approved local commit before interpreting a
remote run.

## Update without host GitHub credentials

From an approved, clean local `main`:

```bash
git bundle create /tmp/cybernetic-influence-v3.bundle main
scp /tmp/cybernetic-influence-v3.bundle 100.109.41.60:/tmp/
ssh 100.109.41.60
```

On the Mac:

```bash
cd ~/code/cybernetic_influence_v3
git fetch /tmp/cybernetic-influence-v3.bundle main
git merge --ff-only FETCH_HEAD
export PATH=/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin
npm --prefix frontend ci
npm --prefix frontend run build
.venv/bin/python -m pip install -r requirements-dev.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m mypy
.venv/bin/python -m pytest -q
.venv/bin/python -m pip install -e /Users/b/code/llm_client
```

Use the committed LaunchAgent template and its explicit current certification
placeholders. Do not copy credentials, historical observation IDs, or route
defaults from archived runtime records into a new deployment.
