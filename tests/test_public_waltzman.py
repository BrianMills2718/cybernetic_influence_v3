"""Focused contracts for the read-only public coordination workbench."""

from html.parser import HTMLParser
import json
from pathlib import Path
import plistlib


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "public" / "waltzman"
PAGE = PUBLIC_ROOT / "index.html"
DATA = PUBLIC_ROOT / "data.json"
SCRIPT = PUBLIC_ROOT / "app.js"
PLIST = ROOT / "deploy" / "com.cybernetic-influence.waltzman-public.plist"

RUN_IDS = {
    "run_593ca1c425f2",
    "run_0b5e20260805",
    "run_c688aa8121fe",
    "run_7eae20260805",
    "run_ca9a20260805",
}


class _PageShape(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.element_ids: set[str] = set()
        self.disabled_buttons: list[str] = []
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if element_id := attributes.get("id"):
            self.element_ids.add(element_id)
        if tag == "button" and "disabled" in attributes:
            self.disabled_buttons.append(attributes.get("class") or "")
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.stylesheets.append(attributes.get("href") or "")
        if tag == "script":
            self.scripts.append(attributes.get("src") or "")


def _dataset() -> dict[str, object]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_public_page_is_an_evidence_workbench() -> None:
    page = PAGE.read_text(encoding="utf-8")
    shape = _PageShape()
    shape.feed(page)

    assert shape.h1_count == 1
    assert "Coordination Environment Lab" in page
    assert "Compare" in page
    assert "Inspect run" in page
    assert "Scenario &amp; method" in page
    assert "New live run unavailable" in page
    assert "new-run" in shape.disabled_buttons
    assert shape.stylesheets == ["styles.css?v=workbench-v1"]
    assert shape.scripts == ["app.js?v=workbench-v1"]
    assert {
        "trajectory-grid",
        "run-matrix",
        "run-select",
        "round-buttons",
        "environment-events",
        "gate-checks",
        "group-filters",
        "agent-list",
        "agent-detail",
        "initial-plan",
        "limitations",
        "provenance-digest",
    }.issubset(shape.element_ids)

    lowered = page.lower()
    for internal_surface in (
        "localhost",
        "tail9c321e",
        "/api/",
        "play live simulation",
    ):
        assert internal_surface not in lowered


def test_public_dataset_retains_all_five_runs_and_180_agent_stances() -> None:
    dataset = _dataset()

    assert dataset["schema_version"] == 1
    assert dataset["scenario"] == "regional_outbreak"
    assert dataset["agent_count"] == 12
    assert dataset["round_count"] == 3
    assert dataset["total_model_calls"] == 180
    assert isinstance(dataset["source_sha256"], str)
    assert len(dataset["source_sha256"]) == 64

    runs = dataset["runs"]
    assert isinstance(runs, list)
    assert {run["run_id"] for run in runs} == RUN_IDS
    assert sum(run["model_calls"] for run in runs) == 180
    assert sum(len(run["rounds"]) for run in runs) == 15

    stances = [
        stance
        for run in runs
        for round_document in run["rounds"]
        for stance in round_document["stances"]
    ]
    assert len(stances) == 180
    assert all(stance["rationale"].strip() for stance in stances)
    assert all(len(round_document["stances"]) == 12 for run in runs for round_document in run["rounds"])
    assert all(len(run["gate_checks"]) == 3 for run in runs)

    outcomes = [run["outcome"] for run in runs]
    assert outcomes.count("joint_response_approved") == 3
    assert outcomes.count("no_joint_response") == 2


def test_public_client_exposes_inspection_without_execution() -> None:
    script = SCRIPT.read_text(encoding="utf-8")

    for capability in (
        "renderComparison",
        "renderInspector",
        "renderEnvironment",
        "renderGate",
        "renderAgents",
        "readStateFromUrl",
        "syncUrl",
        "fetch('data.json'",
    ):
        assert capability in script

    lowered = script.lower()
    for execution_surface in ("/api/", "eventsource", "websocket", "openrouter"):
        assert execution_surface not in lowered


def test_public_launch_agent_serves_only_the_static_workbench() -> None:
    plist_bytes = PLIST.read_bytes()
    plistlib.loads(plist_bytes)
    plist = plist_bytes.decode("utf-8")

    assert "com.cybernetic-influence.waltzman-public" in plist
    assert "http.server" in plist
    assert "8621" in plist
    assert "127.0.0.1" in plist
    assert "__PYTHON__" in plist
    assert "__PROJECT_ROOT__/public/waltzman" in plist
    assert "CYBERNETIC_INFLUENCE_LIVE" not in plist
    assert "OPENROUTER" not in plist
