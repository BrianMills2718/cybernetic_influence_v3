"""Post-run coordination measurement with no world-execution authority."""

from __future__ import annotations

import json
from bisect import bisect_right
from collections.abc import Callable, Mapping, Sequence
from importlib import resources
from typing import Any, Literal, cast

import yaml
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, JsonValue

from cybernetic_influence.active_runtime.models import ActiveRuntimeResult
from cybernetic_influence.analysis.coordination_measurement import (
    CODED_MEASURE_IDS,
    COORDINATION_MEASUREMENT_SPEC,
    COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
    CodedMeasureId,
    CoderOutput,
    EvidenceAttachment,
    ExactMeasureId,
    IndicatorEvidence,
    MeasurementCallEvidence,
    MeasurementEvidenceBundle,
    RunMeasurement,
    RunMeasurementConsumer,
    validate_coder_output,
)
from cybernetic_influence.causal_core.models import CausalEvent, EventKind
from cybernetic_influence.llm_backend import structured_backend_options
from cybernetic_influence.run_store import RunStore
from cybernetic_influence.scenarios.coordination_decision import (
    MEETING_TIMES,
    MINUTES_PER_DAY,
    PERSON_IDS,
    PRESSURE_SOURCE_IDS,
    SCENARIO_ID,
)

CODER_TASK = "cybernetic_coordination_evidence_coding"
CODER_PROMPT_VERSION = "coordination_evidence_coder/v1"
CODER_SCHEMA_REVISION: Literal[1] = 1
# One categorical response covers three bounded indicators; the ceiling prevents
# verbose prose from displacing the complete typed result.
CODER_MAX_TOKENS = 900
# Match the existing structured-call tolerance while retaining one visible call.
CODER_TIMEOUT_SECONDS = 180
CODER_MAX_BUDGET = 0.10

StructuredCall = Callable[..., tuple[Any, Any]]
ExactValues = dict[ExactMeasureId, JsonValue]


