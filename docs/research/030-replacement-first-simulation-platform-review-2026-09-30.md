---
doc_role: research-ledger
status: current-evidence
reviewed: 2026-09-30
authority_refs:
  - ../GOAL.md
  - ../ROADMAP.md
  - ../adr/017-replacement-first-simulation-platform.md
---

# Replacement-first simulation platform review — 2026-09-30

## Question

Can a mature off-the-shelf simulation platform replace most or all of Cybernetic Influence V3's generalized-simulator machinery?

The decision criterion is replacement, not novelty. If a mature product or library can do the job with ordinary model-specific work, that is a success condition.

## Common comparison case

Use the retained **regional outbreak coordination** experiment as the shared workload.

Required behavior:

1. 12+ heterogeneous decision-makers with role-specific goals and context;
2. common initial outbreak information plus later differentiated developments;
3. multiple rounds / simulated time;
4. explicit information delivery and agent-local observations;
5. external pressure processes that may react to prior public outputs;
6. one stabilization intervention that cannot directly write participant decisions;
7. a hard collective decision rule over final participant stances;
8. exact retention of individual decisions/rationales and selected events;
9. matched experimental conditions and repeated runs;
10. comparison of outcomes and mechanism-sensitive measures;
11. assumptions/limitations kept explicit;
12. no claim that synthetic trajectories are calibrated real-world predictions.

The comparison does not require reproduction of Cybernetic Influence's current UI or historical wire formats. Those are migration concerns, not reasons to keep a simulator.

## Candidate 1 — Simudyne Nexus + Agentic Simulation Lab Python SDK

### What exists off the shelf

Current official documentation describes Nexus as an AI-powered model builder with a five-stage path:

```text
research question
  -> discover related ABM / system-dynamics models
  -> select a structured template
  -> refine mechanisms, parameters, and constraints
  -> generate Python simulation code
  -> validate against empirical targets / stochasticity budgets
```

Nexus is built on the Simudyne `abm-lab` Python SDK.

The current SDK already provides:

- rule-based, LLM, hybrid, RL, and external-proxy agents;
- links, topologies, and typed message passing;
- multiple execution backends;
- Monte Carlo evaluation;
- parameter sweeps;
- sensitivity experiments;
- statistical validation;
- Bayesian calibration;
- mechanism ablation;
- LLM response caching for reproducible replay;
- multi-level recording;
- checkpoints;
- OpenTelemetry;
- REST/WebSocket serving;
- Docker/Helm deployment.

Official docs:
- https://docs.simudyne.com/nexus/
- https://docs.simudyne.com/python-sdk/overview/introduction/
- https://docs.simudyne.com/reference/agents/communication
- https://docs.simudyne.com/reference/agents/connection/

### Mapping the outbreak case

| Outbreak requirement | Simudyne path |
|---|---|
| heterogeneous people | heterogeneous `LLMAgent` / `HybridAgent` groups |
| role/persona prompts | LLM-agent configuration |
| asymmetric information | links + targeted messages |
| pressure sources | rule/hybrid agent groups |
| hard decision gate | deterministic model logic |
| stabilization intervention | parameter/mechanism condition or intervention agent |
| repeated matched conditions | experiment runner / Monte Carlo |
| sensitivity | parameter sweeps + statistical layer |
| reproducible LLM behavior | response cache + deterministic seed tree |
| event/results retention | SimulationRecorder + output sinks/checkpoints |
| deployment | REST, WebSocket, Docker, Helm |
| natural-language model authoring | Nexus architect / CMS workflow |

### What may still require project-specific code

- exact Waltzman/Levin analytical readouts;
- any unusually strict per-event causal-provenance projection;
- a project-specific review UX if Nexus's review surface is insufficient;
- explicit authority/refusal semantics if the model requires stronger guarantees than normal deterministic agent/model rules.

Those are plausible thin extensions. They are not evidence for keeping a general simulator.

### Current blocker

Nexus / Simudyne SDK access is licensed/private. Official access documentation offers a trial route and direct commercial licensing.

This means the replacement hypothesis cannot be closed from public docs alone. It requires an authentic trial.

### Disposition

