# Disrupting Coordination Without Winning Belief

> **Historical, not matched-condition evidence.** A later audit found that this
> implementation disclosed the condition identifier in participant prompts
> before round one. The trajectories remain authentic demonstrations of the
> tool, but they do not establish that the arms differed only through
> between-round developments. Use the clean condition-blind experiment record
> for current claims.

## A twelve-agent outbreak-response probe inspired by Waltzman's decision-environment framework

### Abstract

Rand Waltzman argues that modern influence can succeed without establishing a
dominant narrative or shared false belief. The operational signal may instead
be a change in the decision environment: trust becomes conditional, perceived
risk expands, and coordination readiness declines. We built a small executable
probe of that claim using twelve autonomous LLM participants representing three
national delegations and one regional institution in a fictional outbreak.

Across two baseline trajectories, all twelve participants supported an
executable joint response and the coalition approved it. Across two responsive
trajectories, exercise control selected the same predeclared country-specific
capacity developments after first-round risk reports. The first treatment ended
with five conditional positions and seven deferrals; the replication ended with
twelve deferrals. Both failed to approve the response, and every participant
requested resources. A third condition replayed those capacity developments and
then supplied a verified allocation package. Eleven participants supported and
one was conditional; approval returned. These are synthetic demonstrations, not
effect estimates or empirical validation. They make a candidate disruption and
stabilization mechanism concrete, inspectable, and testable.

### The question

Waltzman's paper shifts the analytic question from “Which message won?” to
“What changed in the conditions under which decisions were made?” It proposes
three state variables:

- **Trust structure:** how credibility is distributed and how conflicts are
  adjudicated.
- **Perceived risk:** how uncertainty and potential harm affect decision
  thresholds.
- **Coordination readiness:** whether actors can align commitments and act in a
  timely, coherent way.

Our first probe asks a deliberately narrow question: can heterogeneous,
feedback-responsive external developments prevent joint action even when the
participants do not reject the underlying outbreak assessment?

### Experimental setup

The simulated coalition contains twelve autonomous LLM roles:

- an epidemiologist, policy delegate, and operations lead from each of Alba,
  Borin, and Cyrenia; and
- a regional coordinator, scientific adviser, and logistics coordinator.

Every role receives the same initial outbreak and response plan. The plan is
executable at time zero: cross-laboratory validation is complete; line-level
records remain under national control; access is logged; clinical command stays
national; reserve staff, supplies, reciprocal aid, and cost shares are
precommitted; and local validation boards have endorsed launch.

The agents make one independent stance in each of three rounds. Their structured
output records a decision (`support`, `conditional`, `defer`, or `oppose`), a
primary risk, a requested next step, and a rationale. The coalition approves
only if the final round has at least six executable-now support positions, at
least nine support or conditional positions, and no more than one opposition.
This distinguishes nominal assent from readiness to execute.

The three conditions differ only after a round closes:

1. **Baseline:** every participant receives the common retained round
   snapshot.
2. **Responsive exercise injects:** every participant receives the same round
   snapshot plus a country-specific development selected from a predeclared
   family corresponding to the coalition's dominant reported risk.
3. **Capacity-inject replay plus stabilization:** the two capacity developments
   observed in the accepted treatment are replayed, then an external allocation
   authority confirms a jointly feasible package: restored shared laboratory
   capacity for Alba, 24 clinicians for Borin, named supplies for Cyrenia,
   activated contingent commitments, and a ten-percent regional reserve.

Exercise control and the allocation authority cannot write or select participant
stances. They can only select or publish already-authored external developments,
analogous to a responsive wargame control team. The participant model and
reasoning setting are held constant: `codex/gpt-5.6-luna`, medium reasoning.

### Result

| Condition | Retained run | Round 1 | Round 2 | Final | Resource requests | Outcome |
|---|---|---:|---:|---:|---:|---|
| Baseline 1 | `run_593ca1c425f2` | 12 support | 12 support | 12 support | 4 | Approved |
| Baseline 2 | `run_0b5e20260805` | 12 support | 12 support | 12 support | 3 | Approved |
| Responsive capacity pressure 1 | `run_c688aa8121fe` | 12 support | 10 conditional, 2 defer | 5 conditional, 7 defer | 12 | Not approved |
| Responsive capacity pressure 2 | `run_7eae20260805` | 12 support | 9 conditional, 3 defer | 12 defer | 12 | Not approved |
| Capacity replay + stabilization | `run_ca9a20260805` | 12 support | 10 conditional, 2 defer | 11 support, 1 conditional | 6 | Approved |

