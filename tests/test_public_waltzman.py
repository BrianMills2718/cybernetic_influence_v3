"""Focused contracts for the executable public coordination workbench."""

from html.parser import HTMLParser
import json
from pathlib import Path
import plistlib

from fastapi.testclient import TestClient

from cybernetic_influence.api import create_app


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "public" / "waltzman"
PAGE = PUBLIC_ROOT / "index.html"
DATA = PUBLIC_ROOT / "data.json"
SCRIPT = PUBLIC_ROOT / "app.js"
STYLE = PUBLIC_ROOT / "styles.css"
REVIEW_PAGE = PUBLIC_ROOT / "review.html"
REVIEW_STYLE = PUBLIC_ROOT / "review.css"
REVIEW_TRACE = PUBLIC_ROOT / "simulation-trace.md"
AUTONOMOUS_PROBE = PUBLIC_ROOT / "autonomous-probe.json"
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
        if tag == "link" and attributes.get("rel") == "stylesheet":
            self.stylesheets.append(attributes.get("href") or "")
        if tag == "script":
            self.scripts.append(attributes.get("src") or "")


def _dataset() -> dict[str, object]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_public_page_is_an_executable_evidence_workbench() -> None:
    page = PAGE.read_text(encoding="utf-8")
    shape = _PageShape()
    shape.feed(page)

    assert shape.h1_count == 1
    assert "Coordination Environment Lab" in page
    assert "Create a coordination experiment" in page
    assert "Open Lab" in page
    assert "Lab workspace" in page
    assert "Choose, configure, run" in page
    assert "Overview" in page
    assert "Terminal decision gate" in page
    assert "Open method" in page
    assert "AI coordination simulation workbench" in page
    assert "Test how distributed influence changes a group’s ability to coordinate" in page
    assert "Configure the actors, pressure, and response loop" in page
    assert "Define the coalition" in page
    assert "Current demo template" in page
    assert "can an autonomous CSO cell respond?" in page
    assert "CSO detects and diagnoses" in page
    assert "Same role. Different environment. Different decision." in page
    assert "Inspect all agent decisions" in page
    assert "Waltzman mechanism probe" in page
    assert "From Minds to Coordination · autonomous influence probe" in page
    assert "Influence agents cannot vote or edit participants" in page
    assert "Run this condition again" in page
    assert "Can different local pressures push a coalition" in page
    assert "bounded exercise controller" in page
    assert "1 experiment" in page
    assert "3 decision rounds per condition" in page
    assert "Launch a joint regional response—or wait" in page
    assert "What each stance means" in page
    assert "Twenty-four regional clinicians" in page
    assert "10% regional reserve" in page
    assert "What enters the decision environment?" in page
    assert "Edit one role—or keep the reviewed coalition" in page
    assert "Institutional oughts—not personal commands" in page
    assert "Edit personal character and memory" in page
    assert "Mechanism analysis and retained evidence" in page
    assert shape.stylesheets == ["assets/styles.css?v=waltzman-cso-v1"]
    assert shape.scripts == ["assets/app.js?v=message-trace-v2"]
    assert {
        "overview-view",
        "case-view",
        "research-case-runs",
        "case-evidence-records",
        "case-cso-records",
        "run-view",
        "condition-options",
        "agent-config-select",
        "agent-mandate",
        "agent-context",
        "person-position",
        "person-disposition",
        "person-memories",
        "person-values",
        "person-goals",
        "person-beliefs",
        "person-decision-tendencies",
        "person-social-perceptions",
        "person-current-state",
        "person-capabilities",
        "person-limitations",
        "shared-situation",
        "control-preview",
        "run-experiment",
        "live-run-status",
        "open-live-run",
        "trajectory-grid",
        "run-matrix",
        "mechanism-view",
        "example-environment-select",
        "example-stage",
        "full-example-analysis",
        "case-trajectories",
        "case-overview-table",
        "case-gate-table",
        "agent-evidence-preview",
        "all-agent-evidence",
        "waltzman-lens",
        "mechanism-table",
        "run-select",
        "environment-results",
        "decision-gate-results",
        "raw-evidence-results",
        "participant-results",
        "round-buttons",
        "environment-events",
        "gate-checks",
        "run-inputs",
        "agent-list",
        "agent-detail",
        "limitations",
        "provenance-digest",
    }.issubset(shape.element_ids)

    lowered = page.lower()
    assert "localhost" not in lowered
    assert "tail9c321e" not in lowered


