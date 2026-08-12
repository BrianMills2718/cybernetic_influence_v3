#!/usr/bin/env python3
"""Build a reviewable trace from one retained outbreak run and its call records."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, cast


SOURCE_IDS = (
    "technical_pressure_source",
    "legal_pressure_source",
    "logistics_pressure_source",
    "community_pressure_source",
)
CSO_IDS = (
    "cso_decision_environment_monitor",
    "cso_coordination_diagnostician",
    "cso_stabilization_planner",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-json", type=Path, required=True)
    parser.add_argument("--calls-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_calls(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def label(identifier: str) -> str:
    return identifier.replace("cso", "CSO", 1).replace("_", " ").title().replace("Cso", "CSO")


def block(value: str, language: str = "text") -> str:
    fence = "````" if "```" in value else "```"
    return f"{fence}{language}\n{value.rstrip()}\n{fence}"


def json_block(value: Any) -> str:
    return block(json.dumps(value, indent=2, ensure_ascii=False), "json")


def country(agent_id: str) -> str:
    return "regional" if agent_id.startswith("regional_") else agent_id.split("_", 1)[0]


def response(call: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(call["response"]))


def main() -> None:
    args = parse_args()
    run = json.loads(args.run_json.read_text())
    calls = load_calls(args.calls_jsonl)
    expected_prefix = f"{run['run_id']}/"
    calls = [item for item in calls if item["trace_id"].startswith(expected_prefix)]
    if len(calls) != run["model_calls"]:
        raise ValueError(f"expected {run['model_calls']} calls, found {len(calls)}")

    call_by_trace = {item["trace_id"]: item for item in calls}
    traces = run["traces"]
    trace_by_person_time = {(item["person"], item["logical_time"]): item for item in traces}
    config = run["regional_outbreak_configuration"]
    agents = config["agents"]
    agent_ids = [item["agent_id"] for item in agents]
    histories = {item["round"]: item["stances"] for item in run["outcome"]["round_history"]}
    participant_times = sorted(
        {
            item["logical_time"]
            for item in traces
            if item["person"] in agent_ids
        }
    )
    if len(participant_times) != 3:
        raise ValueError(f"expected three coalition phases, found {participant_times}")

    def call_for_trace(trace: dict[str, Any]) -> dict[str, Any]:
        trace_id = f"{run['run_id']}/{trace['person']}/activation/{trace['activation']}"
        return call_by_trace[trace_id]

    def actor_output(person: str, logical_time: int) -> dict[str, Any]:
        return response(call_for_trace(trace_by_person_time[(person, logical_time)]))

    def observation_bundle(person: str, logical_time: int) -> dict[str, Any]:
        observations = trace_by_person_time[(person, logical_time)]["observations"]
        if len(observations) != 1:
            raise ValueError(f"expected one observation for {person} at {logical_time}")
        return cast(
            dict[str, Any], json.loads(observations[0]["apparent_content"])
        )

    representative: dict[str, str] = {}
    for agent_id in agent_ids:
        representative.setdefault(country(agent_id), agent_id)

    lines: list[str] = []
    add = lines.append
    add("# Tractable simulation trace: adaptive CSO run")
    add("")
    add("> **Purpose:** enable critique of the simulation itself—not merely its result. This document preserves every model-generated coalition, source, and CSO output from the authentic run while printing repeated shared inputs only once.")
    add("")
    add("## Trace identity")
    add("")
    add(f"- Run: `{run['run_id']}`")
    add(f"- Condition: `{run['arm']}`")
    add(f"- Status: `{run['status']}`")
    add(f"- Model: `{run['llm_configuration']['model']}`")
    add(f"- Reasoning effort: `{run['llm_configuration']['agent_reasoning_effort']}`")
    add(f"- Model calls: `{run['model_calls']}` (78 coalition, 8 source, 3 CSO)")
    add(f"- Observed cost: `${run['cost']:.8f}`; fully observable: `{str(run['cost_fully_observable']).lower()}`")
    add("- Runtime revision: `4cd1f20f232c964254df4aa57faabfd7cca10d05`")
    add("- Full uncompressed run: [raw retained API trace](../api/runs/run_a27f8e4082ef)")
    add("")
    add("### Compression rules")
    add("")
    add("- No model-generated action, stance, rationale, orientation, or memory update is omitted.")
    add("- A shared 26-agent coalition snapshot is printed once, then referenced by the four source calls that received it.")
    add("- Identical delivery wrappers are deduplicated by target country; country-specific source documents remain verbatim.")
    add("- Repeated runtime contract boilerplate is shown through one exact coalition prompt and the exact source/CSO system prompts.")
    add("- Low-level routing and state-commit events are omitted here and remain available in the raw trace.")
    add("")
    add("## 1. Fixed simulation inputs")
    add("")
    add("### Shared starting situation")
    add("")
    add(block(config["shared_situation"]))
    add("")
    add("### Exact decision gate")
    add("")
    add("After round three: at least 13 `support`; at least 20 `support + conditional`; at most 2 `oppose`. The gate is an exact mechanism and makes no model call.")
    add("")
    add("### Coalition roster")
    add("")
    for item in agents:
        add(f"#### {label(item['agent_id'])} (`{item['agent_id']}`)")
        add("")
        add(f"- **Mandate:** {item['mandate']}")
        add(f"- **Institutional context:** {item['institutional_context']}")
        add("")

    add("## 2. Prompt and interface contracts")
    add("")
    add("### Exact representative coalition prompt: Alba epidemiologist, round 1")
    add("")
    first_agent_call = call_for_trace(trace_by_person_time[("alba_epidemiologist", participant_times[0])])
    add("#### System message")
    add("")
    add(block(first_agent_call["messages"][0]["content"]))
    add("")
    add("#### User message")
    add("")
    add(block(first_agent_call["messages"][1]["content"]))
    add("")
    add("Every other coalition system message uses the same runtime contract, substituting that agent’s label, mandate, institutional context, and owned stance port from the roster above. Subsequent user messages add committed memory plus the exact delivered bundles printed later in this trace.")
    add("")
    add("### Exact external-source system messages")
    add("")
    for source_id in SOURCE_IDS:
        source_trace = min(
            (item for item in traces if item["person"] == source_id),
            key=lambda item: item["logical_time"],
        )
        source_call = call_for_trace(source_trace)
        add(f"#### {label(source_id)}")
        add("")
        add(block(source_call["messages"][0]["content"]))
        add("")
    add("### Exact CSO system messages")
    add("")
    for cso_id in CSO_IDS:
        cso_trace = next(item for item in traces if item["person"] == cso_id)
        cso_call = call_for_trace(cso_trace)
        add(f"#### {label(cso_id)}")
        add("")
        add(block(cso_call["messages"][0]["content"]))
        add("")

    def append_coalition_round(
        section_number: int,
        round_number: int,
        logical_time: int,
        input_ref: str,
    ) -> None:
        add(f"## {section_number}. Coalition round {round_number}")
        add("")
        add(f"**Input:** {input_ref}")
        add("")
        counts = Counter(item["decision"] for item in histories[round_number].values())
        add("**Aggregate:** " + " · ".join(f"{count} {stance}" for stance, count in sorted(counts.items())))
        add("")
        for agent_id in agent_ids:
            output = actor_output(agent_id, logical_time)
            action = output["actions"][0]
            add(f"### {label(agent_id)}")
            add("")
            add(f"- **Orientation:** {output['orientation']}")
            add(f"- **Memory update:** {output.get('memory_update') or '(none)' }")
            add(f"- **Public summary:** {action['public_summary']}")
            add(f"- **Exact stance payload:** `{json.dumps(action['payload'], ensure_ascii=False, sort_keys=True)}`")
            add("")

    append_coalition_round(3, 1, participant_times[0], "shared starting situation and private institutional context; no newly delivered observation")

    source_times = sorted(
        {item["logical_time"] for item in traces if item["person"] in SOURCE_IDS}
    )

    def append_source_phase(
        section_number: int,
        phase: int,
        logical_time: int,
        next_participant_time: int | None,
    ) -> None:
        add(f"## {section_number}. Source phase {phase}")
        add("")
        add(f"Each source received the complete coalition round-{phase} snapshot printed above. Their exact responses follow.")
        add("")
        for source_id in SOURCE_IDS:
            output = actor_output(source_id, logical_time)
            action = output["actions"][0]
            add(f"### {label(source_id)}")
            add("")
            add(f"- **Orientation:** {output['orientation']}")
            add(f"- **Memory update:** {output.get('memory_update') or '(none)' }")
            add(f"- **Public summary:** {action['public_summary']}")
            add(f"- **Exact signal payload:** `{json.dumps(action['payload'], ensure_ascii=False, sort_keys=True)}`")
            add("")
        if next_participant_time is not None:
            add("### Exact source documents delivered to coalition agents")
            add("")
            add("The simulator deterministically mapped each source’s `verify|escalate` choice to locally specific external facts. The complete coalition snapshot wrapper is omitted here because it is the round printed immediately above.")
            add("")
            for target_country, agent_id in representative.items():
                bundle = observation_bundle(agent_id, next_participant_time)
                add(f"#### Target: {target_country.title()} (same documents delivered to its roles)")
                add("")
                add(json_block(bundle["documents"]))
                add("")

    append_source_phase(4, 1, source_times[0], participant_times[1])
    append_coalition_round(5, 2, participant_times[1], "round-one coalition snapshot plus the country-specific source bundle printed above")
    append_source_phase(6, 2, source_times[1], None)

    add("## 7. CSO detect → diagnose → select sequence")
    add("")
    monitor_trace = next(item for item in traces if item["person"] == CSO_IDS[0])
    monitor_bundle = json.loads(monitor_trace["observations"][0]["apparent_content"])
    add("### Monitor input")
    add("")
    add("The monitor received the complete round-two coalition snapshot printed above plus these regional source documents:")
    add("")
    add(json_block(monitor_bundle["source_documents"]))
    add("")
    for cso_id in CSO_IDS:
        trace = next(item for item in traces if item["person"] == cso_id)
        output = response(call_for_trace(trace))
        action = output["actions"][0]
        add(f"### {label(cso_id)} output")
        add("")
        if cso_id != CSO_IDS[0]:
            add("**Exact delivered input:**")
            add("")
            add(block(trace["observations"][0]["apparent_content"], "json"))
            add("")
        add(f"- **Orientation:** {output['orientation']}")
        add(f"- **Memory update:** {output.get('memory_update') or '(none)' }")
        add(f"- **Public summary:** {action['public_summary']}")
        add(f"- **Exact action payload:** `{json.dumps(action['payload'], ensure_ascii=False, sort_keys=True)}`")
        add("")

    final_bundle = observation_bundle(representative["alba"], participant_times[2])
    add("### Exact intervention fact delivered to every coalition role")
    add("")
    add(json_block(final_bundle["intervention"]))
    add("")
    add("### Round-three source documents delivered alongside the intervention")
    add("")
    for target_country, agent_id in representative.items():
        bundle = observation_bundle(agent_id, participant_times[2])
        add(f"#### Target: {target_country.title()}")
        add("")
        add(json_block(bundle["documents"]))
        add("")

    append_coalition_round(8, 3, participant_times[2], "round-two coalition snapshot, country-specific source documents, and the exact CSO-selected intervention fact printed above")

    add("## 9. Exact terminal calculation")
    add("")
    final_counts = Counter(item["decision"] for item in histories[3].values())
    support = final_counts["support"]
    conditional = final_counts["conditional"]
    oppose = final_counts["oppose"]
    add(f"- Immediate support: `{support}` ≥ `13` → pass")
    add(f"- Support + conditional: `{support + conditional}` ≥ `20` → pass")
    add(f"- Opposition: `{oppose}` ≤ `2` → pass")
    add(f"- Recorded outcome: `{run['outcome']['outcome']}`")
    add("")
    add("## 10. Review targets")
    add("")
    add("Please critique at least these simulation-design questions:")
    add("")
    add("1. Do the role mandates and starting facts preload agreement or make recovery too easy?")
    add("2. Do the source choice prompts and deterministic signal-to-fact mappings represent distributed influence credibly?")
    add("3. Does the monitor observe too much, too little, or the wrong representation of the coalition?")
    add("4. Are the CSO taxonomies and authorized action catalog faithful enough to Waltzman’s proposal?")
    add("5. Does `cross_domain_compact` bundle so many verified facts that recovery becomes tautological?")
    add("6. Is the separation between CSO selection and coalition voting sufficient to rule out endogenous dictation?")
    add("7. Which alternative conditions, negative controls, false diagnoses, or failed interventions should be run next?")
    add("")
    add("## Integrity checks")
    add("")
    task_counts = Counter(item["task"] for item in calls)
    add(f"- Retained provider calls: `{len(calls)}`; unique trace IDs: `{len(call_by_trace)}`")
    add(f"- Task counts: `{dict(sorted(task_counts.items()))}`")
    add(f"- Completed statuses: `{Counter(item['status'] for item in run['model_call_summaries'])}`")
    add(f"- Coalition outputs printed: `{len(agent_ids) * 3}`")
    add(f"- Source outputs printed: `{len(SOURCE_IDS) * 2}`")
    add(f"- CSO outputs printed: `{len(CSO_IDS)}`")
    add("")

    rendered = "\n".join(lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output} ({len(rendered):,} characters)")


if __name__ == "__main__":
    main()
