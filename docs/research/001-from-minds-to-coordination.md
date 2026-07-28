---
doc_role: source_evidence
authority: evidence
status: active
created: 2026-07-25
updated: 2026-07-27
---

# Source Note: *From Minds to Coordination*

## Provenance

- **Title:** *From Minds to Coordination: AI Swarms and the Collapse of
  Collective Sensemaking — A State-Variable Framework for Detecting and
  Stabilizing Decision Environments*
- **Author:** Rand Waltzman
- **Source supplied by:** project operator as
  `From Minds to Coordination Paper.pdf`
- **Document metadata date:** 2026-04-23
- **Extent:** 19 pages
- **SHA-256:** `d35b4782ea11c46ad965b69f1c6c143daee8b508d4cb10bdba8396fb029a4524`
- **Review scope:** all 19 pages read on 2026-07-25
- **Visibility:** local project input; this note paraphrases the paper and does
  not copy it into the repository

This note is a project interpretation of the source, not a replacement for the
paper and not evidence that its proposed constructs have been empirically
validated.

## Central claim

**Paper location:** abstract through sections 1–2, pages 1–5.

The paper argues that an influence operation need not create a dominant
narrative, shared false belief, or attributable campaign. Diverse and
individually plausible interactions may still degrade the conditions under
which a group makes decisions. The proposed analytic shift is from similarity
among messages to directional changes in the decision environment.

Its motivating scenario is a multinational partnership considering a
bio-surveillance deployment. Different communities raise technical,
sovereignty, transparency, and safety concerns. No single false claim or unified
campaign explains the result, but meetings slow, settled issues reopen,
verification grows, informal coordination declines, and the deployment is
delayed or reduced.

## Proposed decision-environment dimensions

**Paper location:** section 3, pages 5–7.

### Trust structure

Trust structure concerns how credibility is distributed across people,
institutions, and information sources. The paper proposes indicators such as:

- more requests for verification or independent validation;
- divergence over which sources are authoritative; and
- reduced reliance on previously trusted intermediaries.

### Perceived risk

Perceived risk concerns how actors interpret uncertainty, harm, and adverse
outcomes. Proposed indicators include:

- more precautionary or hedging language;
- expansion of the considered risk set beyond directly relevant factors; and
- greater sensitivity to uncertainty without new evidence.

### Coordination readiness

Coordination readiness concerns whether actors can align decisions and actions
in time while expecting others to honor shared commitments. Proposed indicators
include:

- delayed decisions and longer meetings;
- reopening previously resolved issues; and
- reduced informal communication and alignment.

The paper treats the three dimensions as distinct but mutually reinforcing.
Trust fragmentation can expand perceived risk; increased perceived risk can
raise action thresholds; coordination failures can then reinforce distrust.

## Directional patterns called “invariants”

**Paper location:** section 4, pages 7–9.

The paper uses *invariant* to mean a consistent direction of effect across
heterogeneous inputs. Messages may differ in source, tone, and content while
trust becomes more conditional, the considered risk set expands, or
coordination slows.

For this project, that is a hypothesis to operationalize rather than a formal
mathematical invariant. One event or one trajectory cannot demonstrate it.
Repeated trajectories, counterfactual conditions, context/subgroup reporting,
and uncertainty are required before the simulator may report a candidate
directional pattern.

## Proposed mechanism

**Paper location:** section 5, pages 10–12.

The paper identifies adaptive interaction as the mechanism and argues that AI
swarms can make it:

- individualized to a person or community;
- responsive to earlier reactions;
- distributed across different messages and sources;
- locally adapted while aligned to a shared system objective; and
- persistent, intermittent, or resumable over time.

The paper's important modeling implication is that coherent collective effects
need not come from coherent content. A simulator must therefore preserve local
interaction paths and compare their accumulated effects rather than place one
campaign narrative directly into every participant.

## Cognitive Security Operations

**Paper location:** section 6, pages 12–15.

The proposed Cognitive Security Operations cycle has three functions:

1. **Detect:** monitor directional changes in the decision environment.
2. **Diagnose:** interpret which dimensions are shifting, whether the shift is
   local or propagating, and how dimensions interact.
3. **Stabilize:** clarify authority and decision processes, bound relevant
   uncertainty and thresholds, and reinforce timelines, commitments, and shared
   expectations.

The paper presents CSO as continuous and complementary to content, narrative,
and attribution analysis. It does not supply a validated detector, intervention
policy, or measurement formula.

