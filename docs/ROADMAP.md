---
doc_role: active_authority
authority: canonical
status: active
created: 2026-07-23
updated: 2026-07-31
supersedes: comparison-centered roadmap at 0c91c418377a47185e40456eef77a67686f1f6ac
---

# Cybernetic Influence V3 Roadmap

## Outcome

For an analyst studying influence and multiscale agency, turn a bounded
organizational decision problem into a reviewable simulation configuration,
run one meaningful trajectory, and inspect:

- what happened;
- how the decision environment changed under Waltzman's framework;
- what collective goal-directed competence was observed under a Levin-informed
  framework; and
- which retained evidence supports or limits every finding.

Delivery maturity is a private functional PoC. Capability ambition is an
advanced but bounded multiscale social simulator, not a production platform.

The MVP acceptance contract remains
[Configurable Waltzman–Levin Research MVP Goal](GOAL.md). The operator has also
selected the next architecture outcome: reusable typed composition of reviewed
people, mechanisms, information carriers, places, and routes, with retained
compiler/runtime diagnostics. That work is owned by
[Slice 25](plans/025-typed-component-composition.md); it must preserve the
MVP's evidence and non-claim boundaries rather than replace them.

## Canonical Outcome Probe

Starting input:

> Model a multinational partnership deciding whether and how to deploy a
> bio-surveillance capability while different communities and participants
> encounter different technical, sovereignty, safety, and transparency
> concerns.

User operation:

1. converse with the authoring assistant;
2. inspect and edit the compiled people, information, mechanisms, places,
   candidate boundary, collective goal, run termination, and assumptions;
3. approve the configuration;
4. play one reference or live simulation; and
5. inspect the story, maps, participant/boundary accounts, and two theoretical
   readouts.

Inspectable result:

- retained approved-scenario and run URLs;
- initial situation, concise trajectory, outcome, and completion reason;
- spatial topology, configured interaction pathways, and realized causal graph;
- separate Waltzman and Levin findings;
- method labels distinguishing exact, calculated, and LLM-coded findings; and
- evidence step-down through a retained run-evidence bundle.

Negative case: a draft that requests an unsupported behavior, references a
missing entity, connects incompatible interfaces, or lacks a candidate goal or
terminal condition remains visibly unapprovable. A failed analysis leaves the
completed simulation intact and visible.

Non-claim: the PoC does not establish predictive accuracy, empirical validity,
hostile attribution, consciousness, or a universal scalar measure.

## Architecture of the Research Workflow

The initiative distinguishes four specifications:

```text
ScenarioSpec + RunSpec
        -> causal execution
        -> RunEvidenceBundle
        -> AnalysisSpec
        -> per-run Waltzman and Levin findings

ExperimentSpec + several retained runs
        -> post-MVP comparison, perturbation, or robustness analysis
```

### Scenario specification

Owns what is simulated:

- people, positions, descriptive dispositions, memories, and capabilities;
- information, sources, recipients, representations, channels, and timing;
- world objects, records, policies, incentives, software, and mechanisms;
- places and spatial topology;
- candidate analytical boundaries, collective goals, and constraints;
- decision procedures, feedback, schedules, and terminal conditions; and
- fidelity assumptions and known omissions.

Waltzman's heterogeneous, individualized, distributed, adaptive, and persistent
interactions are scenario expressiveness requirements. They are not themselves
per-run measurements.

### Run specification

Owns one execution's model, reasoning, horizon, budgets, timing options,
authorization, and checkpoint identity. It does not change the scenario's
meaning.

### Analysis specification

Owns versioned per-run constructs, operational definitions, required evidence,
method, aggregation, uncertainty, and limitations.

- The Waltzman module analyzes trust structure, perceived risk, and
  coordination readiness.
- The Levin module analyzes candidate boundary/goal, collective glue,
  boundary-scale activity, observed correction, persistence, adaptation, and
  scale-specific competence.

The modules share evidence but do not share conclusions or mutate execution.

### Experiment specification

Owns post-MVP conditions, perturbations, repetitions, matching rules, and
cross-run comparisons. It is explicitly outside the current MVP.

## Current Truth

### Outcome progress

- The canonical configurable Waltzman–Levin workflow is technically observed
  through conversational authoring, approval, live execution, dual analysis,
  restart, and reopen.
- Closed scenario playback, conversational authoring for two short templates,
  and the fixed multi-episode coordination scenario are technically observed.
