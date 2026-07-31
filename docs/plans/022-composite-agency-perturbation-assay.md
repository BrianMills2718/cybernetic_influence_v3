---
doc_role: implementation_plan
authority: bounded_design
status: packet_22a2_technical_complete
created: 2026-07-27
updated: 2026-07-31
---

# Slice 22: Composite-agency perturbation assay

## Assignment boundary

This is a post-MVP experimental candidate, not the current MVP goal. Do not
implement it until the configurable per-run workflow in
[Slice 24](024-configurable-theory-analysis-mvp.md) is complete and the operator
explicitly selects a robustness, recovery, member-replacement, or
persuadability question that requires controlled perturbation.

When selected, re-plan this candidate against current scenario, evidence-bundle,
analysis, run-store, graph, and narrative contracts. Do not assume that
completion of the historical Slice 21 comparison is the only valid gate.
It does not create another scenario, organization executor, agency score,
general causal-attribution framework, or generalized perturbation DSL.

On 2026-07-30 the operator explicitly selected the implementation foundation,
then on 2026-07-31 separately authorized Packet 22A1's provider-free scripted
vertical and Packet 22A2's analyst UI. Packets 22A0–22A2 are technically
complete. The Packet-22A2 stakeholder readout and Packet 22B remain open; 22B
requires a later instruction. This selection does not mark the Slice-24 M7
stakeholder readout complete or redefine the MVP.

## Analyst outcome

An analyst can select the multinational partnership's execution-inert
analytical boundary and ask:

> Does this concrete collection of people, records, policies, routes,
> schedules, incentives, and feedback mechanisms preserve a valid collective
> decision capability after specific perturbations, and which substrate changes
> most alter that capability?

The result is an intervention-specific composite-control profile with exact
step-down to components and events. It is not evidence that the partnership is
conscious, has a hidden mind, or caused an outcome independently of its
components.

## Theoretical bridge

This assay combines three already accepted perspectives without merging their
ontologies:

- BDM-informed person assumptions describe selected local dispositions and
  possible response pathways; they are not calibrated susceptibility scores.
- Waltzman's coordination constructs describe derived changes in trust-related,
  risk-related, and coordination-related evidence; they are not world state.
- Levin's TAME framing motivates perturbation tests of goal preservation,
  correction, recovery, rerouting, and robustness under member replacement; it
  does not supply an organization-agency scalar.

The concrete causal runtime remains authoritative. Aggregate interpretations
are reversible measurements over retained runs under
[ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md) and
[ADR 012](../adr/012-decision-environment-measures-are-derived.md).

Slice 22 consumes the typed `BoundaryActivityProjection` produced and observed
in Packet 21A2. It must not reconstruct crossings or coordination episodes from
prose, timestamps, focus overlap, or configured routes, and it must not change
the v1 one-output-per-episode rule during the assay.

## Frozen target artifact

The first assay uses the Slice-21 partnership boundary and one reviewed
collective capability:

> Reach a terminal deployment decision by the modeled deadline while obeying
> the retained validation, blocking-issue, active-partner, scope, and commitment
> rules.

This target deliberately does not equate agency with deployment or speed. A
safe reduced-scope decision may satisfy the capability. A fast decision that
bypasses a blocking issue does not. A justified delay may be adaptive if it
occurs through the reviewed decision rules; the exact day-10 no-decision state
remains a failed deadline outcome for this particular bounded capability.

The human-reviewable output is one matched-condition table plus trace step-down:

| Perturbation | Goal/constraints | Correction | Recovery | Rerouting | Members | Outcome |
|---|---|---|---|---|---|---|
| control | exact result | exact evidence | modeled duration | used routes | retained/replaced | terminal state |

Each row retains its runs, validity, exact measurements, coded interpretations,
limitations, and the concrete components changed by the intervention.

## Non-goals and non-claims

- No aggregate node acts, observes, remembers, decides, or owns an interface.
- No scalar ranks organizations from less to more agentic.
- No additive percentage attributes causation to “the organization” versus
  people.
- No perturbation changes hidden global trust, risk, coordination, or agency.
- No result establishes consciousness, moral status, real-world prediction, or
  empirical validation of Levin's biological findings in organizations.
- No delay, disagreement, verification request, or cautious decision is
  automatically classified as degradation.
- No arbitrary user-authored predicate or executable perturbation code.

## Domain contracts

### Reviewed capability specification

