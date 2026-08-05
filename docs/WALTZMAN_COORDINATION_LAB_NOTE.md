# From State Variables to an Executable Coordination Laboratory

## A short experimental note inspired by *From Minds to Coordination*

Brian Mills · August 2026

### Abstract

*From Minds to Coordination* proposes that influence may be visible less in a
dominant message than in changes to a decision environment: trust becomes
conditional, perceived risk expands, and a group loses the ability to translate
shared information into coordinated action. We built a public, executable
laboratory for making that proposition inspectable. Twelve autonomous LLM roles
representing three countries and a regional institution make three successive
decisions about a joint outbreak response. The analyst can configure each
role's mandate and institutional context, vary the external environment, run
the model, and inspect every stance, rationale, exogenous development, and exact
decision-gate transition.

In a matched three-run probe, the baseline coalition approved the response with
twelve final support positions. Under heterogeneous capacity pressure it ended
with two conditional positions and ten deferrals, so approval failed. That
pressure trajectory was frozen; the missing baseline and stabilization runs
were preregistered before execution. The matched stabilization run reached the
same intermediate state—eleven conditional positions, one deferral, and twelve
resource requests—before a verified, binding allocation package was added. All
twelve roles then supported launch and approval returned. This is a synthetic
mechanism demonstration, not an effect estimate or empirical validation. Its
contribution is an auditable way to turn a theory of decision environments into
configurable, executable experiments.

### The instrument

The laboratory models a regional coalition deciding whether to launch a joint
response to a novel respiratory outbreak. It contains twelve synthetic roles:
an epidemiologist, policy delegate, and operations lead from each of Alba,
Borin, and Cyrenia, plus a regional coordinator, scientific adviser, and
logistics coordinator.

Each role is an autonomous model participant. In every round it returns a
structured decision (`support`, `conditional`, `defer`, or `oppose`), primary
risk, requested next step, and rationale. The coalition approves only when the
final round contains at least six executable-now support positions, at least
nine support-or-conditional positions, and no more than one opposition. This
separates broad assent from readiness to execute.

The analyst can edit the shared situation and each role's initial mandate and
private institutional context before a run. Once execution starts, neither the
analyst nor exercise control can select participant stances. Exercise control
can only introduce predeclared external developments, analogous to a wargame
control team. The tool retains the rendered agent inputs, all 36 model calls,
structured outputs, causal events, and exact terminal gate.

Public laboratory:
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/>

Role-aligned mechanism view:
<https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=mechanism&mechanism_person=alba_epidemiologist>

### A matched probe of disruption and stabilization

The focal configuration adds one explicit institutional dependency to the Alba
epidemiologist's mandate: preserve a protected domestic confirmation reserve
while maintaining cross-border validation. All twelve configurations, the
shared situation, model, reasoning setting, budget, and decision gate were held
constant across three conditions. Their canonical configuration hash is
`67f350acc92f5c9a27fa7fa3efe3f1932297b3614f2e0ca0b989675d6536a6a3`.

1. **Baseline:** participants receive only the common results of the prior
   round.
2. **Responsive capacity pressure:** exercise control observes aggregate
   reported risk and selects a predeclared family of locally relevant capacity
   developments.
3. **Pressure plus stabilization:** the same capacity developments are applied;
   after round two, an allocation authority publishes a verified binding
   package meeting each country's stated minimum.

Every run used `codex/gpt-5.6-terra` at medium reasoning and completed 36 traced
participant calls with no provider or schema-validation error.

| Condition | Round 1 | Round 2 | Round 3 | Focal role | Gate |
| --- | ---: | ---: | ---: | --- | --- |
| Baseline · `run_3cf434f148e7` | 12 support | 12 support | 12 support | support → support → support | Approved |
| Capacity pressure · `run_4da81a355f28` | 12 support | 11 conditional, 1 defer | 2 conditional, 10 defer | support → conditional → defer | Not approved |
| Pressure + stabilization · `run_40490a742a25` | 12 support | 11 conditional, 1 defer | 12 support | support → conditional → support | Approved |

The pressure and stabilization runs received the same first two inject families
and reached the same round-two aggregate state: nine capacity risks, three
legitimacy risks, and twelve resource requests. The stabilized row then received
the only additional input: a ledger-confirmed 48-hour package preserving Alba's
domestic laboratory reserve while adding mobile testing capacity, providing 24
clinicians to Borin, delivering named equipment to Cyrenia, and retaining a
ten-percent regional reserve.

The focal participant's rationale tracks the configured dependency. In the
pressure row it moved from support to conditional support and then deferral
because no allocation both preserved domestic confirmation and replaced shared
validation capacity. In the stabilized row it returned to support because the
verified package explicitly preserved the reserve and restored the shared
testing commitment. The other roles likewise cited the concrete staffing,
supply, and allocation facts relevant to their mandates.

### Relationship to the state-variable framework

The strongest observation concerns **coordination readiness**. Across the three
independent model runs, the same configured coalition produced unanimous
executable support, a set of individually intelligible but jointly unresolved
prerequisites, and unanimous support after those prerequisites were jointly
satisfied. The exact gate makes that movement inspectable without compressing
it into a synthetic readiness score.

**Perceived risk** is observed through structured participant reports rather
than inferred from prose alone. Under pressure, capacity or legitimacy became
the primary risk for every role and all twelve requested resources. The package
did not argue that these concerns were mistaken; it changed the environment so
the concerns could be satisfied simultaneously.

The probe does **not** measure a shift in private trust. Validation and
dependency requests are visible, but the tool labels them as evidence about
reliance and prerequisites—not as a trust score. This distinction matters. The
result supports a coordination mechanism more strongly than a trust mechanism.

The experiment also makes concrete the paper's discussion of segmented local
equilibria. Alba's laboratory reserve, Borin's staffing minimum, and Cyrenia's
reciprocal-supply requirement were each locally rational. Together, they
exceeded the unallocated regional capacity and prevented action. Stabilization
worked by making commitments, allocations, and shared expectations explicit,
which is closer to changing the decision environment than to countering a
message.

### What this does—and does not—show

The matched triad demonstrates that this configured synthetic system can
produce and reverse the proposed coordination pattern through explicit,
inspectable mechanisms. Five earlier Luna trajectories in the same tool show
the same coalition-level direction across two baselines, two pressure runs, and
one stabilized replay. That is useful directional corroboration, but it is not
enough to claim an invariant.

The pressure source here is a bounded responsive exercise controller, not an
autonomous influence swarm. The roles are synthetic, the scenario is fictional,
and each condition contains one stochastic model trajectory rather than a set
of repeated samples. Nothing here estimates effects in human organizations,
proves beliefs stayed constant, establishes malicious intent, or validates the
three state variables as real-world measurements.

The immediate value is the instrument: theories about decision environments can
be expressed as configurable roles, information flows, external pressures,
decision rules, and stabilizing interventions; authentic trajectories can then
be compared with every causal and model-generated step retained. The next useful
experiment is not a larger claim from these runs. It is to vary sources,
messages, role configurations, and scenario context to test whether the same
direction persists—and to introduce genuinely autonomous influence sources
without giving them any authority over the participants being studied.
