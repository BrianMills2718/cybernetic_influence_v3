#!/usr/bin/env python3
"""Gate the flagship case's first-frame and comparison usability.

This check exists because a 2026-09-07 render review found defects that ordinary
DOM-presence and primary-control checks did not catch: tiny/clipped default graph
labels, hidden mobile top-level destinations, a walkthrough control overlaying
content, and comparison values that technically fit the page while being clipped
inside their own cells.

It is read-only against the served page and makes no model calls.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright


@dataclass(frozen=True)
class Viewport:
    width: int
    height: int


VIEWPORTS = (Viewport(1440, 1000), Viewport(390, 844))


def fully_inside_viewport(page: Page, selector: str) -> list[str]:
    """Return visible matched elements that extend outside the viewport."""
    return page.eval_on_selector_all(
        selector,
        """(elements) => elements.flatMap((element) => {
          const style = getComputedStyle(element)
          if (style.display === 'none' || style.visibility === 'hidden') return []
          const r = element.getBoundingClientRect()
          if (!r.width || !r.height) return []
          const outside = r.left < -1 || r.top < -1 || r.right > innerWidth + 1 || r.bottom > innerHeight + 1
          return outside ? [element.textContent.trim() || element.id || element.tagName] : []
        })""",
    )


def overlap_area(page: Page, left: str, right: str) -> float:
    return float(
        page.evaluate(
            """([leftSelector, rightSelector]) => {
              const a = document.querySelector(leftSelector)?.getBoundingClientRect()
              const b = document.querySelector(rightSelector)?.getBoundingClientRect()
              if (!a || !b) return 0
              const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left))
              const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top))
              return width * height
            }""",
            [left, right],
        )
    )


def audit_viewport(page: Page, base_url: str, viewport: Viewport) -> list[str]:
    failures: list[str] = []
    page.set_viewport_size({"width": viewport.width, "height": viewport.height})
    page.goto(f"{base_url}/?view=case", wait_until="networkidle", timeout=90_000)
    page.locator("#case-at-a-glance article").first.wait_for(state="visible", timeout=30_000)
    page.locator("#case-network-graph.case-system-flow-host").wait_for(state="visible", timeout=30_000)

    prefix = f"{viewport.width}x{viewport.height}"
    doc_width = int(page.evaluate("() => document.documentElement.scrollWidth"))
    if doc_width > viewport.width + 2:
        failures.append(f"{prefix}: page requires horizontal scrolling ({doc_width}px wide)")

    tour = page.locator("#tourLayer")
    if tour.count() and tour.is_visible():
        failures.append(f"{prefix}: direct case deep link auto-started the product tour")

    glance = page.locator("#case-at-a-glance article")
    if glance.count() != 4:
        failures.append(f"{prefix}: expected four first-frame case-at-a-glance cards, found {glance.count()}")
    glance_text = page.locator("#case-at-a-glance").inner_text().casefold()
    for expected in ("decision", "pressure", "trajectory", "boundary"):
        if expected not in glance_text:
            failures.append(f"{prefix}: case-at-a-glance is missing {expected!r}")

    if page.locator("#case-network-graph.react-canvas-host").count():
        failures.append(f"{prefix}: default system map still mounts the dense graph canvas")
    cards = page.locator("#case-network-graph [data-case-system-node]")
    if cards.count() != 7:
        failures.append(f"{prefix}: readable system flow should expose 7 selectable semantic cards, found {cards.count()}")

    if viewport.width <= 620:
        tabs = page.locator(".view-tabs button[data-view]")
        if tabs.count() != 5:
            failures.append(f"{prefix}: expected five top-level destinations, found {tabs.count()}")
        outside = fully_inside_viewport(page, ".view-tabs button[data-view]")
        if outside:
            failures.append(f"{prefix}: top-level destinations extend outside viewport: {outside}")
        position = page.locator("#case-walkthrough").evaluate("element => getComputedStyle(element).position")
        if position != "static":
            failures.append(f"{prefix}: mobile case walkthrough should be in document flow, got position={position}")

    for _ in range(6):
        next_button = page.locator("#case-walkthrough-next")
        if next_button.is_visible():
            next_button.click()
            page.wait_for_timeout(60)
    page.locator("#case-evasion-contract article").first.wait_for(state="visible", timeout=10_000)

    if page.locator("#case-evasion-contract article").count() != 4:
        failures.append(f"{prefix}: comparison contract should contain four cards")
    contract_text = page.locator("#case-evasion-contract").inner_text().casefold()
    for expected in ("held fixed", "changed", "observed", "not established"):
        if expected not in contract_text:
            failures.append(f"{prefix}: comparison contract missing {expected!r}")

    rows = page.locator(".case-comparison-table tbody tr")
    if rows.count() != 5:
        failures.append(f"{prefix}: aligned comparison should contain five shared measures, found {rows.count()}")
    comparison_text = page.locator("#case-evasion-compare").inner_text().casefold()
    for expected in (
        "6 support · 20 conditional",
        "26 conditional",
        "blocked",
        "degrading",
        "incompatible requirements",
        "process delay",
        "one cross-domain compact",
        "14 support · 11 conditional · 1 defer",
    ):
        if expected.casefold() not in comparison_text:
            failures.append(f"{prefix}: aligned comparison missing {expected!r}")

    clipped_cells = page.eval_on_selector_all(
        ".case-comparison-table td",
        """(cells) => cells.flatMap((cell) => {
          const clipped = cell.scrollWidth > cell.clientWidth + 2 || cell.scrollHeight > cell.clientHeight + 2
          return clipped ? [cell.textContent.trim()] : []
        })""",
    )
    if clipped_cells:
        failures.append(f"{prefix}: comparison values are clipped inside cells: {clipped_cells}")

    if viewport.width <= 620:
        area = overlap_area(page, "#case-walkthrough", "#case-evasion-contract")
        if area > 1:
            failures.append(f"{prefix}: walkthrough controls overlap comparison contract ({area:.0f}px²)")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--chromium", default=None, help="explicit Chromium executable; otherwise let Playwright resolve it")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    failures: list[str] = []
    with sync_playwright() as playwright:
        launch_options: dict[str, object] = {"headless": True, "args": ["--no-sandbox"]}
        if args.chromium:
            launch_options["executable_path"] = args.chromium
        browser = playwright.chromium.launch(**launch_options)  # type: ignore[arg-type]
        page = browser.new_page()
        for viewport in VIEWPORTS:
            try:
                failures.extend(audit_viewport(page, base_url, viewport))
            except Exception as error:  # noqa: BLE001 - an unreadable flagship case is a gate failure
                failures.append(f"{viewport.width}x{viewport.height}: case audit could not complete ({type(error).__name__}: {error})")
        browser.close()

    if failures:
        print("FLAGSHIP CASE UX FAILURES:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("flagship case is readable and usable at desktop and mobile review widths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
