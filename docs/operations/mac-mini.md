# Mac Mini Development Host

The approved development instance runs as the `b` user's LaunchAgent on
`brian-mac-mini`:

- private URL: <https://brian-mac-mini.tail9c321e.ts.net:8620/>
- checkout: `/Users/b/code/cybernetic_influence_v3`
- retained runs:
  `/Users/b/Library/Application Support/CyberneticInfluenceV3/runs`
- service: `com.cybernetic-influence.v3`
- logs: `/Users/b/Library/Logs/cybernetic-influence-v3*.log`

The service binds only to `127.0.0.1:8620`. Tailscale Serve adds the
tailnet-only HTTPS listener. Do not use Funnel for this port, and do not reset
the machine's Serve configuration because its other listeners are unrelated.

Live execution uses the shared `llm_client` checkout at
`/Users/b/code/llm_client`. The LaunchAgent starts through
`deploy/run-with-provider-secret.sh`, which first checks the login Keychain
service `cybernetic-influence-v3-openrouter`, then an owner-only raw secret file
when the Keychain is locked to noninteractive services. The credential is not
stored in the repository or LaunchAgent plist.

Last verified 2026-07-24:

- simulator: `374b2a50d168fb4c16a9ed834157890f89159384`;
- shared client: `07b168ff616b079da5be5f7a71555467439a9be5`;
- advertised route: Terra only;
- Terra certification:
  `routeobs1_d9cdaf56c225479422018a8f,routeobs1_360219087d7a8109c385c817`;
- final causal canary: `run_7666035b2c17`, completed
  `closed_confirmed`, seven participant calls, `$0.033916875`;
- open limitation: narrator call refused by OpenRouter key-total-limit 403.

The currently advertised live route is
`openrouter/openai/gpt-5.6-terra`. The explicit provider prefix is required
because bare `gpt-5.6-terra` intentionally selects the direct OpenAI route in
`llm_client`. The UI exposes Terra agent reasoning at low, medium, or high,
defaults to medium, and retains low narrator reasoning. Scenario participant
and narrator calls use a 384-token structured-output ceiling; retained
successful evidence peaked at 169 and 191 tokens respectively.

Runtime contracts cap each participant call at $0.05 and narration at $0.02 per
bounded moment. The UI advertises the conservative combined $0.74 envelope.
Typical Service Desk runs quiesce well before that bound. Only one live run may
execute at a time.

DeepSeek V4 Flash is a configured candidate, not an advertised route. The
shared policy supports high reasoning for the exposed DeepSeek agent/narrator
path, but final-revision structured probes repeatedly returned empty content.
Do not add `CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH` until fresh exact
participant and narrator observations plus a complete canary pass.

Purchase-to-payment uses the same explicit model at medium human reasoning and
low narrator reasoning. Its observation-driven settled and processor-declined
paths allow at most four human and four narrator calls under a conservative
$0.38 combined envelope. Denied or malformed paths quiesce earlier; the model
and budget boundary do not change.

## Inspect

```bash
ssh 100.109.41.60 \
  'launchctl print "gui/$(id -u)/com.cybernetic-influence.v3"'

curl https://brian-mac-mini.tail9c321e.ts.net:8620/api/config
```

The config response reports `build_commit`; compare it with the approved local
commit before interpreting a remote run.

## Update Without Host GitHub Credentials

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
```

Install the accepted `llm_client` revision into the simulator environment:

```bash
.venv/bin/python -m pip install -e /Users/b/code/llm_client
```

The installed LaunchAgent binds route evidence explicitly:

```text
LLM_CLIENT_REVISION=<exact shared-client commit>
LLM_ROUTE_CERTIFICATION_ROOT=/Users/b/Library/Application Support/LLMClient/route_certification
LLM_CLIENT_TIMEOUT_POLICY=allow
CYBERNETIC_INFLUENCE_CERT_TERRA=<participant observation>,<narrator observation>
```

An observation is accepted only when its requested model, exact provider-schema
digest, shared-client revision, successful transport evidence, and seven-day
freshness all replay successfully. Registry membership or a configured key is
not enough.

OpenRouter's generation metadata endpoint is eventually consistent. A
successful model call may be followed by repeated
`GET /api/v1/generation?id=...` 404s. This does not invalidate the model
response, but it prevents route advertisement until the retained logical call,
generation ID, exact schema, and later metadata are joined. Re-query metadata;
do not pay to repeat a successful call solely because this lookup lagged.

Provision or replace the provider credential through the Keychain prompt:

```bash
security add-generic-password -U \
  -a "$(id -un)" \
  -s cybernetic-influence-v3-openrouter \
  -w
```

If the login Keychain cannot be unlocked for a background service, place only
the raw key in
`/Users/b/Library/Application Support/CyberneticInfluenceV3/openrouter.key`,
owned by `b` with mode `0600`. The launcher refuses other owners or modes.

Render the LaunchAgent template with the new commit in `__BUILD_COMMIT__`, the
approved Tailscale login in `__ALLOWED_TAILSCALE_USERS__`, and
`/Users/b/Library/Application Support/LLMClient` in
`__LLM_CLIENT_DATA_ROOT__`. Set `__OPENROUTER_KEY_FILE__` to the protected file
path even when Keychain is preferred; it is the fail-closed fallback. Validate
the result with `plutil -lint`, then use:

```bash
launchctl bootout "gui/$(id -u)/com.cybernetic-influence.v3"
sleep 1
launchctl bootstrap "gui/$(id -u)" \
  ~/Library/LaunchAgents/com.cybernetic-influence.v3.plist
```

On this host the first immediate `bootstrap` after `bootout` has intermittently
returned error 5 while the old job finishes exiting. Wait two seconds and retry
once, then require `launchctl print` to show `state = running`; do not interpret
the first error or an empty command result as success.

Reopen an existing retained run after restart before considering the update
complete. Before advertising live execution, make one bounded provider-backed
run, verify its retained model-call evidence and cost, and confirm that the
missing-credential and unauthorized-live controls fail closed. Delete
transferred bundles after the update; they are only transport.
