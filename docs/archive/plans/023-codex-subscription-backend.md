---
doc_role: historical_evidence
authority: evidence
status: archived_completed_deployment_evidence
archived: 2026-07-30
---

# Plan 023: Codex subscription backend

## Archive disposition

This provider/deployment proof is retained as evidence only. It does not state
the current provider default or route availability; inspect the running
application and current shared-client capability evidence before authorizing a
live run.

**Status:** Complete

## Outcome

The canonical simulator uses `codex/gpt-5.6-luna` with medium reasoning through
the operator's ChatGPT Codex subscription. OpenRouter routes remain optional,
explicit alternatives. No failed Codex call silently changes model or provider.

## Acceptance

1. Participant, narrator, and scenario-authoring structured calls use the same
   isolated Codex transport settings through `llm_client`.
2. The deployment advertises Luna only after current-revision participant and
   narrator schemas execute successfully through that exact route.
3. The UI identifies subscription-included execution and does not present a
   usage-based planning amount as the operative constraint for Luna.
4. A deployed live run retains Luna as requested, resolved, and executed model,
   medium reasoning, validated structured results, narration, and zero marginal
   provider cost with `subscription_included` evidence.
5. If this exact route fails, the simulator fails loudly and reports the
   retained boundary; it does not upgrade or fall back automatically.
6. A deployment-supplied client revision must match the imported shared-client
   code before startup or certification. Certification validates the returned
   content against the exact response model before retaining an observation.
7. Authoring exposes only reasoning levels supported by the selected route,
   and each retained run carries its own billing mode so history does not
   change when the current model catalog changes.

## Canonical example

An operator selects Service Desk, leaves the default Luna/medium configuration,
and plays a live simulation. Each person and narrator call executes through the
ChatGPT-authenticated Codex CLI, while exact mechanisms adjudicate state. The
completed run remains inspectable in the existing spatial, configured-pathway,
and realized-causal views.

## Work

- [x] Certify Luna/medium structured output through the shared client.
- [x] Admit and certify the route in `llm_client` Plan 340.
- [x] Integrate the isolated backend across all simulator call sites.
- [x] Make Luna/medium the truthful default in API, authoring, UI, and deploy.
- [x] Add focused regression tests and run the full local checks.
- [x] Deploy, certify the exact current schemas, and inspect one complete live
      trace before calling the route usable.
- [x] Bind certification and startup to the installed shared-client revision,
      validate certification content, constrain authoring reasoning by route,
      and retain run-level billing provenance.

## Local evidence

- All 183 simulator tests passed before the final subscription-language UI
  refinement; its focused API, authoring, configuration, and backend checks
  also pass.
- Seven exact schema calls passed through Luna/medium: generic participant,
  narrator, and all five Coordination person schemas. A rejected Coordination
  `oneOf` exposed a shared-client projection defect; `llm_client` Plan 340
  fixed it and passed 441 focused client tests before the successful replay.
- Live physical-access run `run_f83a6380e122` completed with three participant
  and three narrator calls, the exact `Entered equipment room` outcome, medium
  reasoning, no fallback, and subscription-included `$0` marginal cost.
- The earlier disinformation-campaign authoring prompt compiled into a ready
  typed proposal in two Luna attempts: one visible fidelity-question repair,
  then one accepted result. Both retained `$0` marginal cost.
- The certification-integrity follow-up passed all 185 simulator tests, static
  typing, the production frontend build, and deployment-launcher syntax. Its
  focused configuration, authoring, and API boundary passed 58 tests.

## Deployed evidence

- Mac simulator behavior revision `6944dd26e1b905b3d3089c1b9045430090110ed1`
  with shared client `2e5ae381556c710f891c390783c5403df8038407`
  passed the production build, typing, and all 183 tests before restart.
- Fresh Mac observations certify the exact generic participant and narrator
  schemas plus all five Coordination person schemas through `codex_cli`.
- Deployed run `run_5bb293db1358` completed the authorized physical-access
  trajectory with three participant and three narrator calls, medium reasoning,
  no fallback, fully observable subscription billing, and `$0` marginal cost.
- Browser verification `run_535a61277c16` passed direct-link reopening, all
  three graph projections, spatial/causal composite collapse, participant/group
  accounts, narrative modes, and reference pause/resume with no console or
  failed-network errors. A separate 1440×1000 rendered inspection confirmed the
  Luna selector and medium reasoning remain visible while the irrelevant
  usage-based cost field is hidden.
- Certification-integrity deployment `cd333b200e551e4c23b7e482c0e6c2893636dff8`
  uses shared client `144d118658ee1c99275576e7e212475021613930` and
  seven fresh revision-bound Luna schema observations. Live physical-access run
  `run_e81b408516a2` completed with the exact entry outcome, three participant
  and three narrator calls, medium reasoning, retained
  `subscription_included` billing, and fully observable `$0` marginal cost.
- Browser verification `run_edb6edc921ad` passed narrative hierarchy, direct
  links, all three projections, projection-preserving composite collapse and
  expansion, both composites, the pre-run Service Desk preview, and
  Coordination pause/resume.
