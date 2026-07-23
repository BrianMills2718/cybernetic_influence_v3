# ADR-005: Mechanisms Read Only Declared Stored Representations

## Status

Accepted — 2026-07-23.

## Context

The causal core allowed an exact mechanism to read declared facts and the
representation carried by its triggering effect. It could not read a separate
stored representation such as a policy copy physically or logically attached
to an access controller.

Encoding policy authorization as an abstract edge or an intrinsic person
property would collapse information, permission, technical capability, and
realized outcome. Giving mechanisms a global representation lookup would
instead create the non-local explanatory search the core is intended to avoid.

## Decision

Add `read_representation_ids` to an exact mechanism's declared authority
surface.

- every declared ID must resolve in the scenario state;
- the mechanism context receives defensive copies of only those
  representations;
- an undeclared read fails with `StateAccessViolation`;
- exact mechanism events retain the declared representation-read surface;
- causal graph projection links the mechanism to the stored representation;
- analyst projection exposes the relationship while applying the existing
  visibility redaction to protected content and hashes.

The triggering representation remains separate from stored representation
reads. A mechanism still cannot enumerate or search global information.

## Consequences

A policy document can now be modeled as information on a concrete carrier that
an exact controller consults. Changing that representation can change an
authorization result without pretending that the document executes an action.

This is intentionally not a knowledge base, wiki retrieval layer, ontology
registry, or game-master search mechanism. Dynamic replacement of a mechanism's
bound policy ID remains future work until a grounded scenario requires it.
