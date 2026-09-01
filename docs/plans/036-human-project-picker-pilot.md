---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-08-31
updated: 2026-09-01
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

The predecessor roles preserve project lineage only. V1 and V2 are archived
source/evidence donors, not active capability authorities, normal picker
entries, or workspace folders.

## Slices

1. **Canonical composition.** Add this manifest, a typed schema and Project
   Graph pointer, plus validation proving one editable membership source.
2. **Picker consumption.** Extend the existing Ecosystem Ops workspace helper
   to resolve project records and install a small VS Code extension exposing the
   Quick Pick command.
3. **Authentic workflow.** Install the extension and exact-session hook locally,
   inspect the generated workspace, then exercise a real same-session supporting
   claim and confirm automatic add/remove while lineage repositories stay
   hidden.

## Acceptance

1. Project Meta validation accepts the checked-in Cybernetic manifest and
   rejects missing, malformed, ambiguous, or unknown-repository compositions.
2. The picker lists active `project` records only; it does not list the active
   repository catalog.
3. Selecting Cybernetic opens one generated workspace with the claimed V3
   worktree when healthy, otherwise its canonical checkout.
4. A same-session `llm_client` claim automatically adds its worktree; releasing
   it automatically removes the folder without manual VS Code workspace edits.
5. V1 and V2 never appear as normal picker choices or workspace folders.
6. The installed VS Code command is exercised from the same extension
   entrypoint the operator will use, with an inspectable generated workspace as
   evidence.

## Evidence

- Ecosystem Ops PR #40 installed the generic Codex hook and focused both-sign
  checks; all three CI jobs passed before merge at `26b9e7b`.
- A genuine clean `llm_client` claim changed the generated Cybernetic workspace
  from one folder to two through the installed hook. Sanctioned claim closeout
  changed it from two back to one and removed the proof worktree and branch.
- A fresh Codex TUI process loaded the configuration and recorded trust only for
  the new `PostToolUse` and `SessionStart` workspace-sync entries.
- VS Code's extension host records installed-command activation. The final
  operator-visible Quick Pick selection/open remains the one outstanding
  acceptance observation.

## Disproof

The pilot fails if Cybernetic-specific IDs are hard-coded into the extension,
the picker lists repositories, a workspace view becomes an authority for
membership, or a predecessor appears merely because it remains locally
available.

## Non-goals

- moving or archiving any repository;
- representing every human project in the ecosystem;
- replacing repository-native planning, instructions, or Git authority.
