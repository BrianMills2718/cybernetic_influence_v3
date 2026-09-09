---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-09-09
updated: 2026-09-09
depends_on:
  - ../ROADMAP.md
  - ../GOAL.md
  - 037-waltzman-outreach-funnel.md
  - 038-living-replay-generated-worlds.md
---

# Plan 39: Cloudflare-native Waltzman deployment

## Goal

Move the sendable Waltzman demo off the Mac-mini tunnel without rewriting the
simulator: Cloudflare serves the hook/replay assets at the edge and forwards the
same-origin authoring/run API to one Linux Container running the existing FastAPI
+ Concordia service.

The public route is `https://brianmills.dev/world-substrate-visualization/`.
The path must remain available while the Mac mini is powered off.

## Architecture

```text
brianmills.dev/world-substrate-visualization/
        -> Cloudflare Worker
           -> static hook/replay assets from Workers Static Assets
           -> /api/* to one named Cloudflare Container
                    -> existing public FastAPI application
                    -> existing authoring/compiler/Concordia runtime
```

No new simulation engine, authoring system, or consequence authority is created.
The Worker is routing/deployment infrastructure only.

## Safety and provenance

- `llm_client` remains a separately versioned private provider boundary. Workers
  Builds materializes one exact pinned revision using the existing read-only
  deploy key; the key is never copied into the Docker image.
- The runtime receives provider credentials only from Cloudflare Worker Secrets.
- The existing route-certification gate remains intact. Missing/stale
  certification must make authoring unavailable rather than silently selecting a
  model.
- The Container has outbound internet access only because the existing provider
  client needs HTTPS egress.
- Cloudflare Container disk is ephemeral. For this first stakeholder gate the
  named backend stays active for two hours after activity; current-session files
  remain available while it runs. Durable cross-restart retention is explicitly
  deferred to R2/FUSE or a storage adapter rather than being implied.

## Build and deploy

Workers Builds uses GitHub `main` as production authority.

Build command:

```bash
npm run cf:prepare
```

Deploy command:

```bash
npx wrangler deploy
```

Required protected build variable/secret:

- `LLM_CLIENT_DEPLOY_KEY` — existing read-only SSH deploy key for the private
  provider repository.

Required runtime secret before live generation:

- `OPENROUTER_API_KEY`

Required current certification material before the app may advertise Sol:

- a certification observation bundle materialized into `.route_certification/`
  at build time;
- `CYBERNETIC_INFLUENCE_CERT_SOL`;
- `CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL`.

The general-world fresh-run path does not require the legacy coordination
certification group; `resolve_live_configuration()` uses the globally advertised
model catalog and authoring has its own separate certification contract.

The certification values are evidence references, not a bypass. They are still
validated against exact schema digests, provider transport evidence, installed
`llm_client` revision, and the seven-day age limit at runtime.

## Acceptance

- [ ] Wrangler dry-run validates Worker, assets, Durable Object migration, and
      Container configuration without account credentials.
- [ ] The root `Dockerfile.cloudflare` builds with the pinned private `llm_client`
      checkout and imports the existing public application.
- [ ] `/world-substrate-visualization` redirects to the trailing-slash route.
- [ ] static hook/replay assets do not require a Container cold start.
- [ ] `/world-substrate-visualization/api/*` strips only the public prefix and
      reaches the unchanged FastAPI routes.
- [ ] missing provider/certification material leaves generation visibly
      unavailable; retained/static surfaces still load.
- [ ] no credential, deploy key, certification generation payload, or provider
      response is committed to Git.
- [ ] after the Cloudflare Git connection/secrets are configured, the public
      route returns HTTP 200 with the Mac off and one fresh natural-language run
      reaches the living replay.

## Verification so far

- `pytest -q tests/test_cloudflare_deploy.py`: 4 deployment contract tests passed.
- `npm run cf:check`: Wrangler 4.130.0 dry-run passed, read 15 static assets, validated bindings/migration, and built the complete Container image.
- The corrected Docker build context includes `src/`, `public/`, `web/`, the exact private `llm_client` checkout, and the (currently empty) route-certification store.
- The built image reports the exact pinned `llm_client` SHA from inside the image and imports `cybernetic_influence.public_waltzman:app`.
- A local Container HTTP smoke returned 200 for `/` and `/api/config`; the hook/input markers were present. With `CYBERNETIC_INFLUENCE_LIVE=1` but no certification bundle, the app advertised zero authoring models, proving the existing route gate fails closed.
- Public `https://brianmills.dev/numogram/` returns HTTP 200 while the Mac-backed root route returns Tunnel 1033, proving path-specific Workers can bypass the powered-off Mac origin on this domain.

## Stop condition

Do not add persistence, R2/FUSE, autoscaling, a second API, or new simulation
semantics merely to complete the first Cloudflare stakeholder deployment. If
cross-restart retention becomes a real outreach requirement, earn it as a
separate storage slice.
