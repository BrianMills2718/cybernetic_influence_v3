"""Verify the retained five-condition comparison in the real desktop UI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8622")
    parser.add_argument("--assay-id")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument(
        "--chromium",
        default=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    if args.assay_id:
        response = httpx.get(
            f"{base_url}/api/composite-assays/{args.assay_id}", timeout=30
        )
    else:
        response = httpx.post(f"{base_url}/api/composite-assays", timeout=240)
    response.raise_for_status()
    assay = response.json()
    assay_id = assay["assay_id"]
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
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
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
        page.goto(f"{base_url}/?assay={assay_id}", wait_until="networkidle")

        assert page.locator("#history-view").is_visible()
        comparison = page.locator(f'section[data-assay-id="{assay_id}"]')
        comparison.wait_for(state="visible")
        assert comparison.locator("tbody tr").count() == 5
        assert comparison.locator("tbody tr.selected").count() == 1
        assert "Matched control" in comparison.locator("tbody tr.selected").inner_text()
        comparison_text = comparison.inner_text().lower()
        assert "what reached the group" in comparison_text
        assert "what the group sent out" in comparison_text
        assert "what happened outside" in comparison_text

        comparison.locator('[data-row-id="feedback_interruption"]').click()
        selected = comparison.locator("tbody tr.selected")
        assert "Verification feedback lost" in selected.inner_text()
        assert "Not preserved" in selected.inner_text()
        assert "No recovery observed" in selected.inner_text()
        selection = comparison.locator(".assay-selection")
        assert "1 outward result" in selection.inner_text().lower()

        comparison.locator('[data-row-id="external_risk"]').click()
        assert "Legitimate external risk" in comparison.locator(
            "tbody tr.selected"
        ).inner_text()
        assert "observed response: rational caution" in selection.inner_text().lower()
        assert "1 incoming flow" in selection.inner_text().lower()
        assert not selection.locator(".assay-evidence-details p").first.is_visible()

        selection.locator(".open-assay-group").click()
        page.locator("#map-section").wait_for(state="visible")
        assert page.locator("#narrative-section").is_visible()
        assert page.locator("#theory-analysis-section").is_visible()
        assert page.locator("#analytical-scale-control").is_visible()
        assert page.locator("#trace .composite-account").is_visible()
        assert "Deployment partnership" in page.locator("#trace").inner_text()
        assert page.locator("#spatial-layout").is_visible()
        assert page.locator("#causal-layout").is_visible()
        assert page.locator("#trajectory-layout").is_visible()

        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.locator("#history-tab").click()
            comparison.wait_for(state="visible")
            assert page.evaluate("window.scrollY") == 0
            page.screenshot(path=str(args.screenshot), full_page=True)
        browser.close()

    assert console_errors == [], console_errors
    assert failed_requests == [], failed_requests


if __name__ == "__main__":
    main()
