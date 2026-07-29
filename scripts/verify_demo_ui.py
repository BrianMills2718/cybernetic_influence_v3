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
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").is_enabled()
        assert page.locator("#analytical-boundary").is_enabled()

        first_story = page.locator("#turn-narratives .turn-narrative").first
        assert first_story.locator("p").is_visible()
        assert first_story.locator("p").inner_text().startswith("The schedule opened")
        first_metadata = first_story.locator(".narrative-meta").inner_text()
        assert first_metadata.startswith("Day 0 ·")
        assert "scenario minutes into" not in first_metadata

        page.locator("#narrative-detailed").click()
        detailed_story = page.locator("#detailed-narrative")
        detailed_story.wait_for(state="visible")
        detailed_prose = " ".join(detailed_story.locator("p").all_inner_texts())
        for internal_phrase in (
            "through connection",
            "Committed mechanism",
            "state revision",
            '{"',
        ):
            assert internal_phrase not in detailed_prose
        assert (
            "The coordinator's request for explicit review reached 4 team members."
            in detailed_prose
        )
        assert detailed_story.locator(".detailed-narrative-moment").first.evaluate(
            "card => card.querySelector('p').compareDocumentPosition(card.querySelector('.narrative-meta')) & Node.DOCUMENT_POSITION_FOLLOWING"
        )
        assert not detailed_story.locator(".narrative-evidence small").first.is_visible()

        group_tab = page.locator(
            '#trace-tabs button[data-person="deployment_partnership"]'
        )
        assert group_tab.inner_text() == "Deployment partnership · group view"
        assert page.locator(
            '#trace-tabs button[data-person="mission_coordinator"]'
        ).inner_text() == "Mission Coordinator"
        group_tab.click()
        group_account = page.locator("#trace .composite-account")
        group_account.wait_for(state="visible")
        page.wait_for_function(
            """() => !document.querySelector('#trace .boundary-activity')?.textContent.includes('Loading')"""
        )
        assert group_account.locator(".eyebrow").first.inner_text() == "GROUP VIEW"
        assert "This view follows 5 people as one group." in group_account.inner_text()
        for internal_phrase in (
            "Execution-inert",
            "Analytical composite",
            "Visible exact members",
            "World executor",
            "No realized boundary crossing",
        ):
            assert internal_phrase not in group_account.inner_text()
        technical_details = group_account.locator(".participant-technical")
        assert not technical_details.locator("dd").first.is_visible()
        assert group_account.locator("#inspect-composite").inner_text() == (
            "Highlight this group on the map"
        )
        page.locator(".timeline-marker").last.evaluate("element => element.click()")
        page.wait_for_function(
            """() => !document.querySelector('#trace .boundary-activity')?.textContent.includes('Loading')"""
        )
        assert "What the group did by this point" in group_account.inner_text()
        assert "produced 1 outward action" in group_account.inner_text()
        assert not group_account.locator(".boundary-episode").first.is_visible()
        assert not group_account.locator(".group-activity-details").get_attribute("open")
        page.locator(
            '#trace-tabs button[data-person="mission_coordinator"]'
        ).click()
        assert "took part in" in page.locator("#trace .trace-summary p").inner_text()
        assert "was activated" not in page.locator("#trace .trace-summary p").inner_text()
        first_participant_moment = page.locator("#trace .trace-step").first
        assert first_participant_moment.locator("strong").inner_text() == "Day 0"
        assert (
            "requested explicit, reasoned review"
            in first_participant_moment.locator("p").first.inner_text()
        )
        assert "activation_" not in first_participant_moment.inner_text()
        assert not first_participant_moment.locator("pre").is_visible()
        assert "scope_reduced" not in " ".join(
            page.locator("#trace .trace-step > p").all_inner_texts()
        )
        if args.screenshot:
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.locator("#narrative-section").screenshot(path=str(args.screenshot))

        page.locator("#analytical-scale-toggle").click()
        page.locator(
            ".cy-graph-bar strong",
            has_text="World topology · collapsed composite",
        ).wait_for()
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Expand "
        )
        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="World topology").wait_for()
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Collapse "
        )

        page.locator("#causal-layout").click()
        assert page.locator("#causal-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").is_enabled()
        assert page.locator("#analytical-boundary").is_enabled()

        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()
        assert page.locator(
            '.projection-toolbar button[aria-pressed="true"]'
        ).inner_text() == "Configured interaction pathways"
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Expand "
        )

        page.locator("#spatial-layout").click()
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").is_enabled()
        page.locator(
            ".cy-graph-bar strong",
            has_text="World topology · collapsed composite",
        ).wait_for()
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        page.locator("#causal-layout").click()
        assert page.locator("#causal-layout").get_attribute("aria-pressed") == "true"
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()

        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Expanded exact network").wait_for()
        page.locator("#analytical-boundary").select_option("pressure_source_ensemble")
        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert "Pressure-source ensemble" in page.locator(
            "#analytical-scale-toggle"
        ).inner_text()

        page.locator("#trajectory-layout").click()
        assert page.locator("#trajectory-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").is_disabled()
        assert page.locator("#analytical-boundary").is_disabled()
        page.locator("#causal-layout").click()
        assert page.locator("#causal-layout").get_attribute("aria-pressed") == "true"
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()

        page.locator("#scenario").select_option("service_desk")
        page.wait_for_function(
            """() => document.querySelectorAll('#analytical-boundary option').length === 1
                && document.querySelector('#spatial-layout')?.getAttribute('aria-pressed') === 'true'"""
        )
        assert page.locator("#analytical-scale-toggle").is_enabled()
        page.locator("#analytical-scale-toggle").click()
        page.locator(
            ".cy-graph-bar strong",
            has_text="World topology · collapsed composite",
        ).wait_for()
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="World topology").wait_for()

        browser.close()
    assert not console_errors, console_errors
    assert not failed_requests, failed_requests
    print(
        f"PASS {run_id}: narrative hierarchy and readable detailed story; deep link, "
        "all projections, projection-preserving spatial/causal collapse/expand, "
        "both composites, and service-desk preview"
    )


if __name__ == "__main__":
    main()
