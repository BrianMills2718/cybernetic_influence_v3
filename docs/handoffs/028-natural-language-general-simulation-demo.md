---
doc_role: implementation_handoff
status: implemented_not_deployed
created: 2026-08-13
source_plan: docs/plans/028-natural-language-general-simulation-demo.md
---

# Slice 28 handoff: natural-language general simulation demo

## Stakeholder path

Public entrypoint after deployment:

`/waltzman/?view=create`

Three actions for a Waltzman demo:

1. Describe a sociotechnical situation and research question in ordinary language, or load the relief-port example prompt.
2. Review compiler-generated execution coverage and directly change one person's character, one world-state value, one information recipient, or one scheduled time.
3. Approve and run with Luna, then use the automatically generated walkthrough and evidence view to inspect observations, intents, transactions, validation outcomes, and the Waltzman-informed diagnostic projection.

## Implemented production seam

```text
ordinary language
→ GeneralSimulationProposalV1
→ trusted registry resolution + ExecutionCoverageReportV1
→ retained typed review/edit/approval
→ stock Concordia Simultaneous engine
→ authorized actor contexts at one frozen revision
→ one joint Luna transition authority
→ typed WorldTransaction + canonical validation/commit
→ retained checkpoint, traces, generic graph, walkthrough, and analysis
```

The `general_simulation` package does not import or execute
`ActiveRuntimeSession` or `CausalSession`. Historical workflows retain their
existing runtime for compatibility; they are not hidden inside the Concordia
path.

## Evidence obtained

- Desktop and mobile first-screen authoring controls were observed in a real browser.
- A browser direct edit changed person character, world state, information recipients, and timing from retained revision 1 to revision 2 without a model call; coverage recompiled and no console error occurred.
- Provider-free API execution completed the port fixture with 4 actors × 3 moments plus 3 adjudications, retained three checkpoints, reopened through the summary endpoint, and generated replay scenes without additional calls.
- Authentic Luna service canary completed two actor calls plus one joint adjudication on the production schemas.
- Authentic Luna port execution completed all 15 calls on the stock simultaneous engine. One transaction committed; two were visibly rejected by generic validation. Trace prefix: `slice28_authentic_port_full_v2/general/`.
- Authentic Luna service execution completed all 6 calls through the same compiler, runner, world, and receipt. One transaction committed; one was visibly rejected. Trace prefix: `slice28_authentic_service_full/general/`.

## Interpretation boundary

The demonstrations establish that the mechanism can execute and remain
inspectable under the configured assumptions. They do not establish predictive
validity, human realism, a stable stochastic transition law, a temporal
invariant, or causal effects outside the retained synthetic trajectory.

The Waltzman-informed projection reports only transparent diagnostic signals:
configured broadcast/targeted exposure, literal source mentions, actor-stated
risk rationales, named dependencies, and a bounded coordination-readiness
signal. Every finding retains method, evidence references, uncertainty, and a
limitation.

## Known gaps

- A structurally invalid but semantically plausible Luna transaction is rejected rather than automatically repaired in the same moment.
- A failed run retains the last checkpoint and explicit resume boundary, but a public one-click checkpoint-resume action is not yet implemented.
- The current generic affordance model is delegated partly to the bounded Luna adjudicator; it is not an exhaustive capability/affordance resolver.
- Exact provider cost was not available for Codex subscription calls; call traces and configuration identity are retained.
- Deployment and exact public-build verification remain separate operator actions.

## Recommended next engineering move

Add one bounded adjudicator-repair attempt using validator errors and the
unchanged base revision, then test it against the retained port and service
failure shapes. This would improve run completion quality without adding a
domain template or weakening generic invariants.
