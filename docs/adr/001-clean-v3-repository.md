# ADR-001: Clean V3 Repository

## Status

Accepted — 2026-07-23.

## Context

The V2 repository proved the causal core, active runtime, exact mechanisms,
durable trace semantics, service-desk intervention, and operator inspection.
It also retained a legacy V2 simulator, historical artifacts, compatibility
surfaces, and two overlapping user interfaces. Continuing there made product
identity and architectural authority ambiguous.

## Decision

V3 is a new repository with fresh history. Migration is whitelist-only:

- borrow the proven causal core and active runtime;
- borrow one complete service-desk reference scenario;
- use `llm_client` as the provider boundary;
- build one small operator-first API and interface;
- do not import either earlier repository at runtime;
- do not migrate artifacts, compatibility adapters, old tabs, or historical
  planning bulk.

The product is called the Simulator. “V3” identifies repository lineage, not a
second user-facing mode.

## Consequences

Earlier repositories remain inspectable history. Compatibility is intentionally
broken. Any capability not demonstrated through the new vertical slice must be
reintroduced deliberately rather than copied by default.

This decision would be superseded only if an essential capability cannot be
expressed without importing an earlier runtime wholesale.
