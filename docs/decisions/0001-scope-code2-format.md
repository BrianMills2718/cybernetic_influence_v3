---
description: Why the code2 format covers only the public spend controls and why make check is split
---

# 0001 Scope the code2 format to the public spend controls

Date: 2026-11-17
Status: accepted
Source: inferred by agent, 2026-11-17 (Brian, 2026-11-17: "option B is what i want").

## Context

Active vision parts adopt the code2 format now. This repository has a large source tree under strict mypy, a frontend build and a long `make check`. Lockstep scans one source folder.

## Decision

- One capability, `public-spend-controls` (ADR-016), is specified; its existing tests carry `req` markers. A thin `code2_scope/` folder re-exports it so the source file does not move.
- The old `check` target is renamed `full` (unchanged stages). `check` runs Lockstep, OpenSpec validation and the scoped tests. Lockstep is pinned through `uvx` in the Makefile, so `pyproject.toml` dependencies are untouched.
- Older documentation systems (`meta-process/`, `.company-planning/`, `.project-brain/`) are left in place.

## Consequences

`make check` takes seconds; the full gate runs as `make full` (CI still runs the repository's workflow). Other capabilities adopt the format when next changed.

## Wrong if

The scoped `check` passes while `make full` fails on the public spend controls, or CI is switched to `make check` and lets unrelated regressions through.