## Evasion dimensions

**Paper location:** section 7, pages 15–17.

The paper describes five ways influence could obscure its effects:

| Dimension | Strategy | Observable implication |
|---|---|---|
| Time | Low-amplitude pressure or temporal fragmentation | Changes look gradual or intermittent |
| Structure | Segmented targeting and incompatible local equilibria | Subgroups appear stable while cross-group coordination degrades |
| Signal | Oscillating pressure | Volatility hides a consistent trend |
| Distribution | Switching pressure among variables | No single dimension crosses a threshold |
| Context | Environmental masking | Effects appear attributable to legitimate events |

These are later challenge conditions. They should not be implemented before a
basic baseline/pressure/stabilization assay produces an inspectable trajectory.

## Connection to behavioral drivers

The paper and UNICEF's *Behavioural Drivers Model* address different scales of
the same possible process. The BDM is an individual-centered checklist of
psychological, social, and environmental factors that may help explain why a
specific person attends, trusts, hesitates, intends, or acts. Waltzman's
framework asks whether many heterogeneous local interactions produce a
directional change in a collective decision process.

For this project the connection is a traceable micro-to-macro hypothesis:

```text
concrete source, message, channel, and social context
  -> person-local interpretation, memory, and action
  -> requests, verification, issues, commitments, delays, or withdrawal
  -> derived trust-, risk-, and coordination-related patterns
  -> collective decision outcome
```

[Slice 18](../plans/018-bdm-informed-person-review.md) already exposes a small,
reviewable person vocabulary informed by the BDM. It must remain selective:
the BDM itself warns that its drivers are entangled, context dependent, and not
a universal weighted causal model. A future coordination assay may use those
person descriptions and may retain scenario-specific driver hypotheses as
analysis metadata. It must not create a universal susceptibility score, insert
all BDM drivers into every person, or treat a person's explanation as proof
that a named driver caused an action.

## Connection to composite agency

The paper's decision environment can also be interpreted as part of the
control substrate through which an organization exhibits candidate composite
agency. The organization is not an additional executor. Its apparent
competence is the result of concrete people, records, policies, information
routes, incentives, schedules, and feedback mechanisms jointly preserving a
goal, detecting error, and coordinating correction.

Under this interpretation:

- trust structure affects which error and evidence signals propagate;
- perceived risk affects action thresholds and the set of states treated as
  requiring correction; and
- coordination readiness affects whether distributed commitments can become
  coherent action in modeled time.

Heterogeneous influence can therefore degrade higher-scale competence while
each component person remains locally intelligent and reasonable. That is a
testable Levin-style perturbation hypothesis, not evidence that the aggregate
has consciousness or a hidden mind. The relevant assay asks whether the same
concrete boundary preserves a reviewed collective goal after shocks, member
replacement, structural changes, or feedback interruption. It must distinguish
at least four possible patterns: loss of competence, effective-goal drift or
capture, fragmentation into incompatible subgroups, and successful defensive
adaptation. Rational caution is not automatically degradation.

The coordination assay must be observed before this composite-agency assay.
The former establishes the concrete multi-episode substrate and derived
measurements; the latter reuses it for matched perturbations under
[ADR 006](../adr/006-boundaries-are-derived-coarse-grainings.md).

## What the paper does not establish

**Review basis:** the complete supplied document, including the conclusion on
pages 18–19.

The paper is a conceptual framework. In the supplied version it reports no
dataset, experimental results, validated scale, causal estimator, threshold,
sample-size calculation, or empirical calibration procedure. In particular it
does not establish:

- that trust, risk, or coordination is a single scalar;
- that the three dimensions are exhaustive or independent;
- that listed indicators uniquely identify influence rather than ordinary
  disagreement or real external events;
- that directional change establishes hostile intent or attribution;
- that an LLM can reliably infer the dimensions from text alone; or
- that a stabilizing intervention improves real decisions.

## Project implications

The project will:

- model local beliefs, information deliveries, requests, commitments, and
  decisions as concrete simulation state and events;
- derive paper-inspired measurements after execution with exact evidence
  step-down under [ADR 012](../adr/012-decision-environment-measures-are-derived.md);
- compare baseline, heterogeneous pressure, and stabilization conditions;
- separate direct trace measures from LLM-coded analytical judgments;
- report indicator vectors and uncertainty without collapsing them into a
  universal trust, coordination, or agency score; and
- defer evasion and composite-agency assays until the basic coordination
  vertical is observed.
