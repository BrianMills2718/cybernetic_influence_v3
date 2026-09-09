import { Container, getContainer } from "@cloudflare/containers";

const PUBLIC_PREFIX = "/world-substrate-visualization";
const BACKEND_INSTANCE = "public-waltzman";
const STATIC_CSP = "default-src 'self'; script-src 'self' 'sha256-QQJ2PGXNGfiy+vLgpHfeDVKbBTZHhHMuQIAgDnS5Cxw=' 'sha256-+qC1ebufslvFzqzMrGgJdeA3GN5JkfeFJbmP5joYTFY='; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'";

export class WaltzmanContainer extends Container {
  defaultPort = 8080;
  sleepAfter = "2h";
  enableInternet = true;
}

function backendEnvironment(env) {
  const values = {
    CYBERNETIC_INFLUENCE_LIVE: "1",
    CYBERNETIC_INFLUENCE_PUBLIC_ROOT: "/app/public/waltzman",
    CYBERNETIC_INFLUENCE_RUNS_DIR: "/data/runs",
    CYBERNETIC_INFLUENCE_BUILD_COMMIT: env.BUILD_COMMIT || "cloudflare",
    LLM_CLIENT_DATA_ROOT: "/data/llm_client",
    LLM_CLIENT_PROJECT: "cybernetic_influence_v3",
    LLM_CLIENT_REVISION: env.LLM_CLIENT_REVISION,
    LLM_CLIENT_OPENROUTER_ROUTING: "off",
    LLM_CLIENT_TIMEOUT_POLICY: "allow",
    LLM_ROUTE_CERTIFICATION_ROOT: "/app/route_certification",
  };
  for (const name of [
    "OPENROUTER_API_KEY",
    "CYBERNETIC_INFLUENCE_CERT_SOL",
    "CYBERNETIC_INFLUENCE_CERT_AUTHORING_SOL",
  ]) {
    if (env[name]) values[name] = env[name];
  }
  return values;
}

function stripPublicPrefix(request) {
  const url = new URL(request.url);
  url.pathname = url.pathname.slice(PUBLIC_PREFIX.length) || "/";
  return new Request(url, request);
}

async function proxyApi(request, env) {
  const backend = getContainer(env.WALTZMAN_CONTAINER, BACKEND_INSTANCE);
  await backend.startAndWaitForPorts({
    ports: [8080],
    startOptions: { envVars: backendEnvironment(env), enableInternet: true },
    cancellationOptions: { portReadyTimeoutMS: 30_000 },
  });
  return backend.fetch(stripPublicPrefix(request));
}

function staticAssetRequest(request) {
  const url = new URL(request.url);
  let relative = url.pathname.slice(PUBLIC_PREFIX.length) || "/";
  if (relative === "/review") relative = "/review.html";
  else if (relative === "/review/trace") relative = "/simulation-trace.md";
  else if (relative.startsWith("/assets/")) relative = relative.slice("/assets".length);
  url.pathname = relative;
  return new Request(url, request);
}

function secureStaticResponse(response, publicPath) {
  const headers = new Headers(response.headers);
  headers.set("Content-Security-Policy", STATIC_CSP);
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "no-referrer");
  headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()");
  if (publicPath.startsWith("/assets/")) headers.set("Cache-Control", "no-cache");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === PUBLIC_PREFIX) {
      url.pathname = `${PUBLIC_PREFIX}/`;
      return Response.redirect(url.toString(), 308);
    }
    if (!url.pathname.startsWith(`${PUBLIC_PREFIX}/`)) {
      return new Response("Not found", { status: 404 });
    }
    const relative = url.pathname.slice(PUBLIC_PREFIX.length);
    if (relative.startsWith("/api/")) return proxyApi(request, env);
    const assetResponse = await env.ASSETS.fetch(staticAssetRequest(request));
    return secureStaticResponse(assetResponse, relative);
  },
};
