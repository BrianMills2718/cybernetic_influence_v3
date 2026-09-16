// Public Waltzman at brianmills.dev/waltzman/ (ADR-015, amended by ADR-016).
// Static retained-review bundle from Workers Static Assets; /waltzman/api/* proxied to the
// live simulator on the personal VPS, reached through the Cloudflare tunnel hostname.
const API_ORIGIN = "https://waltzman-api.brianmills.dev";

function unavailable(detail) {
  return Response.json(
    { error: "live_simulator_unavailable", detail },
    { status: 503, headers: { "cache-control": "no-store" } },
  );
}

async function proxyApi(request, url) {
  const target = new URL(API_ORIGIN);
  target.pathname = url.pathname.replace(/^\/waltzman\/api\//, "/api/");
  target.search = url.search;

  const headers = new Headers(request.headers);
  headers.delete("host");
  const clientIp = request.headers.get("cf-connecting-ip");
  if (clientIp) {
    // Spend controls key the per-visitor limit on this address.
    headers.set("cf-connecting-ip", clientIp);
    headers.set("x-waltzman-client-ip", clientIp);
  }

  let response;
  try {
    response = await fetch(target, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "manual",
    });
  } catch (error) {
    return unavailable(
      `The live simulator could not be reached (${error}). Retained runs and replays on this page remain available.`,
    );
  }
  // Tunnel/origin failures arrive as Cloudflare HTML error pages; keep them visible as JSON
  // so the page reports the simulator as unavailable instead of rendering a blank result.
  const type = response.headers.get("content-type") || "";
  if ([502, 503, 504, 520, 521, 522, 523, 524, 525, 526, 530].includes(response.status) && !type.includes("application/json")) {
    return unavailable(
      `The live simulator is temporarily unavailable (origin status ${response.status}). Retained runs and replays on this page remain available.`,
    );
  }
  const out = new Response(response.body, response);
  out.headers.set("cache-control", "no-store");
  return out;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/waltzman/api/")) {
      return proxyApi(request, url);
    }

    if (url.pathname.startsWith("/waltzman/assets/")) {
      url.pathname = url.pathname.replace("/waltzman/assets/", "/waltzman/");
      return env.ASSETS.fetch(new Request(url, request));
    }

    return env.ASSETS.fetch(request);
  },
};
