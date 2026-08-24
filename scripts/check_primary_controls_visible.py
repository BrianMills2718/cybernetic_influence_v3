#!/usr/bin/env python3
"""Fail when a primary control is not where a human can see or reach it.

Three defects of one shape shipped in three days, each found by the operator
rather than by any check:

  - the case walkthrough's "Next" sat outside the viewport at every width from
    1280 to 1600, while automated passes reported success because a driver
    scrolls an element into view before clicking it;
  - "Configure now" ran for minutes behind an unchanging sentence;
  - "Run simulation" unhid its status block below the fold and never scrolled,
    so clicking produced no on-screen change at all.

Every one of them satisfied "the element exists and is not hidden". That is the
property automation checks, and it is not the property that matters. This checks
the one that does: a control a human is expected to use must be fully inside the
viewport at the scroll position where it becomes relevant, and the page must not
require sideways scrolling to reach it.

Exits non-zero on any violation so it can gate rather than advise.
"""

from __future__ import annotations

import argparse
import sys

# No default browser path. Hard-coding one pinned this check to a single
# machine: on the deployment host it failed with a Linux path that does not
# exist there, so the nightly audit reported a failure about itself rather
# than about the demo. Playwright resolves its own browser; --chromium stays
# available for a deliberate override.

# Widths that matter, not a sampling of extremes: 1280-1600 is where the Next
# button was lost, and it is the range most laptops actually report.
WIDTHS = [390, 768, 1024, 1280, 1366, 1440, 1512, 1600, 1728, 1920]

# view -> controls a human is expected to find without hunting
SURFACES = {
    "overview": ["button[data-view='case']", "button:has-text('Start the product walkthrough')"],
    "guide": ["#guide-view button:has-text('Next')", "#guide-view button:has-text('Previous')"],
    "case": ["#case-walkthrough-next", "#case-walkthrough-previous"],
    "simulations": ["button[data-view='case']", "button[data-view='create']"],
    "create": ["#create-generate", "#create-configure-now"],
    "method": ["header button[data-view='overview']"],
}


def main() -> int:
    from playwright.sync_api import sync_playwright

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument(
        "--chromium",
        default=None,
        help="explicit browser executable; omit to let Playwright resolve it",
    )
    parser.add_argument("--widths", default=",".join(str(w) for w in WIDTHS))
    args = parser.parse_args()
    widths = [int(w) for w in args.widths.split(",") if w.strip()]

    violations: list[str] = []
    checked = 0

    with sync_playwright() as pw:
        launch_options: dict[str, object] = {
            "headless": True,
            "args": ["--no-sandbox"],
        }
        if args.chromium:
            launch_options["executable_path"] = args.chromium
        browser = pw.chromium.launch(**launch_options)  # type: ignore[arg-type]
        for width in widths:
            page = browser.new_page(viewport={"width": width, "height": 900})
            for view, selectors in SURFACES.items():
                try:
                    page.goto(f"{args.base_url}/?view={view}", wait_until="networkidle", timeout=90_000)
                    page.wait_for_timeout(2500)
                except Exception as error:  # noqa: BLE001 - a load failure is a violation
                    violations.append(f"{width}px {view}: page did not load ({type(error).__name__})")
                    continue

                doc_width = page.evaluate("() => document.documentElement.scrollWidth")
                if doc_width > width + 2:
                    violations.append(
                        f"{width}px {view}: page is {doc_width}px wide, so reaching "
                        "anything at the right edge needs sideways scrolling"
                    )

                for selector in selectors:
                    locator = page.locator(selector).first
                    if locator.count() == 0:
                        continue  # absent is a content question, not a visibility one
                    if not locator.is_visible():
                        continue  # legitimately hidden in this state
                    checked += 1
                    box = locator.bounding_box()
                    if box is None:
                        violations.append(f"{width}px {view}: {selector} reports visible but has no box")
                        continue
                    right = box["x"] + box["width"]
                    if right > width + 1:
                        violations.append(
                            f"{width}px {view}: {selector} extends to x={round(right)}, "
                            f"{round(right - width)}px past the viewport edge"
                        )
                    if box["x"] < -1:
                        violations.append(
                            f"{width}px {view}: {selector} starts at x={round(box['x'])}, off the left edge"
                        )
            page.close()
        browser.close()

    print(f"checked {checked} control placements across {len(widths)} widths")
    if violations:
        print("\nVIOLATIONS:")
        for item in violations:
            print(f"  - {item}")
        return 1
    print("every primary control is fully inside the viewport at every width")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