**Primary replacement candidate. Stop general simulator expansion until tested.**

If the regional-outbreak case can be authored, run, repeated, inspected, and compared in Simudyne with project code limited to the case model plus genuinely domain-specific analyses, retire the corresponding Cybernetic Influence general-runtime/authoring/experiment infrastructure.

---

## Candidate 2 — Google DeepMind Concordia

### What exists off the shelf

Concordia is an Apache-2.0 generative social-simulation library.

It already owns the concepts Cybernetic Influence selected it for:

- generative agents;
- memories and observations;
- modular components;
- Game Masters;
- environment resolution;
- sequential/simultaneous engines;
- scheduling;
- structured logs;
- checkpoints.

Official source/docs:
- https://github.com/google-deepmind/concordia
- https://github.com/google-deepmind/concordia/blob/main/concordia/environment/README.md
- https://github.com/google-deepmind/concordia/blob/main/concordia/components/README.md

The standard `EventResolution` path may use an LLM to resolve a putative action. Deterministic or structured behavior can instead be implemented in custom Game Master components.

### Mapping the outbreak case

Concordia is a natural fit for the participant cognition and interaction loop. The current CI V3 `general_simulation` path already uses it.

What Concordia does **not** provide as strongly off the shelf as Simudyne:

- experiment-design / statistical-analysis tooling;
- calibration and validation framework;
- AI model-builder workflow comparable to Nexus;
- a production deployment and model lifecycle stack comparable to Simudyne's current SDK.

### Disposition

**Valid open-source foundation / fallback, but not evidence that Cybernetic Influence should remain a large platform.**

If Simudyne is unavailable or fails the trial, keep Concordia and collapse CI toward a thin set of domain-specific components, experiment definitions, and read-only analyses. Do not recreate generic simulation lifecycle, memory, scheduling, or checkpoint machinery around it.

---

## Candidate 3 — GAMA

### What exists off the shelf

GAMA is a free/open-source general agent-based modeling environment with:

- a high-level modeling language (GAML);
- spatial/data-driven ABM;
- large-scale simulations;
- built-in UI/visualization;
- BDI/BEN cognition with beliefs, desires, intentions, emotions, norms, and social relations;
- agent messaging/network integration;
- batch experiments, parameter exploration, and optimization;
- headless and server modes.

Official docs:
- https://gama-platform.org/
- https://gama-platform.org/wiki/Using-BEN-simple-bdi
- https://gama-platform.org/wiki/RunningHeadless
- https://gama-platform.org/wiki/RunningExperiments

### Mapping the outbreak case

GAMA can model the outbreak experiment conventionally:

- each participant as a BDI/social agent;
- information delivery as messages;
- pressure/stabilization as processes or agents;
- the coalition rule as deterministic model logic;
- conditions/repetitions as batch experiments;
- results through built-in displays or headless output.

### Main mismatch

The current product premise is LLM-native conversational authoring and LLM-driven participants. GAMA does not appear to make that the center of gravity. Adding it would require external integration and would move us back toward adapter-building.

### Disposition

**Excellent replacement for classical/social ABM if LLM residents are not actually required. Not the default replacement for the present CI product experience.**

If future evidence shows scripted/BDI agents are sufficient, strongly prefer GAMA over maintaining a home-grown simulator.

---

## Candidate 4 — AnyLogic

### What exists off the shelf

AnyLogic is a mature commercial multi-method simulation platform.

Current official documentation supports:

- agent-based models;
- statecharts/events and hierarchical agents;
- system dynamics and process modeling in the same environment;
- parameter variation;
- Monte Carlo experiments;
- sensitivity analysis;
- calibration;
- optimization;
- custom experiments;
- model snapshots;
- external application integration;
- Cloud/API execution and parallel runs.

Official docs:
- https://anylogic.help/anylogic/agentbased/agent.html
- https://anylogic.help/anylogic/experiments/about-experiments.html
- https://anylogic.help/anylogic/experiments/monte-carlo-experiment.html
- https://anylogic.help/anylogic/experiments/custom-experiment.html
- https://anylogic.help/anylogic/running/snapshots.html

### Mapping the outbreak case

AnyLogic can represent:

