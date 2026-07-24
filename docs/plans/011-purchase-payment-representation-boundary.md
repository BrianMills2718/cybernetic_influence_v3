# Slice 11: Purchase-to-Payment Representation Boundary

**Status: Packet 1 complete; Packet 2 live canary pending — 2026-07-23.**

## Outcome

For an analyst studying multiscale agency, turn one synthetic purchase into an
inspectable trajectory across concrete people, documents, internal controls,
and an external payment processor. The operator must be able to distinguish:

- what each person perceived and attempted;
- what a policy copy said;
- what the internal control software accepted or denied;
- what the coarsely represented external processor returned;
- which exact members and flows are hidden by each organizational-scale view.

The company, operating unit, and finance function are derived analytical
boundaries. None receives an activation, chooses an action, or mutates state.

## Frozen Target

The requester submits purchase request `purchase_17` and invoice `invoice_17`.
The approver receives the submitted package and records an approval or denial.
The accounts-payable clerk receives that signed decision and may request
payment. An exact internal control checks the invoice/request match, recorded
decision, concrete policy copy, and signing authority before emitting a typed
payment instruction. A coarse processor returns only a settled or declined
result through the same typed boundary a finer processor could later implement.

Three conditions isolate different causal layers:

1. `settled`: internal approval is valid and the coarse processor settles.
2. `approval_denied`: the requested amount exceeds the copied policy limit, so
   the approver records a denial and no payment instruction reaches the
   processor.
3. `processor_declined`: internal approval is valid, but the coarse processor
   returns declined without supplying an internal causal explanation.

## Target Derivation

| Target behavior | Required state | Owning operation | Contract | Acceptance |
|---|---|---|---|---|
| Separate request, invoice, policy, approval, and payment information | concrete carriers and representations | scenario fixture and exact mechanisms | strict Pydantic document models plus lineage | no document is replaced by an abstract relationship |
| Human approval remains a human attempt | approver memory, delivered package, owned output | approver active system | typed `ApprovalDecision` action | exact trace records the person before the recorder mechanism |
| Software enforcement differs from written permission | policy copy, signer credential, matching documents | internal payment gate | `PaymentRequest -> PaymentInstruction | denied` | forced invalid payment attempt is denied |
| External outcome is coarse and question-limited | authored response mode | processor implementation | `PaymentInstruction -> PaymentResult` | result is inspectable; omitted processor internals are not invented |
| Organizational views remain derived | exact member and route evidence | analyst boundary projection | three execution-inert boundaries | no boundary appears in active specs, actions, or mechanisms |

## Boundaries and Owned Rules

### People

- The requester owns whether to submit the retained purchase package.
- The approver owns the attempted approve/deny decision. The copied policy is
  remembered social/institutional context, not an instruction injected as an
  intrinsic role.
- The accounts-payable clerk owns whether to request payment from the delivered
  decision and retained invoice context.

People may use only initially retained or delivered representations through
their declared output interfaces.

### Exact internal mechanisms

- Intake copies the submitted request and invoice into a delivered review
  package without deciding whether it should be approved.
- Approval recording verifies the concrete signer credential and records the
  person's attempted decision; it does not become the approver.
- The payment gate enforces the copied limit, positive recorded decision,
  matching request/invoice identifiers and amounts, and signer authority. A
  structurally valid but unauthorized payment request is denied visibly.
- Delivery mechanisms create later observations; they do not grant same-moment
  omniscience.

### Coarse external processor

The processor is an exact transition over a deliberately coarse representation:
it consumes one validated payment instruction and returns `settled` or
`declined`. Its `FidelityNote` preserves instruction/result timing and status,
while explicitly omitting accounts, fraud models, networks, counterparties,
queues, retries, and the causal reason for a decline. Therefore the run may
support “the processor declined this instruction,” but not “why the banking
system declined it.”

### Analytical boundaries

- `operating_unit_view`: requester, approver, originating documents, and their
  local interfaces.
- `finance_operations_view`: accounts-payable clerk, internal payment control,
  payment records, and processor-facing interfaces.
- `purchase_to_payment_view`: the exact superset spanning both views.

Membership overlap or subset is descriptive evidence. This slice authors the
three views and permits separate collapse/step-down; it does not yet claim a
general nested-boundary algebra or a composite mind.

## Runtime and Trace Contract

