# Public influence-network authoring certification

Observed at `2026-08-12T05:48:21Z` for the public Waltzman workbench.

## Verdict

- Capability ID: `cybernetic-influence.waltzman-public-influence-network-v1`
- Owner: `cybernetic_influence_v3`
- Advertised action: describe a bounded influence network in natural language,
  edit the typed result, approve it, run autonomous LLM people, and inspect the
  retained decision evidence.
- Surface/profile: public service plus UI action.
- Target: `Bs-Mac-mini.local`, LaunchAgent
  `com.cybernetic-influence.waltzman-public`, public Funnel route
  `https://brian-mac-mini.tail9c321e.ts.net/waltzman/`.
- Source revision: `e5ce0df4d4d5c4eaa8576d27db7539b2b432b00f`.
- Evidence level: `deployment_verified`.
- Surface status: `verified` for the bounded `influence_network_v1` workflow.

This verdict does not certify arbitrary-world authoring, physical-world
mechanism generation, human behavioral fidelity, empirical validity, or
stakeholder usefulness.

## Valid deployed composition

The exact public revision completed this path:

```text
natural-language request
→ Terra typed proposal
→ compiler validation
→ direct no-model edit
→ approval and composition receipt
→ Luna participant execution
→ exact decision gate
→ retained API result
→ public browser rendering
```

- Draft: `draft_62711b1c8522`
- Accepted authoring trace:
  `draft_62711b1c8522/revision/1/attempt/1`
- Authored topology: 3 people, 1 common message, 3 directed deliveries, and 2
  decision rounds.
- Direct edit: revision 2, source `direct_proposal_edit`, zero model calls.
- Approved proposal digest:
  `c0cc87b14f632f73dd50753d694eba0f4db2e655e5a1c2443054e4a4e3c461b4`
- Composition receipt digest:
  `29312621844096241b3afb259dd250a13ca4533e01091b0d5c8894c6c3b4b2f8`
- Run: `run_7c3df8e8ebe5`
- Participant model: `codex/gpt-5.6-luna`, medium reasoning.
- Result: completed after 9 of 9 successful participant calls, 9 committed
  traces, 102 events, 22 causal moments, and one terminal completion.
- Exact gate: 1 support, 2 conditional, 0 defer, and 0 oppose. The combined and
  opposition gates passed; the 2-support minimum failed, so the proposal was
  not approved.
- Observed provider cost: `$0.00`, subscription included and fully observable.
- Browser consumer: rendered the edited draft, exact recipient controls, all
  three people, stance counts, and all gate calculations with zero console
  errors and zero failed requests.

The authoring lifecycle retained one `started`, two `heartbeat`, and one
`completed` event for one logical call. Each of the nine Luna logical calls
retained exactly one `started` and one `completed` event. No participant call
failed or produced a second terminal event.

## Negative controls

- Typed invalid input: a proposal whose `scenario_id` was an integer returned
  HTTP 422 at the public endpoint and did not replace the valid draft.
- Missing unique dependency: an isolated app from the exact deployed checkout,
  with route-certification variables removed, advertised no authoring or live
  models and rejected Terra authoring with HTTP 422 before provider dispatch:
  `authoring model route is not currently certified`.
- Advertising enforcement: production configuration and dispatch now use the
  same current route-certification catalog. A route cannot remain selectable
  only because it appears in the static authoring option registry.

## Current bindings and invalidation inputs

- Simulator revision:
  `e5ce0df4d4d5c4eaa8576d27db7539b2b432b00f`
- Shared-client revision:
  `ce66e74e9929c7a0b031e38ac46d0f38a25ba703`
- Authoring prompt: `scenario_draft.v7`
- Current certified subscription models: `codex/gpt-5.6-terra` and
  `codex/gpt-5.6-luna`
- Fresh Terra global certification:
  `routeobs1_9d215f94f99c7560e1a475c1`,
  `routeobs1_b56404820f4f991293d3caf7`
- The verdict becomes stale when source code, typed schemas, prompt, model
  selector, shared client, certification observations, LaunchAgent
  configuration, public assets, run store, or public route changes.

## Artifact hashes

- HTML: `e81eb962674faff805623aa5accdd2b055ee7cd7f642dd53dedad766a0d53ed4`
- JavaScript:
  `228fe6e5e108352289a9a952d56d3ce36f5ee28a8f838c48ec42b7f0f94c9cb0`
- CSS: `95cbec88da970f27d8b04c9e9180ccb5216d805ebc0167a7e73631b753323de2`
- Public configuration:
  `9b8f51d491a8ca02815893fc43d678cca3c7265f22649971cbf29cac3cbc09ba`
- Retained draft:
  `c611869fb7ebe2c83ba3f36c88b68d2264d5a5cd996c7b66b4e6b368e4b9f39c`
- Retained run:
  `68564e1d56bc5c6e4a36d626d48e164b7cb5f404307285161c8dc7bb961dcf59`
- Browser screenshot:
  `95a6ab5a270cb0e2237d66e30299dc2300c675771c8372ad74ebf07f2b9cf961`
- Authoring lifecycle summary:
  `3029a2c3fc07e0a68b42c27acf7a80c5a99723223f961a1bff52e0a426fc714b`
- Participant lifecycle projection:
  `175a493e4785b0d51e7ccccdad970167dcce6336a400315ecbd5af0ce955ca80`

## Reproduction entry points

```bash
curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/config

curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/authoring/drafts/draft_62711b1c8522

curl -fsS \
  https://brian-mac-mini.tail9c321e.ts.net/waltzman/api/runs/run_7c3df8e8ebe5
```

Browser evidence:

`https://brian-mac-mini.tail9c321e.ts.net/waltzman/?view=create&draft=draft_62711b1c8522&authored_run=run_7c3df8e8ebe5`
