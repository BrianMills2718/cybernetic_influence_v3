# Slice 5: Physical Access Generalization

**Status: In progress — 2026-07-23.**

## Frame

Test whether the causal core, active runtime, analyst projection, and one-page
inspector generalize beyond the service-desk scenario without first inventing a
scenario framework.

## Ontology Claim Under Test

A person, a policy, a credential, an access controller, a latch, and a room do
not jointly imply an abstract `can_enter` relation.

- the person can physically present a carried credential through an owned
  interface;
- an exact authenticator compares that presentation with protected verifier
  state;
- an exact authorization mechanism consults a concrete policy representation;
- a latch mechanism can fail independently of authentication and
  authorization;
- a crossing attempt changes location only when the physical boundary is open;
- sensors deliver observations after outcomes rather than granting the person
  omniscient state access.

The policy representation is evidence used by a mechanism. It is not an
executor, an intrinsic property of the person, or an outcome-causing abstract
edge.

## Intervention Arms

1. **Authorized access:** valid credential, authorizing policy copy, operable
   latch. The person may enter after the mechanisms unlock the boundary.
2. **Authorization absent:** valid credential and operable latch, but the
   policy copy does not authorize this person. Authentication succeeds while
   authorization and entry fail.
3. **Latch jammed:** valid credential and authorizing policy copy, but the
   physical latch cannot release. Authentication and authorization succeed
   while opening and entry fail.

These arms distinguish identity proof, normative permission, technical
availability, and realized physical outcome in the trace.

## Modality

Entity/interface identities, exact mechanism read/write surfaces, protected
credential redaction, event-time replay, and intervention isolation are
deductive. Whether the concise account makes the three failure layers obvious
to a human is exploratory and requires browser inspection.

## Slice Contract

- **Vertical scope:** choose physical access → activate one person → present a
  credential → authenticate → consult policy → actuate latch → attempt crossing
  → receive sensor feedback → inspect the exact temporal evidence.
- **Success:** the three arms produce distinct grounded outcomes; no credential
  value reaches the analyst document or person prompt; location changes only
  after a committed open-boundary state; policy denial and physical failure are
  narrated differently; retained restart/reopen remains exact.
- **Audit:** forged credential, authorization without authentication, stale or
  missing policy representation, jammed latch, crossing while locked,
  invented representation access, future-state leakage, cross-scenario API
  confusion, hidden paid calls, and hostile rendered content.
- **Cleanup:** share only presentation and API seams proven identical by both
  scenarios. Keep scenario construction, exact mechanisms, scripted oracle,
  and outcome readout local to the new scenario.
- **Done when:** direct causal tests, API tests, all prior regression gates,
  browser inspection, secret scan, and concern triage pass; the accepted commit
  is pushed and deployed.

## YAGNI Boundary

Do not add a general game-master abstraction, ontology registry, scenario DSL,
database, organization executor, aggregate graph algorithm, or stochastic
behavior merely to support this slice. One person and one short schedule are
enough to test the new causal distinctions.

## Concern Register

- C021 open: the current analyst-document builder has service-desk naming
  around otherwise general projection helpers. Extract only the seam exercised
  by the second scenario.
- C022 open: the current API and UI assume one scenario and one arm vocabulary.
  Add a closed two-scenario catalog, not a plugin framework.
- C023 adversarial invariant: a valid credential must not imply authorization,
  and authorization must not imply physical operability or entry.
- C024 adversarial invariant: protected badge/verifier content and hashes must
  not cross retained/API/browser boundaries.
- C025 exploratory: the human account must make the denial layer apparent
  without requiring raw-event inspection.
- C026 deferred: multiscale aggregate visualization remains a later vertical
  slice after two grounded scenarios prove the reusable node/route semantics.
