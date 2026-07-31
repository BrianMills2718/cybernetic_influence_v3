---
doc_role: execution_goal
authority: continuous_execution
status: active
created: 2026-07-27
updated: 2026-07-31
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
- The prior strict comparison implementation remains useful post-MVP evidence,
  but its unfinished paid matrix is no longer active work.
- Route availability remains mutable and must be freshly certified before any
  later live run; the retained Packet 24C proof does not authorize another.

## Active Plan

Follow [Slice 24: Configurable theory-informed simulation
MVP](plans/024-configurable-theory-analysis-mvp.md) for MVP acceptance. Packets
24A0–24D are technically complete; M7 remains the stakeholder review of the
corrected retained run. The operator has separately selected
[Slice 26: Foundation decision for a generalized cybernetic
simulator](plans/026-concordia-foundation-research.md) as the active architecture
research path. Capability equivalence is the premise: Concordia and Cybernetic
Influence can both combine language with typed state. Source-level research
must decide which foundation gives the product the clearest state authority,
least duplicated machinery, fewest compromised guarantees, and best reuse.
[Slice 25](plans/025-typed-component-composition.md) Packets 25A–25C remain
completed evidence; 25D and further simulator construction are paused until
Slice 26 records an architecture decision and replacement implementation
handoff. This reset does not change the MVP criteria or close M7.

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

- repeated baseline/pressure/stabilization comparisons;
- directional-invariant claims across runs;
- perturbation and member-replacement assays;
- recovery, robustness, and axis-of-persuadability experiments;
- Waltzman's evasion dimensions;
- causal attribution and predictive or empirical calibration; and
- generalized reusable component composition beyond the canonical scenario
  family.
