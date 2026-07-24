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
- autonomous multirate causal moments in the Service Desk: each person or exact
  process may wake from delivered information or retained internal timing, and
  everyone due at one timestamp receives the same frozen pre-moment state;
- an exact three-phase remediation process that advances without model calls,
  including one moment shared with a triager reconsidering without new input;
- zero-cost scripted reference runs;
- live LLM runs behind `CYBERNETIC_INFLUENCE_LIVE=1`;
- sequential live-LLM causal-moment narratives grounded in exact causal event
  IDs and informed by the prior moment narratives;
- a pannable, zoomable, selectable causal graph of people, information, world
  objects, mechanisms, and concrete declared routes;
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
- retained run history that survives refreshes and server restarts;
- recoverable deletion and visible failed/interrupted records.

## Run

```bash
make install
make check
make serve
```

Open <http://127.0.0.1:8620>.

The native LLM path uses the shared `llm_client` checkout installed in the
environment. Scripted runs require no provider and make no model calls.

The user-facing Service Desk simulation is autonomous and event driven. Its
initial customer report starts the triager; thereafter, newly delivered
observations and retained `next_update_at` intentions form the next frozen
activation set. A person can therefore reconsider without a new message, while
an exact state-machine controller can advance more often without paying for an
LLM call. The UI and narrator expose each moment's simulated time, time unit,
participant kind, and activation cause. The older fixed nine-activation
schedule remains only inside the closed fidelity-report harness so historical
comparison evidence retains its original sampling contract.

This MVP does not yet interleave unrelated processes inside one exact action's
nonzero-delay causal cascade; the representative Service Desk uses zero-delay
message routes and explicit scheduled process wakes. General asynchronous
channel interleaving is a future causal-core extension, not a claimed result of
this slice. See
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
