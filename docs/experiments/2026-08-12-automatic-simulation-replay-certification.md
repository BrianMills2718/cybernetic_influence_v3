# Automatic retained-simulation replay certification

Observed on 2026-08-12 for the public Coordination Environment Lab.

## Verdict

- Capability ID: `cybernetic-influence.automatic-retained-simulation-replay`
- Advertised action: list every retained completed simulation and open any one
  through a shared step-by-step replay whose node and directed-edge key adapts
  to the evidence in that run.
- Target: `Bs-Mac-mini.local`, LaunchAgent
  `com.cybernetic-influence.waltzman-public`, and
  <https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=simulations>.
- Deployed revision: `cae8dbc6338e0dc924410773b8b1a3f010aa993b`.
- Evidence level: `deployment_verified` for retained completed runs exposing
  the current summary and canonical network contracts.

This technical certification does not establish arbitrary-world authoring,
fresh provider execution, stakeholder comprehension, human fidelity, or the
scientific validity of a retained simulation.

## Valid deployed behavior

The public run inventory contained 37 records, of which 29 were completed. The
Simulations page rendered exactly those 29 completed runs. New execution was
not required: opening a replay is a read-only summary request with one terminal
HTTP response.

Two structurally different retained runs exercised the shared path:

| Run | Structure | Replay evidence |
| --- | --- | --- |
| `run_ffe88e1c15d5` | Authored city-election influence network | 7 scenes; source, information, person, and mechanism nodes; directed issue, delivery, and decision-contribution edges |
| `run_37bc6e802787` | Coordination-decision causal world | 13 scenes; source, information, person, thing, and mechanism nodes; seven canonical connection, information, mechanism, and observation edge types |

Both returned `simulation-replay.v1`. Every projected edge in both summaries
reported `directed: true`. The second run therefore demonstrates that the UI is
not relying on the influence-network fixture or a scenario-specific walkthrough.

## Browser consumption

A fresh Chromium session at 1440 by 1000 pixels:

- loaded all 29 completed-run choices;
- opened the 7-step influence replay;
- advanced its replay and observed its run-specific graph key;
- switched to the 13-step coordination replay and observed a different key;
- reloaded the coordination deep link with the selected run preserved; and
- produced no unexpected console error, page error, or failed request.

A fresh 390 by 844 pixel session opened the influence deep link, advanced the
replay, kept the catalogue and Next action visible, and contained the graph
within a 319-pixel-wide box inside the viewport. The rendered page was inspected
from the retained screenshot.

The browser audit initially detected invalid `NaN` SVG geometry while switching
between runs. Revision `cae8dbc` corrected the lifecycle boundary by unmounting
the React graph before hiding or replacing it. The complete browser sequence
then passed with zero unexpected errors.

## Negative controls

- `GET /api/runs/not-a-run/summary` returned HTTP 422 and `invalid run ID`.
- `GET /api/runs/run_000000000000/summary` returned HTTP 404 and `run not found`.
- The missing-run deep link displayed `Retained simulation unavailable` and did
  not silently substitute another replay.

## Deployment identity and rollback

`/api/config`, the target checkout, and the LaunchAgent environment all report
`cae8dbc6338e0dc924410773b8b1a3f010aa993b`. The service reports `state =
running`, `live_authorized: true`, and Luna as the default authoring model.

The immediately prior deployment is retained at:

- Git ref `refs/deployments/waltzman-public-pre-cae8dbc`;
- LaunchAgent backup
  `~/Library/LaunchAgents/com.cybernetic-influence.waltzman-public.plist.pre-cae8dbc`.

Public bytes matched the deployed checkout:

- HTML: `52b87f7044248e1a27e3b1d4c38d961e75af14230dc80a8d354cfbbd0dc87b67`
- application JavaScript: `5adaf3f402fcf37fa267f7d18c25b1452d3b4cf543f3ee5f4094ea168e8f92c0`
- graph JavaScript: `a3b19280c68b804e288741e86004b7b3f18d3e52bd5ca6db42b14e0770683eb8`
- application CSS: `cf04cf7075e242ca03948fd414fa2a92cb2743d08cfcc50a12338df5de03eb71`

## Invalidation boundary

This record becomes stale if the source revision, summary or replay contract,
canonical network projection, public run store, UI assets, LaunchAgent, Funnel
mapping, or public DNS/TLS target changes. Failed, interrupted, and in-progress
runs are intentionally excluded from the catalogue until they complete.
