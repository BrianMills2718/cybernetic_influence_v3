---
doc_role: architectural_decision
authority: canonical
status: accepted
created: 2026-09-30
updated: 2026-09-30
---

# ADR-017: Replacement-first simulation platform gate

## Context

The project owner explicitly prefers adopting an existing mature system over maintaining locally novel or duplicative infrastructure.

Cybernetic Influence V3 already accepted Concordia as its simulation foundation because maintaining a second bespoke simulation framework was undesirable.

A fresh replacement review of the same regional-outbreak coordination case found a stronger candidate: the current Simudyne Nexus + Agentic Simulation Lab Python SDK stack appears to supply not only ABM execution but also first-class LLM/hybrid agents, experiments, Monte Carlo evaluation, validation, calibration, ablation, recording, checkpointing, deployment, and AI-assisted model authoring.

Public documentation is not enough to prove fit because Simudyne access is licensed/private.

## Decision

**Replacement testing precedes further generalized-simulator implementation.**

The project will not add another general runtime, authoring, experiment-management, calibration, replay, deployment, or model-lifecycle capability until the Simudyne replacement gate has been attempted or a concrete access/fit blocker is recorded.

Priority:

1. trial Simudyne Nexus + Python SDK on the retained regional-outbreak coordination experiment;
2. if Simudyne is unavailable or fails for a concrete reason, use Concordia as the open-source foundation and minimize the local layer;
3. prefer GAMA if the use case does not require LLM-native residents;
4. prefer AnyLogic when mature commercial multi-method simulation is more important than LLM-native authoring.

## Replacement rule

A mature external platform wins unless local code is required by an observed, decision-relevant gap.

The following are not reasons to preserve local infrastructure:

- novelty;
- sunk cost;
- stylistic preference;
- tighter control in the abstract;
- a local feature that can be reproduced with ordinary model-specific code;
- historical compatibility that is not needed by a live user.

## Simudyne trial gate

Use the regional-outbreak coordination experiment.

Success means the external platform owns generic:

- agent execution;
- scheduling;
- communication;
- experimental conditions and repetitions;
- run recording/checkpointing;
- model lifecycle;
- ordinary validation/deployment;

while local code is limited to the specific model and domain-specific analyses.

The trial must not invoke the Cybernetic Influence runtime behind the external platform.

## Consequences

- ADR-013 remains valid as the open-source/fallback foundation decision, but it no longer authorizes continued generalized-simulator expansion before replacement testing.
- Existing Cybernetic Influence capabilities remain parity/evidence assets, not migration requirements.
- A successful Simudyne trial is grounds to retire overlapping CI infrastructure rather than port it.
- A failed trial must document the exact missing capability or unacceptable operational constraint.
- The project may continue maintaining deployed evidence/demo surfaces, but maintenance must not silently become new platform development.

## Evidence

See [replacement-first simulation platform review](../research/030-replacement-first-simulation-platform-review-2026-09-30.md).