- The operator has repeatedly reviewed the private UI and accepted the current
  maps, live causal animation, authoring conversation, and multi-episode
  narrative as useful foundations.
- An audit of the retained canonical run found one invalid Levin goal
  classification plus incomplete configured-graph relationships and ambiguous
  terminal wording. The implementation repair and corrected provider-free
  retained readout are complete; stakeholder comprehension is the remaining
  MVP decision.

### Enabling progress

- Autonomous causal execution, exact mechanisms, information lineage, positive
  modeled time, replay, pause/resume, and retained narratives are implemented.
- Spatial topology, configured pathways, realized causal graphs, and
  execution-inert analytical boundaries are implemented.
- The authoring workflow supports revision, direct person editing, approval,
  compiled previews, and live/reference execution for two templates.
- The fixed coordination scenario supports five LLM people, recurring meetings,
  exact decision mechanisms, typed boundary activity, and Waltzman-inspired
  measurement.
- Accepted live Terra/medium baseline, pressure, and stabilization trajectories
  remain retained evidence; see [Mac operations](operations/mac-mini.md).
- Comparison schema version 2 and its zero-cost six-run fixture remain working
  post-MVP infrastructure.
- Authored draft `draft_019c16228a62` and live run
  `run_e1a91d0a47e1` provide the canonical Packet 24C evidence. The live run
  retained 46 participant calls, 45 narrator calls, the exact outcome
  `no_decision_by_horizon`, and separate Waltzman and Levin readouts.
- Corrected draft `draft_6fbb279df69b` and zero-call reference run
  `run_eded0f70b15f` provide Packet 24D evidence. The run ended
  `scope_reduced`; both theory modules are available; the Levin goal result is
  calculated from retained configuration, terminal state, and completion
  evidence; the preview has 51 causal and 3 analytical-only nodes with no
  unexplained isolation.

### Process progress

- The previous goal incorrectly made a strict repeated comparison the MVP
  completion boundary and placed Levin-relevant output after the MVP.
- On 2026-07-30 the operator replaced that target. The old goal is superseded;
  its completed work is retained rather than replayed.

## Capability Map

| ID | Capability | Dependency | State | Satisfaction gate |
|---|---|---|---|---|
| `MVP-C0` | Existing causal execution, evidence, maps, narrative, pause/resume | hard | satisfied | Preserve regression behavior |
| `MVP-C1` | Conversational multi-episode coordination `ScenarioSpec` | hard | satisfied | One reviewed draft compiles to the existing coordination runtime without hand-editing Python |
| `MVP-C2` | Explicit `RunSpec` and `AnalysisSpec` snapshot bound to the approved scenario | hard | satisfied | Preview and retained run expose all three identities and digests |
| `MVP-C3` | Theory-neutral `RunEvidenceBundle` | hard | satisfied | Bundle includes configuration, state/events, information lineage, participant evidence, boundary activity, and completion evidence with reference validation |
| `MVP-C4` | Waltzman per-run module over the evidence bundle | hard | satisfied | Existing exact/coded measures consume the common bundle and render with method/provenance |
| `MVP-C5` | Levin per-run module over the evidence bundle | hard | satisfied | Candidate goal/boundary, glue, activity, correction, persistence, adaptation, and limits render without an aggregate executor or scalar |
| `MVP-C6` | One integrated private review flow | evidence | technical execution passed; stakeholder judgment pending | Analyst authors, approves, runs, understands, and disputes the canonical example without raw JSON |
| `POST-C1` | `ExperimentSpec` and repeated comparison | optional | deferred | Explicit post-MVP selection |
| `POST-C2` | Perturbation, robustness, and persuadability assays | optional | Packets 22A0–22A2 technically satisfied; stakeholder readout pending | Five matched provider-free rows distinguish concrete pathways and step down through one comparison UI to exact retained evidence |

The only open MVP boundary is the stakeholder judgment portion of `MVP-C6`.

## Shortest Critical Path

1. **Stakeholder readout — current boundary.** Review corrected run
   `run_eded0f70b15f` and decide whether its
   situation, trajectory, Waltzman readout, Levin readout, evidence, and
   limitations are understandable without raw JSON.
2. **MVP closeout — conditional next step.** If accepted, mark M7 and the goal
   complete and select a post-MVP direction. If rejected, convert the concrete
   usability failure into one bounded correction rather than reopening the
   simulator architecture.

