---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-08-31
updated: 2026-08-31
depends_on:
  - docs/ROADMAP.md
  - project-membership.yaml
---

# Slice 36: open the human project, not a repository maze

## Outcome

Brian opens VS Code, runs **Projects: Open Project**, selects **Cybernetic
Influence V3**, and receives one project window whose Explorer initially shows
only the current V3 implementation. Supporting repository worktrees appear in
that same workspace only while the exact agent session has a healthy write
claim for them. Earlier implementation lineages remain discoverable without
becoming normal picker entries or workspace folders.

## Existing seams

- Project Meta owns stable identities, lifecycle, repository placement, and the
  pointer to this repository's project membership manifest.
- `project-membership.yaml` owns Cybernetic project-context membership and
  roles.
- Ecosystem Ops owns the generated `.code-workspace` projection and VS Code
  picker extension.
- Repository-native instructions, roadmaps, code, and claims remain
  authoritative for implementation. The project composition does not copy
  them.

## Contract

The manifest has one project ID, one display name, one context epoch, one
revision policy, and a non-empty repository list. Each repository uses an exact
Project Graph repository ID and declares:

- one project-context role;
- workspace presentation (`default`, `on_claim`, or `hidden`);
- repository-native authority entrypoints; and
- any cross-repository contract seam relevant to this project.

Exactly one member is `primary` and `default`. Unknown or duplicate repository
IDs, multiple primary members, absolute authority paths, a missing manifest,
or a project-record/manifest ID mismatch fail loudly.

The Cybernetic pilot contains:

| Repository | Role | Workspace presentation |
| --- | --- | --- |
| `cybernetic_influence_v3` | `primary` | `default` |
| `llm_client` | `supporting` | `on_claim` |
| `cybernetic_influence_v2` | `retained_predecessor` | `hidden` |
| `cybernetic_influence` | `historical_predecessor` | `hidden` |

The predecessor roles do not claim that V2 is currently deployed or that
either predecessor is archive-safe. The roadmap owns that unresolved
disposition.

## Slices

1. **Canonical composition.** Add this manifest, a typed schema and Project
   Graph pointer, plus validation proving one editable membership source.
2. **Picker consumption.** Extend the existing Ecosystem Ops workspace helper
   to resolve project records and install a small VS Code extension exposing the
   Quick Pick command.
3. **Authentic workflow.** Install the extension locally, open the Cybernetic
   project through the command, inspect the generated workspace, then exercise
   a same-session supporting-claim fixture and confirm lineage repositories stay
   hidden.

## Acceptance

1. Project Meta validation accepts the checked-in Cybernetic manifest and
   rejects missing, malformed, ambiguous, or unknown-repository compositions.
2. The picker lists active `project` records only; it does not list the active
   repository catalog.
3. Selecting Cybernetic opens one generated workspace with the claimed V3
   worktree when healthy, otherwise its canonical checkout.
4. A same-session `llm_client` claim adds its worktree; releasing it removes the
   folder on regeneration.
5. V1 and V2 never appear as normal picker choices or workspace folders.
6. The installed VS Code command is exercised from the same extension
   entrypoint the operator will use, with an inspectable generated workspace as
   evidence.

## Disproof

The pilot fails if Cybernetic-specific IDs are hard-coded into the extension,
the picker lists repositories, a workspace view becomes an authority for
membership, or a predecessor appears merely because it remains locally
available.

## Non-goals

- moving or archiving any repository;
- deciding whether V2 still has operational consumers;
- representing every human project in the ecosystem;
- automatically invoking workspace regeneration from every claim hook; or
- replacing repository-native planning, instructions, or Git authority.
