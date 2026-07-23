# Slice 9: Event-Driven Causal Moments

**Status: Complete — 2026-07-23.**

## Outcome

An operator runs the Service Desk and sees a sequence of meaningful causal
moments. Each moment combines all people triggered by newly delivered
information, shows their separately retained decisions, and receives one
human-readable LLM narrative. The operator can still step down to every exact
event and participant activation.

## Boundaries

- Active runtime owns pending-observation detection and frozen activation sets.
- Service Desk owns its initial trigger, quiescence loop, and finite moment cap.
- Exact mechanisms retain all action, routing, and world-state authority.
- Presentation derives moment and participant views from canonical attempts.
- Narration receives only analyst-visible moment evidence and prior narratives.
- The UI labels moments, activations, and events without conflating them.

## Acceptance

- Baseline produces at least one multi-participant causal moment.
- Every participant in that moment receives the same pre-state digest.
- No participant receives another participant's same-moment action as an
  observation.
- Baseline, missing-direct-path, and speed-pressure arms reach their expected
  exact outcomes and then terminate at quiescence.
- Missing-direct-path remediation occurs later than baseline; speed pressure
  still produces an exactly denied premature closure.
- Narrator calls equal causal moments, not participant activations.
- Each narrator citation belongs to its current moment.
- The selected timeline event displays its containing moment narrative.
- Old retained `turns` narration remains readable as compatibility input.
- Scripted tests, typing, production build, deployed API, desktop/mobile UI,
  console, and one bounded live trace pass.

## Non-goals

Do not add universal clocks, random activations, background thoughts, continuous
physics, new provider abstractions, or a general conflict-resolution language.
Do not rewrite the historical fixed-schedule fidelity report in this slice.

## Completed Evidence

- Local and Mac-host gates passed mypy, 36 tests, the production React Flow
  build, and deployment script syntax.
- Scripted baseline, missing-direct-path, and speed-pressure runs quiesced after
  5, 7, and 5 causal moments respectively; the baseline and speed-pressure
  runs each grouped supervisor and triager in one frozen activation set.
- The missing path delayed remediation from moment 1 to moment 3, while speed
  pressure retained one exact denial before confirmed closure.
- Live run `run_11a699e00d2e` completed with five moments, six agent calls, five
  narrator calls, and fully observed cost of $0.058196875.
- Full `llm_client` trace inspection confirmed that the simultaneous supervisor
  and triager calls received different delivered observations at the same
  logical time without either seeing the other's proposal. The third narrator
  call received both participant traces plus the two prior narratives and cited
  only current-moment events.
- The focused forged-citation test rejects narration that cites outside its
  moment.
- Deployed Chrome showed five primary timeline markers, a combined
  `supervisor + triager` third moment with ten selectable exact events, a
  selectable final silent moment, no console errors, and no page-level overflow
  at 1440 px or 390 px.

These checks establish technical execution. Whether causal moments and their
narratives are sufficiently intuitive remains an operator comprehension
judgment rather than an automated claim.
