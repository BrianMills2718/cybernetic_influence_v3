# Cybernetic Influence V3

A clean implementation of a traceable cybernetic multiscale agency simulator.

The simulator models people, information, stateful objects, interfaces,
connections, and mechanisms separately. Organizations are analytical
boundaries—not hidden minds or executors. Occupied positions are external
social context remembered and interpreted by people, not intrinsic behavioral
programs.

## Working simulator

The service-desk scenario supports:

- personal-disposition plus remembered-position cognition;
- an explicit procedural control profile;
- normal, missing-channel, and speed-pressure world conditions;
- zero-cost scripted reference runs;
- live LLM runs behind `CYBERNETIC_INFLUENCE_LIVE=1`;
- human narrative synchronized to an exact causal timeline;
- event-focused information routes, world nodes, and person traces;
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

Runs are retained under `artifacts/runs/`. Override that location with
`CYBERNETIC_INFLUENCE_RUNS_DIR`. A shared development host can bind another
interface explicitly:

```bash
make serve HOST=0.0.0.0 PORT=8620
```

Binding a network interface does not add authentication. Use private-network
access rather than exposing this development server publicly.

## Lineage

- `cybernetic_influence`: original research implementation.
- `cybernetic_influence_v2`: governed architecture and evidence work.
- this repository: clean product/runtime line with no V2 imports.

The earlier repositories remain historical sources, not runtime dependencies.
