#!/usr/bin/env python3
"""The bundle the demo serves must be what frontend/src currently builds.

`make ui-build` writes to `web/`, which is what `cybernetic_influence.api:app`
serves locally. The public demo is a different app -- `public_waltzman.py` calls
create_app(web_root=public/waltzman) -- and nothing copied between the two. So
`make ui-build` reported success for ten days while public/waltzman/graph-canvas.js
sat frozen at its 2026-08-16 content, and every check that ran the build agreed
the build worked. It did. It just wasn't reaching the reader.

This checks the result rather than the mechanism: build the current source into a
scratch directory and byte-compare it against the files the demo actually serves.
It deliberately does not compare `web/` against `public/waltzman/` -- that would
pass whenever both are equally stale, which is the failure it needs to catch.
"""

from __future__ import annotations

import filecmp
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "frontend"
SERVED = REPO / "public" / "waltzman"
ARTIFACTS = ("graph-canvas.js", "graph-canvas.css")


def main() -> int:
    if not (FRONTEND / "node_modules").is_dir():
        print(
            "frontend dependencies are not installed; run `make ui-install` before this check",
            file=sys.stderr,
        )
        return 2

    with tempfile.TemporaryDirectory() as scratch:
        build = subprocess.run(
            ["npx", "vite", "build", "--outDir", scratch, "--logLevel", "error"],
            cwd=FRONTEND,
            capture_output=True,
            text=True,
        )
        if build.returncode != 0:
            print("the frontend build failed, so the served bundle cannot be checked", file=sys.stderr)
            print(build.stderr.strip() or build.stdout.strip(), file=sys.stderr)
            return 3

        stale = []
        for name in ARTIFACTS:
            fresh = Path(scratch) / name
            served = SERVED / name
            if not fresh.is_file():
                print(f"the build did not produce {name}", file=sys.stderr)
                return 3
            if not served.is_file():
                stale.append((name, "the demo is not serving this file at all"))
            elif not filecmp.cmp(fresh, served, shallow=False):
                stale.append(
                    (name, f"served {served.stat().st_size} bytes, source builds {fresh.stat().st_size}")
                )

        if stale:
            print("the demo is serving a bundle that frontend/src no longer produces:", file=sys.stderr)
            for name, detail in stale:
                print(f"  {name}: {detail}", file=sys.stderr)
            print("\nrun `make ui-sync` to rebuild and copy it into public/waltzman/", file=sys.stderr)
            return 1

    print(f"served bundle matches frontend/src ({', '.join(ARTIFACTS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
