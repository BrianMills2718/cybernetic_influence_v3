#!/usr/bin/env python3
"""Observe the exact resource-fork case in a real browser."""

from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--overview-screenshot", type=Path)
    parser.add_argument("--chromium", type=Path)
    parser.add_argument(
        "--require-network-graph",
        action="store_true",
        help="Require the retained run API and exercise both network projections.",
    )
    args = parser.parse_args()
    console_errors: list[str] = []
    failed_requests: list[str] = []
    with sync_playwright() as playwright:
        launch_options: dict[str, object] = {"headless": True, "args": ["--no-sandbox"]}
        if args.chromium:
            launch_options["executable_path"] = str(args.chromium)
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on(
            "console",
            lambda message: console_errors.append(message.text)
            if message.type == "error"
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                f"{request.method} {request.url}: {request.failure}"
            ),
        )
        page.goto(
            f"{args.base_url.rstrip('/')}/?view=case",
            wait_until="domcontentloaded",
        )
        page.locator("#case-view").wait_for(state="visible")
        assert "Four national response networks" in page.locator(
            "#research-case-title"
        ).inner_text()
        assert page.locator(".national-network-grid article").count() == 5
        assert "Regional coordination network" in page.locator(
            ".case-organizations"
        ).inner_text()
        assert "Conditional" in page.locator(".case-decision-key").inner_text()
        assert "How local pressure can become a collective decision problem" in page.locator(
            "#case-network-title"
        ).inner_text()
        if args.require_network_graph:
            page.locator("#case-network-graph .react-flow__node").first.wait_for(
                state="visible", timeout=60_000
            )
            assert "40 exact entities and 138 routes" in page.locator(
                "#case-network-status"
            ).inner_text()
            page.locator('[data-case-graph="exact"]').click()
            page.wait_for_timeout(1_000)
            exact_node_count = page.locator("#case-network-graph .react-flow__node").count()
            assert exact_node_count == 40, exact_node_count
            assert "40 exact entities · 138 exact routes" in page.locator(
                "#case-network-status"
            ).inner_text()
            page.locator("#case-network-graph .react-flow__node").first.click(force=True)
            assert "Select a node or connection" not in page.locator(
                "#case-network-inspector"
            ).inner_text()
            page.locator('[data-case-graph="system"]').click()
        assert page.locator("[data-case-branch]").count() == 4
        assert page.locator('[data-case-branch="complete"]').get_attribute("class").find(
            "active"
        ) >= 0
        assert "6 verified" in page.locator("#case-branch-detail").inner_text()
        assert "24 conditional" in page.locator(
            '[data-case-branch="complete"]'
        ).inner_text()
        page.locator('[data-case-branch="false_claim"]').click()
        assert "6 rejected by the audit" in page.locator(
            "#case-branch-detail"
        ).inner_text()
        assert "21 defer" in page.locator(
            '[data-case-branch="false_claim"]'
        ).inner_text()
        assert "exact reasoning" in page.locator("#case-evidence-records").inner_text()
        assert page.locator("#case-evidence-records article").count() == 3
        page.locator('[data-view="create"]').first.click()
        page.locator("#create-view").wait_for(state="visible")
        assert page.locator("#create-prompt").is_visible()
        assert page.locator("#create-generate").is_visible()
        page.locator(".create-boundary summary").click()
        page.locator("[data-open-lab]").first.click()
        page.locator("#run-view").wait_for(state="visible")
        assert page.locator("#condition-options").is_visible()
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.locator('[data-view="case"]').first.click()
            page.locator("#case-view").wait_for(state="visible")
            page.screenshot(path=str(args.screenshot), full_page=True)
        page.locator('[data-view="overview"]').first.click()
        page.locator("#overview-view").wait_for(state="visible")
        assert page.locator(".overview-goals li").count() == 7
        assert "Model people as people—not as role labels" in page.locator(
            ".overview-goals"
        ).inner_text()
        assert "Homogeneous broadcasts" in page.locator(".overview-goals").inner_text()
        if args.overview_screenshot:
            args.overview_screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.overview_screenshot), full_page=True)
        browser.close()
    if console_errors:
        raise RuntimeError(f"browser console errors: {console_errors}")
    if failed_requests:
        raise RuntimeError(f"failed browser requests: {failed_requests}")
    graph_status = " and both retained network projections" if args.require_network_graph else ""
    print(f"Resource-fork case{graph_status} and preserved Lab entry rendered without browser errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
