---
doc_role: experiment_record
status: clean_replacement_signed_off
created: 2026-08-05
---

# Custom-mandate matched outbreak triad

> **Audit correction (2026-08-05): invalid for matched-condition inference.**
> The participant system prompt included the experiment condition identifier,
> so the three arms were not condition-blind before round one. The retained
> trajectories remain authentic historical artifacts, but the sign-off and
> mechanism claim below are withdrawn. A clean replacement must use identical
> participant personas across arms and vary only delivered exogenous events.

## Clean replacement protocol

The replacement freezes the same twelve-role configuration, situation, model,
reasoning setting, budget, three-round structure, and exact gate. Participant
personas must be byte-identical across `baseline`,
`responsive_exercise_injects`, and
`capacity_inject_replay_with_stabilization`; condition names and descriptions
must not appear in participant system prompts. One fresh trajectory per arm is
run from the corrected deployed revision. The public comparison is pinned to
those three exact run IDs. Results are reported as observed, including a null or
reversed pattern, without substituting the invalidated trajectories.

## Clean replacement executed readout

Corrected deployed revision:
`62dee59e57f95a47653dc2f80da8c3216b74e9e0`. The canonical configuration
SHA-256 remained
`67f350acc92f5c9a27fa7fa3efe3f1932297b3614f2e0ca0b989675d6536a6a3`
for every arm.

| Condition | Run | Round 1 | Round 2 | Round 3 | Gate |
| --- | --- | ---: | ---: | ---: | --- |
| Baseline | `run_8924342b56ce` | 12 support | 12 support | 12 support | Approved |
| Responsive pressure | `run_946a10a820fc` | 12 support | 11 conditional, 1 defer | 1 conditional, 11 defer | Not approved |
| Pressure + stabilization | `run_05acbaea1137` | 12 support | 10 conditional, 2 defer | 12 support | Approved |

All three runs completed 36 unique participant calls and 36 committed traces
with zero provider or schema-validation errors. Raw shared-client evidence
contained no experiment-arm identifier in any of the 108 rendered prompts. For
each of the twelve roles, the first-round system prompt and complete user prompt
were byte-identical across the three arms. The pressure and stabilization arms
received the same capacity-development families and both produced twelve
round-two resource requests; only stabilization received the verified allocation
package before round three.

Public reproduction:

- [exact clean role-aligned comparison](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=mechanism&mechanism_person=alba_epidemiologist&runs=run_8924342b56ce,run_946a10a820fc,run_05acbaea1137)
- [clean baseline](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_8924342b56ce&round=3&person=alba_epidemiologist)
- [clean pressure](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_946a10a820fc&round=3&person=alba_epidemiologist)
- [clean stabilization](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_05acbaea1137&round=3&person=alba_epidemiologist)

## Clean replacement independent sign-off

**Verdict: SIGNED-OFF for the one-configuration qualitative claim only.** A
fresh adversarial verifier re-fetched the deployed revision and run documents,
reconstructed the 36-call and 36-trace completion of every arm, checked common
configuration identity and exact gates, and reproduced the baseline approval,
pressure non-approval, and stabilization approval outcomes.

- Validity: pass.
- Representativeness: pass only for the declared twelve-role configuration.
- Diagnosis: pass; the capacity prerequisites and resolving allocation package
  are retained and inspectable.
- Generalization: not applicable to the bounded claim and rejected beyond it.
- Decision: replace the withdrawn note only with this statement: **in this
  configured synthetic coalition, the observed pressure trajectory disrupted
  approval and the observed allocation trajectory restored it.**

No repeatability, generalization, human-behavior, real-world causality,
effect-size, or empirical-validation claim is signed off.

## Decision and claim

**Claim.** In this synthetic coalition, a predeclared capacity shock can make a
configured institutional dependency decision-relevant and disrupt coordination
without exercise control selecting participant stances; a verified allocation
package can restore executable support by resolving that dependency.

**Decision.** Use the triad as the empirical center of the concise
Waltzman-facing note only if all three runs are valid and the exact evidence
shows baseline approval, pressure-only non-approval, and stabilization approval,
with the edited Alba epidemiologist's rationale responding to the configured
reserve and delivered capacity evidence. Otherwise revise the note to the
narrower observed pattern or stop the mechanism claim.

