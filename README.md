# Cybernetic Influence V3

A clean implementation of a traceable cybernetic multiscale agency simulator.

The simulator models people, information, stateful objects, interfaces,
connections, and mechanisms separately. Organizations are analytical
boundaries—not hidden minds or executors. Occupied positions are external
social context remembered and interpreted by people, not intrinsic behavioral
programs.

Current direction and MVP boundaries are maintained in
[docs/ROADMAP.md](docs/ROADMAP.md). Binding architectural decisions live under
[`docs/adr/`](docs/adr/README.md), and the roadmap links the sole active packet indexed
under [`docs/plans/`](docs/plans/README.md).

## Working simulator

The simulator currently includes:

- a service-desk scenario with normal, missing-channel, and speed-pressure
  conditions, plus an explicit operations-center/customer-site geography that
  remains separate from digital communication and authority;
- a physical-access scenario that keeps credential proof, policy
  authorization, latch operability, crossing, and sensor feedback distinct;
- a purchase-to-payment scenario that keeps a person's approval attempt,
  concrete policy and signing records, exact internal authorization, and a
  deliberately coarse external processor result distinct;
- authoritative topological places, entity placements, and concrete spatial
  links whose existence never implies permission or successful traversal;
- personal-disposition plus remembered-position cognition;
- an explicit procedural control profile;
- autonomous causal moments in the Service Desk and purchase-to-payment
  scenarios: each person or exact process may wake from delivered information
  or retained internal timing, everyone due together receives the same frozen
  pre-moment state, and every successive moment has a unique causal timestamp;
- an exact three-phase remediation process that advances without model calls,
  including one moment shared with a triager reconsidering without new input;
- zero-cost scripted reference runs;
- live LLM runs behind `CYBERNETIC_INFLUENCE_LIVE=1`;
- typed live-run controls for deployment-certified model routes, model-supported
  agent reasoning, and a total spend authorization, with the effective policy
  retained on success or failure;
- inline explanations of scenario assumptions, known omissions, fidelity
  questions, maps, analytical scales, narratives, and exact evidence;
- sequential live-LLM causal-moment narratives grounded in exact causal event
  IDs and informed by the prior moment narratives;
- a pannable, zoomable, selectable causal graph of people, information, world
  objects, mechanisms, and concrete declared routes;
- a separate realized-trajectory graph of retained events and explicit
  causal-parent links, synchronized with the moment inspector and distinct from
  both spatial topology and possible structural routes;
- a synchronized world-topology graph with place containers, event-time
  occupants, pathway substrates, and one-click return to exact causal flow;
- reversible execution-inert aggregate views—including separate operating,
  finance, and end-to-end purchase views—with explicit information-loss counts,
  expanded composite hulls, and one-step return to exact evidence at the same
  revision;
- event-focused graph nodes, routes, and participant traces;
- event-revision snapshots rather than final-state leakage into earlier events;
- analyst-safe evidence that redacts mechanism-only values and protected
  representation content;
- a separate run-history workspace that survives refreshes and server restarts;
- pause at a validated causal boundary and continuation of retained Service
  Desk runs, including live LLM runs on the same deployment and configuration;
- recoverable deletion and visible failed/interrupted records.
- conversational typed authoring through a task-tested structured model, with
  retained feedback revisions and per-message Terra/Sol plus thinking selection,
  revisioned review and approval for reviewed resource-request and
  information-campaign templates;
- an exact information-campaign reference path that distinguishes a source's
  publication attempt, configured channel delivery, and recipient assessment
  without pretending to infer persuasion or geopolitical effects.

## Run

```bash
make install
make check
make serve
```

Open <http://127.0.0.1:8620>.

The native LLM path uses the shared `llm_client` checkout installed in the
environment. Scripted runs require no provider and make no model calls.
The private Mac host currently advertises exact-schema-certified Terra and
DeepSeek V4 Flash routes. DeepSeek with `none` reasoning is the default;
DeepSeek `high` and `xhigh` are visibly experimental, and unsupported
`medium` is rejected by shared-client policy. Configured candidates that fail
route or full-run evidence stay absent.

The current private-demo finish line is intentionally smaller than the full
research vision: exercise one DeepSeek-default Service Desk run through map,
narrative, traces, cost, pause/resume, and history; verify the resumed trace and
desktop interaction; then obtain the operator's short usability judgment. The
canonical checklist is in
[Slice 14](docs/plans/014-pausable-live-runs.md). Typed scenario authoring now
supports two bounded reviewed templates; its compiler and approval contract is in
[Slice 17](docs/plans/017-conversational-scenario-authoring.md).

The user-facing Service Desk simulation is autonomous and event driven. Its
initial customer report starts the triager; thereafter, newly delivered
observations and retained `next_update_at` intentions form the next frozen
activation set. A person can therefore reconsider without a new message, while
an exact state-machine controller can advance more often without paying for an
LLM call. The UI and narrator expose each moment's unique causal timestamp,
participant kind, and activation cause. A separate scenario clock is retained
for authored process delays; the Service Desk currently uses uncalibrated
process ticks rather than claiming realistic elapsed seconds. Exact subevents
within moment `c2`, for example, have canonical trace positions `c2.1`,
`c2.2`, and so on; explicit parent links, not that stable replay order, state
which events actually caused others. The older fixed nine-activation schedule
remains only inside the closed
fidelity-report harness so historical comparison evidence retains its original
sampling contract.

The multirate Service Desk now requires every non-metadata causal child event to
complete at a later modeled scenario time than its parent. Its first timing
source is a declared scenario-wide minimum duration, not a real-world estimate.
If the retained single-threaded trace order delays an otherwise-ready event, that
additional delay is retained separately as runtime serialization rather than
being attributed to the scenario assumption.
Other authored scenarios remain legacy zero-duration traces until a concrete
timing slice migrates them. The realized activity/event causal graph is distinct
from the existing structural graph of entities and possible routes. See
[ADR 010](docs/adr/010-autonomous-multirate-process-time.md).

Runs are retained under `artifacts/runs/`. Override that location with
`CYBERNETIC_INFLUENCE_RUNS_DIR`. A shared development host can bind another
interface explicitly:

```bash
make serve HOST=0.0.0.0 PORT=8620
```

Binding a network interface does not add authentication. Use private-network
access rather than exposing this development server publicly. When Tailscale
Serve fronts the app, restrict run endpoints to one or more injected logins:

```bash
export CYBERNETIC_INFLUENCE_ALLOWED_TAILSCALE_USERS="operator@example.com"
```

The comma-separated allowlist is optional for a local-only process. The Mac
development host enables it. Live execution also requires
`CYBERNETIC_INFLUENCE_LIVE=1`; the private Mac development host currently
enables it behind the allowlist.

`requirements-dev.lock` pins the accepted application and test environment.
The shared `llm_client` checkout remains a separately versioned optional
integration because scripted reference runs do not require a provider.

## Lineage

- `cybernetic_influence`: original research implementation.
- `cybernetic_influence_v2`: governed architecture and evidence work.
- this repository: clean product/runtime line with no V2 imports.

The earlier repositories remain historical sources, not runtime dependencies.
