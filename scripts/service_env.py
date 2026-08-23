#!/usr/bin/env python3
"""Read the waltzman-public service environment from its launchd plist.

The authoring-route health check and the certification refresh must run with
the same environment as the running service. Reading it from the loaded plist
is the only source that cannot drift from what the service actually uses: a
shell profile, a .env file, or a hand-exported variable can all disagree with
the process that is really serving the demo, and that disagreement is exactly
how a healthy-looking check reported "Create is already dark" on 2026-08-23
when the route was in fact fine.

As a script, prints shell exports for `eval`. As a module, `service_env()`
returns the mapping.
"""

from __future__ import annotations

import plistlib
import shlex
from pathlib import Path

SERVICE_LABEL = "com.cybernetic-influence.waltzman-public"


def plist_path() -> Path:
    return Path.home() / "Library/LaunchAgents" / f"{SERVICE_LABEL}.plist"


def service_env() -> dict[str, str]:
    """Return the service's EnvironmentVariables, or raise if unreadable."""
    path = plist_path()
    if not path.exists():
        raise FileNotFoundError(f"service plist not found: {path}")
    with path.open("rb") as handle:
        document = plistlib.load(handle)
    env = document.get("EnvironmentVariables")
    if not isinstance(env, dict) or not env:
        raise ValueError(f"no EnvironmentVariables in {path}")
    return {str(key): str(value) for key, value in env.items()}


def main() -> int:
    for key, value in sorted(service_env().items()):
        print(f"export {key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