- Stage: exploratory PoC / qualitative mechanism probe.
- Unit of analysis: one 12-role, three-round trajectory per condition.
- Intended user: a researcher inspecting a theory-relevant executable model.
- Population: the twelve fictional synthetic roles in the regional-outbreak
  scenario; no human or real-institution population is represented.
- Minimum useful result: a condition-linked change in the exact coalition gate
  plus a rationale-level response by the edited role to evidence about its
  configured reserve dependency.
- Non-claims: no effect size, statistical estimate, invariant, predictive
  validity, human-belief inference, real-world causal attribution, or measured
  trust score.

## Frozen system and comparison contract

The existing pressure run `run_4da81a355f28` was treated as the preregistered treatment.
Its exact `regional_outbreak_configuration` is the only allowed configuration
for the two new runs. The configuration contains twelve unique roles, the same
shared situation, and this edited Alba epidemiologist mandate:

> You are accountable for evidentiary quality, epidemic control, and preserving
> a protected domestic confirmation reserve. Support launch only when the shared
> plan preserves that reserve while maintaining cross-border validation.

Held constant:

- deployed public API implementation and schema;
- `codex/gpt-5.6-terra`, medium reasoning, subscription billing;
- maximum run budget `$0.74` and maximum 36 participant calls;
- all twelve mandates, institutional contexts, and the shared situation;
- three rounds and the exact coalition gate.

Only the condition varies:

| Condition | Exogenous environment |
| --- | --- |
| `baseline` | Common round feedback only. |
| `responsive_exercise_injects` | Predeclared developments selected from aggregate reported risk. |
| `capacity_inject_replay_with_stabilization` | The accepted capacity developments plus a verified minimum-capacity allocation package. |

Configuration identity is validated by hashing the canonical JSON projection of
`regional_outbreak_configuration`. Any mismatch invalidates the comparison.
Unavailable model certification, a partial run, any failed model call, missing
round, or malformed outcome also invalidates that run rather than counting as a
bad coordination outcome.

## Preregistered readout

| Construct | Exact method | Decision-linked threshold | Uncertainty |
| --- | --- | --- | --- |
| Coalition readiness | Terminal exact gate and its three checks | Baseline passes, pressure fails, stabilization passes | Three qualitative trajectories; no sampling estimate |
| Position movement | Round-by-round structured decision counts | Direction must agree with the gate pattern | Model stochasticity is not estimated |
| Configured dependency activation | Edited role's exact decision, risk, request, and rationale | Pressure rationale must cite the reserve/capacity dependency rather than an unrelated reason | One synthetic role and prompt configuration |
| Stabilization mechanism | Delivered authoritative allocation evidence followed by role/coalition response | Stabilization must resolve or explicitly bound the capacity dependency and restore approval | Temporal association inside the model, not real-world causality |
| Execution validity | Retained call summaries, participant traces, lifecycle events, and completion | 36 completed calls, 36 committed traces, one start and one terminal lifecycle per call, one run completion | Infrastructure failure invalidates the row |

Secondary exploratory readouts may describe which other roles change their
risks or requests, but they cannot replace the primary decision rule.

## Controls, budget, and artifacts

- Positive control: the already completed pressure run has 36 completed call
  summaries, 36 committed traces, and one terminal completion.
- Negative control: the deployed API rejected an 11-agent configuration with a
  typed HTTP 422 and retained no run.
- Corruption control: canonical configuration hashes and exact role identity
  sets must match before interpreting outcomes.
- Maximum new execution: two runs, 72 participant calls, `$1.48` configured
  aggregate ceiling; the certified subscription route is expected to retain
  `$0.00` observed marginal cost.
- Durable artifacts: public isolated run documents and shared-client lifecycle
  traces on the Mac; run IDs, hashes, exact readout, and reproduction links are
  added to this record after execution.

## Stop and handoff rules

- **Continue to concise note:** all rows valid and the preregistered three-part
  gate pattern is present with mechanism-relevant participant evidence.
