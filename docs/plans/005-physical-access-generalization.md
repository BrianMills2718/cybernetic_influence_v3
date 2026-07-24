---
doc_role: historical_evidence
authority: evidence
status: complete
updated: 2026-07-23
---

# Slice 5: Physical Access Generalization

**Status: Complete — 2026-07-23.**

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

- C021 resolved: one common analyst-document seam now serves both scenarios;
  scenario outcome/readout logic remains local.
- C022 resolved: the API and UI use a closed two-scenario catalog with no plugin
  or authoring framework.
- C023 verified invariant: matched arms and a forced-crossing adversarial test
  separate authentication, authorization, latch operability, and entry.
- C024 verified invariant: badge/verifier canaries, content, and hashes remain
  absent from prompts, retained documents, API responses, causal graph
  projections, and browser DOM.
- C025 passed: browser inspection distinguishes policy denial from physical
  latch failure in the headline and two-sentence account.
- C026 deferred: multiscale aggregate visualization remains a later vertical
  slice after two grounded scenarios prove the reusable node/route semantics.

## Audit Result

The accepted 0.5 environment passes strict typing across 23 source files and 25
tests under both Python 3.12 and Mac Python 3.14. The pinned dependencies are
consistent and have no known published vulnerabilities.

The three zero-cost reference arms produce:

- authorized access: 30 events, seven temporal snapshots, and a committed
  hallway-to-equipment-room crossing;
- authorization absent: 20 events, five snapshots, successful authentication,
  policy denial, a locked latch, and no crossing;
- latch jammed: 20 events, five snapshots, successful authentication and
  authorization, physical actuation failure, and no crossing.

A forged badge cannot inherit policy authorization. A forced crossing after
policy denial remains in the hallway. Removing the mechanism's bound policy
representation makes scenario validation fail rather than causing a global
lookup or silent default.

The Mac Mini runs exact commit `dc64041` with live execution disabled and the
Tailscale identity allowlist enabled. All three retained samples reopened
unchanged after a forced service restart. A tailnet browser reopened the
jammed-latch sample with synchronized scenario controls, narrative, timeline,
nodes, routes, and person trace. Private file modes and unrelated Tailscale
routes remained unchanged.

## Historical Next-Slice Direction

Implemented by [Slice 6](006-reversible-multiscale-graph.md). This section
records the contemporaneous handoff and is not a current instruction.

Add the first execution-inert multiscale graph view over grounded scenario
members:

- render analytical boundaries as expandable aggregate nodes;
- derive aggregate inputs, outputs, state summaries, and event traces only from
  member evidence;
- let the operator move between the coarse boundary and exact people,
  information, objects, interfaces, and mechanisms;
- make information lost by the coarse view explicit;
- never schedule or execute an organization/boundary as an actor.

This should be a visual and evidentiary vertical slice over the existing
scenarios, not a new ontology registry or organization-agent framework.
