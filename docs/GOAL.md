---
doc_role: execution_goal
authority: continuous_execution
status: active
created: 2026-07-27
updated: 2026-07-31
supersedes: configurable Waltzman-Levin MVP as active product frontier; retained below as baseline evidence
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

## Adopted foundation

[ADR-013](adr/013-generalized-simulator-foundation.md) adopts Concordia as the
simulation foundation. Concordia owns the entity/component lifecycle,
environment/game-master loop, scheduling, and checkpoint substrate. Existing
Cybernetic Influence code is retained as baseline evidence and selectively
ported where its exact mechanisms, information lineage, causal inspection,
authoring, UI, or analysis add observable value.

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
- No public hosting, mobile requirement, production hardening, arbitrary world
  language, generalized game master, universal fidelity score, trust score,
  coordination score, or agency score.

## Current Truth

- The product owner adopted a Concordia-first generalized simulation direction
  on 2026-07-31. Wargaming is an exemplar, not the goal.
- Current Cybernetic Influence behavior remains the parity baseline. No
  Concordia-first product implementation has begun.

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
- The prior strict comparison implementation remains useful post-MVP evidence,
  but its unfinished paid matrix is no longer active work.
- Route availability remains mutable and must be freshly certified before any
  later live run; the retained Packet 24C proof does not authorize another.

## Active Plan

The generalized-product track starts with the [Slice 27 parity
proof](handoffs/027-foundation-implementation.md), after separate implementation
authorization. [Slice 26 foundation research](plans/026-concordia-foundation-research.md)
is complete; the owner revised its invariant-preserving recommendation and adopted Concordia as the product foundation in
[ADR-013](adr/013-generalized-simulator-foundation.md). The first migration
boundary must reproduce the physical-access capability with Concordia actually
owning execution before broader parity work begins. [Slice 25](plans/025-typed-component-composition.md)
Packets 25A–25C and all retained runs remain baseline evidence. This reset does
not retroactively change the prior MVP evidence or close M7.

The retained-MVP track remains governed by [Slice 24: Configurable
theory-informed simulation MVP](plans/024-configurable-theory-analysis-mvp.md)
only for its separate stakeholder decision. Packets 24A0–24D are technically
complete; M7 remains the review of the corrected retained run.

The operator separately selected and completed Packet 22A0's contract
foundation, Packet 22A1's five provider-free scripted trajectories, and Packet
22A2's comparison/step-down UI. Those post-MVP packets do not mark M7 complete,
change this MVP, or authorize Packet 22B's live repetitions.

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

Reset the implementation plan after two substantive increments or four elapsed
hours without a new user-visible part of the parity or generalization flow.
Also reset if migration requires the old runtime as a hidden executor,
arbitrary generated mechanism code, or a new scenario-specific runtime.

## Retained deferred work

The following are preserved but not required for current capability parity:

- repeated baseline/pressure/stabilization comparisons;
- directional-invariant claims across runs;
- perturbation and member-replacement assays;
- recovery, robustness, and axis-of-persuadability experiments;
- Waltzman's evasion dimensions;
- causal attribution and predictive or empirical calibration; and
- additional perturbation or domain families beyond the one required
  materially different generalization exemplar.
