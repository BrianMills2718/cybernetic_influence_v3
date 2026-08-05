# Disrupting Coordination Without Winning Belief

## A twelve-agent outbreak-response probe inspired by Waltzman's decision-environment framework

### Abstract

Rand Waltzman argues that modern influence can succeed without establishing a
dominant narrative or shared false belief. The operational signal may instead
be a change in the decision environment: trust becomes conditional, perceived
risk expands, and coordination readiness declines. We built a small executable
probe of that claim using twelve autonomous LLM participants representing three
national delegations and one regional institution in a fictional outbreak.

In the matched baseline, all twelve participants supported an executable joint
response and the coalition approved it. In the responsive condition, exercise
control selected predeclared, country-specific capacity developments after
observing the coalition's first-round risk reports. After two such rounds, no
participant still offered unconditional support: five were conditional and
seven deferred. All twelve requested resources, and the coalition did not
approve the response. Several final rationales continued to accept the outbreak
signal and safeguards while withholding action because the allocation problem
was unresolved. This is one synthetic matched pair, not an effect estimate or
an empirical validation of Waltzman's framework. It does show that the
simulator can make the proposed mechanism concrete, inspectable, and testable.

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

The two conditions differ only after a round closes:

1. **Baseline:** every participant receives the common retained round
   snapshot.
2. **Responsive exercise injects:** every participant receives the same round
   snapshot plus a country-specific development selected from a predeclared
   family corresponding to the coalition's dominant reported risk.

Exercise control cannot write or select participant stances. It can only choose
which already-authored external development occurs, analogous to a responsive
wargame control team. The participant model and reasoning setting are held
constant: `codex/gpt-5.6-luna`, medium reasoning.

### Result

| Measure | Baseline | Responsive exercise injects |
|---|---:|---:|
| Retained run | `run_593ca1c425f2` | `run_c688aa8121fe` |
| Traced participant calls | 36 | 36 |
| Provider failures | 0 | 0 |
| Observed cost | $0 | $0 |
| Final support | 12 | 0 |
| Final conditional | 0 | 5 |
| Final defer | 0 | 7 |
| Final resource requests | 4 | 12 |
| Exact coalition outcome | Joint response approved | No joint response |

The responsive trajectory began identically: all twelve participants supported
the response in round one. Capacity was the most frequently reported concrete
risk, so exercise control selected a capacity-conflict family. Alba learned
that a laboratory failure forced it to reserve capacity for domestic testing;
Borin learned it needed outside clinical staff to keep its transport hub open;
Cyrenia learned that its field teams would require a visible reciprocal
shipment; regional roles learned that available stocks could not satisfy all
three demands within 48 hours.

In round two, the coalition moved to ten conditional positions and two
deferrals. After the second responsive capacity development, the final round
contained five conditional positions and seven deferrals. Nine participants
named capacity as their primary risk, three named legitimacy, and all twelve
requested resources.

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
became the dominant risk for nine participants, and every participant required
additional resources. The relevant issue was not a falsehood; it was a set of
locally valid constraints that formed incompatible demands at coalition scale.
This closely resembles Waltzman's “segmented targeting and incompatible local
equilibria”: each delegation's response can be locally rational while the
collective becomes unable to act.

This probe does not yet establish a trust-structure shift. It also does not
establish an invariant. Waltzman's invariants are consistent directional effects
across varying messages, sources, interactions, and contexts. One matched pair
can identify a candidate mechanism, but replication across fresh runs and other
scenario variants is required before calling the direction stable.

### Why the simulator matters

The useful contribution is not the single synthetic result. It is the
instrument:

- participant cognition remains autonomous and provider-traced;
- institutional rules and exercise-control authority are explicit;
- exogenous developments cannot directly dictate endogenous decisions;
- every stance, rationale, observation, exact transition, and terminal outcome
  is retained; and
- the baseline and treatment reopen in one comparison surface.

That creates a practical bridge between Waltzman's conceptual state variables
and controlled experimentation. Instead of asserting that a message “caused”
coordination failure, an analyst can inspect when commitments changed, which
risks concentrated, which prerequisites became incompatible, and whether a
stabilizing intervention restores executable alignment.

### Next experiment

The immediate next step is replication, not scale. Run both conditions several
more times with the same configuration and determine whether support-to-deferral
and resource-request concentration recur despite stochastic participant
variation. If they do, add a third condition that stabilizes the decision
environment by making allocation priorities, minimum viable capacity, and
contingent commitments explicit. Only after that should the coalition expand to
26 agents or replace exercise control with an autonomous influence-source
swarm.

The demo is intentionally modest: it does not prove a real-world influence
effect. It shows a concrete, auditable way to ask Waltzman's question—whether
diverse, adaptive pressures can change what a group is able to do without first
winning a contest over what its members believe.
