# From Minds to Coordination: an executable mechanism demonstration

Brian Mills · August 2026

## Question

*From Minds to Coordination* argues that influence can impair collective action
without installing one shared false belief. Heterogeneous, locally plausible
signals can instead alter a group's decision environment: authority becomes
conditional, the relevant risk set expands, and individually reasonable
requirements become difficult to satisfy together. The paper proposes watching
directional changes in trust structure, perceived risk, and coordination
readiness—and stabilizing the decision environment rather than merely rebutting
content.

We built a synthetic, executable version of that mechanism. The purpose is not
to validate the framework against human institutions. It is to make the causal
story configurable, observable, and falsifiable inside a controlled multi-agent
simulation.

Research case:
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=case>

## Demonstration

Twenty-six autonomous LLM roles represent four countries—Alba, Borin, Cyrenia,
Darsia—and a regional coordination network deciding whether to activate a
cross-border early-warning compact. Activation requires comparable evidence,
lawful data access, staff, laboratories, supplies, transport, funding, and
credible local safeguards. No single role or organization controls all of them.
A fixed coalition gate determines whether the compact is executable: at least 13
support positions, at least 20 support-or-conditional, and no more than 2
opposed.

Local pressures enter through separately relevant channels—laboratory failures,
staffing demands, supply constraints, legal challenges, contested evidence,
community concerns. The messages do not repeat one narrative. After two rounds
the coalition has not rejected the shared objective; it has become jointly
unable to act. Twenty-three roles will proceed only conditionally, three defer,
and no role supports activation outright.

## The controlled comparison

We saved the simulation at exactly that point and continued it four ways. Every
agent, memory, prior message, world state, model, prompt, and approval rule is
identical when the four continuations begin. The only variable is the resource
package that arrives after round two.

| Continuation | Commitments | Verification | Final stances | Outcome |
| --- | --- | --- | --- | --- |
| No package | 0 | absent | 21 defer, 5 conditional | not approved |
| Partial resources | 2 | verified | 23 conditional, 3 defer | not approved |
| Complete resources | 6 | verified | 24 conditional, 2 defer | not approved |
| False claims | 6 claimed | contradicted | 21 defer, 5 conditional | not approved |

Shared checkpoint digest
`390dd40850fa118d89c673a37da925f7ab9d85adf31c75cba35fe5fc289e71ad`, reached
after 56 model calls. The complete retained execution contains 26 agents, four
exact continuations, and 160 model calls at `codex/gpt-5.6-luna`, medium
reasoning, at subscription-included observed cost of $0.

No branch reached approval, and no branch produced a single outright support
position.

## What actually changed

The uniform outcome conceals the result. Real, verified resources moved *which*
constraint was binding rather than whether one was.

| Named top risk | No package | Complete resources |
| --- | --- | --- |
| Capacity | 24 | 9 |
| Evidence quality | 1 | 9 |
| Sovereignty | 0 | 5 |
| Legitimacy | 1 | 3 |

Requested next steps moved with it: requests for resources fell from 14 to 3,
while requests for safeguards rose from 0 to 12. Supplying the missing capacity
did not clear the path—it exposed legal-authority and evidentiary requirements
that had been present but not binding while capacity dominated. The partial
package sits between the two, retaining a capacity-dominated profile (17 of 26)
while beginning to surface evidence-quality concerns.

The false-claim branch is the sharper result. Six resource commitments were
claimed but the simulated audit contradicted the manifest. The coalition then
landed on the no-package profile exactly: the same 21 defer / 5 conditional
split, and all 26 roles naming capacity as their top risk. Within this
simulation, unsubstantiated claims of support were worth precisely what
providing nothing was worth.

## Relationship to the paper

The demonstration operationalizes three especially concrete claims from the
paper:

1. **Collective effects need not require coherent content.** Distinct local
   domains produced different concerns but one directional coalition effect.
2. **Segmented local equilibria can impair joint action.** Each role's
   requirements remained intelligible within its mandate while the combined
   requirements became incompatible.
3. **A stabilization attempt is testable, and can partially succeed.** The
   checkpoint fork isolates one intervention dimension and shows it resolving
   its own dimension without restoring readiness.

The result is strongest as a demonstration of coordination readiness and
constraint compatibility, and specifically of *layered* constraint structure. It
is weaker as evidence about private trust, which the simulation does not
directly measure.

## Limits and proposed discussion

This is one fictional scenario with synthetic LLM behavior and one trajectory
per continuation. Only the final-round continuations are checkpoint-paired, and
model sampling is not seeded, so branch differences are not a clean
intervention-only counterfactual at the token level. The packages and resource
mechanics are scenario-authored experiment controls, not discovered behavior. It
does not estimate effects in people, establish hostile intent, validate the
paper's state variables, or show that the same direction generalizes across
contexts.

What the tool contributes is an inspectable experimental substrate: roles,
information paths, decision rules, interventions, prompts, retained rationales,
and the fork point itself are retained rather than collapsed into a narrative
summary. The useful question for discussion is whether this is a faithful
minimal operationalization of the paper's mechanism—and which scenario,
observable, or stabilization test would make the next experiment genuinely
informative.

## Retained prior evidence

An earlier source-pressure quartet on the same 26-role configuration remains in
the public run store as `run_ef3763b4d477`, `run_3303c9302a36`,
`run_e2f31904e10b`, and `run_a27f8e4082ef`, sharing canonicalized configuration
SHA-256
`d6242eac5ae7d85ce74bd6ddc99f8002f77702eb7e99f99ed6e76bd96fc8ce0d`. In that
design four autonomous source agents introduced technical, legal, logistical,
and legitimacy signals between rounds, and a verified compact package restored
support. Those runs are retained tool demonstrations. The checkpoint fork above
supersedes them as the presented case because it holds the pre-intervention
state exactly constant rather than re-running the trajectory.

Earlier still, a twelve-agent outbreak probe was withdrawn as matched-condition
evidence when a 2026-08-05 audit found participant prompts disclosed the
condition identifier before round one. Those runs remain authentic historical
trajectories and are not used for comparison claims.
