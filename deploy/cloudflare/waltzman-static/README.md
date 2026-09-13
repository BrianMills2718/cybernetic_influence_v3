# Cloudflare retained-review deployment

This deployment restores the public Waltzman retained-evidence and replay
surface at <https://brianmills.dev/waltzman/> without the Mac Mini in the
request path.

```bash
npx --yes wrangler@4.131.1 deploy \
  --config deploy/cloudflare/waltzman-static/wrangler.jsonc
```

The asset root is the repository's `public/` directory, so the route prefix
maps directly to `public/waltzman/`. A small Worker preserves the former
FastAPI static mapping by rewriting `waltzman/assets/*` to the files retained
directly under `public/waltzman/`. It also returns an explicit JSON 404 for
`api/*`; the frontend catches that response and labels the live simulator
unavailable while retaining the committed case data, replay, methodology,
review dossier, and World Substrate sidecar.

This is a recovery surface, not the stateful simulator deployment. Natural-
language authoring, new runs, and persistent run storage remain unavailable
until the API moves to a Cloudflare runtime with durable storage.
