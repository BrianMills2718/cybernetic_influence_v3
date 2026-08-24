#!/usr/bin/env python3
"""Fail when the page states something the retained runs do not support.

The worst defect found in this demo was not a broken control or a failing
request. It was a chapter that described, in correct and well-rendered prose, an
experiment the run was not performing: the page told a reader that the identical
group continues four times with different resource packages, while the run
actually shown had three rounds, four pressure sources and one intervention.

Nothing caught it. The page returned 200, every element rendered, every element
assertion passed, and the text was internally coherent. It was simply not true
of the run. A reader who is the author of the framework being demonstrated would
have found it immediately, and it would have cost more than any bug here.

So this checks the one thing those other checks cannot: that the claims written
into the page agree with the evidence projected from the runs. It covers the
numbers a reader will compare against the case study, the words the detection
cell actually recorded, and the vocabulary of experiments this demo no longer
runs.

Exit non-zero on any disagreement, naming the claim and the evidence.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Experiments this demo used to show. Prose describing them is stale by
# definition: the flagship changed and the page did not follow.
SUPERSEDED_VOCABULARY = (
    "continues four times",
    "replay only the resource",
    "four continuations",
    "resource package arrives",
    "identical group continues",
)


def _decisions(rounds: list[dict[str, Any]], index: int) -> dict[str, int]:
    return dict(rounds[index]["decisions"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page", type=Path, default=Path("public/waltzman/index.html"))
    parser.add_argument("--case", type=Path, default=Path("public/waltzman/cso-case.json"))
    parser.add_argument(
        "--evasion", type=Path, default=Path("public/waltzman/evasion-case.json")
    )
    args = parser.parse_args()

    page = args.page.read_text(encoding="utf-8")
    case = json.loads(args.case.read_text(encoding="utf-8"))
    problems: list[str] = []

    # 1. Prose describing a superseded experiment.
    for phrase in SUPERSEDED_VOCABULARY:
        if phrase in page:
            problems.append(
                f'page still describes a superseded experiment: "{phrase}"'
            )

    # 2. The landing page states the trajectory as literal text. It is the first
    #    thing a reader sees and the only place the numbers are not rendered from
    #    the projection, so it is the only place they can silently drift.
    rounds = case.get("rounds") or []
    if len(rounds) < 3:
        problems.append(f"{args.case.name}: expected at least 3 rounds, got {len(rounds)}")
    else:
        first, middle, last = _decisions(rounds, 0), _decisions(rounds, 1), _decisions(rounds, -1)
        agents = case.get("agent_count")
        claims = [
            (f"<b>{first.get('support', 0)}</b>", "first-round support count"),
            (
                f"<b>{middle.get('conditional', 0)} of {agents}</b>",
                "second-round conditional count",
            ),
            (f"<b>{last.get('support', 0)}</b>", "final-round support count"),
        ]
        for literal, label in claims:
            if literal not in page:
                problems.append(
                    f"{label}: page does not state {literal!r}, which the retained "
                    f"run supports"
                )

    # 3. The detector's own words, where the page names them outside the
    #    projection-rendered comparison.
    if args.evasion.exists():
        evasion = json.loads(args.evasion.read_text(encoding="utf-8"))
        for arm in ("overt", "evasion"):
            detector = (evasion.get(arm) or {}).get("detector") or {}
            for field in ("coordination_readiness", "mechanism"):
                value = detector.get(field)
                if not value:
                    problems.append(f"{args.evasion.name}: {arm}.{field} is missing")
        overt = (evasion.get("overt") or {}).get("detector") or {}
        shaped = (evasion.get("evasion") or {}).get("detector") or {}
        if overt.get("coordination_readiness") == shaped.get("coordination_readiness"):
            problems.append(
                "the evasion comparison claims the detector read the two arms "
                "differently, but both readiness values are "
                f"{overt.get('coordination_readiness')!r}"
            )

    if problems:
        print(f"{len(problems)} claim(s) the evidence does not support:", file=sys.stderr)
        for item in problems:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"page claims agree with the retained evidence ({args.case.name}, {args.evasion.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
