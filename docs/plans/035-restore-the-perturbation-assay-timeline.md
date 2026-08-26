---
doc_role: implementation_plan
authority: bounded_design
status: active
created: 2026-08-25
updated: 2026-08-25
depends_on:
  - docs/ROADMAP.md
  - docs/plans/022-composite-agency-perturbation-assay.md
  - docs/handoffs/2026-08-25-review-and-assay-control.md
---

# Slice 35: give the perturbation assay its own timeline

## The outcome this serves

Packet 22A2 claims five matched rows that "distinguish concrete pathways" and
step down to exact retained evidence. That claim is currently false, and has
been since 2026-08-03. This slice makes it true again, and makes it stop
depending on a constant somebody else is free to change.

## What is actually wrong

`54394e0` ("Remove inert gaps from Waltzman demo timeline") compressed the
coordination scenario for demo pacing: `MEETING_DAYS` from `(0, 3, 6, 9)` to
`(0, 1, 2, 3)`, `DECISION_DEADLINE_DAY` from 10 to 4. That is a good change to
a demo.

The assay reuses that scenario and expressed its own timing as absolute day
counts authored against the 10-day world:

```python
PERTURBATION_APPLICATION_TIME = 4 * MINUTES_PER_DAY   # 5760
VERIFICATION_FEEDBACK_DELAY   = 2 * MINUTES_PER_DAY   # 2880
```

In the compressed world the meetings are at 0, 1440, 2880, 4320 and the
deadline is 5760. So `PERTURBATION_APPLICATION_TIME` is now **exactly the
deadline** — every perturbation is applied after the last meeting, at the
instant the fallback fires. And a 2880-minute feedback delay cannot complete
inside a 5760-minute world once it is requested at any meeting after the first.

The observed consequence, measured 2026-08-25:

| Row | capability | outcome | decision time | differentiating evidence |
| --- | --- | --- | --- | --- |
| `matched_control` | false | `no_decision_by_horizon` | 5768 | — |
| `member_replacement` | true | `deploy_on_time` | 4358 | replacement recorded |
| `route_interruption` | false | `no_decision_by_horizon` | 5773 | none; `alternate_routes_used: []` |
| `feedback_interruption` | false | `no_decision_by_horizon` | 5773 | none |
| `external_risk` | false | `no_decision_by_horizon` | 5774 | none |

Four of five rows are indistinguishable. The one that differs does so only
because member replacement is a configuration change applied before execution
rather than a timed perturbation. The assay has been exercising one path four
times, and its control has been failing, for three weeks.

This is not primarily a deadline bug. The deadline is where it surfaced.

## The design

The assay must own its timing, and must express it against the world it is
actually running in rather than against a world it was authored for.

Both constants are private to `src/cybernetic_influence/experiments/
composite_agency.py`; nothing else in `src/`, `tests/`, or `scripts/` reads
them. So the change is bounded to the assay and cannot affect the demo, the
public V2 path, or the scenario's Pydantic contracts — which pin
`deadline_day: Literal[4]` and would otherwise have to be widened.

Derive both from the scenario's own meeting cadence:

```python
_MEETING_INTERVAL = MEETING_TIMES[2] - MEETING_TIMES[1]
PERTURBATION_APPLICATION_TIME = MEETING_TIMES[1] + _MEETING_INTERVAL // 3
VERIFICATION_FEEDBACK_DELAY = (_MEETING_INTERVAL * 2) // 3
```

This is a derivation, not a retuning. Under the original 10-day world the
interval was 4320, so it reproduces exactly the authored 5760 and 2880. Under
the compressed world it yields 1920 and 960 — the same intent, expressed
proportionally: apply the perturbation a third of the way into the gap after
the second meeting, leaving two further meetings for the system to respond,
and let verification feedback return within two thirds of one meeting gap.

The rejected alternative is moving the deadline so the control passes. That
fits the ruler to the measurement and is what a control exists to prevent.

## Acceptance

Measured by running the assay, not by the tests alone:

1. `matched_control` reaches `deploy_on_time` with `capability_satisfied` true.
2. The five rows are no longer interchangeable: `route_interruption` records a
   non-empty `alternate_routes_used` and a measured `recovery`;
   `external_risk` records a measured `recovery`; `feedback_interruption`
   fails for a *named* reason (`failed_constraint_ids` non-empty) rather than
   by falling off the end of the world.
3. `tests/test_composite_agency_execution.py` and `tests/test_composite_agency.py`
   pass.
4. `mypy --strict` clean.

## Disproof

If the control still misses its deadline, or if any two rows remain
indistinguishable on their exact values, the derivation is wrong and the
timeline needs authoring rather than deriving.

## What this does not claim

Restoring differentiation is not evidence for any particular contrast. The
retained pre-2026-08-03 readouts were produced under the 10-day world and are
not comparable to post-fix rows; they remain historical evidence. This slice
does not authorize live repetitions, scalar agency scores, or causal claims,
and Packet 22A2's stakeholder readout remains pending as before.
