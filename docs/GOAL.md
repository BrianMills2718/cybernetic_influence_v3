---
doc_role: execution_goal
authority: continuous_execution
status: active
created: 2026-07-27
updated: 2026-08-11
supersedes: earlier comparison-centered and configurable Waltzman-Levin goals as the active product frontier; retained below as baseline evidence
---

# Generalizable Socio-Technical Simulation System Goal

## Mission

Build a reviewable private simulation system in which an analyst can:

1. describe a bounded socio-technical world conversationally;
2. review and edit the compiled simulation configuration;
3. run interacting LLM and deterministic entities through a Concordia-owned
   simulation lifecycle; and
4. inspect the trajectory, state, assumptions, provenance, and selected
   domain-specific analyses.

The system must first reproduce the current Cybernetic Influence capabilities,
then demonstrate that a materially different domain can be expressed through
reusable components rather than another bespoke runtime. Wargaming, economic
modeling, and organizational analysis are exemplar applications, not the
definition of the product.

The simulation explores conditional pathways, mechanisms, strategies, and
sensitivities under explicit assumptions. It does not claim predictive accuracy
for chaotic socio-technical systems or real-world probabilities merely from
generated trajectories.

The product is a general **executable laboratory for decision environments**.
Waltzman's framework is one theory module and supplies the first substantial
experimental question; it does not define the whole product.

## Adopted foundation

[ADR-013](adr/013-generalized-simulator-foundation.md) adopts Concordia as the
outer simulation foundation. Concordia owns entity/component lifecycle, actor
selection, the environment/game-master loop, scheduling, and checkpoint
invocation. A project-owned canonical-world component owns typed world truth,
transition validation, and atomic commit without recreating the old runtime as
a second engine. Existing Cybernetic Influence code remains baseline evidence
and is selectively ported only when it adds observable value.

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
not supply. The bounded claim is theory development, conditional exploration,
and controlled scenario experimentation.

## Retained baseline exemplar

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

## Retained baseline contracts

The implementation must keep these concerns separate:

1. **Scenario specification** — the world and situation being simulated.
2. **Run specification** — model, reasoning, horizon, timing, budget, and other
   controls for one execution.
3. **Analysis specification** — the per-run constructs, operational definitions,
   evidence requirements, and methods used to produce findings.
4. **Experiment specification** — conditions, perturbations, repetitions, and
   comparisons across runs.

Only the first three were part of the retained MVP. `ExperimentSpec` was
post-MVP and remains deferred unless selected for the generalized product.

## Current acceptance

| ID | Criterion | Provenance | Evidence |
|---|---|---|---|
| G1 | The Concordia-first product reproduces the current user-visible authoring, execution, inspection, replay, and analysis capabilities | explicit_user | Side-by-side parity inventory and inspectable retained runs |
| G2 | Concordia—not the old `CausalSession`/`ActiveRuntimeSession`—owns the migrated simulation lifecycle | explicit_user | Runtime trace, dependency review, and negative control proving the old runtime was not invoked |
| G3 | Exact rules and structured evidence remain selective, question-relative components rather than a second hidden foundation | explicit_user | Component/state/evidence inspection in the parity exemplar |
| G4 | At least one materially different exemplar reuses the same authoring and execution seams without generated executable code or another scenario-specific runtime | explicit_user | Reviewed compile/run/reopen flow and implementation-diff review |
| G5 | Every result exposes assumptions and limitations and avoids predictive or real-world-probability claims unsupported by calibration | explicit_user | Human inspection of the rendered run and analysis surfaces |

## Retained MVP acceptance evidence

The following completed or pending criteria describe the pre-migration
Cybernetic Influence baseline. They remain parity evidence; they no longer
select the product foundation.

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

## Retained MVP boundaries

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
- No generalized game master, universal fidelity score, trust score,
  coordination score, or agency score. User-approved exception, 2026-08-05:
  one public workbench may configure and execute the bounded synthetic outbreak
  experiment. Its simulator API and run store are isolated from the private
  simulator and private retained evidence; this is a development tool, not a
  general public-hosting or production-hardening commitment.

## Current Truth

- The product owner adopted a Concordia-first generalized simulation direction
  on 2026-07-31 and reaffirmed its outer-lifecycle boundary after current-source
  inspection and a disposable bridge/port probe on 2026-08-11. Wargaming is an
  exemplar, not the goal.
- Current Cybernetic Influence behavior remains the parity baseline. No
  Concordia-first product implementation has begun.
- The user-approved public outbreak workbench is deployed at
  <https://brian-mac-mini.tail9c321e.ts.net/waltzman/>. It remains a retained
  example and capability baseline, not the generalized product architecture. A
  user can edit the shared
  situation plus each role's mandate and private institutional context; choose
  baseline, responsive exercise injects, or inject replay plus stabilization;
  execute one authentic 12-role, three-round model trajectory; and inspect or
  compare the retained result. The mechanism view aligns one role across
  conditions and reports dependency evidence, stated risk, and exact gate
  readiness without inventing a trust or coordination score. The public process
  uses an isolated run store. Provider availability is mutable; retained Luna
  and Terra executions are evidence about those runs, not current route claims.
