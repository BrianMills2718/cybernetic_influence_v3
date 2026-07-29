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

Current V3 deployment observed 2026-07-28:

- simulator behavior revision:
  `5465e012db5a3328fb06117eb7e11facbdd0a3c2`;
- the private config endpoint reports `openrouter/deepseek/deepseek-v4-flash`
  at `none` reasoning, with the unchanged participant observation
  `routeobs1_029097c508a11554b6b9301f` and fresh V3 narrator observation
  `routeobs1_16e4dfd28d81316f24dc81ec` bound to the current narrator schema;
- `run_20d2a0000001` paused after one committed causal step, then resumed the
  same checkpoint without replaying its prefix. It retained eight participant
  calls and `$0.001218052` provider-observed cost before failing closed;
- the retained failure is an LLM action that supplied `representation_id: null`
  for a Service Desk remediation interface with a required representation. The
  action escaped the active-runtime interface check and the exact mechanism
  rejected it with `ValueError: service-desk mechanism requires a
  representation`;
- Packet 20D2 is therefore **not accepted**: it has no terminal outcome or V3
  narrative. Do not repeat the paid run, switch to Terra, or relax the V3
  contract without an operator decision on the model/action-contract topology;
- after the service restart, retained authored run `run_6ff09016a6e0` reopened
  with its completed narration and unchanged retained `$0.00101175` cost; this
  readback made no provider call.

Terra replacement observation on 2026-07-28:

- Terra's V3 narrator route is now certified by participant observation
  `routeobs1_7cc1c51f065c181a33ff422d` and narrator observation
  `routeobs1_982bdef5232df0ada7f8e2fe`; the latter reused a successful
  `$0.00097625` call after OpenRouter's delayed generation metadata became
  available, rather than paying for a second certification call;
- `run_20d2b0000002` used Terra `medium` for people and Terra `low` for
  narration. It paused after one causal step, resumed that exact checkpoint,
  and reached `closed_confirmed` through terminal condition
  `confirmed_closure` with 27 retained calls and `$0.2113171875` observed
  cost;
- it is **not accepted** as the complete 20D2 proof: 16 of 25 V3 narrator
  moments were retained, then a valid Terra narrator call cost `$0.0203225`,
  exceeding the fixed `$0.02` per-call narrator ceiling. The run failed closed
  with no fallback or hidden cost overrun;
- a replacement requires an operator decision on the Terra narrator
  per-call/cap topology and fresh authorization. Keep the participant and
  narrator contracts intact; do not silently raise the ceiling or mix models.

Terra `$0.025` ceiling replay on 2026-07-28:

- build `ebfd1414b8bed64e68c9b7ebe13080e3119648c7` raised the simulator-owned
  narrator ceiling to `$0.025` and kept the total hard cap at `$0.74`;
- `run_20d2c0000003` again paused after one causal step, resumed the same
  checkpoint, and reached `closed_confirmed`. It retained 31 unique calls, 90
  unique events, and `$0.3051715625` provider-observed cost with no provider
  errors;
- it is still **not accepted**: 20 of 25 V3 narrator moments were retained,
  then the next valid narration call cost `$0.0252121875`, above the new
  ceiling. The simulator stopped narration loudly rather than accepting an
  over-cap call;
- the observed cause is cumulative prompt growth: each narrator call receives
  all prior detailed accounts even though the required continuity input is the
  prior narrative summaries. The next bounded repair is to supply compact prior
  summaries to the narrator while retaining the full simulator-owned evidence
  context and prior-record chain. Do not continue raising costs blindly.

Compact-continuity proof on 2026-07-28:

- build `749d4022a8a9beea35f727db87a1d8a989f4c7a6` supplies only each prior
  concise narrative summary to the narrator while retaining the complete
  simulator-owned evidence context and prior-record chain outside the prompt;
- `run_20d2d0000004` used Terra `medium` for people and Terra `low` for
  narration, paused after one causal step, resumed the retained checkpoint, and
  completed `closed_confirmed` through `confirmed_closure` at causal time 11
  (logical time 87);
- the retained proof has 90 unique events, 35 unique provider calls,
  `$0.1360228125` provider-observed cost, no provider errors, and all 25 of 25
  V3 causal-moment narratives. Its 25 retained narration contexts are version
  2 and use `causal_moment_narrator/v4`;
