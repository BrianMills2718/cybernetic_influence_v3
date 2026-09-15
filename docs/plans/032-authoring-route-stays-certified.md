---
doc_role: implementation_plan
authority: bounded_design
status: implemented
created: 2026-08-23
updated: 2026-09-06
depends_on:
  - docs/ROADMAP.md
  - docs/plans/031-cso-stabilization-flagship.md
plan_id: "cybernetic_influence_v3#32"
dependencies: ["cybernetic_influence_v3#31"]
dependency_evidence:
  "cybernetic_influence_v3#31": "- docs/plans/031-cso-stabilization-flagship.md"
dependencies_reviewed: "2026-09-15"
---

# Slice 32: the authoring route stays certified without a human

## Why

The public Create surface depends on a route certification that expires seven
days after it is produced. Producing one was already automated
(`scripts/certify_codex_luna.py`). Installing one never was: the observation ids
it prints had to be pasted into the service plist by hand and the service
restarted by hand.

That gap is the direct cause of a repeating failure. Nothing reports a problem
until the margin is already gone, and the first visible symptom is a disabled
button with the message "Simulation builder unavailable", which is
indistinguishable from a route that never existed. It went dark on 2026-08-19
and cost hours to trace. `scripts/check_authoring_route_health.py` (Slice 30)
made the expiry *visible* in advance, but a warning still requires a human to
act on it, and the human it requires is the operator, who has said plainly that
he does not want to perform this step.

A second cause surfaced on 2026-08-23: the host's Codex login was on an account
whose usage limit had been exhausted, while a different machine held a working
login for a new account. The health check reported the route as configured, so
the failure was invisible to it. The account was corrected by copying the login
between hosts; the durable protection is that a certification failure over the
free route must be loud and must fall back rather than leave the surface dark.

## What this slice does

1. `scripts/service_env.py` reads the service environment from the launchd
   plist the service actually loads, so a check can never pass or fail against
   an environment the running service does not have. Reading it any other way
   produced a false "Create is already dark" report on 2026-08-23.
2. `scripts/host_busy_check.py` factors the deploy path's in-flight-work gate
   into one shared implementation. Any restart destroys what the service is
   executing; the deploy path learned this by destroying user runs three times.
   The certification refresh restarts the service too, so it must use the same
   gate, and a second copy of that logic would drift.
3. `scripts/refresh_authoring_certification.py` certifies when the margin is
   short, installs the ids into the plist, restarts the service, and re-checks
   that the margin actually grew. It refuses to install while work is in
   flight, and returns non-zero on every path it cannot complete.
4. `scripts/install_certification_refresh_job.sh` schedules that nightly on the
   deployment host.

## Cost boundary

The free Codex subscription route is preferred. If it cannot certify and the
margin is inside two days, the refresh certifies over the metered OpenRouter
route instead and says so in its log. That is a deliberate, bounded spend of
roughly one certification call: a surface going dark in front of a reviewer
costs more than that call. `--no-paid-fallback` forbids spend entirely.

## Pass/fail

- `refresh_authoring_certification.py` run against a short margin extends it,
  and the extension is visible to `check_authoring_route_health.py` afterwards.
- Run again immediately with a healthy margin, it exits 0 and changes nothing.
- With a simulated in-flight run present, it does not restart the service.
- The scheduled job is loaded and its log records each night's outcome.

## Explicitly not in scope

Cross-host credential syncing. The Mac could not reach the workstation over SSH
(no sshd there), and the account correction that motivated it is a rare event,
not a recurring one. The refresh handles a dead free route by falling back and
reporting, which covers the failure without standing access between machines.
