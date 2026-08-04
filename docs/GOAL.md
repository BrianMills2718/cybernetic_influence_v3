---
doc_role: execution_goal
authority: continuous_execution
status: active
created: 2026-07-27
updated: 2026-08-03
supersedes: comparison-centered research MVP goal at 0c91c418377a47185e40456eef77a67686f1f6ac
---

# Configurable Waltzman–Levin Research MVP Goal

## Mission

Deliver a reviewable private PoC in which an analyst can:

1. describe a bounded organizational decision situation conversationally;
2. review and edit the compiled simulation configuration;
3. run one meaningful LLM-driven multi-episode trajectory; and
4. inspect separate Waltzman- and Levin-informed per-run findings, with every
   finding labeled by method and linked to the retained evidence that supports
   it.

The MVP proves a configurable simulation-and-analysis workflow. It does not
require a perturbation assay, repeated comparison, counterfactual attribution,
or predictive validation.

## Accepted product direction beyond the MVP

The product is a general **executable laboratory for decision environments**.
An analyst should be able to model a bounded socio-technical environment, run
controlled conditions, compare directional changes, diagnose candidate
mechanisms, and test stabilizing interventions. Waltzman's framework is one
theory module over that general simulation system; it does not define the whole
product, and wargaming is only an exemplar use case.

The first representative post-MVP experiment is the same organizational
decision problem under matched conditions:

1. ordinary decision-making without the selected pressure;
2. heterogeneous, adaptive, persistent pressure; and
3. the same pressure plus a reviewed stabilization intervention.

The analyst compares trust structure, perceived risk, and coordination
readiness over time and across subgroups, with every candidate pattern stepping
down to retained interactions and evidence. Repetitions expose variability;
they do not by themselves establish a real-world causal effect.

This direction does **not** make the product an operational influence detector.
That would require real organizational data, empirically validated measures,
calibration, and prospective evaluation that Waltzman's conceptual paper does
not supply. Until then, the bounded claim is theory development and controlled
scenario experimentation. The foundation decision must be evaluated against
this laboratory workflow rather than determining the product identity first.

## Canonical Example

The analyst describes a multinational partnership deciding whether and how to
deploy a bio-surveillance capability while different participants encounter
different technical, sovereignty, safety, and transparency concerns.

Before running, the analyst can review and directly edit:

- people, positions, descriptive dispositions, and initial memories;
- candidate organizations as execution-inert analytical boundaries;
- the collective decision goal and its validity constraints;
- information representations, sources, recipients, channels, and timing;
- records, meetings, commitments, feedback, and exact decision mechanisms;
- places and spatial topology;
- terminal conditions, horizon, fidelity assumptions, and analysis selection.

After running, the analyst can inspect:

- the initial situation and a concise human-readable account of the trajectory;
- spatial topology, configured interaction pathways, and realized causal graph;
- participant and analytical-boundary accounts;
- a Waltzman readout of trust structure, perceived risk, and coordination
  readiness;
- a Levin readout of the candidate boundary, goal, collective glue,
  boundary-scale activity, observed correction, persistence, adaptation, and
  scale-specific competence; and
- provenance from each finding to configuration, state, events, information
  lineage, participant output, boundary activity, or other retained evidence.

## Four Contracts

The implementation must keep these concerns separate:

1. **Scenario specification** — the world and situation being simulated.
2. **Run specification** — model, reasoning, horizon, timing, budget, and other
   controls for one execution.
3. **Analysis specification** — the per-run constructs, operational definitions,
   evidence requirements, and methods used to produce findings.
4. **Experiment specification** — conditions, perturbations, repetitions, and
   comparisons across runs.

Only the first three are part of this MVP. `ExperimentSpec` is post-MVP.

## Acceptance

| ID | Criterion | Provenance | Evidence |
|---|---|---|---|
| M1 | A user can create, revise, approve, and run one Waltzman–Levin-relevant multi-episode scenario without editing Python | explicit_user | Retained draft, approved configuration, compiled preview, and run |
| M2 | The compiled scenario exposes concrete people, information, mechanisms, places, a candidate boundary, a candidate collective goal, run termination, and fidelity assumptions before Play | explicit_user | Review UI/API projection and negative compile fixtures |
| M3 | One approved reference run and one authorized live run use the existing causal runtime and preserve the initial situation, narrative, three graph meanings, pause/resume, and exact participant/mechanism evidence | governing_authority | Retained run URLs, focused regression checks, and complete live traces |
| M4 | A theory-neutral retained evidence bundle contains configuration, run identity, state/event evidence, information lineage, participant evidence, boundary activity, and completion evidence without treating narrator prose as source truth | explicit_user | Versioned bundle schema, positive fixture, corrupt/missing-reference failures, and reopen-without-reexecution check |
| M5 | The Waltzman module produces per-run findings about trust structure, perceived risk, and coordination readiness; every finding states its method, evidence, uncertainty, and limitation | explicit_user | Exact/calculated/coded fixtures plus one retained readout |
| M6 | The Levin module produces per-run findings about the candidate collective goal, boundary inputs/outputs, collective glue, observed correction/persistence/adaptation, and scale-specific competence without creating an organization executor or scalar agency score | explicit_user | Positive and negative fixtures plus one retained readout |
| M7 | A demo user can explain the situation, what happened, what each theoretical readout says, and what evidence supports or limits each claim without opening raw JSON | explicit_user | Operator review of the canonical retained run |
| M8 | Canonical documents and UI language distinguish scenario inputs, per-run measurements, and post-MVP experiments | explicit_user | Documentation/link check and rendered UI inspection |

