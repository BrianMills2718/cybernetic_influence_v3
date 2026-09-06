---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-08-23
updated: 2026-09-06
depends_on:
  - docs/plans/031-cso-stabilization-flagship.md
  - docs/plans/033-evasion-space-case.md
  - docs/handoffs/2026-08-23-waltzman-demo-session.md
  - docs/research/001-from-minds-to-coordination.md
---

# Slice 34: keep the demo correct without anyone watching it

## The outcome this serves

Rand Waltzman opens one URL, understands what it is without help, reads a run
that executes the framework in his own paper, and finds nothing that is untrue.
He is a domain expert and the author of the source; an error he catches costs
more than any defect a general reader would find.

The demo currently reaches that bar. This slice is about it *staying* there
while work continues, because on 2026-08-23 it did not: a chapter described an
experiment the run was not performing, in correct and well-rendered prose, and
every check in place passed.

## Why the existing checks were not enough

| Defect found 2026-08-23 | What passed while it was true |
| --- | --- |
| Shared link served an unstyled page with dead navigation | page 200, API 200, deployed commit matched |
| A chapter described a superseded experiment | every element rendered; text internally coherent |
| Every coordination measure read zero | the analysis "succeeded" and returned a result |
| Saved simulations became unopenable | the change typechecked and its own tests passed |
| The trailing-slash redirect did nothing | the deploy reported success |

The pattern is one thing: **each check confirmed a mechanism worked, and none
confirmed the result was true.** Every fix below closes that gap for one class,
and each was written only after a real defect escaped.

## What this slice installs

1. `scripts/check_page_claims_match_evidence.py` — the numbers the page states
   must match the retained projection, the detector's recorded words must be
   present and must differ between the two arms, and prose describing a
   superseded experiment fails the build. Verified to catch both defect shapes
   by reintroducing them.
2. `scripts/check_public_assets.py` — resolves the page's own asset references
   from the exact URL a reader is given. Already in the deploy path.
3. `scripts/audit_public_demo.py` — runs all of the above plus control
   visibility and certification margin, and exits non-zero if any fails.
4. `scripts/install_demo_audit_job.sh` — schedules that nightly at 04:15.
5. The deploy refuses to publish when the claims check fails.
6. `scripts/check_served_bundle_matches_source.py` — builds `frontend/src` into a
   scratch directory and byte-compares it against what the demo serves. Added
   2026-08-26 after a cold-start pass found `make ui-build` writing to `web/`
   (the local app's root) while the public demo serves `public/waltzman/`, with
   nothing bridging them: the served graph bundle was frozen at its 2026-08-16
   content for ten days while every build reported success. Deliberately does
   not compare the two directories to each other, which would pass whenever both
   are equally stale. `make ui-sync` rebuilds and copies. Verified to fail by
   reintroducing a stale served bundle. Blocking in the deploy path and in
   `make check`, both of which run here. Deliberately not in the nightly audit:
   that runs on the deployment host, which receives the frontend source but not
   its `node_modules`, so the check could not build there and would fail every
   night for a reason that has nothing to do with the demo.

Every one of these is offline or read-only. **No model calls, so the audit costs
nothing and can run as often as is useful.**

## The review cadence

- **Every deploy:** claims, assets, served-bundle-matches-source, deployed-commit
  match. Automatic; blocking.
- **Nightly:** the full audit, including control visibility across widths and
  the authoring certification margin. Automatic; logged; non-zero on failure;
  and the verdict is written into the demo's card on the project deck, so a
  failure is visible on the page that actually gets opened rather than in a
  log on the deployment host. A failing audit names the failing checks and
  says not to share the demo until they are fixed. Both the passing and the
  failing rendering were exercised on the live deck.
- **Before sharing with anyone new:** one human walk of the seven-step case
  study and one Create run. Not automatable — comprehension is the thing being
  tested, and an agent reviewing its own work is the weakest possible reviewer.
- **When the flagship changes:** rebuild both projections, then run the claims
  check. It is the specific guard against the failure that happened.

## Pass/fail

- Reintroducing any 2026-08-23 defect fails at least one automated check.
- The nightly job runs under the scheduler and records an outcome.
- A deploy that would publish an unsupported claim is refused.

## What remains, and what it costs

Under a $1 live-spend cap, the remaining work is all zero-cost except one item:

| Item | Cost | State |
| --- | --- | --- |
| Second evasion pair, to see whether the misread reproduces | ~$1.50 | **blocked by the cap** |
| Authoring says "2-3 minutes" and takes ~5 with a silent retry | none | open |
| Generated analyses on drafts predating 35d6ba8 still request unsatisfiable evidence | none | open |
| Header brand wraps to two lines at 1280 | none | cosmetic |

The evasion result therefore stands as a single pair, and the page says so.
That is the honest position and it does not need spend to hold.

## Explicitly not in scope

Broadening the audit into a general web-quality suite. Every check here was
bought by a specific failure; adding checks that no defect motivated is how a
suite becomes noise that nobody reads.