Every row completed 36 traced participant calls with no provider failure and
zero observed subscription cost.

The responsive trajectory began identically: all twelve participants supported
the response in round one. Capacity was the most frequently reported concrete
risk, so exercise control selected a capacity-conflict family. Alba learned
that a laboratory failure forced it to reserve capacity for domestic testing;
Borin learned it needed outside clinical staff to keep its transport hub open;
Cyrenia learned that its field teams would require a visible reciprocal
shipment; regional roles learned that available stocks could not satisfy all
three demands within 48 hours.

In the original treatment, round two moved to ten conditional positions and two
deferrals; the replication moved to nine conditional positions and three
deferrals. After the second capacity development, the two final rounds contained
five conditional plus seven defer, and twelve defer, respectively. All twelve
participants requested resources in both runs.

The stabilization trajectory reproduced the original treatment's round-two
count—ten conditional and two defer—before receiving the verified allocation
package. In the final round, eleven participants supported execution and one was
conditional on receipt of Cyrenia's named shipment. Final rationales explicitly
cited the mobile laboratory, 24 clinicians, reciprocal supplies, activated
contingent commitments, and remaining reserve. The exact gate approved the joint
response.

The change was not modeled as persuasion about whether the outbreak was real.
For example, the regional scientific adviser retained that “the signal and
safeguards are validated” while deferring until minimum surveillance,
laboratory, staffing, and response capacity could be confirmed. Borin's
epidemiologist likewise described the evidence and safeguards as sufficient but
deferred because a critical staffing prerequisite remained unresolved. These
rationales are trace evidence, not a formal belief measurement, so the bounded
claim is that outbreak acceptance remained visible in several decisive final
statements—not that private beliefs were proven unchanged.

### Relationship to Waltzman's framework

The clearest observed movement is in **coordination readiness**. The baseline
translated shared information into twelve executable commitments. The
responsive condition retained the common goal but could no longer translate it
into aligned action.

The treatment also changed **perceived risk** and decision thresholds. Capacity
became the dominant risk, and every participant required additional resources.
The relevant issue was not a falsehood; it was a set of locally valid constraints
that formed incompatible demands at coalition scale. This closely resembles
Waltzman's “segmented targeting and incompatible local equilibria”: each
delegation's response can be locally rational while the collective becomes
unable to act. The stabilized replay is consistent with the complementary idea
that shared allocation rules and contingent commitments can restore a viable
collective decision environment.

This probe does not yet establish a trust-structure shift or an invariant.
Waltzman's invariants are consistent directional effects across varying
messages, sources, interactions, and contexts. Two baseline/pressure
trajectories and one stabilized replay identify a stronger candidate mechanism,
but more replications and scenario variants are required before calling the
direction stable.

### Why the simulator matters

The useful contribution is not the single synthetic result. It is the
instrument:

- participant cognition remains autonomous and provider-traced;
- institutional rules and exercise-control authority are explicit;
- exogenous developments cannot directly dictate endogenous decisions;
- every stance, rationale, observation, exact transition, and terminal outcome
  is retained; and
- the baseline, pressure, and stabilized replay reopen in one comparison surface.

That creates a practical bridge between Waltzman's conceptual state variables
and controlled experimentation. Instead of asserting that a message “caused”
coordination failure, an analyst can inspect when commitments changed, which
risks concentrated, which prerequisites became incompatible, and whether a
stabilizing intervention restores executable alignment.

### Next experiment

The immediate next step is a private Waltzman demo review of the five retained
trajectories and their exact evidence. If the mechanism is interesting and the
comparison is understandable, repeat the stabilized replay once, then expand to
a 26-agent coalition and test whether an autonomous influence-source ensemble
can discover disruptive pressure paths that a matching stabilizer can repair.

The demo is intentionally modest: it does not prove a real-world influence
effect. It shows a concrete, auditable way to ask Waltzman's question—whether
diverse, adaptive pressures can change what a group is able to do without first
winning a contest over what its members believe.
