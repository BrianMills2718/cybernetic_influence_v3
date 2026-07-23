# ADR-002: Durable Local Runs Before Remote Hosting

## Status

Accepted — 2026-07-23.

## Context

The first slice returned a complete run only in the HTTP response. Refreshing
the page or restarting the server discarded the operator's path back to that
evidence. Hosting this behavior on another machine would make it available but
would not make it dependable.

## Decision

Store each run as one versioned JSON document under a configurable local run
directory. Writes use a temporary file plus atomic replacement. A run identity
is written before execution; an incomplete record found during a later server
start is marked interrupted. Deletion moves a run to a private trash directory
instead of unlinking it.

The API exposes list, retrieve, and delete operations. The browser treats the
server as authoritative and never uses browser-local persistence.

Do not introduce a database, task queue, user accounts, cross-host
synchronization, or public deployment in this slice.

## Alternatives

- SQLite would provide richer queries and transactions but adds schema and
  migration work before query requirements exist.
- Browser storage would not retain authoritative evidence across devices.
- Immediate Mac Mini hosting would add operations without repairing the
  evidence-retention boundary.

## Consequences

Completed and failed runs survive refreshes and server restarts. Individual
documents remain inspectable and portable. Concurrent multi-process writers and
large-scale querying are intentionally unsupported; evidence that those are
needed would supersede this decision.