def test_external_review_dossier_is_concise_and_auditable() -> None:
    page = REVIEW_PAGE.read_text(encoding="utf-8")
    style = REVIEW_STYLE.read_text(encoding="utf-8")
    shape = _PageShape()
    shape.feed(page)

    assert shape.h1_count == 1
    assert "assumes familiarity with" in page
    assert "Did we implement Waltzman’s proposed defensive coordination loop faithfully?" in page
    assert "Autonomy boundary" in page
    assert "Fixed decision gate" in page
    assert "Four retained conditions" in page
    assert "Complete adaptive CSO trace" in page
    assert "Planner’s authorized choice set" in page
    assert "Representative independent decisions" in page
    assert "What the evidence supports" in page
    assert "Not established" in page
    assert "run_a27f8e4082ef" in page
    assert "review/trace" in page
    assert "89 model outputs · exact prompts and inputs" in page
    assert "api/runs/run_a27f8e4082ef" in page
    assert "tail9c321e" not in page.lower()
    assert shape.stylesheets == ["assets/review.css?v=waltzman-review-v1"]
    assert shape.scripts == []
    assert "max-width: 1180px" not in style


def test_tractable_trace_retains_every_model_output_and_review_input() -> None:
    trace = REVIEW_TRACE.read_text(encoding="utf-8")

    assert "critique of the simulation itself" in trace
    assert "Shared starting situation" in trace
    assert "Exact representative coalition prompt" in trace
    assert "Exact external-source system messages" in trace
    assert "Exact CSO system messages" in trace
    assert "Coalition round 1" in trace
    assert "Coalition round 2" in trace
    assert "Coalition round 3" in trace
    assert "Source phase 1" in trace
    assert "Source phase 2" in trace
    assert "CSO detect → diagnose → select sequence" in trace
    assert "Exact intervention fact delivered to every coalition role" in trace
    assert "Coalition outputs printed: `78`" in trace
    assert "Source outputs printed: `8`" in trace
    assert "CSO outputs printed: `3`" in trace
    assert "Does `cross_domain_compact` bundle so many verified facts" in trace
    assert 60_000 <= len(trace) <= 180_000


def test_autonomous_probe_retains_the_completed_matched_runs() -> None:
    probe = json.loads(AUTONOMOUS_PROBE.read_text(encoding="utf-8"))

    assert probe["schema_version"] == 1
    assert [condition["arm_id"] for condition in probe["conditions"]] == [
        "baseline",
        "adaptive_heterogeneous_pressure",
        "adaptive_pressure_with_stabilization",
    ]
    baseline, adaptive, stabilization = probe["conditions"]
    assert baseline["run_id"] == "run_73b84f6d4682"
    assert adaptive["run_id"] == "run_e3a1f6742777"
    assert baseline["outcome_label"] == "DEPLOY ON TIME"
    assert adaptive["outcome_label"] == "NO DECISION"
    assert [meeting["open_risks"] for meeting in baseline["meetings"]] == [0, 0, 0, 0]
    assert [meeting["open_risks"] for meeting in adaptive["meetings"]] == [0, 1, 3, 3]
    assert len(adaptive["source_moves"]) == 3
    assert stabilization["run_id"] == "run_7b3695edc3c1"
    assert stabilization["outcome_label"] == "NO DECISION"
    assert [meeting["open_risks"] for meeting in stabilization["meetings"]] == [0, 1, 3, 3]
    assert stabilization["meetings"][1]["stances"] == {"support_reduced": 5}


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
    assert all(
        len(round_document["stances"]) == 12
        for run in runs
        for round_document in run["rounds"]
    )
    assert all(len(run["gate_checks"]) == 3 for run in runs)

    outcomes = [run["outcome"] for run in runs]
    assert outcomes.count("joint_response_approved") == 3
    assert outcomes.count("no_joint_response") == 2


