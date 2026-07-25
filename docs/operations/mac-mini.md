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

- simulator: `ecce006c77e99f968230d9e5fb0f78cfcac727b4`;
- shared client: `9f61bd7c9419c93961a722a7ef6209adcf593382`;
- advertised routes: Terra and DeepSeek V4 Flash;
- Terra certification:
  `routeobs1_7cc1c51f065c181a33ff422d,routeobs1_bb5643a65107960dadc76a36`;
- DeepSeek certification:
  `routeobs1_029097c508a11554b6b9301f,routeobs1_ba61b37be133f07f47177352`;
- default route: DeepSeek V4 Flash with `none` participant and narrator
  reasoning;
- exact-revision complete canary: `run_954220d513c3`, completed
  `closed_confirmed`, seven participant calls plus eight causal-moment narrator
  calls, `$0.0034581043` provider-observed;
- checkpoint-continuation canary: `run_abcd00000000`, completed from its
  retained live checkpoint with 12 causal moments, 23 total model calls, and
  `$0.0054597981` provider-observed;
- continuation trace: 105 unique ordered events and 23 unique logical calls;
  every call has one start and completion, native JSON-schema output, no retry,
  error, warning, or validation failure, and the receipt sum exactly matches
  retained cost;
- rendered desktop canary: `run_251610100415` paused after one live call,
  resumed, and completed with 19 calls, ten narratives, both map projections,
  participant/composite traces, causal-moment controls, and history readback;
  no browser console/network or backend error remained, and the reproduced
  trace-selection scroll jump is fixed;
- causal-time correction canary: scripted `run_7124717c9dcd` retained unique
  moment timestamps `c1` through `c8`, 67 unique exact trace positions, and an
  explicitly separate uncalibrated process clock; rendered readback also
  upgraded the older live canary to unique causal labels without console,
  network, or new backend errors;
- open limitation: operator usability judgment remains pending; mobile is out
  of scope for this private PoC.

The default live route is
`openrouter/deepseek/deepseek-v4-flash` at `none` reasoning for participants
and narration. DeepSeek `high` and `xhigh` are visible experiments rather than
certified settings; shared-client policy rejects `medium`. Terra remains
selectable as `openrouter/openai/gpt-5.6-terra` with `none`, `low`, `medium`,
or `high` participant reasoning and `low` narrator reasoning. Explicit provider
prefixes are required because bare model identifiers may select direct-provider
routes in `llm_client`.

Runtime contracts cap each participant call at $0.05 and narration at $0.02 per
bounded moment. The UI advertises the conservative combined $0.74 envelope.
Typical Service Desk runs quiesce well before that bound. Only one live run may
execute at a time.

Service Desk scripted and live runs can pause only after a validated quiescent
causal boundary. Resume requires the same scenario identity, effective LLM
configuration, and shared-client revision; it appends from the retained
checkpoint rather than replaying the committed prefix. The current PoC does not
interrupt an in-flight provider request or automatically resume after a server
restart.

Purchase-to-payment uses the operator-selected effective live configuration;
the server default is therefore also DeepSeek `none`. Its observation-driven
settled and processor-declined paths allow at most four human and four narrator
calls. Denied or malformed paths quiesce earlier. Pause/resume remains limited
to Service Desk.

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
CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH=<participant observation>,<narrator observation>
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
