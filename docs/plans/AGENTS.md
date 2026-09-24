# Implementation Plans

[README.md](README.md) is the index of what is actually being worked on;
[../ROADMAP.md](../ROADMAP.md) is the canonical authority for direction and
carries each slice's real status. Read those two. This file only records the
local conventions.

## Conventions

- Plans are `NNN-kebab-case-name.md`, numbered in the order they were opened.
- Each plan opens with YAML frontmatter: `doc_role: implementation_plan`,
  `authority: bounded_design`, `status`, `created`, `updated`, and `depends_on`
  listing the roadmap, ADRs, and research notes it is bounded by.
- `status` is the plan's own lifecycle (`proposed`, `active`, `paused`,
  `implemented`, `complete`). The roadmap table is what a reader trusts; keep
  the two consistent, because a plan left `active` after its slice shipped is
  the drift this file exists to prevent.
- Commit plan-owned work with a `[Plan #N]` prefix, and `[Trivial]` for changes
  under about twenty lines that add no files and do not touch `src/`.
- [TEMPLATE.md](TEMPLATE.md) is the starting point for a new plan. Its header
  block predates the YAML frontmatter above and has not been reconciled; follow
  an existing recent plan for the frontmatter and the template for the body.

There is no `complete_plan.py`. Completing a plan means updating its `status`,
updating its row in the roadmap, and closing the lane with `make session-close`.