def calculate_exact_values(result: ActiveRuntimeResult) -> ExactValues:
    """Calculate the 15 exact measures from typed retained state and events."""

    if result.status != "completed" or result.scenario_id != SCENARIO_ID:
        raise ValueError("coordination measurement requires one completed v1 run")
    if result.completion is None:
        raise ValueError("completed coordination run lacks completion evidence")

    events = result.core_result.events
    state = result.core_result.final_state
    terminal_events = _outcome_events(events, "terminal_decision_accepted")
    if len(terminal_events) != 1:
        raise ValueError("coordination trace requires one accepted terminal decision")
    terminal = terminal_events[0]
    terminal_proposals = [
        event
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "terminal_proposal_out"
    ]

    verification_events = [
        event
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "verification_request_out"
    ]
    verification_by_meeting = [
        {
            "meeting_index": index,
            "modeled_day": MEETING_TIMES[index] // MINUTES_PER_DAY,
            "count": sum(
                _meeting_index(item.logical_time) == index
                for item in verification_events
            ),
        }
        for index in range(len(MEETING_TIMES))
    ]

    source_records = _records(
        state.fact("source_disposition_register.items").value,
        label="source disposition register",
    )
    source_edges: list[JsonValue] = [
        cast(
            JsonValue,
            {
                "actor_id": record.get("person_id"),
                "source_id": record.get("source_id"),
                "disposition": record.get("disposition"),
                "evidence_refs": record.get("evidence_refs", []),
            },
        )
        for record in source_records
    ]
    issue_records = _records(
        state.fact("issue_register.items").value,
        label="issue register",
    )
    open_issue_count = _open_issue_count(issue_records)
    issue_open_events = _outcome_events(events, "issue_open")
    threshold_events = _outcome_events(events, "scope_threshold_recorded")
    meeting_events = _outcome_events(events, "meeting_wake_recorded")
    reopening_events = _outcome_events(events, "issue_reopened")
    disengagement_events = _outcome_events(events, "partner_withdrawal_recorded")
    bypass_events = _outcome_events(events, "intermediary_bypass_recorded")
    alignment_events = [
        event
        for event in events
        if event.event_kind == "action_attempted"
        and event.source_port_id == "alignment_message_out"
    ]
    external_actions = [
        event
        for event in events
        if event.event_kind == "action_attempted"
        and event.actor_entity_id in {*PERSON_IDS, *PRESSURE_SOURCE_IDS}
    ]
    active_partner_count = _required_int(
        state.fact("decision_record.active_partner_count").value,
        "active partner count",
    )
    terminal_status = _required_string(
        state.fact("external_decision_registry.received_status").value,
        "terminal deployment status",
    )
    terminal_scope = _required_string(
        state.fact("external_decision_registry.received_scope").value,
        "terminal deployment scope",
    )
    decision_latency: JsonValue
    if terminal_proposals:
        proposal = terminal_proposals[0]
        decision_latency = cast(
            JsonValue,
            {
                "scenario_minutes": terminal.logical_time - proposal.logical_time,
                "proposal_event_id": proposal.event_id,
                "terminal_event_id": terminal.event_id,
            },
        )
    else:
        decision_latency = cast(
            JsonValue,
            {
                "scenario_minutes": None,
                "proposal_event_id": None,
                "terminal_event_id": terminal.event_id,
            },
        )

    values: ExactValues = {
        "final_deployment_status": terminal_status,
        "modeled_time_to_terminal": cast(
            JsonValue,
            {
                "scenario_minutes": result.completion.logical_time,
                "scenario_days": result.completion.logical_time / MINUTES_PER_DAY,
                "completion_reason": result.completion.reason,
                "event_ids": list(result.completion.evidence_event_ids),
            },
        ),
        "partners_retained": cast(
            JsonValue,
            {
                "count": active_partner_count,
                "proportion": active_partner_count / len(PERSON_IDS),
            },
        ),
        "final_approved_scope": terminal_scope,
        "verification_requests": cast(
            JsonValue,
            {
                "total": len(verification_events),
                "by_meeting": verification_by_meeting,
                "event_ids": _event_ids(verification_events),
            },
        ),
        "source_reliance_topology": cast(
            JsonValue,
            {"edge_count": len(source_edges), "edges": source_edges},
        ),
        "intermediary_bypass": cast(
            JsonValue,
            {"count": len(bypass_events), "event_ids": _event_ids(bypass_events)},
        ),
        "risk_register_expansion": cast(
            JsonValue,
            {
                "distinct_risks": len(
                    {
                        str(item["issue_id"])
                        for item in issue_records
                        if isinstance(item.get("issue_id"), str)
                    }
                ),
                "event_ids": _event_ids(issue_open_events),
            },
        ),
        "action_threshold_change": cast(
            JsonValue,
            {
                "count": len(threshold_events),
                "final_threshold": state.fact(
                    "deployment_proposal.decision_threshold"
                ).value,
                "event_ids": _event_ids(threshold_events),
            },
        ),
        "unresolved_risk_load": cast(
            JsonValue,
            {
                "at_meetings": _unresolved_risk_series(events),
                "final_open_count": open_issue_count,
            },
        ),
        "decision_latency": decision_latency,
        "deliberation_load": cast(
            JsonValue,
            {
                "meeting_cycles": len(meeting_events),
                "external_action_attempts": len(external_actions),
                "event_ids": _event_ids([*meeting_events, *external_actions]),
            },
        ),
        "issue_reopening": cast(
            JsonValue,
            {
                "count": len(reopening_events),
                "event_ids": _event_ids(reopening_events),
            },
        ),
        "informal_alignment": cast(
            JsonValue,
            {
                "message_count": len(alignment_events),
                "event_ids": _event_ids(alignment_events),
            },
        ),
        "disengagement": cast(
            JsonValue,
            {
                "count": len(disengagement_events),
                "event_ids": _event_ids(disengagement_events),
            },
        ),
    }
    return values


