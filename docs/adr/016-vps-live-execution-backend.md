# ADR-016: Live authoring and execution run on the personal VPS

## Status

Accepted — 2026-09-15. Amends ADR-015 (supersedes only its durable-storage
clause: "A later stateful deployment must retain run and draft state in a
Cloudflare durable service").

## Context

ADR-015 moved the public request path for `https://brianmills.dev/waltzman/` to
Cloudflare and published the retained-review bundle, leaving live authoring,
new runs, and the run store unavailable until a durable state boundary existed.
It assumed that boundary would be a Cloudflare durable service. The simulator's
state is a file/SQLite run store, authoring drafts, experiments, the shared
`llm_client` observability database, and route-certification observations;
moving all of that onto a Cloudflare storage adapter would be a rewrite of the
storage layer, not a deployment.

Project Meta's `docs/ops/DEPLOYMENT_HOSTING_POLICY.md`, section "Netcup VPS as
the durable backend host (adopted 2026-09-15)", now makes Brian's personal
netcup VPS (`BrianMills2718/personal-vps`) the home for personal workloads that
need a long-running process or durable local disk, keeps Cloudflare as the edge
and static host, requires public entry through an outbound Cloudflare tunnel,
and requires public demos to stay public with sign-in-free spend controls.
Rule 6 of that section requires this repository's decision to be updated
before deploying.

## Decision

1. Cloudflare remains the canonical public host. The Worker in
   `deploy/cloudflare/waltzman-static/` keeps serving the committed
   `public/waltzman/` bundle byte-for-byte.
2. The live simulator (`cybernetic_influence.public_waltzman:app`) runs in a
   Docker container on the personal VPS (`deploy/vps/Dockerfile`; compose and
   operations in personal-vps `apps/waltzman/`). Its entire state lives on the
   VPS disk under `/srv/apps/waltzman/data`, which the host's nightly backup
   copies off-host.
3. The Worker proxies `/waltzman/api/*` to `https://waltzman-api.brianmills.dev`,
   a hostname served only through the VPS's Cloudflare tunnel; the container
   publishes no host port. Method, query, body, and the visitor address
   (`CF-Connecting-IP`) are preserved. When the backend is unreachable the
   Worker answers a JSON 503 `live_simulator_unavailable`, so the page stays in
   its retained-review mode and says so, never blank.
4. Live LLM routes are OpenRouter (`openrouter/openai/gpt-5.6-sol`) so the host
   needs no ChatGPT/Codex login. Routes are advertised only with current
   certifications produced on the host by `scripts/certify_codex_luna.py`
   (real calls). `LLM_CLIENT_REVISION` is pinned to the installed `llm_client`
   checkout so certifications and the application agree.
5. The demo has no login, password, access code, or Cloudflare Access. Spend is
   bounded by `cybernetic_influence.public_spend_controls`: a per-visitor hourly
   limit on starting live runs and authoring requests, a global daily cap on
   each (persisted on the data disk), the existing per-call `max_budget`
   ceilings and call-count limits, and `llm_client`'s monthly project budget as
   a hard stop. A refusal is HTTP 429 with a plain-language `detail` that the
   page renders in its status line. Read, replay, progress, and scripted
   requests are uncapped. Anonymous deletion of retained runs, assays, and
   experiments is refused on the public app; operators delete on the host.

## Requirements before live controls are advertised

- A completed run must survive both a container restart and a host reboot and
  still be listed by `https://brianmills.dev/waltzman/api/runs`.
- A request past the daily cap must be refused with the visible message.
- The data directory must appear in the off-host backup.
- A fresh run must complete end to end through the public page in a browser.

## Consequences

- Live authoring and execution return without restoring the Mac Mini, which
  stays history only (`docs/operations/mac-mini.md`).
- The public page now depends on one VPS for live work; its retained review does
  not. A VPS outage degrades to retained review, visibly.
- Route certifications lapse after seven days; personal-vps
  `apps/waltzman/refresh-certification.sh` re-certifies on a timer.
- Wrong-when: revisit if the VPS-hosted service has more than two unplanned
  outages in 30 days, or if this route's monthly OpenRouter spend exceeds $20
  despite the caps (the Project Meta policy's own triggers).
