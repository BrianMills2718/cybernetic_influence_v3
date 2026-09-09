---
type: Index
title: Cybernetic Influence V3 Project Composition
description: Routing index compiled from the canonical Cybernetic Influence V3 project-membership manifest.
updated: 2026-09-09
source_revision: 488c7960c1e466f5c6fc650ed50b9923d09210ae
---

# Cybernetic Influence V3 project composition

Canonical source: [`project-membership.yaml`](../../project-membership.yaml).
This page reproduces only fields declared in that manifest. If this page and
the manifest disagree, the manifest governs.

## Declared members

| Repository ID | Role | Function | Workspace | Authority entrypoints | Contract seams |
| --- | --- | --- | --- | --- | --- |
| `cybernetic_influence_v3` | `primary` | `current_product` | `default` | `CLAUDE.md`; `docs/GOAL.md`; `docs/ROADMAP.md` | None declared |
| `llm_client` | `supporting` | `shared_infrastructure` | `on_claim` | `CLAUDE.md`; `README.md` | `python-package:llm_client` |
| `cybernetic_influence_v2` | `retained_predecessor` | `predecessor_reference` | `hidden` | `CLAUDE.md`; `README.md`; `PROGRESS.md` | None declared |
| `cybernetic_influence` | `historical_predecessor` | `predecessor_reference` | `hidden` | `CLAUDE.md`; `README.md` | None declared |

## How to use this route

Resolve a repository by its exact `repository_id`, then open one of the
manifest-declared authority entrypoints shown above. This page does not infer
responsibility beyond the declared role, function, workspace, entrypoints, and
contract seams.
