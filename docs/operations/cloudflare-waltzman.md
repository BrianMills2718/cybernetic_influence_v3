---
doc_role: operations
status: active
updated: 2026-09-09
---

# Cloudflare-native Waltzman deployment

## Target

The public stakeholder route is:

`https://brianmills.dev/world-substrate-visualization/`

The route is owned by a Cloudflare Worker named
`world-substrate-visualization`. Static assets are served at the edge; only the
same-origin `/api/*` path starts/contacts the backend Container.

This replaces the Mac-mini tunnel as the normal host for this path. Do not remove
or repurpose the Mac route merely to deploy this Worker; it remains rollback
infrastructure until the Cloudflare route has passed public HTTP/browser checks.

## Git authority

GitHub `main` is the deployable source. Workers Builds should be connected to
`BrianMills2718/cybernetic_influence_v3` with:

- production branch: `main`;
- build command: `npm run cf:prepare`;
- deploy command: `npx wrangler deploy --var BUILD_COMMIT:$WORKERS_CI_COMMIT_SHA`.

The Worker name in Cloudflare must match `wrangler.jsonc` exactly.

## Build material

Workers Builds needs the protected build secret `LLM_CLIENT_DEPLOY_KEY`. The
prepare script uses it only to fetch the exact pinned private `llm_client`
revision into the ignored `.llm_client/` build context. The key file is temporary
and is not copied by the Dockerfile.

A current route-certification bundle may be supplied as the protected build
secret `LLM_ROUTE_CERTIFICATION_ARCHIVE_B64`. If no bundle is supplied, the
image contains an empty certification store and the application must advertise
no certified authoring route.

## Runtime secrets

Configure these in Cloudflare Worker Variables & Secrets; never write their
values into Git or issue/PR text:

- `OPENROUTER_API_KEY`;
- `CYBERNETIC_INFLUENCE_CERT_SOL`;
- `CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL`;

The three certification values do not grant authority by themselves. The Python
service revalidates the corresponding observation records against the installed
`llm_client` revision, exact schema digests, transport evidence, and age limit.

## Storage boundary

The Container is pinned to Cloudflare `basic` (1 GiB memory / 4 GB disk). A
local boot of the exact image idled at about 290 MiB, already above Cloudflare
`lite`'s 256 MiB memory limit; leaving the instance type implicit would be an
invalid production assumption.

The first Container deployment uses the existing filesystem-backed run/draft
stores. Cloudflare Container disk is ephemeral across container sleep/restart.
The Worker keeps the one public backend instance active for two hours after
activity, which is adequate for a bounded stakeholder session but is not durable
persistence.

Do not describe this deployment as durable saved-world storage. R2/FUSE or an
explicit storage adapter is a later slice if outreach proves it necessary.

## Pre-deploy verification

From a clean worktree with `.llm_client/` materialized at the pinned revision:

```bash
npm ci
npm run cf:check
python -m pytest -q tests/test_cloudflare_deploy.py tests/test_public_waltzman.py
```

`cf:check` performs a Wrangler dry run and builds the Container image locally;
it does not require Cloudflare account credentials.

## Public smoke test

After Workers Builds deploys `main`:

1. verify `/world-substrate-visualization` redirects to the trailing-slash URL;
2. verify the trailing-slash URL returns HTTP 200 while the Mac is off;
3. verify the first viewport shows the Waltzman hook and natural-language input;
4. verify `/api/config` is same-origin and only advertises routes with valid
   certification material;
5. generate one Waltzman-relevant scenario, approve it, run it, and reach the
   living replay;
6. verify no request falls through to Cloudflare Tunnel error 1033.
