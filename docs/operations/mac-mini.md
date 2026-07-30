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

Planning disposition updated 2026-07-30: the Packet-21C capacity and resume
records below remain dated runtime evidence, but they are no longer an active
instruction to launch the repeated comparison. The canonical
[roadmap](../ROADMAP.md) and [goal](../GOAL.md) now route MVP work through
[Slice 24](../plans/024-configurable-theory-analysis-mvp.md). A future
comparison requires explicit post-MVP selection.

Packet 21C1 deployment and capacity boundary observed 2026-07-30:

- simulator `b2f0655e8a613cbc109467332dcbe0cadff5b93a` and unchanged shared
  client `7501811bee49fe4c20af2d2a50e4040a596b328b` are running behind the
  private URL. The exact candidate passed the production frontend build,
  strict Python typing, and all 230 Mac tests before restart;
- the restarted config retains the certified `codex/gpt-5.6-terra` medium
  route, 150-participant, 57-narrator, and one-coder guards. Both retained run
  readback and the new config returned successfully after restart;
- authorized second-baseline attempt `run_71a55a23f247` failed before its first
  participant response because the Codex CLI reported the account usage limit,
  with reset at 2026-08-05 00:09 local time unless credits are added. The
  retained record contains one failed Terra/medium participant lifecycle, no
  world event, no narrator or coder call, and `$0` observed marginal cost. Its
  retained-file SHA-256 is
  `99c5f57a6e49453b22e0552db7449ff7d538a2292b584630570847d634d2b979`;
- no replacement was launched, and the separately authorized pressure and
  stabilization replicates were not launched into the known capacity
  rejection. Packet 21C1 therefore remains incomplete. Resume only after the
  subscription route has capacity and the operator explicitly authorizes one
  replacement baseline.

Packet 21B2 deployment and three-condition canary gate observed 2026-07-30:

- simulator `fd85ead3565b3f42f9e47b02aa516fb421a457da` and shared client
  `7501811bee49fe4c20af2d2a50e4040a596b328b` supplied the accepted canary
  evidence. The config defaulted to `codex/gpt-5.6-terra` at medium reasoning and
  separately advertises certified Luna/medium. Coordination permits at most
  150 participant decisions as an emergency run-length guard, not a simulated
  pressure setting or target, plus 57 narrator and one post-run coder call;
- Terra generic participant/narrator certification observations are
  `routeobs1_4f9772426288e374ab4c4460` and
  `routeobs1_ac896d144bea9fc40db5f66a`; its five Coordination person schemas
  plus `CoderOutput` are bound by `routeobs1_adf8cf81d926d5ef4b185627`,
  `routeobs1_834e9e26e778184bf945354e`,
  `routeobs1_d7d7824142051f8c4bbb2546`,
  `routeobs1_74e266ff78785303e9f0905b`,
  `routeobs1_6930d041f684abc0e356afb3`, and
  `routeobs1_7655ebcee683cbf74955560a`;
- Luna generic participant/narrator certification observations are
  `routeobs1_ff4e493f370c2a643ba4bf59` and
  `routeobs1_718bec3ff7f4b167dada2901`; its Coordination certification group is
  retained in the LaunchAgent and certification store;
- accepted Terra baseline `run_994222dd246f` completed 38 participant, 29
  narrator, and one coder call with no error, retry, or fallback. It retained
  exact
  `deploy_on_time`, full scope, all five partners, zero final open risks, and a
  valid provenance-labeled measurement;
- accepted Terra stabilization `run_e2c6181e721f` completed 47 participant, 42
  narrator, and one coder call with no error, retry, or fallback. It retained
  exact `no_decision_by_horizon`, five partners, two final open risks, and a
  valid measurement after the trajectory first converged on reduced scope;
- accepted Terra pressure `run_2a4055a4a51f` completed 48 participant, 43
  narrator, and one coder call with no error, retry, or fallback. It retained
  exact `no_decision_by_horizon`, five partners, two final open risks, and a
  valid measurement, terminating at the day-10 condition rather than the
  150-decision guard. The 92 calls used only `codex/gpt-5.6-terra` at medium
  reasoning with complete `subscription_included` zero-cost coverage;
- superseded pressure `run_e3173c381918` remains retained as evidence of the
  former 48-call safety-limit failure. The new canary supersedes that failure;
  it does not rewrite it.

Live execution uses the shared `llm_client` checkout at
`/Users/b/code/llm_client`. The LaunchAgent starts through
`deploy/run-with-provider-secret.sh`, which first verifies that the Codex CLI is
logged in through ChatGPT. It optionally loads an OpenRouter credential from the
login Keychain service `cybernetic-influence-v3-openrouter`, then an owner-only
raw secret file when the Keychain is locked to noninteractive services. The
credential is not stored in the repository or LaunchAgent plist.

Codex subscription deployment observed 2026-07-29:

- simulator behavior revision `6944dd26e1b905b3d3089c1b9045430090110ed1`
  and shared client `2e5ae381556c710f891c390783c5403df8038407`
  passed the production build, strict typing, and all 183 tests on the Mac;
- the LaunchAgent verifies `codex login status` reports ChatGPT authentication,
  sets subscription billing, and treats OpenRouter credentials as optional;
- fresh Mac observations certify Luna's generic participant and narrator
  schemas and all five Coordination person schemas. The private config exposes
  `codex/gpt-5.6-luna` at medium reasoning as the default and records
  `verified local ChatGPT Codex login` plus `subscription_included`;