## Boundaries

- People and exact or declared-coarse mechanisms execute. Organizations remain
  reversible analytical boundaries.
- The authoring model may populate reviewed fields. It may not generate
  executable mechanism code, invent implementation identities, or hide an
  unresolved capability.
- Concrete person-local trust judgments, risks, goals, and memories may be
  scenario inputs. Aggregate trust structure, perceived risk, coordination
  readiness, or agency may not be inserted as hidden global causal state.
- A retained trace is one evidence source, not the definition of a measurement.
- Narratives are presentation. They are not measurement source truth.
- Every finding is classified as `exact`, `calculated`, or `llm_coded`.
- Waltzman and Levin modules consume the same evidence contract independently;
  neither may mutate the world or the other module's results.
- Use the existing shared `llm_client`; every call retains `task`, `trace_id`,
  `max_budget`, native `json_schema`, raw lifecycle evidence, and observed
  accounting.
- No public hosting, mobile requirement, production hardening, arbitrary world
  language, generalized game master, universal fidelity score, trust score,
  coordination score, or agency score.

## Current Truth

- The causal runtime, maps, narrative, pause/resume, analytical boundaries, and
  exact evidence inspection are technically observed.
- Conversational authoring is technically observed for two short scenario
  families and the reviewed five-person coordination template. The canonical
  live draft, `draft_019c16228a62`, was generated in one structured Terra
  medium attempt, approved as revision 2, and compiled without exposing
  compiler-owned runtime identities or implementations to the model.
- The fixed multinational coordination scenario is technically observed in
  reference and live modes, with accepted baseline, pressure, and stabilization
  trajectories.
- An authored coordination draft can be edited directly, approved, compiled,
  run in reference or live mode, reopened, and inspected with either or both
  selected Waltzman- and Levin-informed readouts.
- The Waltzman- and Levin-informed per-run modules consume one theory-neutral
  evidence bundle and remain separate from the world execution.
- Boundary activity and coordination episodes exist as reversible analyst
  projections.
- Canonical live run `run_e1a91d0a47e1` completed through the existing causal
  runtime with 46 participant calls and exact
  `no_decision_by_horizon`. Narration-only recovery added 45 narrator calls
  without replaying the world; all 535 narrated event references and all 41
  exact-work references were retained.
- The retained draft and run reopened after a service restart with unchanged
  proposal, world, evidence-bundle, and analysis identities. The rendered
  desktop surface showed the initial situation, concise and detailed
  narratives, all three graph meanings, participant and composite accounts,
  exact outcome, and both theory readouts without browser or backend errors.
- Corrected reference draft `draft_6fbb279df69b` and run
  `run_eded0f70b15f` are retained on the private Mac surface. The approved
  goal distinguishes three satisfying outcomes from partner disengagement and
  no decision; the run ended `scope_reduced`, used zero model calls, reopened
  with unchanged evidence and analysis digests, and rendered separate
  Waltzman and Levin readouts. The Levin goal finding is calculated from the
  reviewed configuration, exact terminal state, and completion record.
- M1–M6 and M8 now have technical evidence. Packet 24D also completes the
  configured-relationship projection, reports zero unexplained isolated nodes
  in the corrected preview, rejects the all-terminal-outcomes negative control
  without changing the approved draft, and passes the deployed desktop browser
  flow without console or request errors. M7 remains the operator's
  comprehensibility judgment on this corrected surface.
- On 2026-07-31 the operator imposed a 24-hour limit to finish a Waltzman-facing
  demo before further product-architecture work. Packet 24E adds an executive
  Waltzman instrument over the existing retained findings: the exact modeled
  result, separate trust/risk/readiness observations, retained chronology, and
  an explicit nonclaim. An audit rejected the earlier causal-chain presentation
  because verification and threshold activity preceded the scheduled outside
  sources and the run ended without a decision. The corrected surface is a
  presentation candidate for M7, not evidence of stakeholder comprehension,
  adaptive influence, a directional invariant, or causal influence.