- **Revise:** all rows valid but only part of the pattern appears; report exact
  trajectories without the failed mechanism clause.
- **Stop:** configuration identity fails, traces are incomplete, or a run is not
  terminal after the allowed execution window.

Before the readout determines the paper claim, hand the completed artifacts to
`eval-decision-signoff` for a fresh execution-based validity check.

## Executed readout

The two missing rows were launched only after preregistration commit `92544b8`.
The canonical configuration projection is UTF-8 JSON produced with recursively
sorted object keys, no insignificant whitespace, no trailing newline, and the
agent list in configured order. Its SHA-256 is
`67f350acc92f5c9a27fa7fa3efe3f1932297b3614f2e0ca0b989675d6536a6a3`
for all three runs.

| Condition | Run | Round 1 | Round 2 | Round 3 | Gate |
| --- | --- | ---: | ---: | ---: | --- |
| Baseline | `run_3cf434f148e7` | 12 support | 12 support | 12 support | Approved |
| Responsive pressure | `run_4da81a355f28` | 12 support | 11 conditional, 1 defer | 2 conditional, 10 defer | Not approved |
| Pressure + stabilization | `run_40490a742a25` | 12 support | 11 conditional, 1 defer | 12 support | Approved |

The focal Alba epidemiologist moved `support → support → support`,
`support → conditional → defer`, and `support → conditional → support`
respectively. Pressure and stabilization delivered the same eight
country/delegation-level developments and produced the same round-two aggregate
state before the package: 11 conditional, 1 defer; 9 capacity risks, 3
legitimacy risks; and 12 resource requests. The stabilized condition then added
the verified binding minimum-capacity package and no participant stance command.

Canonical retained-document SHA-256 values:

- baseline: `f0eedd0578820b1ca381f2e8f9c56114457aa74f52e1da92217e6d1c19ec8a08`;
- responsive pressure: `5df16346fce7d9b7b3cb9d0af2ee5824daf0927bddedecab980b5e7f34f12a75`;
- stabilization: `a63f3b026bd4befc409bcf5af700a7d74fa65a0efc6e56c66f95c3e0d0e38517`.

Each run retained 36 completed call records, 36 unique trace IDs, 36
committed participant traces, one run completion, zero provider errors, and
zero schema-validation errors. The shared-client lifecycle store contains one
`started` and one `completed` event for every call; baseline and pressure also
contain one and five nonterminal heartbeats respectively.

Public reproduction:

- [role-aligned mechanism comparison](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=mechanism&mechanism_person=alba_epidemiologist)
- [baseline](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_3cf434f148e7&round=3&person=alba_epidemiologist)
- [pressure](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_4da81a355f28&round=3&person=alba_epidemiologist)
- [stabilization](https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=inspect&run=run_40490a742a25&round=3&person=alba_epidemiologist)

## Independent eval-decision sign-off

**Decision:** use the triad as the empirical center of the concise note, limited
to the one-configuration qualitative demonstration.

**Verdict: SIGNED-OFF.**

1. **Validity — PASS.** The fresh verifier re-fetched all three public run
   documents, reproduced semantic identity with the retained artifacts,
   checked the exact deployed revision, recomputed configuration identity and
   gates, inspected raw shared-client records and lifecycle events, and reran
   the 11-agent typed negative control without creating a run.
2. **Representativeness — PASS for the declared unit only.** The full configured
   12-role synthetic population is present. This would fail for any claim about
   repeatability, broader synthetic populations, humans, institutions, or the
   real world.
3. **Diagnosis — PASS.** The gate results, identical pre-stabilization aggregate
   state, and focal dependency-specific rationales were independently
   reconstructed.
4. **Generalization — NOT APPLICABLE.** No generalizing fix, effect estimate, or
   transferable restoration claim is accepted.
5. **Decision — PASS.** The comparison was warranted to observe irreducibly
   empirical model-generated stances, and the decision preserves the
   preregistered non-claims.

The signed-off statement is therefore: **in this configured synthetic
coalition**, capacity shocks were followed by dependency-specific stance
changes and failed approval, while a verified package resolved the stated
dependency and was followed by restored approval; exercise control never
selected a participant stance.