```python
class CompositeCapabilitySpec(_ProducedModel):
    schema_version: Literal[1]
    capability_id: Literal["valid_collective_decision_by_deadline_v1"]
    boundary_id: Literal["deployment_partnership"]
    member_refs: list[str]
    substrate_refs: list[str]
    exact_success_measure_ids: list[str]
    exact_constraint_measure_ids: list[str]
    limitations: list[str]
```

The compiler supplies `member_refs` and `substrate_refs`; the analysis layer
validates them against the retained scenario fingerprint. The LLM never chooses
members, success rules, constraints, or system-assigned IDs.

### Reviewed perturbation specification

```python
class PerturbationSpec(_ProducedModel):
    schema_version: Literal[1]
    perturbation_id: str
    family: Literal["component", "structure", "feedback", "shock"]
    variant: Literal[
        "position_matched_member_replacement",
        "decision_route_interruption",
        "verification_feedback_interruption",
        "relevant_external_risk",
    ]
    application: Literal["initial_condition", "scheduled_day_4"]
    changed_refs: list[str]
    matched_control_id: str
    description: str
```

These four variants are the entire first PoC language. Each variant is compiled
by reviewed code into an existing typed scenario configuration. Unknown
variants, arbitrary patches, and changes outside `changed_refs` fail before a
run. A replacement preserves the reviewed position, owned interfaces, and
institutional responsibilities, but changes the person identity, selected
BDM-informed profile assumptions, and scripted choice pattern. It is not
behaviorally equivalent; preserving behavior would make the component test
vacuous. The readout must show all declared person-level differences.

`position_matched_member_replacement` is the only initial-condition variant.
The route, feedback, and shock variants are applied by exact scheduled events
at modeled day 4, after the first two decision meetings and before the day-6
meeting. Variant/application mismatches fail compilation. The scheduled event,
changed concrete state, and downstream consequences must be retained in the
causal DAG. The initial replacement instead appears in the matched
configuration diff and configured/spatial graph; its person's realized actions
appear in the causal DAG.

### Run and readout records

```python
class CompositeAssayRunRef(_ProducedModel):
    run_id: str
    perturbation_id: str
    scenario_fingerprint: str
    evidence_bundle_version: int
    valid: bool
    invalid_reason: str | None

class CompositeControlReadout(_ProducedModel):
    schema_version: Literal[1]
    capability_id: str
    boundary_id: str
    perturbation_id: str
    exact_values: dict[str, JsonValue]
    boundary_activity_ref: str
    input_crossing_ids: list[str]
    output_crossing_ids: list[str]
    coordination_episode_ids: list[str]
    output_attempt_event_ids: list[str]
    external_result_event_ids: list[str]
    terminal_outcome_event_id: str
    framework_readout_refs: list[str]
    coded_patterns: list[CompositePatternEvidence]
    source_run_ids: list[str]
    limitations: list[str]
```

`CompositePatternEvidence` is a separate evidence-cited type for the six
perturbation interpretations listed below. The existing Slice-21
`IndicatorEvidence` cannot be reused truthfully because its ID union is frozen
to three Waltzman-inspired indicators.

`_ProducedModel` uses strict validation and `extra="forbid"`. Reopening uses a
separate consumer projection with `extra="ignore"` while retaining all required
identity, version, validity, and evidence-reference checks; it must not weaken
the producer schema. All IDs and references are locally validated before
retention.

## Owned business rules

1. **Matched-world rule — assay compiler:** control and perturbation must share
   the same scenario revision, initial state, model policy, run-control plan,
   and evidence-bundle version except for declared `changed_refs`.
2. **Concrete-change rule — assay compiler:** every perturbation compiles to a
   real person, route, mechanism, record, or exogenous-event change. Analysis
   labels cannot drive execution.
3. **Goal-integrity rule — exact calculator:** capability success requires the
   terminal decision and every reviewed constraint; speed alone cannot pass.
4. **Correction rule — exact calculator:** a correction exists only when a
   retained error/issue state is followed through explicit causal parents to a
   valid goal-relevant state change.
5. **Recovery rule — exact calculator:** for a scheduled perturbation, recovery
   time is measured from its retained application event to restored capability-
   relevant state. No observed restoration is `not_observed`, not zero. The
   control and initial member-replacement rows report `not_applicable` rather
   than inventing an application time.
6. **Rerouting rule — exact calculator:** an alternate route counts only when
   concrete retained delivery traverses a configured path different from the
   perturbed path.
7. **Validity rule — analysis service:** infrastructure/schema failure,
   fingerprint drift, missing perturbation application, missing scheduled work,
   or an incomplete current evidence bundle/framework readout invalidates the
   run and cannot be scored as low agency.