def build_measurement_evidence_bundle(
    result: ActiveRuntimeResult,
    *,
    expected_scenario_fingerprint: str,
) -> tuple[MeasurementEvidenceBundle, list[EvidenceAttachment]]:
    """Build the exact redacted evidence that one coder call may inspect."""

    if result.status != "completed" or result.scenario_id != SCENARIO_ID:
        raise ValueError("evidence coding requires one completed coordination run")
    required_kinds = _coded_source_event_kinds()
    trace_ids = _event_trace_ids(result)
    visible_events = [
        {
            "event_id": event.event_id,
            "run_id": result.run_id,
            "event_kind": event.event_kind,
            "summary": event.summary,
            "trace_ids": trace_ids[event.event_id],
        }
        for event in result.core_result.events
        if event.event_kind in required_kinds
    ]
    bundle = MeasurementEvidenceBundle.model_validate(
        {
            "run_id": result.run_id,
            "run_status": result.status,
            "scenario_fingerprint": result.scenario_fingerprint,
            "expected_scenario_fingerprint": expected_scenario_fingerprint,
            "measurement_spec_version": 1,
            "measurement_spec_fingerprint": (COORDINATION_MEASUREMENT_SPEC_FINGERPRINT),
            "expected_measurement_spec_fingerprint": (
                COORDINATION_MEASUREMENT_SPEC_FINGERPRINT
            ),
            "visible_events": visible_events,
        }
    )
    attachments = [
        EvidenceAttachment(
            indicator_id=cast(CodedMeasureId, indicator_id),
            source_event_ids=[
                item.event_id
                for item in bundle.visible_events
                if item.event_kind
                in _coded_indicator_event_kinds(cast(CodedMeasureId, indicator_id))
            ],
            source_trace_ids=list(
                dict.fromkeys(
                    trace_id
                    for item in bundle.visible_events
                    if item.event_kind
                    in _coded_indicator_event_kinds(cast(CodedMeasureId, indicator_id))
                    for trace_id in item.trace_ids
                )
            ),
        )
        for indicator_id in CODED_MEASURE_IDS
    ]
    return bundle, attachments


def code_coordination_evidence(
    bundle: MeasurementEvidenceBundle,
    attachments: list[EvidenceAttachment],
    *,
    model: str,
    reasoning_effort: str,
    trace_id: str,
    max_budget: float,
    structured_call: StructuredCall | None = None,
) -> tuple[list[IndicatorEvidence], MeasurementCallEvidence]:
    """Make one strict shared-client call and bind it to supplied evidence."""

    if max_budget <= 0:
        raise ValueError("measurement coder budget must be positive")
    call = structured_call or _resolve_structured_call()
    system_prompt, user_prompt = _render_prompt(bundle)
    with structured_backend_options(model) as backend_options:
        parsed, meta = call(
            model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model_justification=(
                "Classify only the three frozen evidence-coded coordination "
                "indicators from the analyst-visible retained trace."
            ),
            response_model=CoderOutput,
            task=CODER_TASK,
            trace_id=trace_id,
            max_budget=max_budget,
            max_tokens=CODER_MAX_TOKENS,
            timeout=CODER_TIMEOUT_SECONDS,
            reasoning_effort=reasoning_effort,
            **backend_options,
        )
    output = CoderOutput.model_validate(
        parsed.model_dump(mode="json") if isinstance(parsed, BaseModel) else parsed
    )
    indicators = validate_coder_output(bundle, output, attachments)
    observed_cost = _observed_cost(meta)
    evidence = MeasurementCallEvidence(
        status="completed",
        task=CODER_TASK,
        trace_id=trace_id,
        schema_revision=CODER_SCHEMA_REVISION,
        prompt_version=CODER_PROMPT_VERSION,
        model=model,
        reasoning_effort=reasoning_effort,
        max_budget=max_budget,
        observed_cost=observed_cost,
        cost_source=_cost_source(meta),
        cost_covers_all_attempts=_cost_covers_all_attempts(meta),
        structured_output=output,
    )
    return indicators, evidence


