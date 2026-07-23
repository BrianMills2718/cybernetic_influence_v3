# Slice 3: Private Mac Mini Development Host

**Status: Complete — 2026-07-23.**

## Frame

Make one approved simulator build continuously available for retained scripted
runs without turning deployment into a second development workflow.

## Modality

Service lifecycle, binding, approved-commit provenance, retention path, and
private routing are deductive. Whether remote availability improves the
development loop is exploratory; the readout is whether a run can be created,
reopened after service restart, and inspected remotely with fewer manual steps
than starting the local server.

## Slice Contract

- **Vertical scope:** exact commit → isolated environment → user service →
  retained scripted run → tailnet URL → restart → reopen.
- **Success:** the service reports the deployed commit, is locally bound, is
  tailnet-only, survives restart, preserves a scripted run, and exposes no live
  authorization.
- **Audit:** preserve existing Tailscale routes, check public reachability,
  inspect service logs, verify no secrets were copied, simulate service
  restart, and compare the retained run before and after.
- **Cleanup:** keep one LaunchAgent template and one update procedure; do not
  add containers, CI/CD, databases, or public ingress.
- **Done when:** all gates pass, findings are dispositioned, cleanup is
  complete, and this register is triaged.

## Concern Register

- C009 mitigated: the host lacks GitHub credentials; use an exact Git bundle
  now and prefer a read-only deploy key later.
- C010 deferred: the host lacks `llm_client` and provider-secret injection;
  live execution remains off rather than adding keys to launchd configuration.
- C011 verified invariant: the existing Tailscale Serve and Funnel mappings
  remained unchanged except for the new port-8620 listener.
- C012 mitigated: port 8620 is present in Tailscale Serve and absent from
  `AllowFunnel`; application-level authorization remains future work if access
  expands beyond the current tailnet.
- C013 resolved: an immediate launchd bootstrap after bootout returned a
  transient input/output error. A one-second lifecycle boundary succeeded and
  is now part of the operator procedure.

## Audit Result

The Mac installed and passed strict typing plus all seven tests under Homebrew
Python 3.14. The LaunchAgent runs from exact commit `7d9d26a`, binds only to
`127.0.0.1:8620`, and reports that commit through `/api/config`. No dotenv file,
provider environment variable, live authorization, or API key was copied.

A zero-cost missing-path run completed with 66 exact events. After a forced
service restart, its ID and event document reopened unchanged through the
tailnet-only HTTPS URL. Browser rendering showed the retained run, alternate
route narrative, synchronized 66-event timeline, and focused entities.
Tailscale's existing port 443 Funnel and port 8765 Serve proxy remained
unchanged; port 8620 is not Funnel-enabled.

The exploratory readout passes: the remote path creates and reopens retained
evidence without starting a development shell, while the local checkout remains
the sole source-editing workflow.

## Next Slice Direction

Add one small non-service-desk scenario that exercises a physical boundary,
credential-bearing person, exact access controller, policy representation, and
observation channel. This should test whether the ontology and causal runtime
generalize beyond the scenario from which they were extracted before adding a
scenario-authoring framework or aggregate organization view.
