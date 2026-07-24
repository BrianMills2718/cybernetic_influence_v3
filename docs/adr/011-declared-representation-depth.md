# ADR 011: Declare Representation Depth Per Subsystem

**Status:** Accepted direction — 2026-07-23. General framework deferred.

## Decision

The simulator may represent different subsystems at different depths according
to the question being studied. A subsystem may be backed by:

- an original executable implementation;
- exact stipulated mechanisms;
- an empirical or learned behavioral surrogate;
- a stochastic transition model;
- an LLM decision process;
- an exogenous trace or authored process.

These are alternative implementations of typed sensing, state, timing, and
effect contracts. They are not new ontological kinds of actor. In particular, a
stochastic stock-price process is a declared substitute for omitted exchanges,
orders, traders, and information flows; it is not “the market” acting.

Representation depth is question-relative rather than a universal quality
ranking. A calibrated aggregate surrogate may preserve the relevant readout
better than a detailed but misspecified mechanism. Conversely, a surrogate
cannot support claims about omitted internal causal pathways.

## Fidelity Declaration

Every nontrivial subsystem representation must state:

- the phenomena and readouts it intends to preserve;
- omitted entities, mechanisms, and interactions;
- typed inputs and outputs;
- temporal resolution and update semantics;
- whether transitions are exact, empirical, stochastic, learned, LLM-produced,
  or externally replayed;
- provenance or calibration basis;
- uncertainty and known failure conditions;
- which questions the representation cannot answer;
- the condition that would require a finer or different representation.

Existing `FidelityNote` records remain the MVP documentation surface. This ADR
does not authorize a generalized runtime registry, automatic fidelity scoring,
or automatic switching between levels.

## Refinement Boundary

A coarse and fine implementation may expose compatible typed observations and
effects so a scenario can replace one without rewiring every neighboring agent.
Compatibility does not imply identical hidden state, causal explanations, or
valid analytical claims. Retained runs must identify the implementation and
fidelity declaration actually executed.

For example, an agent may receive `price_update` from either:

```text
declared stochastic price process
```

or:

```text
concrete traders and controllers
  -> orders and network delays
  -> exchange matching mechanism
  -> trade and quote observations
```

Only the second representation supports claims about how those lower-level
components produced the price.

## MVP Boundary

Document the ladder now, but add no stock-market scenario, learned surrogate,
calibration pipeline, stochastic-process library, or automatic representation
selection. Implement a shared surrogate boundary only when a second concrete
scenario needs to replace one subsystem while preserving the same neighboring
contracts.