Detailed implementation authority:
[Slice 24](plans/024-configurable-theory-analysis-mvp.md).

In parallel, the operator separately authorized the provider-free execution
vertical of [Slice 22](plans/022-composite-agency-perturbation-assay.md).
Packets 22A0–22A2 now define the strict assay contracts, compile and execute the
five scripted rows, calculate evidence-reversible vectors, retain the results,
and present one matched comparison with exact run and boundary step-down. This
does not authorize live repetitions, scalar agency scores, or causal/predictive
claims.

## Artifact Dispositions

| Artifact | Disposition | Reason |
|---|---|---|
| [Goal](GOAL.md) | update/active | Owns the new MVP completion contract |
| This roadmap | update/active | Owns current direction and first missing boundary |
| [Slice 17](archive/plans/017-conversational-scenario-authoring.md) | reuse unchanged | Completed authoring foundation |
| [Slice 21](archive/plans/021-coordination-environment-assay.md) | completed foundation; 21C post-MVP | Runtime and per-run Waltzman work are reused; paid comparison is not active |
| [Slice 22](plans/022-composite-agency-perturbation-assay.md) | Packets 22A0–22A2 technically complete; stakeholder readout pending | Five zero-cost scripted rows, retained exact readouts, and one comparison/step-down UI are verified; live repetitions remain unauthorized |
| [Slice 24](plans/024-configurable-theory-analysis-mvp.md) | active bounded design | Owns the new execution frontier |
| [ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md) | keep | Organizations remain execution-inert analytical views |
| [ADR 012](adr/012-decision-environment-measures-are-derived.md) | amend | Generalizes measurement input from trace-centric evidence to a run-evidence bundle |
| [Waltzman source note](research/001-from-minds-to-coordination.md) | amend | Separates scenario inputs, per-run measurements, and experiments |

Historical commits, runs, traces, comparison artifacts, and operations records
remain evidence. They do not own current direction.

## Binding Decisions

- [ADR 006](adr/006-boundaries-are-derived-coarse-grainings.md): aggregate
  organizations are reversible analytical boundaries, not hidden executors.
- [ADR 008](adr/008-separate-spatial-topology-from-routing-and-permission.md):
  spatial adjacency is not communication, capability, or authorization.
- [ADR 010](adr/010-autonomous-multirate-process-time.md): components evolve on
  their own modeled timescales.
- [ADR 011](adr/011-declared-representation-depth.md): representation depth is
  explicit, question-relative, and replaceable.
- [ADR 012](adr/012-decision-environment-measures-are-derived.md): theoretical
  measurements are derived analyst views and never hidden causal state.

## Planning Frontier

- `MVP-C1` through `MVP-C5` are satisfied on retained canonical evidence.
- `MVP-C6` has passed technical execution on the corrected retained run; only
  stakeholder comprehensibility remains unobserved.
- Provider-backed execution is operationally conditional on a certified route
  with available capacity. Reference execution remains available and meaningful.
- The Packet-22A0 contract foundation, Packet-22A1 five-row scripted
  execution/readout, and Packet-22A2 analyst comparison are technically
  satisfied. Stakeholder comprehension is unobserved; live repetitions,
  robustness claims, evasion, attribution, calibration, and prediction remain
  deferred.

## Continue, Reset, Scale, Stop

- **Decision:** retain the current direction; repair the audited truthfulness
  defects without reopening the simulator architecture.
- **Continue:** obtain the M7 stakeholder readout on corrected run
  `run_eded0f70b15f`.
- **Reset:** after two substantive increments or four hours without a new
  user-visible part of the canonical flow, or if configuration requires
  arbitrary generated mechanism code/a second runtime.
- **Scale:** do not proceed beyond the retained scripted Packet-22A2 comparison
  into live repetitions without the required human readout and separate
  selection of Packet 22B.
- **Stop:** if the resulting analysis cannot distinguish scenario inputs from
  derived findings, or aggregate findings cannot step down to retained evidence.

## Post-MVP Options

After the canonical flow is observed, select rather than automatically execute:

- repeated baseline/pressure/stabilization comparisons;
- Waltzman's candidate directional invariants and evasion dimensions;
- Levin-style perturbation, member replacement, recovery, robustness, and
  persuadability assays;
- generalized component composition and additional scenario families;
- empirical calibration, attribution, and predictive evaluation; and
- production or public deployment.
