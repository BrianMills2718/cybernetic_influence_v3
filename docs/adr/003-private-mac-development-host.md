# ADR-003: Private Mac Mini Development Host

## Status

Accepted — 2026-07-23.

## Context

Durable runs make an always-available development instance useful. The
available Mac Mini is online in the private tailnet and has a current Homebrew
Python, but it does not have GitHub credentials, `llm_client`, or provider
secrets. It already serves unrelated ports through Tailscale, including an
existing Funnel configuration that this project must not alter.

## Decision

Deploy an exact approved Git commit through a Git bundle until the host has its
own read-only GitHub credentials. Run uvicorn as a user LaunchAgent bound only
to `127.0.0.1`. Retain evidence under the user's Application Support directory,
outside the checkout. Add one new tailnet-only Tailscale Serve listener on port
8620 without modifying existing Serve or Funnel listeners.

Start with zero-cost scripted execution. Do not place provider keys in a plist,
shell profile, repository, or copied dotenv file. Live execution remains
disabled until the shared `llm_client` and a host-native secret injection path
are separately verified.

## Consequences

The development simulator is restart-safe and remotely reachable only to
tailnet members. Updating initially requires transferring another approved Git
bundle, which is deliberate friction around deployment rather than ongoing
source synchronization.

This decision is superseded when the host gains read-only repository access or
when a different deployment surface provides equally inspectable private
access with less operational state.