- after restart, the live host reopened that completed run and also reopened
  older authored run `run_6ff09016a6e0` without a provider call or cost change.
  The old run intentionally retains its legacy narration context;
- this completes the technical portion of packet 20D2. Operator readout is
  still required before packet acceptance: the account must be intelligible
  without raw evidence, disputed claims must step down to retained events, and
  the stopping reason must be clear.

Earlier exact-revision execution verified 2026-07-27:

- simulator behavior revision:
  `08614b4e9f4c7d6bd84c34922c16e83314faa814`;
- pause/resume canary `run_ca0e512a5763` completed `closed_confirmed` from its
  retained checkpoint with 110 unique events, 11 participant calls, two denied
  premature closure attempts, a delivered terminal receipt, and
  `$0.002085029` provider-observed cost;
- adequately authorized narration run `run_6c4975979cec` produced five valid
  detailed accounts before failing strict out-of-context citation validation;
- repaired-prompt run `run_e589d6e3a769` produced seven valid accounts before
  reproducing the same citation failure family; it retained 19 calls and
  `$0.00424612` provider-observed cost;
- participant execution, DeepSeek transport, native structured output,
  pause/resume, and cost visibility are observed; full sequential narration is
  not yet accepted because model-selected arbitrary event IDs proved unreliable;
- the existing narrator route observations certify the deployed v2 schema
  boundary only. Packet 20D1 intentionally changes that schema, so a fresh
  narrator observation is required before the v3 route may be advertised.

Previously verified 2026-07-25 route and compatibility evidence:

- simulator behavior revision:
  `6ec752fc5842673a4934fc159905089092abf3d5`;
- shared client: `9f61bd7c9419c93961a722a7ef6209adcf593382`;
- advertised routes: Terra and DeepSeek V4 Flash;
- Terra certification:
  `routeobs1_7cc1c51f065c181a33ff422d,routeobs1_bb5643a65107960dadc76a36`;
- DeepSeek certification:
  `routeobs1_029097c508a11554b6b9301f,routeobs1_ba61b37be133f07f47177352`;
- default route: DeepSeek V4 Flash with `none` participant and narrator
  reasoning;
- current behavior-revision deployment canary: `run_40fffe835670`, completed
  `closed_confirmed` with 37 participant and narrator calls, one exact
  mechanism denial of a premature closure attempt, and `$0.006233523`
  provider-observed cost;
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
- current rendered desktop readback: live DeepSeek baseline
  `run_eece01600002` completed after pause and resume with 38 model calls,
  `$0.007079` retained cost, and a `closed_confirmed` outcome. The deployed
  view labels the three projections Spatial topology, Configured interaction
  pathways, and Realized causal graph; intentionally nonspatial entities are
  described as outside the spatial projection rather than as missing placement;
- current pre-run readback: the Service Desk spatial topology and configured
  interaction pathways render from the read-only initial-state projection before
  Play, while the realized causal graph remains disabled until retained events
  exist; the initial projection is labeled revision 0;
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

Runtime contracts cap each participant call at $0.05 and narration at $0.025 per
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
CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA=<all exact Coordination person-schema observations, or empty>
CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH=<all exact Coordination person-schema observations, or empty>
```

An observation is accepted only when its requested model, exact provider-schema
digest, shared-client revision, successful transport evidence, and seven-day
freshness all replay successfully. Registry membership or a configured key is
not enough. The global pair makes a route available to scenarios using the
generic person schema. Coordination remains reference-only unless its separate
scenario group contains one current observation for each of the five exact
person schemas.

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
approved Tailscale login in `__ALLOWED_TAILSCALE_USERS__`, the global and
scenario-specific certification groups in their corresponding `__CERT_*__`
placeholders, and `/Users/b/Library/Application Support/LLMClient` in
`__LLM_CLIENT_DATA_ROOT__`. Use an empty string for a scenario-specific group
that has not been certified; never reuse a global pair in its place. Set
`__OPENROUTER_KEY_FILE__` to the protected file path even when Keychain is
preferred; it is the fail-closed fallback. Validate the result with
`plutil -lint`, then use:

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