def test_public_client_runs_and_inspects_the_real_typed_contract() -> None:
    script = SCRIPT.read_text(encoding="utf-8")
    style = STYLE.read_text(encoding="utf-8")

    for capability in (
        "renderRunSetup",
        "startLiveRun",
        "pollLiveRun",
        "loadRetainedLiveRuns",
        "projectLiveRun",
        "renderComparison",
        "renderMechanism",
        "renderAutonomousProbe",
        "startAutonomousProbe",
        "conditionStory",
        "renderInspector",
        "renderEnvironment",
        "renderGate",
        "renderAgents",
        "readStateFromUrl",
        "applyRunScopeFromUrl",
        "syncUrl",
        "view:'overview'",
        "featuredRunIds",
        "researchCaseRunIds",
        "renderResearchCase",
        "fetch('assets/data.json'",
        "fetch('assets/autonomous-probe.json'",
        "apiRequest('api/runs'",
        "regional_outbreak_configuration:editableConfiguration",
        "personProfileFields",
        "retainedPersonExists",
        "selected.person.behavioral_profile",
        "adaptive_cso_stabilization",
        "cso_records:raw.outcome?.cso_records",
        "coordination_messages:raw.outcome?.coordination_messages",
        "Messages received before this decision",
        "Message attempt → delivery outcome",
        "data-message-target",
        "case-cso-records",
    ):
        assert capability in script

    assert "eventsource" not in script.lower()
    assert "websocket" not in script.lower()
    assert "openrouter" not in script.lower()
    assert "for (const run of dataset.runs) run.configuration" not in script
    assert "cannot launch new model runs" not in json.dumps(_dataset())
    assert "[hidden] { display: none !important; }" in style


def test_public_app_serves_defaults_and_rejects_misrouted_agent_configuration(
    tmp_path: Path,
) -> None:
    client = TestClient(
        create_app(
            web_root=PUBLIC_ROOT,
            run_root=tmp_path / "runs",
            allow_inline_styles=True,
        )
    )

    page = client.get("/")
    assert page.status_code == 200
    assert "style-src 'self' 'unsafe-inline'" in page.headers[
        "content-security-policy"
    ]

    review = client.get("/review")
    assert review.status_code == 200
    assert "External review dossier" in review.text

    trace = client.get("/review/trace")
    assert trace.status_code == 200
    assert trace.headers["content-type"].startswith("text/markdown")
    assert "Tractable simulation trace" in trace.text

    response = client.get("/api/config")
    assert response.status_code == 200
    outbreak = response.json()["scenarios"]["regional_outbreak"]
    configuration = outbreak["editable_configuration"]
    assert configuration["person_contract_id"] == "person_contract_v1"
    assert len(configuration["agents"]) == 26
    assert configuration["agents"][0]["agent_id"] == "alba_epidemiologist"
    person = configuration["agents"][0]["person"]
    assert person["entity_id"] == "alba_epidemiologist"
    assert person["disposition"]
    assert person["memories"]
    assert person["behavioral_profile"]["values"]
    assert person["behavioral_profile"]["goals"]
    assert person["behavioral_profile"]["beliefs"]
    assert person["behavioral_profile"]["decision_tendencies"]
    assert person["behavioral_profile"]["social_perceptions"]
    assert person["behavioral_profile"]["current_state"]
    assert person["behavioral_profile"]["capabilities"]
    assert person["behavioral_profile"]["limitations"]
    assert outbreak["maximum_live_calls"] == 89

    invalid = client.post(
        "/api/runs",
        json={
            "scenario": "service_desk",
            "arm_id": "baseline",
            "execution": "scripted",
            "regional_outbreak_configuration": configuration,
        },
    )
    assert invalid.status_code == 422
    assert "applies only to the regional_outbreak scenario" in invalid.json()["detail"]


def test_public_launch_agent_runs_the_typed_simulator() -> None:
    plist_bytes = PLIST.read_bytes()
    plistlib.loads(plist_bytes)
    plist = plist_bytes.decode("utf-8")

    assert "com.cybernetic-influence.waltzman-public" in plist
    assert "run-with-provider-secret.sh" in plist
    assert "uvicorn" in plist
    assert "cybernetic_influence.public_waltzman:app" in plist
    assert "8621" in plist
    assert "127.0.0.1" in plist
    assert "__PROJECT_ROOT__/.venv/bin/python" in plist
    assert "CYBERNETIC_INFLUENCE_PUBLIC_ROOT" in plist
    assert "CYBERNETIC_INFLUENCE_RUNS_DIR" in plist
    assert "CYBERNETIC_INFLUENCE_LIVE" in plist
    assert "__CERT_CODEX_LUNA__" in plist
    assert "__CERT_CODEX_TERRA__" in plist
    assert "__CERT_COORDINATION_CODEX_TERRA__" in plist
    assert "__PUBLIC_RUN_ROOT__" in plist
