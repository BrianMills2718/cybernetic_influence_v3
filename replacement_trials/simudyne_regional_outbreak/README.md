# Simudyne replacement trial package

This directory is the executable handoff for [Slice 39](../../docs/plans/039-simudyne-replacement-trial.md).

## Purpose

Determine whether Simudyne Nexus + the Agentic Simulation Lab Python SDK can replace Cybernetic Influence's **generic platform layers** on the retained 12-participant regional-outbreak coordination case.

The trial is successful when Simudyne owns the generic simulator/experiment lifecycle and local code is limited to case-specific model logic and domain-specific analysis.

## Files

- `case_spec.json` — frozen comparison case.
- `trial_result_template.json` — evidence receipt to complete after execution.
- `validate_case_spec.py` — local structural validation.
- `test_validate_case_spec.py` — positive/negative regression.

## Access status

Trial access was requested directly from Simudyne on 2026-09-30.

The AWS Marketplace SDK listing advertises a 7-day software free trial that automatically becomes a paid subscription if not cancelled; AWS infrastructure charges may still apply. Do **not** activate that route merely to satisfy this test without explicit account-owner approval.

## Execution rule

The implementation used for this trial must not import or invoke the Cybernetic Influence runtime, authoring/compiler, general simulation layer, or experiment/replay infrastructure.

The external platform is allowed to produce different stochastic trajectories. Replacement success is about capability ownership and inspectability, not reproducing historical LLM outputs byte-for-byte.

## First command after access arrives

1. Record the exact Nexus and `abm-lab` versions.
2. Use the research prompt from Slice 39 in Nexus.
3. Save the selected template/CMS and generated Python model in this directory.
4. Run at least two executions for each condition in `case_spec.json`.
5. Complete `trial_result_template.json`.
6. Classify all locally written files as `case_model`, `domain_analysis`, `adapter`, or `generic_infrastructure`.
7. If generic infrastructure was needed locally, document why Simudyne did not supply it.

Do not port CI abstractions before the platform demonstrates that they are actually missing.