- people/organizations as agents;
- message exchange and changing internal state;
- deterministic decision gates and interventions;
- multiple experimental arms;
- replications, confidence intervals, optimization, and sensitivity;
- rich inspection/visualization.

### Main mismatch

Natural-language model authoring and LLM-native social agents are not the platform's core workflow. They can be integrated through external APIs/code, but that is additional integration work.

AnyLogic also brings commercial licensing and a Java-centric extension model.

### Disposition

**Strong replacement if the real requirement is serious conventional simulation/digital-twin experimentation rather than an LLM-native generative-agent product.**

---

## Same-case replacement matrix

Legend:
- **native** — platform directly supplies the capability;
- **thin** — ordinary model-specific implementation or a small adapter;
- **custom** — substantial project-specific platform work;
- **unknown** — requires trial.

| Capability | Simudyne Nexus/SDK | Concordia | GAMA | AnyLogic |
|---|---|---|---|---|
| ABM runtime | native | native | native | native |
| heterogeneous agents | native | native | native | native |
| first-class LLM agents | native | native | custom | thin/custom |
| deterministic agents/rules | native | thin | native | native |
| targeted/asymmetric messaging | native | native/thin | native | native |
| experiment arms / repeats | native | thin/custom | native | native |
| Monte Carlo/statistics | native | custom | native | native |
| calibration/validation | native | custom | thin/native | native |
| mechanism ablation | native | custom | thin | thin |
| natural-language model builder | native (Nexus) | custom | custom | custom |
| model-library discovery | native (Nexus) | custom | model library, not same workflow | public model library, not same workflow |
| replay/checkpoint | native | native | native/thin | native |
| deployment/API | native | thin/custom | native server/headless | native/cloud |
| project-specific theory analyses | thin | thin | thin | thin |
| strict CI-style causal provenance | unknown/thin | custom | custom | custom |
| open-source/no license | no | yes | yes | no |

## Decision

The platform question is no longer open-ended.

1. **Do not build another general simulation capability in Cybernetic Influence until Simudyne is tested.**
2. **Simudyne Nexus + Python SDK is the primary replacement trial.**
3. **Concordia remains the open-source fallback and current adopted component foundation.**
4. **GAMA is the preferred comparison if LLM-native participants are shown unnecessary.**
5. **AnyLogic is the preferred comparison if the requirement shifts toward conventional enterprise simulation/digital twins and commercial tooling is acceptable.**

## Authentic replacement trial

The next experiment is not “can we port one feature?”

It is:

> Can Simudyne reproduce the regional-outbreak coordination experiment without using Cybernetic Influence runtime, authoring, experiment, persistence, or replay infrastructure?

Required trial outputs:

- the same participant roles;
- baseline / pressure / stabilized conditions;
- explicit targeted information delivery;
- hard collective decision gate;
- at least two repeated runs per condition;
- retained individual decisions and rationale/evidence;
- run-level outcome and comparison metrics;
- inspectable assumptions and model configuration.

### Replacement success

Call the trial a replacement success when:

- Simudyne owns generic agent execution, scheduling, experiments, repetition, recording, and model lifecycle;
- Nexus or the SDK owns ordinary model construction/validation rather than CI reproducing those layers;
- remaining local code is specific to the outbreak model or genuinely domain-specific analysis;
- no Cybernetic Influence runtime is secretly invoked behind the comparison.

If that gate passes, archive/retire the overlapping generalized-simulator code instead of adapting it.

### Failure that justifies keeping code

Keeping local machinery requires a concrete, observed failure in the trial, such as:

- the candidate cannot express a decision-relevant mechanism;
- it cannot preserve required participant-local information boundaries;
- its execution model prevents a required hard constraint/refusal;
- its retained evidence cannot support the actual analytical question;
- licensing/deployment constraints make it operationally unsuitable.

Preference, familiarity, sunk cost, or a more elegant local abstraction are not sufficient reasons.

## Bottom line

The strongest current hypothesis is no longer “Cybernetic Influence should become the general simulator.”

It is:

> **A mature simulator—especially Simudyne—may already supply the general platform. Cybernetic Influence should survive only as domain-specific model/analysis material that proves necessary after replacement testing.**
