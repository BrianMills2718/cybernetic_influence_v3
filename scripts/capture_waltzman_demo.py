#!/usr/bin/env python3
"""Capture a short, shareable walkthrough of one retained Waltzman demo run."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8620")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--screenshot", type=Path, required=True)
    return parser.parse_args()


def dwell(page: Page, locator: Locator, milliseconds: int = 1_600) -> None:
    locator.scroll_into_view_if_needed()
    page.wait_for_timeout(milliseconds)


def main() -> None:
    args = parse_args()
    args.video.parent.mkdir(parents=True, exist_ok=True)
    args.screenshot.parent.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    failed_requests: list[str] = []

    with tempfile.TemporaryDirectory(prefix="waltzman-demo-video-") as video_dir:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                record_video_dir=video_dir,
                record_video_size={"width": 1440, "height": 900},
            )
            page = context.new_page()
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
                f"{args.base_url.rstrip('/')}?run={args.run_id}",
                wait_until="networkidle",
            )
            page.locator("#graph .cy-graph-shell").wait_for(state="visible")
            walkthrough = page.locator(".waltzman-demonstration")
            walkthrough.wait_for(state="visible")
            video = page.video

            dwell(page, page.locator("#initial-situation"), 2_200)
            page.locator("#narrative-detailed").click()
            dwell(page, page.locator("#detailed-narrative"), 2_200)
            dwell(page, walkthrough, 3_200)
            walkthrough.screenshot(path=str(args.screenshot))

            evidence = walkthrough.locator(".measurement-evidence").first
            evidence.locator("summary").click()
            page.wait_for_timeout(900)
            evidence.locator(".measurement-evidence-button").first.click()
            page.locator("#event-detail").wait_for(state="visible")
            page.wait_for_timeout(2_600)

            dwell(page, walkthrough, 1_500)
            page.locator("#decision-environment-content .theory-all-findings").evaluate(
                "details => details.open = true"
            )
            page.locator("#decision-environment-content .theory-limitations").evaluate(
                "details => details.open = true"
            )
            dwell(
                page,
                page.locator("#decision-environment-content .theory-limitations"),
                2_400,
            )

            context.close()
            if video is None:
                raise RuntimeError("Playwright did not create a video recorder")
            video.save_as(str(args.video))
            browser.close()

    if console_errors:
        raise RuntimeError(f"browser console errors: {console_errors}")
    if failed_requests:
        raise RuntimeError(f"failed browser requests: {failed_requests}")
    print(f"Captured {args.video} and {args.screenshot}")


if __name__ == "__main__":
    main()