- An audit invalidated the prior public triad as matched-condition evidence:
  participant system prompts disclosed the arm identifier before round one.
  The retained runs remain authentic historical tool demonstrations, but the
  prior sign-off and mechanism inference are withdrawn. The active replacement
  is complete: baseline `run_8924342b56ce` approved at 12 support; pressure
  `run_946a10a820fc` ended at 1 conditional and 11 defer without approval; and
  stabilization `run_05acbaea1137` returned to 12 support and approval after
  the verified allocation package. All 108 calls completed, configuration
  hashes match, and each role's complete first-round prompts are byte-identical
  across arms. The public comparison URL is pinned to those exact three runs.
  Historically, the invalidated triad used the same edited Alba epidemiologist
  mandate, all twelve agent configurations, shared situation, Terra model
  route, reasoning setting, and exact coalition gate.
  Baseline `run_3cf434f148e7` stayed at twelve support positions and approved;
  responsive pressure `run_4da81a355f28` moved to two conditional and ten defer
  and did not approve; matched stabilization run `run_40490a742a25` reached the same
  round-two state as pressure before a verified binding allocation package,
  then returned to twelve support and approved. Across the three rows, 108
  unique participant calls completed with no provider or validation error.
  The later audit withdrew that triad's independent sign-off along with its
  matched-condition inference.

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
- An analyst can now launch the fixed-pressure, adaptive-pressure, or
  adaptive-pressure-with-validation live condition from the canonical
  simulation controls. These conditions reuse the existing model and spend
  authorization, progress, pause/stop, retained-run, and evidence-inspection
  surfaces. API integration tests observe provider-bound participants and the
  selected adaptive/validation mechanism; desktop and mobile browser checks
  observe the complete selector and an explicit unavailable state when no
  freshly certified live route exists. This makes the authentic probe
  operator-accessible but does not itself add a repetition or effect estimate.
- Run history now groups compatible retained live conditions by model and
  reasoning configuration, shows their exact verification and risk differences,
  and opens every underlying trajectory. The grouping is explicitly exploratory:
  separately retained probes may span mechanism revisions and are not promoted
  to a controlled live experiment or effect estimate.
- The accepted Waltzman-facing next experiment is **Disrupting Coordination
  Without Winning Belief**: twelve autonomous LLM roles across Alba, Borin,
  Cyrenia, and a regional institution make three outbreak-response decisions.
  The matched baseline receives common round feedback; the treatment adds only
  predeclared exogenous exercise developments selected from risks participants
  report. Exercise control cannot choose participant stances. The matched
  authentic runs each completed 36 traced `codex/gpt-5.6-luna` calls with no
  provider failures or observed cost. The first pair is retained as
  `run_593ca1c425f2` and `run_c688aa8121fe`. A fresh pair,
  `run_0b5e20260805` and `run_7eae20260805`, repeated the exact coalition-level
  direction: both baselines ended with twelve support positions and approval;
  both capacity-pressure runs ended without approval and with all twelve roles
  requesting resources. The fresh treatment ended with twelve deferrals. A
  matched replay, `run_ca9a20260805`, preserved the same two capacity injects
  and added a verified minimum-capacity allocation package after round two. It
  ended with eleven support positions, one conditional position, and restored
  approval. This is a replicated demonstration and candidate mechanism, not an
  effect estimate or invariant.
- The prior strict comparison implementation remains useful post-MVP evidence,
  but its unfinished paid matrix is no longer active work.
- Route availability remains mutable and must be freshly certified before any
  later live run; the retained Packet 24C proof does not authorize another.

## Active Plan

The generalized-product track starts with the [Slice 27 general world-transition
vertical](handoffs/027-foundation-implementation.md), after separate
implementation authorization. [Slice 26 foundation research](plans/026-concordia-foundation-research.md)
and the [2026-08-11 current-source revisit](research/027-concordia-architecture-revisit.md)
are complete. The first production boundary must express the bridge/port case
through domain-neutral world, context, intent, transition-authority, patch,
validation, checkpoint, and evidence contracts with Concordia actually owning
the outer lifecycle. It must use authentic Luna calls and must not invoke the
old causal or active runtime behind the new path.

[Slice 25](plans/025-typed-component-composition.md) Packets 25A–25C, the public
Waltzman workbench, and all retained runs remain baseline evidence. This reset
does not retroactively change the prior MVP evidence or close M7.

The retained-MVP track remains governed by [Slice 24: Configurable
theory-informed simulation MVP](plans/024-configurable-theory-analysis-mvp.md)
only for its separate stakeholder decision. Packets 24A0–24D are technically
complete; M7 remains the review of the corrected retained run.

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

The current goal is complete when G1–G5 are observed: present capabilities run
on the Concordia foundation, one materially different exemplar reuses the same
seams, and the analyst can inspect assumptions, evidence, and limitations. The
retained MVP's M7 stakeholder judgment may close independently and does not
gate the architecture migration.

Reset the implementation plan at the earliest of roughly 45 minutes, two
consecutive non-outcome increments, or user concern about pace when a different
reversible move would yield substantially more value or decisive learning.
Also reset if migration requires the old runtime as a hidden executor,
arbitrary generated mechanism code, or a new scenario-specific runtime.

## Retained deferred work

The following are preserved but not required for current capability parity:

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
- additional perturbation or domain families beyond the one required
  materially different generalization exemplar.