def analyze_coordination_run(
    result: ActiveRuntimeResult,
    *,
    expected_scenario_fingerprint: str,
    model: str,
    reasoning_effort: str,
    trace_id: str,
    max_budget: float,
    structured_call: StructuredCall | None = None,
) -> RunMeasurement:
    """Create one complete post-run measurement without altering the run."""

    exact_values = calculate_exact_values(result)
    bundle, attachments = build_measurement_evidence_bundle(
        result,
        expected_scenario_fingerprint=expected_scenario_fingerprint,
    )
    coded_indicators, call_evidence = code_coordination_evidence(
        bundle,
        attachments,
        model=model,
        reasoning_effort=reasoning_effort,
        trace_id=trace_id,
        max_budget=max_budget,
        structured_call=structured_call,
    )
    return RunMeasurement(
        measurement_id=f"measurement_{result.run_id.removeprefix('run_')}",
        run_id=result.run_id,
        measurement_spec_version=1,
        measurement_spec_fingerprint=COORDINATION_MEASUREMENT_SPEC_FINGERPRINT,
        scenario_fingerprint=result.scenario_fingerprint,
        exact_values=exact_values,
        coded_indicators=coded_indicators,
        coder_call=call_evidence,
        limitations=[
            *COORDINATION_MEASUREMENT_SPEC.global_limitations,
            "Coded directions are judgments over only the evidence supplied to "
            "this post-run call and never update the simulated world.",
        ],
    )


def retain_coordination_measurement(
    store: RunStore,
    measurement: RunMeasurement,
) -> dict[str, object]:
    """Attach one validated measurement to its existing completed run document."""

    document = store.get(measurement.run_id)
    if document.get("status") != "completed":
        raise ValueError("measurement may be retained only on a completed run")
    if document.get("scenario") != "coordination_decision":
        raise ValueError("measurement run is not the coordination scenario")
    payload = measurement.model_dump(mode="json")
    existing = document.get("coordination_measurement")
    if existing is not None:
        if existing != payload:
            raise ValueError("run already retains a different coordination measurement")
        return document
    return store.save({**document, "coordination_measurement": payload})


def load_retained_coordination_measurement(
    store: RunStore,
    run_id: str,
) -> RunMeasurementConsumer | None:
    """Reopen retained analysis without any provider-capable dependency."""

    payload = store.get(run_id).get("coordination_measurement")
    if payload is None:
        return None
    return RunMeasurementConsumer.model_validate(payload)


def _coded_source_event_kinds() -> set[EventKind]:
    coded_ids = set(CODED_MEASURE_IDS)
    return {
        event_kind
        for definition in COORDINATION_MEASUREMENT_SPEC.measures
        if definition.measure_id in coded_ids
        for event_kind in definition.required_source_event_kinds
    }


def _coded_indicator_event_kinds(indicator_id: CodedMeasureId) -> set[EventKind]:
    definition = next(
        item
        for item in COORDINATION_MEASUREMENT_SPEC.measures
        if item.measure_id == indicator_id
    )
    return set(definition.required_source_event_kinds)


def _event_trace_ids(result: ActiveRuntimeResult) -> dict[str, list[str]]:
    trace_ids: dict[str, list[str]] = {
        event.event_id: [] for event in result.core_result.events
    }
    for attempt in result.attempts:
        for event_id in attempt.core_event_ids:
            trace_ids[event_id].append(attempt.activation_id)
    for work in result.exact_work:
        for event_id in work.core_event_ids:
            trace_ids[event_id].append(work.work_id)
    for event_id, refs in trace_ids.items():
        if not refs:
            refs.append(f"causal_event:{event_id}")
    return trace_ids


