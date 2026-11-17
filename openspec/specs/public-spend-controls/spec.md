# public-spend-controls Specification

## Purpose
Characterize the existing spend controls on the public Waltzman deployment (ADR-016): the sign-in-free demo bounds metered LLM spend by a daily cap and a per-visitor limit instead of a login. This is existing behavior, not a new requirement.

## Requirements

### Requirement: Daily live-run cap

The public application SHALL refuse a provider-backed live run with HTTP 429 and a plain-language message once the day's cap of live runs is used, and SHALL NOT count scripted runs or reads.

Source: inferred by agent, 2026-11-17: restates ADR-016 and `src/cybernetic_influence/public_spend_controls.py` (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Daily cap reached

- **WHEN** live runs have used the day's cap and another live run is requested
- **THEN** the response is 429 with error `daily_run_cap_reached` and a positive `retry-after`, and scripted runs and reads still succeed

### Requirement: Rejected request returns slot

The public application SHALL give back the slot reserved for a request that the application itself rejects with status 400 or above.

Source: inferred by agent, 2026-11-17: restates the module docstring of `public_spend_controls.py` (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Validation error keeps capacity

- **WHEN** a live run is rejected by the application with status 422
- **THEN** the used count stays 0 and the next valid live run is accepted

### Requirement: Durable daily count

The public application SHALL persist the daily count on disk so a restart does not reset it, and SHALL reset it at the next UTC day.

Source: inferred by agent, 2026-11-17: restates the module docstring of `public_spend_controls.py` (Brian, 2026-11-17: "option B is what i want").

#### Scenario: Count survives restart

- **WHEN** the application restarts within the same UTC day after the cap was used
- **THEN** the next live run is refused with 429, and it is accepted after the UTC day rolls over
