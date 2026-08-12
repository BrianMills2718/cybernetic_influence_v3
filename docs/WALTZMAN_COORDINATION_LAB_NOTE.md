# From Minds to Coordination: an executable mechanism demonstration

Brian Mills · August 2026

## Question

*From Minds to Coordination* argues that influence can impair collective action
without installing one shared false belief. Heterogeneous, locally plausible
signals can instead alter a group’s decision environment: authority becomes
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

Twenty-six autonomous LLM roles represent four countries and a regional
institution deciding whether to activate a cross-border early-warning compact.
They make three independent decisions, each retaining a stance, primary risk,
requested next step, and rationale. A fixed coalition gate determines whether
the compact is executable.

In three conditions, four additional LLM agents operate as external sources for
technical evidence, legal authority, logistics, and community legitimacy. After
each public coalition round, every source independently chooses whether its
domain calls for verification or escalation. The simulator retains all four
outputs before delivering a complete, locally adapted signal bundle to the
coalition. The sources cannot vote, recommend a vote, write a participant’s
stance, or modify the decision gate.

The same 26-role configuration, model, reasoning setting, and decision rule are
used for the configuration-matched quartet:

| Environment | Round 1 | Round 2 | Round 3 | Outcome |
| --- | --- | --- | --- | --- |
| Baseline | 26 support | 26 support | 26 support | Approved |
| Autonomous source pressure | 26 support | 3 support, 17 conditional, 6 defer | 17 conditional, 9 defer | Not approved |
| Pressure plus verified compact package | 26 support | 2 support, 21 conditional, 3 defer | 26 support | Approved |
| Pressure plus adaptive CSO cell | 26 support | 2 support, 21 conditional, 3 defer | 26 support | Approved |

Retained runs: `run_ef3763b4d477`, `run_3303c9302a36`,
`run_e2f31904e10b`, and `run_a27f8e4082ef`. Their canonicalized configuration
SHA-256 is identical:
`d6242eac5ae7d85ce74bd6ddc99f8002f77702eb7e99f99ed6e76bd96fc8ce0d`.

The source agents made bounded, heterogeneous choices from the reviewed
developments. Under pressure, the first source phase contained three
verification selections and one escalation; the second contained two of each.
Technical, sovereignty, capacity, and legitimacy requirements accumulated into
a jointly blocking set. The coalition did not reject the shared objective; by
the final round, none of the 26 roles considered the compact executable
immediately.

The stabilization condition kept the autonomous source process active. Its
first phase also contained three verification selections and one escalation;
its second contained two of each. After round two, a verified cross-domain
package clarified evidentiary standards, bounded data and
access authority, assigned staff and supplies, protected national reserves, and
specified reciprocal community safeguards. All 26 roles then returned to
support. The intervention did not instruct them how to vote; it made their
minimum requirements mutually compatible.

The adaptive condition replaces that preselected intervention with three
autonomous CSO roles. After round two, a monitor classified trust structure as
fragmented, perceived risk as high, and coordination readiness as blocked. A
diagnostician identified coalition-wide incompatible requirements across
dimensions. A stabilization planner then selected one action from a reviewed
six-action catalog: the cross-domain compact. Only the selected external facts
reached participants; the internal detection and diagnosis did not. The final
coalition round again ended with 26 support positions. The complete run retained
89 successful model calls and cost $0.54746685.

One retained role illustrates the mechanism. Under source pressure, the Alba
epidemiologist offered only conditional support because national data custody,
foreign-team limits, and visible national command remained unresolved. After
the verified package supplied those conditions—along with protected laboratory
capacity and a 72-hour review—the same role supported immediate activation.

## Relationship to the paper

The demonstration operationalizes three especially concrete claims from the
paper:

1. **Collective effects need not require coherent content.** Four distinct
   domains produced different local concerns but one directional coalition
   effect.
2. **Segmented local equilibria can impair joint action.** Each role’s
   requirements remained intelligible within its mandate while the combined
   requirements became incompatible.
3. **The proposed detect–diagnose–stabilize cycle can be made executable.** In
   the adaptive condition, distinct model roles observed the shift, diagnosed
   the mechanism, and selected a bounded response before coalition members
   independently reassessed their positions.

The result is strongest as a demonstration of coordination readiness and
constraint compatibility. It is weaker as evidence about private trust, which
the simulation does not directly measure.

## Limits and proposed discussion

This is one fictional scenario with synthetic LLM behavior and one stochastic
trajectory per environment. Autonomous source choices can differ between runs,
so this is not a pure intervention-only counterfactual.
It does not estimate effects in people, establish
hostile intent, validate the paper’s state variables, or show that the same
direction generalizes across contexts. The source agents are domain-bounded and
observe public coalition feedback; they are not an unconstrained influence
system. The CSO labels are model judgments inside the simulation, not validated
measurements of Waltzman’s proposed state variables, and one successful
intervention selection does not establish a reliable stabilization policy.

What the tool contributes is an inspectable experimental substrate: roles,
information paths, source adaptation, decision rules, interventions, prompts,
and outputs are retained rather than collapsed into a narrative summary. The
useful question for discussion is whether this is a faithful minimal
operationalization of the paper’s mechanism—and which scenario, observable, or
stabilization test would make the next experiment genuinely informative.
