---
doc_role: historical_evidence
authority: evidence
status: complete
updated: 2026-07-23
---

# Slice 4: Evidence Boundary Repair

**Status: Complete — 2026-07-23.**

## Frame

Repair the evidence instrument so it never reveals mechanism-only content or
describes a state/outcome that did not exist at the selected point in the
realization.

## Constraints

Preserve exact causal contracts, zero-cost scripted execution, retained JSON
documents, the one-page UI, and the single-process development host. Do not add
the second scenario, a database, public access, or a general policy framework
inside this repair.

## Modality

Visibility enforcement, event-time replay, identity binding, permissions,
security headers, and live-run mutual exclusion are deductive invariants.
Whether the repaired timeline remains understandable is an exploratory
readout: selecting early, middle, and terminal events must expose the right
state without hiding the route back to exact evidence.

## Slice Contract

- **Vertical scope:** execute one arm → project analyst-safe evidence → retain
  it privately → reopen → select an event → inspect that revision's state and
  exact activation.
- **Success:** no mechanism value/content/hash crosses the API; event snapshots
  equal canonical prefix replay; narrative agrees with open, remediated, and
  closed outcomes; file/document identities match; storage modes are private;
  one process cannot start concurrent live runs; browser hardening headers are
  present.
- **Audit:** canary credentials, protected patch content, filename/document
  mismatch, malformed JSON, early-event future facts, same-time activations,
  open live trajectory, concurrent live requests, hostile HTML, untrusted
  tailnet identity, and stale retained samples.
- **Cleanup:** extract presentation from the API, centralize authorization and
  security headers, remove duplicated final-state projection, and correct
  version metadata.
- **Done when:** all tests and the temporal readout pass, findings are
  dispositioned, cleanup is complete, the Mac sample is regenerated, and this
  register is triaged.

## Concern Register

- C014 resolved: the analyst projection redacts mechanism values, protected
  representation content and hashes, protected patches, and protected action
  payloads. Canary tests cover the complete serialized document.
- C015 resolved: snapshots come from canonical event-prefix replay and node
  inspection follows the selected event's exact state revision.
- C016 resolved: narrative derives from realized status, remediation, closure,
  and denied attempts rather than the requested intervention arm.
- C017 resolved for the development host: every run endpoint enforces the
  approved Tailscale login allowlist; browser hardening headers are present;
  live remains disabled on the Mac.
- C018 resolved: the accepted Python environment is pinned in
  `requirements-dev.lock`; the separately developed `llm_client` remains an
  explicit optional boundary.
- C019 deferred: aggregate spend needs a durable ledger before live access is
  enabled on an always-on host. Single-process live mutual exclusion is
  enforced and tested.
- C020 deferred: a real connected/multiscale graph remains product scope after
  the evidence instrument is truthful.

## Completion Evidence

- strict type checking passes across 22 source files;
- 19 tests pass, including causal-runtime, presentation, storage, authorization,
  concurrency, restart, and adversarial redaction gates;
- a fresh speed-pressure run retained 63 events and 13 event-time snapshots
  without any credential canary crossing the analyst document;
- browser inspection confirmed exact revision/activation selection and
  truthful outcome-derived narrative;
- retained roots use mode `0700` and documents use `0600`;
- the stale pre-repair sample was moved to recoverable trash and replaced.
