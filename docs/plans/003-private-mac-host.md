# Slice 3: Private Mac Mini Development Host

**Status: In progress — 2026-07-23.**

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
- C010 open: the host lacks `llm_client` and provider-secret injection; live
  execution remains off rather than adding keys to launchd configuration.
- C011 invariant: the existing Tailscale Serve and Funnel mappings are outside
  this project's scope and must remain byte-for-byte unchanged except for the
  new port-8620 listener.
- C012 open: tailnet availability is not equivalent to application-level
  authorization. This instance contains development evidence and must not move
  to Funnel/public ingress.