The scenario reuses `causal-core.v2`, `active-runtime.v1`, the existing
mechanism binding protocol, retained analyst document, causal-moment narration,
and closed API catalog. It adds no scenario DSL or provider abstraction.

Canonical events continue to distinguish action attempt, routed effect,
mechanism execution, committed patch, and later observation. Each processor run
retains its concrete `implementation_id` and fidelity declaration. Scripted
reference bindings establish deterministic positive and negative fixtures;
native bindings use the existing explicit model and budget controls.

## UI Contract

- **User:** analyst studying how individual actions and concrete controls
  produce an organization-scale payment outcome.
- **Critical flow:** choose Purchase to payment → choose a condition → play a
  reference run → compare the causal graph and three derived views → select the
  approval, gate, and processor moments → step down to each person's trace.
- **Existing owner:** the single simulator page, existing JSON run API, and
  existing React Flow canvas.
- **Hypothesis:** the analyst can tell internal authorization failure from an
  opaque external decline without treating the company or processor label as a
  human-like actor.
- **Technical readout:** scenario and arm selection, distinct retained
  outcomes, processor fidelity visible in the inspector, boundary
  collapse/expand at one revision, and clean desktop/mobile browser execution.
- **Stakeholder readout:** whether the resulting graph and narrative are
  understandable remains for later operator use; technical execution alone
  does not establish comprehension.

## Landscape Disposition

- OASIS UBL 2.4 separates Order, Invoice, PaymentMeans, and related references.
  Reuse the document distinctions, not its XML schemas or full procurement
  process: <https://docs.oasis-open.org/ubl/UBL-2.4.html>.
- W3C PROV distinguishes entities, activities, and responsibility-bearing
  agents, plus derivation and attribution. Reuse provenance/lineage distinctions
  while retaining this simulator's stricter rule that an analytical
  organization boundary is not thereby a runtime executor:
  <https://www.w3.org/TR/prov-o/>.
- ADR 006 supplies execution-inert coarse-graining rules; ADR 011 supplies the
  representation-depth and fidelity declaration.

## Acceptance and Disproof

Accept the slice when:

- all three scripted conditions produce the intended distinct outcomes;
- no processor execution occurs after a recorded approval denial;
- a forced payment request with missing, mismatched, over-limit, or unsigned
  evidence is denied by the exact gate;
- the coarse processor's output retains the instruction as lineage but no
  invented internal explanation;
- all three analytical boundaries derive only from exact members and remain
  absent from runtime authority;
- the API rejects cross-scenario arm confusion;
- the existing Service Desk and physical-access checks remain green;
- desktop and mobile browsers exercise selection, graph, boundary controls,
  narratives, and traces without console, network, or layout errors.

Disproof includes an organization acting, a policy edge directly causing
payment, a human seeing an undelivered document, an external decline narrated
with a fabricated reason, or a new generic framework larger than the concrete
scenario.

## YAGNI Boundary

Do not add a general procurement engine, BPMN interpreter, accounting ledger,
banking simulator, probabilistic surrogate library, nested-boundary runtime,
automatic fidelity scoring, public scenario plugins, or calibration pipeline.
Do not run a paid live sample until the deterministic vertical and trace
surface pass.

## Delivery Packets

### Packet 1 — deterministic vertical and operator surface

Add the scenario-local contracts, fixtures, exact mechanisms, scripted/native
bindings, outcome projection, API catalog entry, and regression/negative tests.
Exercise all three reference arms through the API and rendered UI. Stop if the
existing contracts cannot express the coarse processor honestly without a
general runtime change.

Completed locally on 2026-07-23: all three arms produced their intended
outcomes; forced invalid payment, mismatched-document, and inactive-signer
checks stopped before the processor; replay and the full 44-test suite passed;
the production graph build passed; and desktop/narrow-browser checks exercised
spatial/causal projections, all three boundary controls, exact expansion,
participant traces, and processor-fidelity inspection without console or
layout errors. This is technical evidence, not a stakeholder-comprehension
claim.

### Packet 2 — bounded live canary

Only after Packet 1 passes, run one baseline live sample with the existing
configured model. Inspect every full agent and narrator trace, confirm the
processor made no LLM call, and decide whether the scenario supplies enough
concrete pressure to design nested/overlapping boundary semantics. Do not add
those semantics merely because three boundaries exist.
