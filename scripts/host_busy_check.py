#!/usr/bin/env python3
"""Report work in flight on the deployment host that a restart would destroy.

Anything that reloads the service -- a deploy, a certification refresh -- kills
whatever the service process is executing. Doing that mid-run destroyed a
user's work three times before the deploy path grew this gate, so the gate is
shared rather than reimplemented per caller: a second copy would drift, and the
copy that drifts is the one that eats the run.

A simulation run persists its status, so those are detected exactly. An
authoring job does NOT: while it is generating, its draft on disk still reads
status "draft" with no attempts, because the job lives in the service process.
Recent draft mtime is the only disk-visible signal, so that half is a
deliberate over-approximation -- it would rather block a safe restart than
silently destroy a 15-minute authoring job again.

Prints one line per busy item. Exit 0 when idle, 3 when busy.
"""

from __future__ import annotations

import json
import os
import sys
import time

DEFAULT_STORE = "~/Library/Application Support/cybernetic-influence-waltzman"
RUN_LOOKBACK_SECONDS = 3600
DRAFT_LOOKBACK_SECONDS = 1200
ACTIVE_RUN_STATUS = ("running", "narrating", "pause_requested")


def busy_reasons(store: str) -> list[str]:
    reasons: list[str] = []
    now = time.time()

    runs = os.path.join(store, "runs")
    if os.path.isdir(runs):
        for name in sorted(os.listdir(runs)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(runs, name)
            try:
                if now - os.path.getmtime(path) > RUN_LOOKBACK_SECONDS:
                    continue
                doc = json.load(open(path))
            except Exception:
                continue
            status = doc.get("status")
            if status in ACTIVE_RUN_STATUS:
                reasons.append(f"run {name} is {status}")

    drafts = os.path.join(store, "authoring_drafts")
    if os.path.isdir(drafts):
        for name in sorted(os.listdir(drafts)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(drafts, name)
            try:
                age = now - os.path.getmtime(path)
                if age > DRAFT_LOOKBACK_SECONDS:
                    continue
                doc = json.load(open(path))
            except Exception:
                continue
            # A draft that has resolved -- either way -- is not in flight: it
            # moves off "draft" status and records its attempts. A recently
            # touched draft still sitting at "draft" with nothing recorded is
            # the one that is probably mid-generation in the service process.
            resolved = doc.get("status") != "draft" or (doc.get("attempts") or [])
            if not doc.get("proposal") and not resolved:
                reasons.append(
                    f"draft {name} touched {int(age)}s ago, still status=draft with no"
                    " attempts (probable authoring job in flight)"
                )
    return reasons


def main() -> int:
    store = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STORE)
    reasons = busy_reasons(store)
    for reason in reasons:
        print(reason)
    return 3 if reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
