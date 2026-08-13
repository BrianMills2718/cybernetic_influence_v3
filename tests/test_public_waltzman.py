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
PUBLIC_GRAPH_SCRIPT = PUBLIC_ROOT / "graph-canvas.js"
PUBLIC_GRAPH_STYLE = PUBLIC_ROOT / "graph-canvas.css"
CANONICAL_GRAPH_SCRIPT = ROOT / "web" / "graph-canvas.js"
CANONICAL_GRAPH_STYLE = ROOT / "web" / "graph-canvas.css"
REVIEW_PAGE = PUBLIC_ROOT / "review.html"
REVIEW_STYLE = PUBLIC_ROOT / "review.css"
REVIEW_TRACE = PUBLIC_ROOT / "simulation-trace.md"
AUTONOMOUS_PROBE = PUBLIC_ROOT / "autonomous-probe.json"
RESOURCE_FORK = PUBLIC_ROOT / "resource-fork.json"
CASE_NETWORK = PUBLIC_ROOT / "case-network.json"
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
    assert "New simulation" in page
    assert "Guided example" in page
    assert "All simulations" in page
    assert "Methodology" in page
    assert "Every completed simulation automatically becomes the same guided replay" in page
    assert "Open the flagship case study" in page
    assert "Lab workspace" in page
    assert "Choose, configure, run" in page
    assert "Overview" in page
    assert "Terminal decision gate" in page
    assert "Open method" in page
    assert "AI coordination simulation workbench" in page
    assert "Explore how influence changes a sociotechnical system’s ability to coordinate" in page
    assert "What this workbench is for" in page
    assert "Model people as people—not as role labels" in page
    assert "Let information and action remain local" in page
    assert "Give the world independent causal mechanics" in page
    assert "Look for coordination-level effects" in page
    assert "Explore detection and bounded response" in page
    assert "below the level of “the institution”" not in page
    assert "Homogeneous broadcasts" in page
    assert "See how the simulator turns a configured world into a causal record" in page
    assert "Canonical walkthrough · retained Luna execution" in page
    assert "Every displayed node, connection, mechanism, and event comes from the retained run" in page
    assert "The view switches from configured structure to realized causal events" in page
    assert "Deliver one generator before the clinic loses power" not in page
    assert "Person</b> perceives and acts" not in page
    assert page.index('class="guide-controls"') < page.index('class="guide-stage"')
    assert "Four national response networks face one outbreak" in page
    assert "How local pressure can become a collective decision problem" in page
    assert "Complete network" in page
    assert "People participate through five interdependent response networks" in page
    assert "Should these networks activate one joint outbreak response?" in page
    assert "After those pressures stall coordination" in page
    assert "The experiment in three steps" in page
    assert "What the resource package did not solve" in page
    assert "Shared intent is not enough for collective action" in page
    assert "From Minds to Coordination · autonomous influence probe" in page
    assert "Influence agents cannot vote or edit participants" in page
    assert "Run this condition again" in page
    assert "What enters the decision environment?" in page
    assert "Edit one role—or keep the reviewed coalition" in page
    assert "Institutional oughts—not personal commands" in page
    assert "Edit personal character and memory" in page
    assert "Generate editable configuration" in page
    assert "Runnable now:" in page
    assert "1 · Describe" in page
    assert "Guided replay" in page
    assert "Show the complete system" in page
    assert "Edit one person directly" in page
    assert "Edit the influence network directly" in page
    assert "Tell the authoring model what to change" in page
    assert "How the simulator represents a world, produces change, and retains evidence" in page
    assert "The ontology is a set of separations—not a list of agent types" in page
    assert "One typed world—not one narrative per agent" in page
    assert "Information has a carrier, representation, provenance, route" in page
    assert "Project-owned ActiveRuntimeSession + CausalSession" in page
    assert "production integration not yet implemented" in page
    assert "N-ary mechanism semantics" in page
    assert "Undirected spatial links" in page
    assert "Natural language proposes semantic configuration" in page
    assert "Configured structure, spatial topology, and causal history" in page
    assert "Authority boundary: now versus adopted" in page
    assert shape.stylesheets == [
        "assets/graph-canvas.css?v=cleanup1",
        "assets/styles.css?v=authoring1",
    ]
    assert shape.scripts == [
        "assets/graph-canvas.js?v=cleanup1",
        "assets/app.js?v=authoring1",
    ]
    assert {
        "overview-view",
        "guide-view",
        "guide-graph",
        "guide-visual-mode",
        "guide-step-title",
        "guide-step-body",
        "guide-step-facts",
        "guide-step-language",
        "guide-step-takeaway",
        "guide-progress",
        "guide-previous",
        "guide-next",
        "method-view",
        "method-title",
        "method-purpose",
        "method-ontology",
        "method-world",
        "method-relations",
        "method-agency",
        "method-information",
        "method-affordances",
        "method-transitions",
        "method-time",
        "method-systems",
        "method-analysis",
        "method-authoring",
        "method-architecture",
        "method-limits",
        "case-view",
        "research-case-runs",
        "case-branch-detail",
        "case-evidence-records",
        "case-network-graph",
        "case-network-status",
        "case-network-inspector",
        "simulations-view",
        "simulation-list",
        "simulation-replay-host",
        "create-view",
        "create-prompt",
        "create-generate",
        "create-review",
        "create-brief-question",
        "create-brief-people",
        "create-brief-influences",
        "create-brief-rule",
        "create-world-facts",
        "create-world-groups",
        "create-people-list",
        "create-person-select",
        "create-save-person",
        "create-revision-prompt",
        "create-approve",
        "create-run",
        "create-stop",
        "create-result",
        "create-result-people",
        "create-result-steps",
        "create-result-round-tabs",
        "create-result-round",
        "create-result-network-graph",
        "create-replay-progress",
        "create-replay-previous",
        "create-replay-next",
        "create-replay-whole",
        "create-result-analysis",
        "create-coverage",
        "create-scenario-editor",
        "create-save-scenario",
        "create-scenario-concerns",
        "create-network-editor",
        "create-network-feedback",
        "create-network-deliveries",
        "create-save-network",
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
        "probe-condition-select",
        "probe-condition",
        "probe-next",
        "run-probe",
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


def test_public_graph_renderer_has_one_canonical_compiled_lineage() -> None:
    assert PUBLIC_GRAPH_SCRIPT.read_bytes() == CANONICAL_GRAPH_SCRIPT.read_bytes()
    assert PUBLIC_GRAPH_STYLE.read_bytes() == CANONICAL_GRAPH_STYLE.read_bytes()


def test_completed_case_retains_its_exact_network() -> None:
    network = json.loads(CASE_NETWORK.read_text(encoding="utf-8"))
    assert network["schema_version"] == 1
    assert network["source_run_id"] == "run_5010214f2466"
    assert network["status"] == "completed"
    assert network["scenario"] == "regional_outbreak"
    assert len(network["nodes"]) == 40
    assert len(network["edges"]) == 138


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
        "loadRetainedRunHistory",
        "ensureRetainedLiveRuns",
        "projectLiveRun",
        "renderComparison",
        "renderMechanism",
        "renderAutonomousProbe",
        "startAutonomousProbe",
        "renderInspector",
        "renderEnvironment",
        "renderGate",
        "renderAgents",
        "readStateFromUrl",
        "applyRunScopeFromUrl",
        "syncUrl",
        "view:'overview'",
        "renderResearchCase",
        "caseSystemProjection",
        "caseExactProjection",
        "renderCaseNetworkGraph",
        "ensureCaseNetwork",
        "window.CyberneticGraph.render",
        "guideRunId",
        "run_ffe88e1c15d5",
        "guideSteps",
        "canonicalGuideProjection",
        "canonicalGuideTrajectory",
        "ensureGuideRun",
        "renderGuideGraph",
        "renderGuide",
        "advanceGuide",
        "Next: ${guideSteps[state.guideStep + 1].kicker}",
        "renderCreateSimulation",
        "renderAuthoringCoverage",
        "renderCoordinationScenarioEditor",
        "saveCoordinationScenario",
        "coordination-configuration",
        "setAuthoringBusy",
        "advanceAuthoringDraft",
        "saveAuthoringPerson",
        "approveAuthoringDraft",
        "renderAuthoringBrief",
        "runAuthoredSimulation",
            "stopAuthoredSimulation",
            "renderAuthoredResult",
            "renderAuthoredReplay",
            "renderSimulationLibrary",
            "openSimulationReplay",
            "rememberCompletedSimulation",
            "data-simulation-run",
            "result.simulation_replay?.question",
            "CyberneticGraph?.clear",
        "include_projection=false",
        "/summary",
        "narration:'deterministic'",
        "fetch('assets/data.json'",
        "fetch('assets/autonomous-probe.json'",
        "fetch('assets/resource-fork.json'",
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
        "data-case-branch",
        "api/authoring/drafts",
        "codex/gpt-5.6-luna",
    ):
        assert capability in script

    assert "eventsource" not in script.lower()
    assert "websocket" not in script.lower()
    assert "openrouter" not in script.lower()
    assert "for (const run of dataset.runs) run.configuration" not in script
    assert "guide_clinic" not in script
    assert "authored teaching sequence" not in script
    assert "loadRetainedLiveRuns" not in script
    assert "conditionStory" not in script
    assert "example-environment-select" not in script
    assert "#mechanism-view:has(.swarm-demo)" not in style
    for obsolete_id in (
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
    ):
        assert obsolete_id not in PAGE.read_text(encoding="utf-8")
    assert script.index("$('#workbench').hidden = false") < script.index(
        "void loadRetainedRunHistory()"
    )
    assert "cannot launch new model runs" not in json.dumps(_dataset())
    assert "[hidden] { display: none !important; }" in style


def test_public_resource_fork_is_complete_and_checkpoint_paired() -> None:
    evidence = json.loads(RESOURCE_FORK.read_text(encoding="utf-8"))
    assert evidence["schema_version"] == 1
    assert evidence["model"] == "codex/gpt-5.6-luna"
    assert evidence["llm_client_revision"] == (
        "c608df60037ecc9a224b1e16737eeb1e7b2da381"
    )
    assert evidence["agent_count"] == 26
    assert evidence["total_model_calls"] == 160
    assert evidence["shared_checkpoint_digest"]
    assert {item["id"] for item in evidence["branches"]} == {
        "no_intervention", "partial", "complete", "false_claim"
    }
    assert all(len(item["trace_ids"]) == 26 for item in evidence["branches"])
    false_claim = next(item for item in evidence["branches"] if item["id"] == "false_claim")
    assert false_claim["manifest"]["verification_status"] == "contradicted"
    assert all(
        item["world_outcome"] == "claim_rejected_no_custody_change"
        for item in false_claim["resource_commitments"]
    )


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