- deployed live run `run_5bb293db1358` completed with three participant and
  three narrator calls, the exact `Entered equipment room` outcome, fully
  observable `$0` marginal subscription cost, and no model fallback;
- rendered browser verification `run_535a61277c16` passed deep-link reopening,
  all three graph projections, spatial and causal composite collapse, readable
  narrative modes, participant/group accounts, and reference pause/resume with
  no console or failed-request errors. A separate 1440×1000 inspection showed
  the Luna selector and medium reasoning while hiding the irrelevant
  usage-based cost field.

The following section is the immediately preceding DeepSeek coordination
baseline retained for comparison, not the current default.

Current V3 deployment observed 2026-07-29:

- simulator revision `8f59c28f5b96792d459ff60f42f879659aa68fd6` and shared
  client `68949c9427ae4e2249aa2d6bc51949739385c275` (`llm-client` 0.7.1)
  passed the Mac's strict typing, 178-test, production-build, and
  LaunchAgent-template gates before restart;
- its private config exposes the Coordination decision scenario and permits
  only `openrouter/deepseek/deepseek-v4-flash` at `none` reasoning for the
  live Coordination scenario. The current generic participant/narrator route
  observations are `routeobs1_b23c1d902f7d49429598d6f3` and
  `routeobs1_b83c1bf9cefc179a7e0b5650`; the five person-schema observations are
  `routeobs1_6d235df74a36c6671a22dc39`,
  `routeobs1_2d2414497529629f729fd51e`,
  `routeobs1_ea79cbe005b46de152adbd7e`,
  `routeobs1_dfbc17c844d3f8d10c3c350e`, and
  `routeobs1_7edc2427624c701b47e63eec`;
- the one authorized replacement baseline, `run_21a48f59c28f`, completed four
  meeting cycles through exact terminal condition `decision_deploy_on_time`.
  It retained 338 unique events, 28 unique narrated moments, 37 participant
  calls, 28 narrator calls, and `$0.0215453528` known provider cost;
- all 65 logical calls selected a validated DeepSeek response with no fallback
  or terminal call error. Ten calls recovered on one retry: nine repaired a
  strict-schema validation failure and one recovered from a 180-second
  transport timeout. The timeout attempt has no known price, so the run
  correctly retains `cost_fully_observable: false` while preserving the known
  successful-attempt price and completed trajectory;
- after LaunchAgent restart, the run reopened with the same retained-file
  SHA-256 `b6d47e3801cc0fef40dc6efa04d628bef5ebf0d969e21174cfa29e2b3a7ad365`,
  the same 65-call ledger, and no additional cost. A rendered deep-link check
  showed all three map projections, analytical scale, initial situation,
  concise/detailed story, outcome, and participant/group accounts with no
  browser console or network error;
- the technical 21A4 proof is complete. Human readout remains pending because
  some detailed prose still exposes internal labels such as `meeting_clock`,
  and one final account describes an unchanged proposal as denied before the
  exact terminal gate accepts it. Do not run a second replacement baseline;
  use the retained run for the operator decision.

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

The default live route is `codex/gpt-5.6-luna` at medium reasoning for
participants and narration. It uses the signed-in ChatGPT Codex subscription;
usage limits, rather than marginal API price, are the operative external bound.
OpenRouter routes remain explicit alternatives when their current exact-schema
observations and credential are available; no failure silently changes model.

Runtime contracts retain per-call budget bounds required by `llm_client`, but
Luna calls are recorded as subscription-included rather than priced API calls.
The UI therefore hides the usage-based planning field for Luna and instead
states that ChatGPT subscription limits apply. OpenRouter alternatives retain
their explicit cost planning fields. Only one live run may execute at a time.

Service Desk scripted and live runs can pause only after a validated quiescent
causal boundary. Resume requires the same scenario identity, effective LLM
configuration, and shared-client revision; it appends from the retained
checkpoint rather than replaying the committed prefix. The current PoC does not
interrupt an in-flight provider request or automatically resume after a server
restart.

Purchase-to-payment uses the operator-selected effective live configuration;
the current server default is therefore also subscription-backed Luna at
medium reasoning. Its observation-driven
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
CYBERNETIC_INFLUENCE_CERT_CODEX_LUNA=<participant observation>,<narrator observation>
CYBERNETIC_INFLUENCE_CERT_DEEPSEEK_V4_FLASH=<participant observation>,<narrator observation>
CYBERNETIC_INFLUENCE_CERT_COORDINATION_TERRA=<all exact Coordination person-schema and CoderOutput observations, or empty>
CYBERNETIC_INFLUENCE_CERT_COORDINATION_CODEX_LUNA=<all exact Coordination person-schema and CoderOutput observations, or empty>
CYBERNETIC_INFLUENCE_CERT_COORDINATION_DEEPSEEK_V4_FLASH=<all exact Coordination person-schema and CoderOutput observations, or empty>
```

An observation is accepted only when its requested model, exact provider-schema
digest, shared-client revision, successful transport evidence, and seven-day
freshness all replay successfully. Registry membership or a configured key is
not enough. The global pair makes a route available to scenarios using the
generic person schema. Coordination remains reference-only unless its separate
scenario group contains one current observation for each of the five exact
person schemas and the post-run `CoderOutput` schema. Adding or changing the
measurement schema therefore makes Coordination reference-only until that exact
route observation is retained; catalog availability alone is insufficient.

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
