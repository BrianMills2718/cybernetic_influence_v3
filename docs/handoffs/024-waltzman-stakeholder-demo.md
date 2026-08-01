---
doc_role: execution_handoff
authority: packet_24e
status: local_review_ready_private_deployment_pending
updated: 2026-08-01
implementation_commit: bf20cf0f888eda1237149cbec0bc9846546e3fdb
---

# Waltzman Stakeholder Demo

## Outcome

The demo now makes one modeled trajectory legible as an implementation of
Waltzman-relevant ideas. It leads with the result, keeps trust structure,
perceived risk, and coordination readiness separate, connects the trajectory
from information pressure through individual response and a changed
coordination rule to the collective outcome, and links claims to exact retained
events. The full findings, maps, narrative, participant accounts, Levin view,
and advanced evidence remain available.

The surface states its boundary visibly: this is an inspectable synthetic
implementation, not a validated detector, proof of real-world causation, or a
prediction of institutional behavior.

## Review surfaces

- Local retained demo:
  <http://127.0.0.1:8620/?run=run_7624eb5f9278>
- Shareable 28-second screen walkthrough:
  [waltzman-demo-walkthrough.webm](../assets/waltzman-demo-walkthrough.webm)
- Shareable result card:
  [waltzman-demo-walkthrough.png](../assets/waltzman-demo-walkthrough.png)
- Canonical private surface after deployment:
  <https://brian-mac-mini.tail9c321e.ts.net:8620/?run=run_eded0f70b15f>

The local service reports build
`bf20cf0f888eda1237149cbec0bc9846546e3fdb`; its demo run is completed,
provider-free, ended `scope_reduced`, retained both theory modules, and used
zero model calls. The private Mac was unreachable over both HTTPS and SSH at
handoff time, so its current service has not yet been updated.

## Three-minute walkthrough

1. Read the initial situation: five participants are deciding whether and how
   to deploy a multinational bio-surveillance capability.
2. Scan the concise trajectory and outcome: the partnership ultimately accepts
   a smaller deployment.
3. At **What this simulation demonstrates**, read the modeled-result paragraph
   and the three construct cards.
4. Follow the four-step trajectory: risk record, independent verification,
   changed action threshold, reduced-scope collective result.
5. Expand **Inspect supporting events** under any step and select the cited
   event. The interface opens the exact moment in Advanced evidence.
6. Read **What this does not establish**, then open all 16 Waltzman findings if
   Waltzman wants to dispute an operationalization or inspect its uncertainty.

The useful stakeholder question is not whether the simulation predicts a real
institution. It is where this concrete implementation of information pressure,
individual response, trust/risk/readiness, and collective action faithfully or
unfaithfully represents the theory—and what materially different scenario or
mechanism should be demonstrated next.

## Verification

- `37 passed` in `tests/test_api.py`.
- `node --check web/app.js` and `git diff --check` passed.
- The desktop browser verifier passed the authored-run deep link, walkthrough
  content and ordering, exact-event step-down, all three graph projections,
  concise and detailed narrative, participant and group views, both composites,
  service-desk preview, pause/resume, console, and failed requests.
- A fresh local canonical-service browser open showed the walkthrough with no
  console error.
- `scripts/capture_waltzman_demo.py` reproduced the silent 28-second WebM and
  result-card PNG from the real deep-linked run with no console or failed-request
  error. Representative frames were visually inspected at the initial
  situation, Waltzman readout, exact-event step-down, and final limitations.

## Private deployment resume event

When the Mac responds again, deploy canonical `main`, which contains
implementation commit `bf20cf0f888eda1237149cbec0bc9846546e3fdb`, using
[Mac Mini Development Host](../operations/mac-mini.md), restart the LaunchAgent
with the exact deployed `main` commit recorded, and reopen retained run
`run_eded0f70b15f`. Require `/api/config` to report the exact commit and rerun
the desktop verifier against that retained run. Do not make a provider call or
change the retained run.
