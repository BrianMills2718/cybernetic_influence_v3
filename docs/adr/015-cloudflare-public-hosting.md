# ADR-015: Cloudflare public hosting with an explicit stateful boundary

## Status

Accepted — 2026-09-13. Amended by ADR-016 (2026-09-15): live authoring,
execution, and durable run state run on the personal VPS behind the Cloudflare
tunnel instead of a Cloudflare durable service. The rest of this decision
stands.

## Context

The public Waltzman workbench depended on a FastAPI service running on the Mac
Mini. When that machine is off, `https://brianmills.dev/waltzman/` falls
through to the unavailable origin and returns 530. The committed
`public/waltzman/` bundle already contains the retained cases, replays,
methodology, review dossier, and World Substrate sidecar. It also calls the API
for authoring, newly executed simulations, and run-store access.

Cloudflare Workers Static Assets can serve the retained bundle directly.
Cloudflare Container disks are ephemeral and restart from the image after a
sleep or platform stop, so moving the existing SQLite/file run store into a
Container without a durable-storage adapter would silently weaken the product.

## Decision

Cloudflare is the canonical public host. Publish the committed retained-review
bundle first at `/waltzman/*`, with no origin fallback and no SPA fallback that
could disguise missing `api/*` routes as successful HTML responses. The
frontend's existing fail-visible behavior reports the live simulator as
unavailable while the retained evidence remains inspectable.

Preserve the retained bundle byte-for-byte. A bounded Worker routing shim maps
the frontend's historical `/waltzman/assets/*` requests to the corresponding
files directly under `/waltzman/` and returns explicit JSON 404 responses for
the unavailable `/waltzman/api/*` boundary.

This recovery deployment does not claim live authoring, execution, or durable
run creation. A later stateful deployment must retain run and draft state in a
Cloudflare durable service and prove restart survival before those controls are
advertised as available. Do not keep the Mac Mini as a hidden fallback.

## Consequences

- The retained public workbench and its self-contained evidence no longer
  depend on the Mac Mini.
- API-dependent controls remain visibly unavailable rather than failing through
  an offline origin or pretending that static hosting implements them.
- Restoring live execution requires an explicit storage migration and a
  representative restart-survival check.
- ADR-003 remains the history of the private development host; it no longer
  governs the public Waltzman request path.
