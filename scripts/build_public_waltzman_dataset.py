#!/usr/bin/env python3
"""Build the public outbreak-workbench snapshot from retained authentic runs."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RUN_IDS = (
    "run_593ca1c425f2",
    "run_0b5e20260805",
    "run_c688aa8121fe",
    "run_7eae20260805",
    "run_ca9a20260805",
)

CONDITION_LABELS = {
    "baseline": "Baseline",
    "responsive_exercise_injects": "Responsive capacity pressure",
    "capacity_inject_replay_with_stabilization": (
        "Capacity pressure + allocation stabilization"
    ),
}

Decision = Literal["support", "conditional", "defer", "oppose"]
Risk = Literal["none", "evidence_quality", "sovereignty", "capacity", "legitimacy"]
Request = Literal["none", "validation", "safeguards", "resources", "escalation"]


class PublicStance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: str
    person_label: str
    group_id: str
    group_label: str
    decision: Decision
    risk: Risk
    request: Request
    rationale: str


class PublicRound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round: int = Field(ge=1, le=3)
    decision_counts: dict[str, int]
    risk_counts: dict[str, int]
    request_counts: dict[str, int]
    stances: list[PublicStance]


class PublicDevelopment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    after_round: int = Field(ge=1, le=2)
    document_kind: Literal[
        "exercise_development", "authoritative_allocation_package"
    ]
    development_id: str
    source: str
    audience_group: str
    content: str
    instruction: str


class GateCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    check_id: str
    label: str
    observed: int
    required: str
    passed: bool


class PublicRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    condition: str
    condition_label: str
    replicate: int
    created_at: str
    model: str
    reasoning_effort: str
    model_calls: int
    observed_cost: float
    outcome: Literal["joint_response_approved", "no_joint_response"]
    outcome_label: str
    gate_checks: list[GateCheck]
    rounds: list[PublicRound]
    developments: list[PublicDevelopment]


class PersonOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: str
    person_label: str
    group_id: str
    group_label: str


class PublicDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    dataset_id: str
    source_sha256: str
    evidence_latest_at: str
    scenario: str
    scenario_title: str
    scenario_summary: str
    initial_plan: list[str]
    agent_count: Literal[12] = 12
    round_count: Literal[3] = 3
    total_model_calls: Literal[180] = 180
    people: list[PersonOption]
    runs: list[PublicRun]
    limitations: list[str]


def _group(person_id: str) -> tuple[str, str]:
    prefix = person_id.split("_", 1)[0]
    if prefix in {"alba", "borin", "cyrenia"}:
        return prefix, prefix.title()
    return "regional", "Regional institution"


def _person_label(person_id: str) -> str:
    return person_id.replace("_", " ").title()


def _count(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _external_developments(document: dict[str, object]) -> list[PublicDevelopment]:
    developments: dict[tuple[object, ...], PublicDevelopment] = {}
    for event in document.get("events", []):
        if not isinstance(event, dict):
            continue
        patch = event.get("patch")
        if not isinstance(patch, dict):
            continue
        observations = patch.get("observations_added", [])
        if not isinstance(observations, list):
            continue
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            raw_content = observation.get("apparent_content")
            if not isinstance(raw_content, str):
                continue
            try:
                content = json.loads(raw_content)
            except json.JSONDecodeError:
                continue
            if not isinstance(content, dict):
                continue
            kind = content.get("document_kind")
            if kind not in {
                "exercise_development",
                "authoritative_allocation_package",
            }:
                continue
            after_round = content.get("after_round")
            text = content.get("content")
            instruction = content.get("instruction")
            if (
                not isinstance(after_round, int)
                or not isinstance(text, str)
                or not isinstance(instruction, str)
            ):
                raise ValueError("retained external development is malformed")
            if kind == "exercise_development":
                development_id = content.get("inject_id")
                target = observation.get("target_entity_id")
                if not isinstance(development_id, str) or not isinstance(target, str):
                    raise ValueError("retained exercise development lacks identity")
                _, audience_group = _group(target)
                key = (after_round, kind, development_id, audience_group, text)
            else:
                development_id = content.get("stabilization_id")
                if not isinstance(development_id, str):
                    raise ValueError("retained stabilization lacks identity")
                audience_group = "All participants"
                key = (after_round, kind, development_id, text)
            developments[key] = PublicDevelopment(
                after_round=after_round,
                document_kind=kind,
                development_id=development_id,
                source=str(observation.get("apparent_source_ref") or "unknown"),
                audience_group=audience_group,
                content=text,
                instruction=instruction,
            )
    return sorted(
        developments.values(),
        key=lambda item: (
            item.after_round,
            item.document_kind,
            item.audience_group,
            item.content,
        ),
    )


def _gate_checks(final_counts: dict[str, int]) -> list[GateCheck]:
    support = final_counts.get("support", 0)
    conditional = final_counts.get("conditional", 0)
    oppose = final_counts.get("oppose", 0)
    return [
        GateCheck(
            check_id="executable_support",
            label="Executable-now support",
            observed=support,
            required="at least 6",
            passed=support >= 6,
        ),
        GateCheck(
            check_id="aligned_positions",
            label="Support or conditional",
            observed=support + conditional,
            required="at least 9",
            passed=support + conditional >= 9,
        ),
        GateCheck(
            check_id="opposition_ceiling",
            label="Opposition",
            observed=oppose,
            required="no more than 1",
            passed=oppose <= 1,
        ),
    ]


def _public_round(round_document: dict[str, object]) -> PublicRound:
    raw_stances = round_document.get("stances")
    if not isinstance(raw_stances, dict) or len(raw_stances) != 12:
        raise ValueError("retained round must contain twelve stances")
    stances: list[PublicStance] = []
    for person_id, raw_stance in sorted(raw_stances.items()):
        if not isinstance(person_id, str) or not isinstance(raw_stance, dict):
            raise ValueError("retained stance is malformed")
        group_id, group_label = _group(person_id)
        stances.append(
            PublicStance(
                person_id=person_id,
                person_label=_person_label(person_id),
                group_id=group_id,
                group_label=group_label,
                decision=raw_stance.get("decision"),
                risk=raw_stance.get("risk"),
                request=raw_stance.get("request"),
                rationale=raw_stance.get("rationale"),
            )
        )
    round_number = round_document.get("round")
    if not isinstance(round_number, int):
        raise ValueError("retained round lacks its number")
    return PublicRound(
        round=round_number,
        decision_counts=_count([stance.decision for stance in stances]),
        risk_counts=_count([stance.risk for stance in stances]),
        request_counts=_count([stance.request for stance in stances]),
        stances=stances,
    )


def build_dataset(runs_dir: Path) -> PublicDataset:
    source_documents: list[tuple[Path, bytes, dict[str, object]]] = []
    for run_id in RUN_IDS:
        path = runs_dir / f"{run_id}.json"
        raw = path.read_bytes()
        document = json.loads(raw)
        if document.get("run_id") != run_id:
            raise ValueError(f"retained run identity mismatch for {run_id}")
        if document.get("scenario") != "regional_outbreak":
            raise ValueError(f"unexpected scenario for {run_id}")
        if document.get("status") != "completed":
            raise ValueError(f"run is not complete: {run_id}")
        if document.get("model_calls") != 36:
            raise ValueError(f"unexpected call count for {run_id}")
        source_documents.append((path, raw, document))

    combined_digest = sha256()
    for path, raw, _ in source_documents:
        combined_digest.update(path.name.encode("utf-8"))
        combined_digest.update(b"\0")
        combined_digest.update(raw)
        combined_digest.update(b"\0")
    source_digest = combined_digest.hexdigest()

    arm_seen: Counter[str] = Counter()
    public_runs: list[PublicRun] = []
    for _, _, document in source_documents:
        arm = document.get("arm")
        outcome = document.get("outcome")
        configuration = document.get("llm_configuration")
        if not isinstance(arm, str) or not isinstance(outcome, dict):
            raise ValueError("retained run lacks condition or outcome")
        if not isinstance(configuration, dict):
            raise ValueError("retained run lacks LLM configuration")
        raw_rounds = outcome.get("round_history")
        if not isinstance(raw_rounds, list) or len(raw_rounds) != 3:
            raise ValueError("retained run must contain three rounds")
        rounds = [_public_round(item) for item in raw_rounds if isinstance(item, dict)]
        if len(rounds) != 3:
            raise ValueError("retained round history contains malformed entries")
        arm_seen[arm] += 1
        final_counts = rounds[-1].decision_counts
        exact_outcome = outcome.get("outcome")
        if exact_outcome not in {"joint_response_approved", "no_joint_response"}:
            raise ValueError("retained coalition outcome is unsupported")
        public_runs.append(
            PublicRun(
                run_id=str(document["run_id"]),
                condition=arm,
                condition_label=CONDITION_LABELS[arm],
                replicate=arm_seen[arm],
                created_at=str(document["created_at"]),
                model=str(configuration["model"]),
                reasoning_effort=str(configuration.get("agent_reasoning_effort") or "default"),
                model_calls=int(document["model_calls"]),
                observed_cost=float(document.get("cost") or 0),
                outcome=exact_outcome,
                outcome_label=(
                    "Joint response approved"
                    if exact_outcome == "joint_response_approved"
                    else "No joint response"
                ),
                gate_checks=_gate_checks(final_counts),
                rounds=rounds,
                developments=_external_developments(document),
            )
        )

    first_stances = public_runs[0].rounds[0].stances
    people = [
        PersonOption(
            person_id=stance.person_id,
            person_label=stance.person_label,
            group_id=stance.group_id,
            group_label=stance.group_label,
        )
        for stance in first_stances
    ]
    latest = max(str(document["created_at"]) for _, _, document in source_documents)
    return PublicDataset(
        dataset_id=f"regional_outbreak_{source_digest[:16]}",
        source_sha256=source_digest,
        evidence_latest_at=latest,
        scenario="regional_outbreak",
        scenario_title="Regional outbreak response",
        scenario_summary=(
            "Twelve autonomous synthetic roles across three countries and a regional "
            "institution make three successive decisions about a joint outbreak response."
        ),
        initial_plan=[
            "Cross-laboratory validation is complete.",
            "Line-level records remain under national control and access is logged.",
            "Clinical command remains national.",
            "Reserve staff, supplies, reciprocal aid, and cost shares are precommitted.",
            "Local validation boards have endorsed launch.",
        ],
        people=people,
        runs=public_runs,
        limitations=[
            "The roles are synthetic and are not validated models of real people or governments.",
            "These trajectories demonstrate inspectable mechanisms; they do not estimate a real-world effect.",
            "Retained rationales expose stated reasons, not private beliefs.",
            "Live execution depends on the currently advertised certified route; completed public runs are retained separately from the immutable snapshot.",
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-dir", type=Path, default=Path("artifacts/runs"))
    parser.add_argument(
        "--output", type=Path, default=Path("public/waltzman/data.json")
    )
    args = parser.parse_args()
    dataset = build_dataset(args.runs_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(dataset.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "dataset_id": dataset.dataset_id,
                "source_sha256": dataset.source_sha256,
                "runs": len(dataset.runs),
                "stances": sum(
                    len(round_.stances)
                    for run in dataset.runs
                    for round_ in run.rounds
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
