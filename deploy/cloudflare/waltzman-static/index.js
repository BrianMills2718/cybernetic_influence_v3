export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname.startsWith("/waltzman/api/")) {
      return Response.json(
        {
          error: "live_simulator_unavailable",
          detail: "The retained-review deployment does not provide stateful simulation APIs.",
        },
        { status: 404 },
      );
    }

    if (url.pathname.startsWith("/waltzman/assets/")) {
      url.pathname = url.pathname.replace("/waltzman/assets/", "/waltzman/");
      return env.ASSETS.fetch(new Request(url, request));
    }

    return env.ASSETS.fetch(request);
  },
};
