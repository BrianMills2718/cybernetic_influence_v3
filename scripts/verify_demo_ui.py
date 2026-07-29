"""Exercise the stakeholder deep link and multiscale map in a real browser."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8620")
    parser.add_argument(
        "--chromium",
        default=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        help="Optional Chromium executable; otherwise Playwright's installed browser is used.",
    )
    parser.add_argument("--screenshot", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    response = httpx.post(
        f"{base_url}/api/runs",
        json={
            "scenario": "coordination_decision",
            "arm_id": "stabilization",
            "execution": "scripted",
        },
        timeout=60,
    )
    response.raise_for_status()
    run_id = response.json()["run_id"]
    console_errors: list[str] = []
    failed_requests: list[str] = []
    with sync_playwright() as playwright:
        launch_options: dict[str, object] = {
            "headless": True,
            "args": ["--no-sandbox"],
        }
        if args.chromium:
            launch_options["executable_path"] = args.chromium
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
        page.goto(f"{base_url}/?run={run_id}", wait_until="networkidle")
        page.locator("#graph .cy-graph-shell").wait_for(state="visible")
        assert page.locator("#map-section").is_visible()
        assert page.locator("#narrative-section").is_visible()
        assert page.locator("#analytical-scale-control").is_visible()
        assert page.locator("#analytical-boundary option").count() == 2
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Collapse "
        )

        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()
        assert page.locator(
            '.projection-toolbar button[aria-pressed="true"]'
        ).inner_text() == "Configured interaction pathways"
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Expand "
        )

        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Expanded exact network").wait_for()
        page.locator("#analytical-boundary").select_option("pressure_source_ensemble")
        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert "Pressure-source ensemble" in page.locator(
            "#analytical-scale-toggle"
        ).inner_text()

        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(args.screenshot), full_page=True)
        browser.close()
    assert not console_errors, console_errors
    assert not failed_requests, failed_requests
    print(f"PASS {run_id}: deep link, map, both composites, collapse, and expand")


if __name__ == "__main__":
    main()
