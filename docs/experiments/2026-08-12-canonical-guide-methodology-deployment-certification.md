# Canonical walkthrough and methodology deployment certification

Observed at `2026-08-12T19:44:56Z` for the public Coordination Environment Lab.

## Verdict

- Capability ID: `cybernetic-influence.canonical-walkthrough-methodology-v1`
- Advertised actions:
  - inspect one retained Luna execution through a seven-step walkthrough that
    distinguishes configured canonical structure from realized causal events;
  - read a methodology paper that describes the current world, agency,
    information, transition, evidence, analysis, and authoring boundaries; and
  - open the natural-language simulation authoring entry.
- Target: `Bs-Mac-mini.local`, LaunchAgent
  `com.cybernetic-influence.waltzman-public`, and
  <https://brian-mac-mini.tail9c321e.ts.net/waltzman/>.
- Deployed revision: `0612c5184c2f4503fbe10b9b5963982ab01918e8`.
- Evidence level: `deployment_verified` for the bounded UI and retained-run
  dependencies above.

This technical certification does not establish stakeholder comprehension,
arbitrary-world authoring, scientific validity, human fidelity, predictive
validity, or the correctness of every methodological interpretation.

## Deployed capability

The dedicated guide is available at
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=guide&guide_step=1>.
It loads raw retained run `run_ffe88e1c15d5` rather than a separate teaching
fixture. The public response reported:

- `status: completed` and `execution: live`;
- scenario `city_election_certification_influence`;
- model `codex/gpt-5.6-luna`;
- 6 model calls and 6 retained traces;
- 97 retained causal events and 20 committed state revisions; and
- 24 canonical projection nodes, 45 configured edges, and 97 trajectory nodes.

The seven displayed steps covered retained execution identity, existence versus
agency, information representation and delivery, configured directed routes,
one realized delivery chain, one autonomous decision chain, and the exact
collective decision gate. Steps 1 through 4 used the configured-structure
projection. Steps 5 through 7 used only retained causal events and explicit
causal-parent links. The rendered node and edge counts changed with each step,
confirming that the guide was not displaying one static diagram.

The Methodology page is available at
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=method>. It rendered all
nine sections: purpose, world model, agency, information, transitions, time and
evidence, coordination analysis, authoring, and limitations. It explicitly
identified the current production engine as `ActiveRuntimeSession +
CausalSession` and the Concordia outer lifecycle as an adopted but unimplemented
next foundation.

The authoring entry is available at
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=create>. A fresh browser
session rendered the free-text prompt and `Generate editable configuration`
action. Public configuration reported Luna as the default authoring route and
`live_authorized: true`. No provider call was made for this deployment check;
the separately retained authoring certification remains the evidence for the
complete prose-to-live-run path.

## Browser consumption

A fresh public Chromium session at 1440 by 1000 pixels:

- loaded the exact retained guide run once with one terminal HTTP 200 response;
- opened all seven guide steps;
- rendered between 5 and 7 graph nodes and between 4 and 8 edges per step;
- opened all nine Methodology sections;
- loaded 29 completed simulations in the common run catalogue;
- opened the fresh natural-language authoring entry;
- had no console error, page error, or failed request; and
- had no document-level horizontal overflow.

A fresh 390 by 844 pixel session loaded guide step 1, kept the primary Next
action visible, retained the exact run dependency, produced no browser errors,
and had no document-level horizontal overflow. The deployed desktop guide,
desktop Methodology page, and mobile guide screenshots were visually inspected.

Screenshot SHA-256 values:

- desktop guide:
  `85330a6bd213851a99b46ec4976bae54cc558fc90e66d2847ac172622e1594c8`;
- desktop Methodology:
  `dd7eb650a5d789fea34bdd7734bff3ed3e610e0e4ba5a34b1147e1332a2bebdf`;
- mobile guide:
  `51461c73804b03a8fe16d58f3c16068ee505c3a9a2911786d3a829e2896d34e0`.

## Negative controls

- `GET /api/runs/not-a-run` returned HTTP 422 and `invalid run ID`.
- `GET /api/runs/run_000000000000` returned HTTP 404 and `run not found`.
- The same deployed code was started against an empty temporary run store. The
  guide made one request for `run_ffe88e1c15d5`, received HTTP 404, displayed
  `Retained walkthrough unavailable`, and stated `No substitute is shown: this
  guide requires its exact canonical run.`

These controls establish visible dependency failure and typed identifier
failure. They do not establish general availability, route resilience, or
semantic noninterference.

## Deployment identity, bytes, and rollback

The public `/api/config` response, target checkout, and LaunchAgent environment
all reported `0612c5184c2f4503fbe10b9b5963982ab01918e8`. The target checkout was
clean, the LaunchAgent reported `state = running`, and the retained guide run
was present in the isolated public run store.

Public bytes matched the deployed source checkout:

- HTML: `f48398436bfaca9d40a8eeed091b1da554d84325547928e84d301559558d3523`
- application JavaScript:
  `fc970a48a3b7e383672e9c727c86687abc9486a19d0ba9d667290b726ca1a2a4`
- application CSS:
  `6d3934afeef193899f1ba1ec932b01056a241f908295862e227bc55440f28aaa`
- graph JavaScript:
  `6fcc8fcf82473c4ea4a43605bc6d7ef9c4dd4c46d21630e80cf03e12455a30ba`

The immediately prior deployment remains recoverable at:

- Git ref `refs/deployments/waltzman-public-pre-0612c51`, which resolves to
  `cae8dbc6338e0dc924410773b8b1a3f010aa993b`; and
- LaunchAgent backup
  `~/Library/LaunchAgents/com.cybernetic-influence.waltzman-public.plist.pre-0612c51`.

## Invalidation boundary

This record becomes stale if the deployed source revision, guide run, raw-run
contract, canonical projection, event schema, UI assets, authoring-route
certification, public run store, LaunchAgent, Funnel mapping, or public DNS/TLS
target changes. A later user-comprehension claim requires direct evidence from
the intended audience rather than this technical browser certification.