def _render_prompt(bundle: MeasurementEvidenceBundle) -> tuple[str, str]:
    raw = (
        resources.files("cybernetic_influence.active_runtime")
        .joinpath("prompts/coordination_evidence_coder.yaml")
        .read_text(encoding="utf-8")
    )
    template = yaml.safe_load(raw)
    if not isinstance(template, Mapping):
        raise ValueError("coordination evidence-coder prompt must be a mapping")
    environment = Environment(undefined=StrictUndefined, autoescape=False)
    environment.filters["tojson"] = lambda value: json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
    )
    return (
        environment.from_string(str(template["system"])).render(),
        environment.from_string(str(template["user"])).render(
            events=[
                {
                    "evidence_number": index,
                    "event_kind": item.event_kind,
                    "summary": item.summary,
                }
                for index, item in enumerate(bundle.visible_events, start=1)
            ]
        ),
    )


def _resolve_structured_call() -> StructuredCall:
    try:
        from llm_client import call_llm_structured
    except ImportError as error:
        raise RuntimeError(
            "coordination evidence coding requires the shared llm_client"
        ) from error
    return cast(StructuredCall, call_llm_structured)


def _observed_cost(meta: object) -> float | None:
    value = getattr(meta, "cost", None)
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0:
        return float(value)
    return None


def _cost_source(meta: object) -> str:
    value = getattr(meta, "cost_source", None)
    return value if isinstance(value, str) and value else "unavailable"


def _cost_covers_all_attempts(meta: object) -> bool:
    value = getattr(meta, "cost_covers_all_attempts", None)
    if isinstance(value, bool):
        return value
    warning_records = getattr(meta, "warning_records", None)
    if not isinstance(warning_records, list):
        return getattr(meta, "cost", None) is not None
    recovered = any(
        isinstance(record, dict)
        and record.get("code") in {"LLMC_WARN_RETRY", "LLMC_WARN_FALLBACK"}
        for record in warning_records
    )
    return getattr(meta, "cost", None) is not None and not recovered


def _outcome_events(
    events: Sequence[CausalEvent],
    outcome_code: str,
) -> list[CausalEvent]:
    return [
        event
        for event in events
        if event.event_kind == "mechanism_executed"
        and event.details.get("outcome_code") == outcome_code
    ]


def _event_ids(events: Sequence[CausalEvent]) -> list[JsonValue]:
    return [event.event_id for event in events]


def _meeting_index(logical_time: int) -> int:
    return max(
        0, min(len(MEETING_TIMES) - 1, bisect_right(MEETING_TIMES, logical_time) - 1)
    )


def _unresolved_risk_series(events: Sequence[CausalEvent]) -> list[JsonValue]:
    issues: list[dict[str, JsonValue]] = []
    series: list[JsonValue] = []
    for event in events:
        if (
            event.event_kind == "mechanism_executed"
            and event.details.get("outcome_code") == "meeting_wake_recorded"
        ):
            index = len(series)
            series.append(
                cast(
                    JsonValue,
                    {
                        "meeting_index": index,
                        "modeled_day": event.logical_time // MINUTES_PER_DAY,
                        "open_count": _open_issue_count(issues),
                        "event_id": event.event_id,
                    },
                )
            )
        if event.patch is None:
            continue
        for change in event.patch.fact_changes:
            if change.fact_id == "issue_register.items":
                issues = _records(change.after, label="issue register patch")
    return series


def _records(value: JsonValue, *, label: str) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise TypeError(f"{label} must contain object records")
    return [cast(dict[str, JsonValue], item) for item in value]


def _open_issue_count(items: Sequence[Mapping[str, JsonValue]]) -> int:
    return sum(item.get("lifecycle") in {"open", "reopened"} for item in items)


def _required_string(value: JsonValue, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{label} must be a non-empty string")
    return value


def _required_int(value: JsonValue, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer")
    return value
