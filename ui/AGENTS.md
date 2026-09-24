# UI surface routing

`registry.yaml` is the repository's UI inventory authority. Read it before
planning, creating, replacing, or retiring a human-facing surface -- including
when a backend or API change might require a corresponding frontend change.
This repository has two real surfaces already; a third landing page or app
is very unlikely to be the right answer.

- Patch the registered canonical surface by default. Extend `operator-review-app`
  (edit `frontend/src`, not the generated `web/` output) or
  `public-waltzman-demo`, do not create a parallel one.
- If a change genuinely needs a new surface, add it to `registry.yaml` as
  `lifecycle: candidate` first, with a stated reason it can't be an extension
  of an existing surface, before writing its files.
- This directory's coupling in `../scripts/relationships.yaml` requires
  reading this registry before editing `frontend/src/**`, `web/**`,
  `public/waltzman/**`, or the API's UI-serving routes in
  `src/cybernetic_influence/api.py` -- the edit is gated on it, not just
  advisory.
