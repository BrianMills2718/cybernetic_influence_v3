# Public Waltzman authoring and execution certification

Observed on 2026-08-12 for the public Coordination Environment Lab.

## Verdict

- Capability ID: `cybernetic-influence.waltzman-public-influence-network-v2`
- Advertised action: describe a bounded influence network in natural language,
  edit the typed configuration, approve it, run autonomous LLM people, and
  inspect the retained information paths, decisions, and collective gate.
- Target: `Bs-Mac-mini.local`, LaunchAgent
  `com.cybernetic-influence.waltzman-public`, and the public Funnel route at
  <https://brian-mac-mini.tail9c321e.ts.net/waltzman/>.
- Deployed source revision:
  `e563a93f4369d63480c9134bce436757d3893c64`.
- Evidence level: `deployment_verified` for the bounded
  `influence_network_v1` authoring and execution path.
- Public authoring model: `codex/gpt-5.6-luna`, medium reasoning.

This is a report-only technical certification. It does not certify arbitrary
world generation, stakeholder usefulness, human behavioral fidelity,
empirical validity, predictive validity, or general causal claims.

## Deployed path

The exact public deployment completed this path:

```text
natural-language description
-> Luna typed proposal
-> compiler validation
-> direct no-model edit
-> explicit approval and composition receipt
-> Luna participant execution
-> exact decision gate
-> retained API result
-> public browser rendering
```

The analyst request described three fictional municipal participants, an
official audit bulletin delivered to all three, an anonymous allegation
delivered only to two, two decision times, distinct person configurations, and
an exact collective gate. It explicitly prohibited automatic persuasion.

The accepted proposal compiled to reusable causal components rather than
scenario-supplied executable code. Its composition receipt resolved 43 reviewed
components, including concrete people, places, stateful objects, information
carriers, directed routes, exact delivery mechanisms, round mechanisms, a
stance recorder, and the collective decision gate.

## Valid composition evidence

- Draft: `draft_68240a512235`
- Accepted authoring trace:
  `draft_68240a512235/revision/1/attempt/2`
- Workflow: `influence_network_v1`
- Generated people: election director Mara Chen, investigative journalist Eli
  Navarro, and neighborhood coalition organizer Priya Shah.
- Information topology: one documented audit bulletin reached all three people
  at minute 2; one anonymous allegation reached only Navarro and Shah at minute
  5.
- Decision times: minutes 3 and 7.
- Direct edit: revision 2 changed the title to
  `Waltzman influence-network walkthrough`; it recorded source
  `direct_proposal_edit` and made zero model calls.
- Approval: revision 3 approved revision 2 with proposal digest
  `717d2eebb8daf075bf066a81bcf13958ceb31f1efdd0caccd871ac5dc76e8455`
  and composition-receipt digest
  `058a70f89a6deb0ef8d4010196434ea0451280d656517dfc69b02a02646c1762`.
- Run: `run_ffe88e1c15d5`
- Shared-client revision:
  `ce66e74e9929c7a0b031e38ac46d0f38a25ba703`
- Execution: live, `codex/gpt-5.6-luna`, medium reasoning.
- Retention: 6 completed participant calls, 6 committed traces, 97 events, 20
  causal moments, and one terminal simulation completion.
- Exact result: 1 support, 2 conditional, 0 defer, and 0 oppose. The
  support-or-conditional and opposition gates passed; the two-support minimum
  failed, so the group did not approve the proposal.
- Cost: `$0.00` observed marginal cost under subscription-included billing; the
  run marks cost observability complete.
- Analysis projection: 2 rounds, 6 decisions, an 8-node/10-edge visible
  influence graph, and a coordination measurement readout with explicit
  interpretation limits.

The outcome is not treated as a correctness oracle. The evidence establishes
that the configured information paths, autonomous typed decisions, and exact
gate executed and remained inspectable.

## Lifecycle integrity

The first Luna authoring attempt reached its declared 60-second deadline. Its
shared-client lifecycle contains exactly one `started`, four `heartbeat`, and
one `failed` terminal event with `TimeoutError`. The bounded authoring retry then
contains exactly one `started`, three `heartbeat`, and one `completed` terminal
event. The retry compiled successfully; the initial timeout is retained rather
than hidden.

