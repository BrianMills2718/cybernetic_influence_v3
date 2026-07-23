# ADR-004: Analyst Evidence Is a Visibility-Safe Temporal Projection

## Status

Accepted — 2026-07-23.

## Context

The causal state correctly distinguishes `public`, `analyst`, and `mechanism`
visibility, but the first API serialized complete final entities and
representations. This exposed mechanism-only credential material to the UI and
retained files. The timeline also paired early events with final state, and its
human summary was selected by intervention arm rather than derived from the
realized outcome.

These are boundary errors, not parameters to tune. They make an understandable
trace less faithful than the canonical evidence beneath it.

## Decision

Treat the operator as an analyst, not a mechanism:

- public and analyst values may cross the API boundary;
- mechanism-only values remain addressable but their values, content, and
  hashes are redacted;
- raw events receive the same projection;
- each timeline item names the exact activation that produced it when one
  exists;
- retained state snapshots are reconstructed from canonical commit patches and
  keyed by state revision;
- node inspection uses the selected event's revision, never implicit final
  state;
- narrative summaries derive from the realized readout and recorded events.

Keep the complete protected state inside the causal/runtime contracts. Do not
weaken those contracts or create a second mutable world state for the UI.

## Consequences

Analyst documents cannot replay protected state independently because the
canonical digests bind information they cannot see. They remain traceable to
exact event and revision identities. Full protected checkpoints are an
internal forensic surface and are not retained by this operator API.

Existing retained analyst documents created before this boundary must be
removed from normal history and regenerated.

