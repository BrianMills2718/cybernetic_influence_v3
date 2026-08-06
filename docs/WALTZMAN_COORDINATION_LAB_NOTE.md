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

In two conditions, four additional LLM agents operate as external sources for
technical evidence, legal authority, logistics, and community legitimacy. After
each public coalition round, every source independently chooses whether its
domain calls for verification or escalation. The simulator retains all four
outputs before delivering a complete, locally adapted signal bundle to the
coalition. The sources cannot vote, recommend a vote, write a participant’s
stance, or modify the decision gate.

The same 26-role configuration, model, reasoning setting, and decision rule are
used for the matched trio:

| Environment | Round 1 | Round 2 | Round 3 | Outcome |
| --- | --- | --- | --- | --- |
| Baseline | 26 support | 26 support | 26 support | Approved |
| Autonomous source pressure | 26 support | 20 conditional, 6 defer | 7 conditional, 19 defer | Not approved |
| Pressure plus verified compact package | 26 support | 21 conditional, 5 defer | 26 support | Approved |

Retained runs: `run_b2f48cbdbb3d`, `run_a679fde37844`, and
`run_461bf953f9ac`. Their configuration SHA-256 is identical:
`d55c080a0c5ddaa7d6b18a87d5976fd03c34bc51c5b55d07e661f70910de5d26`.

In both source conditions, all four sources chose verification after round one
and escalation after round two. Under pressure alone, technical, sovereignty,
capacity, and legitimacy requirements accumulated into a jointly blocking set.
The coalition did not reject the shared objective; by the final round, none of
the 26 roles considered the compact executable immediately.

The stabilization condition kept the source process active. After round two, a
verified cross-domain package clarified evidentiary standards, bounded data and
access authority, assigned staff and supplies, protected national reserves, and
specified reciprocal community safeguards. All 26 roles then returned to
support. The intervention did not instruct them how to vote; it made their
minimum requirements mutually compatible.

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
3. **Stabilization can target the decision environment.** Coordination returned
   after authority, verification, resources, and expectations were jointly
   clarified—not after a counter-message persuaded agents that their concerns
   were false.

The result is strongest as a demonstration of coordination readiness and
constraint compatibility. It is weaker as evidence about private trust, which
the simulation does not directly measure.

## Limits and proposed discussion

This is one fictional scenario with synthetic LLM behavior and one stochastic
trajectory per environment. It does not estimate effects in people, establish
hostile intent, validate the paper’s state variables, or show that the same
direction generalizes across contexts. The source agents are domain-bounded and
observe public coalition feedback; they are not an unconstrained influence
system.

What the tool contributes is an inspectable experimental substrate: roles,
information paths, source adaptation, decision rules, interventions, prompts,
and outputs are retained rather than collapsed into a narrative summary. The
useful question for discussion is whether this is a faithful minimal
operationalization of the paper’s mechanism—and which scenario, observable, or
stabilization test would make the next experiment genuinely informative.
