"""Exercise the stakeholder deep link and multiscale map in a real browser."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright


def assert_spatial_containment(page: object) -> None:
    """Every placed node must remain inside its rendered place container."""
    violations = page.evaluate(
        """() => {
          const places = [...document.querySelectorAll(
            '.react-flow__node.cy-place-group'
          )]
          const placeById = new Map(
            places.map((element) => [
              element.dataset.id,
              element.getBoundingClientRect(),
            ])
          )
          return [...document.querySelectorAll(
            '.react-flow__node[data-parentid]'
          )].flatMap((element) => {
            const child = element.getBoundingClientRect()
            const parent = placeById.get(element.dataset.parentid)
            if (!parent) return [element.dataset.id]
            const outside =
              child.left < parent.left - 1 ||
              child.top < parent.top - 1 ||
              child.right > parent.right + 1 ||
              child.bottom > parent.bottom + 1
            return outside ? [element.dataset.id] : []
          })
        }"""
    )
    assert violations == [], violations


def assert_launch_controls_do_not_overlap(page: object) -> None:
    """The primary desktop controls must occupy distinct visible rectangles."""
    overlaps = page.evaluate(
        """() => {
          const selectors = [
            '.run-introduction',
            '.scenario-field',
            '.condition-field',
            '.run-card > .live',
            '.run-actions',
          ]
          const items = selectors.map((selector) => {
            const element = document.querySelector(selector)
            return [selector, element?.getBoundingClientRect()]
          }).filter(([, rectangle]) => rectangle && rectangle.width && rectangle.height)
          const collisions = []
          for (let leftIndex = 0; leftIndex < items.length; leftIndex += 1) {
            for (let rightIndex = leftIndex + 1; rightIndex < items.length; rightIndex += 1) {
              const [leftSelector, left] = items[leftIndex]
              const [rightSelector, right] = items[rightIndex]
              const width = Math.max(0, Math.min(left.right, right.right) - Math.max(left.left, right.left))
              const height = Math.max(0, Math.min(left.bottom, right.bottom) - Math.max(left.top, right.top))
              if (width * height > 1) collisions.push([leftSelector, rightSelector, width * height])
            }
          }
          return collisions
        }"""
    )
    assert overlaps == [], overlaps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8620")
    parser.add_argument(
        "--chromium",
        default=os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE"),
        help="Optional Chromium executable; otherwise Playwright's installed browser is used.",
    )
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument(
        "--run-id",
        help="Reuse one disposable completed coordination run instead of creating another.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    if args.run_id:
        response = httpx.get(f"{base_url}/api/runs/{args.run_id}", timeout=30)
        response.raise_for_status()
        if response.json().get("status") != "completed":
            raise RuntimeError("the supplied browser-verification run is not completed")
        run_id = args.run_id
    else:
        response = httpx.post(
            f"{base_url}/api/runs",
            json={
                "scenario": "coordination_decision",
                "arm_id": "stabilization",
                "execution": "scripted",
            },
            timeout=240,
        )
        response.raise_for_status()
        run_id = response.json()["run_id"]
    config_response = httpx.get(f"{base_url}/api/config", timeout=30)
    config_response.raise_for_status()
    config = config_response.json()
    live_expected = bool(
        config.get("live_authorized")
        and config.get("scenarios", {})
        .get("coordination_decision", {})
        .get("live_model_ids", [])
    )
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
        assert_launch_controls_do_not_overlap(page)
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
        assert_spatial_containment(page)
        assert page.locator("#live").is_checked() is live_expected
        if live_expected:
            page.locator("#run-settings").evaluate("element => element.open = true")
            assert page.locator("#model").is_visible()
            assert page.locator("#reasoning").input_value()
            assert page.locator("#max-cost-field").is_hidden() is (
                page.locator("#cost-details").inner_text().find(
                    "included with the signed-in ChatGPT Codex subscription"
                ) >= 0
            )
        else:
            assert page.locator("#live").is_disabled()

        first_story = page.locator("#turn-narratives .turn-narrative").first
        initial_situation = page.locator("#initial-situation")
        assert "The decision:" in initial_situation.inner_text()
        assert "The people:" in initial_situation.inner_text()
        assert "What may change the decision:" in initial_situation.inner_text()
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
            "Exact mechanisms",
            "through connection",
            "Committed mechanism",
            "state revision",
            '{"',
            "relied_on",
        ):
            assert internal_phrase not in detailed_prose
        assert (
            "The coordinator's request for explicit review reached 4 team members."
            in detailed_prose
        )
        assert "The independent verification result was recorded." in detailed_prose
        assert detailed_story.locator(".causal-result").count() > 0
        assert detailed_story.locator(".detailed-narrative-moment").count() == (
            page.locator("#turn-narratives .turn-narrative").count()
        )
        assert detailed_story.locator(".detailed-narrative-moment").first.evaluate(
            "card => card.querySelector('p').compareDocumentPosition(card.querySelector('.narrative-meta')) & Node.DOCUMENT_POSITION_FOLLOWING"
        )
        assert not detailed_story.locator(".narrative-evidence small").first.is_visible()

        group_tab = page.locator(
            '#trace-tabs button[data-person="deployment_partnership"]'
        )
        assert group_tab.inner_text() == "Deployment partnership"
        assert page.locator(
            '#trace-tabs button[data-person="mission_coordinator"]'
        ).inner_text() == "Mission Coordinator"
        assert page.locator(
            '#trace-tabs button[data-person="mission_coordinator"]'
        ).get_attribute("class") == "active"
        assert page.locator(".trace-tab-group").count() == 3
        group_tab.click()
        group_account = page.locator("#trace .composite-account")
        group_account.wait_for(state="visible")
        assert group_account.locator(".eyebrow").first.inner_text() == "GROUP VIEW"
        assert "This view follows 5 people as one group." in group_account.inner_text()
        assert "Showing all retained activity in this completed run." in group_account.inner_text()
        assert "produced 1 outward action" in group_account.inner_text()
        assert group_account.locator(
            'button[data-boundary-scope="full"]'
        ).get_attribute("aria-pressed") == "true"
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
        group_account.locator('button[data-boundary-scope="moment"]').click()
        page.wait_for_function(
            """() => !document.querySelector('#trace .boundary-activity')?.textContent.includes('Loading')"""
        )
        assert "Showing only activity retained through the selected causal moment." in group_account.inner_text()
        assert "Nothing has entered or left this group yet." in group_account.inner_text()
        group_account.locator('button[data-boundary-scope="full"]').click()
        assert "produced 1 outward action" in group_account.inner_text()
        assert not group_account.locator(".boundary-episode").first.is_visible()
        assert not group_account.locator(".group-activity-details").get_attribute("open")
        page.locator(
            '#trace-tabs button[data-person="mission_coordinator"]'
        ).click()
        assert "took part in" in page.locator("#trace .trace-summary p").inner_text()
        assert "was activated" not in page.locator("#trace .trace-summary p").inner_text()
        first_participant_moment = page.locator("#trace .trace-step").first
        assert first_participant_moment.locator("strong").inner_text().startswith(
            "Day 0"
        )
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
        assert_spatial_containment(page)
        assert page.locator("#spatial-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").inner_text().startswith(
            "Collapse "
        )

        page.locator("#causal-layout").click()
        assert page.locator("#causal-layout").get_attribute("aria-pressed") == "true"
        assert page.locator("#analytical-scale-toggle").is_enabled()
        assert page.locator("#analytical-boundary").is_enabled()
        page.wait_for_timeout(600)
        assert page.locator(".cy-graph-warning").count() == 0
        canvas = page.locator(".cy-graph-canvas").bounding_box()
        assert canvas is not None
        for node in page.locator(".react-flow__node").all():
            bounds = node.bounding_box()
            assert bounds is not None
            assert bounds["x"] >= canvas["x"] - 1
            assert bounds["y"] >= canvas["y"] - 1
            assert bounds["x"] + bounds["width"] <= canvas["x"] + canvas["width"] + 1
            assert bounds["y"] + bounds["height"] <= canvas["y"] + canvas["height"] + 1

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
        selected_boundary_label = page.locator(
            "#analytical-boundary option:checked"
        ).inner_text()
        page.locator("#analytical-scale-toggle").click()
        page.locator(".cy-graph-bar strong", has_text="Collapsed composite").wait_for()
        assert page.locator(".cy-flow-node--analytical_boundary").count() == 1
        assert selected_boundary_label in page.locator(
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

        page.locator("#scenario").select_option("coordination_decision")
        page.wait_for_function(
            """() => document.querySelectorAll('#analytical-boundary option').length === 2
                && document.querySelector('#spatial-layout')?.getAttribute('aria-pressed') === 'true'"""
        )
        assert page.locator("#live").is_checked() is live_expected
        if live_expected:
            page.locator("#live").uncheck()
        assert page.locator("#run").inner_text() == "Play reference simulation"
        page.locator("#run").click()
        page.locator("#pause").wait_for(state="visible")
        page.wait_for_timeout(100)
        page.locator("#pause").click()
        page.locator("#resume").wait_for(state="visible", timeout=60_000)
        assert page.locator("#resume").inner_text() == "Resume from retained step"
        assert "completed causal step" in page.locator(
            "#lifecycle-help"
        ).inner_text()
        page.locator("#resume").click()
        page.wait_for_function(
            """() => document.querySelector('#run-status')?.textContent === 'Completed'""",
            timeout=120_000,
        )
        assert page.locator("#map-section").is_visible()
        assert page.locator("#narrative-section").is_visible()

        browser.close()
    assert not console_errors, console_errors
    assert not failed_requests, failed_requests
    print(
        f"PASS {run_id}: narrative hierarchy and readable detailed story; deep link, "
        "all projections, projection-preserving spatial/causal collapse/expand, "
        "both composites, service-desk preview, and coordination pause/resume"
    )


if __name__ == "__main__":
    main()