8. **No scalar rule — presentation:** exact vectors and coded patterns remain
   separate. The UI cannot average them into an agency or systemic-influence
   score.
9. **No causal overclaim rule — evidence coder:** the coder may classify an
   observed pattern as consistent with competence loss, goal drift/capture,
   fragmentation, defensive adaptation, rational caution, or unclear. It must
   cite retained evidence and cannot establish a causal mechanism from one run.
10. **Boundary-output rule — exact calculator:** a composite-scale action counts
    only when a retained Slice-21 `outgoing` crossing exists. The output attempt,
    downstream external result, and terminal outcome remain separate values.
11. **Episode-reuse rule — analysis service:** correction, recovery, and
    rerouting may reference only validated Slice-21 coordination episodes and
    their exact event IDs. Analysis never regroups events by timing or prose.

## Measurement vector

### Exact values

- reviewed capability satisfied: boolean;
- all decision constraints satisfied: boolean plus failed constraint IDs;
- terminal outcome and modeled decision time;
- goal-relevant issue/error corrections: count and event pairs;
- recovery time after a scheduled perturbation, `not_observed`, or
  `not_applicable` for control/initial-condition rows;
- alternate configured routes used after route interruption;
- active partners retained;
- member identities and replacements;
- repeated terminal-proposal denials;
- Slice-21 verification, reopening, commitment-divergence, and source-reliance
  measures by reference rather than duplication.
- incoming/outgoing boundary-crossing counts and IDs;
- completed/in-progress coordination-episode counts and IDs; and
- output attempts with their separate downstream external-result IDs.

### Evidence-coded patterns

- `competence_loss`;
- `effective_goal_drift_or_capture`;
- `fragmentation`;
- `defensive_adaptation`;
- `rational_caution`;
- `unclear`.

The coder sees only analyst-visible retained evidence and the reviewed
capability definition. Every result cites existing event and trace IDs, uses
the shared `llm_client` with `task=`, `trace_id=`, `max_budget=`, and native
`json_schema`, and remains post-run analysis. The first scripted packet may use
typed reference-coded fixtures and makes no provider call.

## Initial perturbation matrix

1. **Matched control:** unmodified Slice-21 baseline.
2. **Component:** replace the technical lead with a position-matched person
   who has different reviewed dispositions and scripted choices while
   preserving position, interfaces, institutional responsibilities, records,
   and routes. This is a matched initial condition.
3. **Structure:** interrupt the direct decision-coordination route while
   preserving people and the alternate configured route, through an exact
   modeled-day-4 event.
4. **Feedback:** interrupt verification-result feedback while retaining the
   original request and response records, through an exact modeled-day-4 event.
5. **Shock:** introduce one legitimate, decision-relevant external risk through
   its own source and route at modeled day 4.

The matrix is not expected to produce a particular ordering. Its exploratory
readout is whether the instrument distinguishes structurally different failure
and recovery paths while preserving step-down to exact evidence. If all rows
are behaviorally identical, inspect fixture adequacy before interpreting the
candidate composite as robust.

## Slice 22A — Scripted perturbation instrument

**Classification:** exploratory measurement vertical.

### Packet 22A0 — schema and both-sign fixtures

**Status:** complete on 2026-07-30. No scripted/live perturbation trajectory or
provider call was made. Do not expose a new API/UI action or start 22A1 without
a later instruction.

Create `src/cybernetic_influence/analysis/composite_agency.py` and focused
`tests/test_composite_agency.py`; extend the shared analysis models only when
the Slice-21 types cannot truthfully express the contract. Implement the strict
capability, perturbation, run-reference, and readout schemas plus compiler
validation against a frozen Slice-21 fixture.

Positive fixtures cover all five matrix rows. Negative fixtures cover unknown
variant, changed ref outside the allowlist, mismatched scenario fingerprint,
aggregate boundary as executor, missing control, missing current framework readouts,
duplicate run ID, invalid evidence ID, and an apparent fast decision that
violates a blocking constraint.

Also reject a missing/mismatched boundary-activity reference, an episode that
names an event outside its source run, a claimed composite output without an
outgoing crossing, a terminal outcome conflated with an output attempt, and any
attempt to rederive an episode from prose or event-time proximity.

Do not edit runtime, API, UI, scenario, prompt, or `llm_client` paths in 22A0.
Audit and commit before 22A1.

Observed evidence:

- the scenario adapter derives the partnership people, execution substrate,
  configured references, exact executors, analytical boundary, and control
  fingerprint from the real reviewed Slice-21 coordination fixture;
- reviewed future shock objects remain explicit additions rather than being
  misrepresented as existing world objects;
- strict producer and forward-tolerant consumer contracts cover the capability,
  four perturbations, run references, separate composite-pattern evidence, and
  evidence-reversible readouts;
- the validator requires five rows, one matched control, matching world/model/
  run-control and evidence-bundle contracts, concrete changed references, retained
  perturbation application evidence, and separate output attempts, boundary
  outputs, external results, and terminal outcomes;
- invalid rows can remain visible and unscored without inventing missing
  framework readouts or boundary activity; and
- `tests/test_composite_agency.py` passes 13 execution-free positive and
  adversarial tests, focused mypy is clean, analysis exports import, bytecode
  compilation succeeds, and `git diff --check` is clean.

Code-diff audit verdict: `pass`. The audit replaced the first manually described
fixture with derivation from the retained scenario contract and added consumer,
invalid-row, evidence-linkage, and schema-self-validation checks.

### Packet 22A1 — zero-cost matched runs and exact calculator

**Status:** complete under adopted revision `PACKET-22A1@2` (2026-07-31).

Runtime reconciliation for this packet:

- all five rows share an inert typed perturbation register, an exact terminal-
  proposal route switch, an alternate configured route, and delayed
  verification delivery so the comparison remains matched;
- scheduled route and feedback changes commit through an exact day-4
  perturbation controller rather than changing topology invisibly;
- their reviewed `changed_refs` therefore name the exact switch facts
  `perturbation_register.direct_route_enabled` and
  `perturbation_register.verification_feedback_enabled`; configured route IDs
  remain the pathways whose use or non-use provides downstream evidence;
- the external-risk row adds its concrete source, representation, carrier,
  ports, route, and delivery mechanism and emits at day 4;
- member replacement keeps the position-owned interface slot stable while a
  different retained person identity, assumptions, and scripted choice pattern
  occupy it; and
- provider-free rows consume the current `RunEvidenceBundle` and framework
  readouts. They do not fabricate a legacy evidence-coder call merely to satisfy
  the older Slice-21 measurement envelope.

This reconciliation supersedes only conflicting 22A1 implementation details;
the frozen capability, four perturbation families, no-aggregate-executor rule,
exact evidence step-down, and no-scalar boundary remain unchanged.

Compile each reviewed perturbation into the existing scripted Slice-21
scenario, run one matched trajectory per row, calculate the exact vector, and
retain the readout through the existing run/analysis store. Add no model call.

Acceptance:

- a changed-ref diff proves every row differs from control only where declared;
- every initial-condition change is visible in the configuration diff and
  configured/spatial graph, and every scheduled perturbation is visible in the
  causal DAG and narrative;
- correction, recovery, and rerouting calculations cite exact event IDs;
- every row retains the exact boundary input/output and coordination-episode
  IDs inherited from Slice 21A2, with attempts and external results separate;
- position-matched member replacement preserves the structure but changes the
  component identity, reviewed person assumptions, and exercised behavior
  visibly;
- the relevant-risk shock can produce rational caution without being labeled
  hostile influence by construction;
- invalid runs remain visible and unscored; and
- rerendering retained results makes no execution or provider call.

Observed evidence (2026-07-31):

- five scripted rows completed and reopened through the ordinary `RunStore` at
  exactly zero model calls and `$0.00` observed cost;
- the component row preserved the technical position's interfaces while
  changing its retained occupant identity, assumptions, and first verification
  request timing;
- the structure row applied its exact day-4 switch, used
  `terminal_proposal_alternate_route`, and still reached `deploy_on_time`;
- the feedback row applied its exact day-4 switch, interrupted all five
  verification deliveries, reached `no_decision_by_horizon`, and truthfully
  reported recovery as `not_observed`;
- the shock row routed a retained representation through a concrete source,
  carrier, ports, connection, and exact delivery, producing an evidence-cited
  `rational_caution` reference pattern without construing it as hostile;
- every row retained current Waltzman and Levin framework readouts over the
  same theory-neutral evidence bundle, plus exact partnership boundary
  crossings and coordination episodes; and
- the full backend suite passed 280 tests before the final audit corrections;
  after those corrections all 17 focused contract/execution tests, focused
  mypy, bytecode compilation, frontend production build, deploy-script syntax,
  and diff hygiene pass;