Each of the six participant traces contains exactly one `started` and one
`completed` event. Every retained participant call reports task
`cybernetic_influence_v3_authored_person_step`, model
`codex/gpt-5.6-luna`, status `completed`, and no error type. No logical call has
a second terminal event.

## Negative controls

- Typed invalid input: replacing the approved proposal with a body whose
  `scenario_id` was the integer `7` returned HTTP 422 with the expected typed
  validation errors. The retained approved draft remained revision 3 with the
  same proposal.
- Missing unique dependency: an isolated invocation of the exact deployed
  checkout with all route-certification variables removed advertised no
  authoring models. A Luna authoring request returned HTTP 422 before provider
  dispatch with `authoring model route is not currently certified`.
- Advertising enforcement: `/api/config` obtains authoring choices from the
  current certified route catalog. The default is Luna; Terra remains a
  separately certified selectable route.

## Browser consumption

A fresh public Chromium session at 1440 x 1000 rendered the authoring entry
screen with:

- the heading `Describe the coordination problem you want to explore.`;
- an editable natural-language input;
- an enabled `Generate editable configuration` action;
- no horizontal overflow;
- zero console errors and zero failed requests.

A second fresh session opened the retained deep link and rendered the edited
title, final gate, two round controls, message recipients, six person decisions,
the 8-node/10-edge graph, and interpretation limits. It also had no horizontal
overflow, console errors, or failed requests.

This is a technical UI-consumption observation, not evidence that Waltzman or
another first-time stakeholder will find the interface useful without further
feedback.

## Exact public entry points

Recommended authoring entry:

<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=create>

Retained completed example:

<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=create&draft=draft_68240a512235&authored_run=run_ffe88e1c15d5>

Machine-readable evidence:

```bash
curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/config

curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/authoring/drafts/draft_68240a512235

curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/runs/run_ffe88e1c15d5

curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/runs/run_ffe88e1c15d5/summary
```

## Deployment and artifact identity

- The target checkout reports revision
  `e563a93f4369d63480c9134bce436757d3893c64`.
- The public `/api/config` reports the same exact revision and
  `live_authorized: true`.
- The public JavaScript and CSS are byte-identical to that revision.
- The LaunchAgent reports `state = running`.
- The previous deployment remains recoverable at Git ref
  `refs/deployments/waltzman-public-pre-e563a93` and LaunchAgent backup
  `~/Library/LaunchAgents/com.cybernetic-influence.waltzman-public.plist.pre-e563a93`.

SHA-256:

- HTML: `ec93911a4fb9a478bdcf8e2a19481f2018d80e3d9bb81f647389fa9d839a1cbd`
- JavaScript:
  `fb2bddb44640d6c32e22a6f66f7ddb0fce15ce32678f98b62d9fd25c229014eb`
- CSS: `9476df4edef254426d7122cbd58a63c02bc0d955555011395290a489fc5aabbb`
- Public configuration:
  `75c3ce4ebf459ca7cfec74ae05073b21a93f94172657a5fa892e00db6bf97e4d`
- Approved draft:
  `edcd19ce3110edf16115d338519361a1b9db5098e22808ab3589d37367793cc1`
- Retained run:
  `d7cb9e4b1307cff914ce1d5391a3dec0f64872b767ec2199788434a9bd7a77eb`
- Public summary:
  `632024b697f7ef16f2f3e41b3bba0302b25f7782f163f382d063d11beff748df`
- Authoring-entry screenshot:
  `02f3c8b52646362cce8047ad5305136c6270f986793cae9225a0d26d621bd79a`
- Retained-result screenshot:
  `cb7604e20d7007f22b2b61ca1c77088dcd17b89a1d8ed76a55f2ce2dbe0d845a`

## Invalidation inputs and unresolved boundary

This verdict becomes stale if the simulator source, public UI/API schema,
authoring prompt (`scenario_draft.v8`), typed proposal schema, component
registry, compiler, participant prompt, shared-client revision, model-route
certification, LaunchAgent configuration, public run store, Funnel mapping, or
public DNS/TLS target changes.

The public authoring surface remains deliberately bounded. It can compile and
run the reviewed `influence_network_v1` family and the other advertised
templates; it does not yet turn arbitrary prose into arbitrary executable world
mechanics. The UI exposes that boundary rather than silently inventing support.
