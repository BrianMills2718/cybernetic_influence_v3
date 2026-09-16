# Cloudflare public Waltzman deployment

This Worker serves the public Waltzman workbench at
<https://brianmills.dev/waltzman/> (ADR-015, amended by ADR-016).

```bash
npx --yes wrangler@4.131.1 deploy \
  --config deploy/cloudflare/waltzman-static/wrangler.jsonc
```

The asset root is the repository's `public/` directory, so the route prefix
maps directly to `public/waltzman/`. The Worker preserves the former FastAPI
static mapping by rewriting `waltzman/assets/*` to the files retained directly
under `public/waltzman/`.

`/waltzman/api/*` is proxied to the live simulator at
`https://waltzman-api.brianmills.dev` (method, query, body, and the visitor's
`CF-Connecting-IP` preserved). That hostname reaches the container on Brian's
personal VPS only through the `personal-vps` Cloudflare tunnel; build, deploy,
spend caps, certification refresh, and backups are documented in
`BrianMills2718/personal-vps` `apps/waltzman/README.md` and the image is
`deploy/vps/Dockerfile`.

If the backend is unreachable the Worker returns a JSON 503
`live_simulator_unavailable`; the page then labels the live simulator
unavailable while the committed case data, replay, methodology, review dossier,
and World Substrate sidecar stay inspectable.