- the isolated code-diff audit found and fixed collision-prone retained run
  IDs, pre-validation partial persistence, route labels that did not name the
  exact changed switch facts, and incomplete embedded-event validation; its
  final verdict is `pass`; and
- repository-wide mypy remains blocked by the same 18 pre-existing errors in
  `tests/test_configurable_theory_analysis.py` reproduced on clean `main`; no
  changed Packet-22A1 file has a mypy error.

### Packet 22A2 — analyst comparison and readout

**Status:** technical execution complete; stakeholder readout pending.

Add the matched-condition table to the existing comparison/run-history UI,
with step-down to the selected run, analytical boundary, graph moment,
narrative, exact measures, and coded reference pattern. Do not build a separate
application or generic perturbation editor.

Selecting the partnership row first shows its boundary inputs, derived
coordination episodes, boundary outputs, and separate external results; the
analyst can then expand the same retained episode into exact people,
mechanisms, routes, events, and the Slice-21 Waltzman-inspired measurements.
Do not add a pseudo-agent orientation or organization-level chain of thought.

The human readout asks:

1. Can the analyst distinguish component failure, structural interruption,
   feedback loss, legitimate shock, and recovery without raw JSON?
2. Does every aggregate claim step down to changed components and retained
   events?
3. Does the presentation avoid equating speed, deployment, or disagreement
   with agency?

Observed technical evidence (2026-07-31):

- Run history groups the five retained rows into one matched-condition table
  while keeping each row independently reopenable through the ordinary run API;
- selecting a condition separates boundary inputs, derived coordination
  episodes, boundary outputs, and external results, with changed references and
  exact event citations behind deliberate evidence step-down;
- the feedback-loss row visibly reports a failed reviewed capability and no
  observed recovery, while the relevant-risk row reports retained rational
  caution without construing it as hostile influence;
- the selected row opens the unchanged Simulation surface with its spatial,
  configured, and realized graphs, analytical scale, narratives, partnership
  account, exact participants, and Waltzman/Levin readouts;
- creating and reopening the comparison are typed API operations; generation
  uses fixed scripted behavior, five retained runs, zero model calls, and no
  provider; grouped deletion is recoverable and rolls back a partial file move;
- the real desktop browser flow passed from a fresh assay deep link with a clean
  console, no failed requests, clean server logs, and an inspected 1440×1100
  rendering; mobile remains outside this PoC;
- all 282 repository tests, focused mypy, the frontend production build,
  JavaScript/Python and deploy-script syntax, and diff hygiene pass; and
- repository-wide mypy retains the same 18 pre-existing errors in
  `tests/test_configurable_theory_analysis.py` documented after Packet 22A1;
  no changed Packet-22A2 file has a type error.

### 22A stopping rule

The technical readout is complete. After the human readout, stop and update
this plan. Do not define numeric
agency thresholds or begin live repetitions. Continue only if the scripted
instrument differentiates at least two concrete perturbation pathways and all
aggregate claims remain reversible.

## Slice 22B — Repeated live composite-control profile

**Status:** skeleton pending 22A readout.

After 22A resolves instrument adequacy, freeze one or two informative
perturbations, the exact scenario and measurement revisions, valid-run rules,
model/reasoning policy, and call/cost bounds. Run one authorized canary per
retained condition, inspect all participant, narrator, Slice-21 measurement,
and composite evidence-coder traces, then request separate authorization for a
small repeated batch.

Report per-run vectors, outcome distributions, between-run variation, invalid
runs, and interaction-specific limitations. Do not collapse the result to an
agency score. Before a result changes the roadmap or supports a systemic-
influence claim, use independent evaluation sign-off on the frozen batch.

## Later questions, not current implementation

- compare declared intervention effort or detailed knowledge requirements as a
  tentative axis-of-persuadability profile;
- test member replacement across several positions rather than one;
- test whether pressure changes the candidate effective goal while preserving
  coordination competence;
- test nested or overlapping candidate boundaries only after composition rules
  supersede ADR 006; and
- calibrate any capability or recovery measure against external observations.

## Verification and closeout

At each packet run the focused composite, coordination-analysis, scenario,
replay, API/presentation, and affected UI checks; run mypy, the frontend build,
and `git diff --check`. Terminal 22A acceptance requires `make check`, retained
reopening, browser console/network inspection, and an isolated code-diff audit.

Commit and report each packet separately. Packet 22A2 is ready for the human
readout recorded above; do not proceed to 22B until that readout is retained
and the operator separately selects it. Any required aggregate executor,
global agency state, arbitrary perturbation code, or non-reversible claim is an
exact stop condition.