- The separately authorized Slice 27 mechanism proof now retains a strict
  four-condition, eight-run provider-free experiment. Concrete pressure sources
  can observe meeting feedback and change a later message; one narrowed
  stabilization condition reads an authoritative-validation fact and retained
  representation. The grouped readout compares pressure presence, adaptation,
  and stabilization while reopening either exact run. This post-MVP evidence
  does not close M7 or establish a real-world invariant or causal effect.
- The 2026-08-04 authentic Slice 27 probe ran the fixed-pressure and
  adaptive-pressure-with-validation conditions once each with five native
  `codex/gpt-5.6-luna` participants. Both complete traces retained 45 successful
  participant calls with no provider errors and subscription-included observed
  cost of $0. The validation condition produced an exact authoritative response
  and moved all five participants from full to reduced-scope support, but both
  runs ultimately reached no decision at the modeled horizon. This is not a
  valid adaptation comparison: after feedback had already moved targets away
  from `support_full`, the narrow scripted source rule repeated its initial
  messages and emitted no adaptive follow-up. The run therefore identifies a
  real mechanism-boundary defect rather than supporting an adaptation effect.
  Independent execution-based sign-off accepted that bounded decision and also
  rejected the two-run result as an adaptation estimate because the compared
  rows changed adaptation and validation together and had no repetitions or
  held-out scenario variation.
- The direct source-policy blocker was then repaired so the second message
  responds to any observed updated commitment rather than only continued full
  support. An isolated live adaptive-without-validation run,
  `run_ecb38b0e3cea`, retained 42 successful participant calls, 35 adaptive
  follow-up event references, and no validation event. Against the one fixed
  run it showed 7 versus 6 verification requests, 3 versus 2 distinct risks,
  and 3 versus 2 final open risks; both ended with no decision. These are
  exact-run candidate directions, not an effect estimate or invariant.
- The prior strict comparison implementation remains useful post-MVP evidence,
  but its unfinished paid matrix is no longer active work.
- Route availability remains mutable and must be freshly certified before any
  later live run; the retained Packet 24C proof does not authorize another.

## Active Plan

Follow [Slice 24: Configurable theory-informed simulation
MVP](plans/024-configurable-theory-analysis-mvp.md) for MVP acceptance. Packets
24A0–24D are technically complete. Packet 24E is the active delivery boundary:
deploy one outcome- and chronology-correct Waltzman-facing instrument over the
retained live run, then return control for the operator's M7 judgment.

[Slice 26: Foundation decision for a generalized cybernetic
simulator](plans/026-concordia-foundation-research.md) and further Slice 25
construction are explicitly paused until that demo review. Their retained
research and implementation evidence remain valid; this time box changes work
priority, not the eventual architecture question or the MVP's evidence and
nonclaim boundaries.

The operator separately selected and completed Packet 22A0's contract
foundation, Packet 22A1's five provider-free scripted trajectories, and Packet
22A2's comparison/step-down UI. Those post-MVP packets do not mark M7 complete,
change this MVP, or authorize Packet 22B's live repetitions.

The operator separately authorized
[Slice 27](plans/027-coordination-dynamics-experiment.md). Its provider-free
mechanism proof does not change Packet 24E's stakeholder boundary or authorize
live repetitions, calibration, attribution, or detection.

Execute one packet at a time from a clean linked worktree. For each packet:

1. implement only the named behavior;
2. run its focused positive and negative checks;
3. audit the owned diff;
4. commit and push the coherent packet; and
5. stop at any explicit provider, deployment, or operator-readout boundary.

Do not resume 21C1, 21C2, Slice 21D, or Packet 22B under this goal. Packet 22A0
through 22A2 remain retained post-MVP evidence and require their own stakeholder
readout before any live repetition work.

## Completion and Reset

The MVP is complete when M1–M8 are demonstrated on one canonical authored
coordination example, all owned changes are verified and merged on canonical
`main`, and the private review surface reopens the accepted draft and run
without re-execution.

Reset the implementation plan after two substantive increments or four elapsed
hours without a new user-visible part of the canonical flow. Also reset if the
coordination scenario cannot be made meaningfully configurable without
arbitrary generated mechanism code or a second simulation runtime.

## Post-MVP

The following are preserved but not required for MVP completion:

- an explicit `ExperimentSpec` for matched baseline, heterogeneous adaptive
  pressure, and stabilization conditions;
- repeated comparisons of directional changes, subgroup differences, and
  uncertainty with evidence step-down;
- adaptive influence actors that remain distinct from the target participants
  and can respond locally while pursuing a shared objective;
- candidate directional-pattern findings across runs, without prematurely
  labeling them validated invariants;
- perturbation and member-replacement assays;
- recovery, robustness, and axis-of-persuadability experiments;
- Waltzman's evasion dimensions;
- later empirical calibration, causal attribution, and operational detection
  only after representative real-world evidence exists; and
- generalized reusable component composition beyond the canonical scenario
  family.
