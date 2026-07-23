"""Recorded-trajectory reconstruction from typed causal-core commit patches."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
import json

from cybernetic_influence.causal_core.models import (
    CausalEvent,
    CausalRunResult,
    CausalScenario,
    CausalState,
    StatePatch,
    scenario_execution_fingerprint,
    state_digest,
)


class ReplayError(RuntimeError):
    """A recorded patch cannot reconstruct its claimed canonical trajectory."""


def apply_state_patch(
    state: CausalState,
    patch: StatePatch,
    *,
    known_event_ids: set[str],
) -> CausalState:
    """Apply one validated patch only when every before claim matches."""
    current = CausalState.model_validate(state.model_dump(mode="json"))
    if current.revision != patch.before_revision:
        raise ReplayError("patch before revision does not match replay state")
    if current.logical_time != patch.before_logical_time:
        raise ReplayError("patch before logical time does not match replay state")
    if state_digest(current) != patch.before_digest:
        raise ReplayError("patch before digest does not match replay state")

    for change in patch.fact_changes:
        fact = current.fact(change.fact_id)
        if fact.visibility != change.visibility:
            raise ReplayError(f"patch visibility mismatch for {change.fact_id!r}")
        if not _json_values_equal(fact.value, change.before):
            raise ReplayError(f"patch before value mismatch for {change.fact_id!r}")
        fact.value = deepcopy(change.after)

    for carrier_change in patch.carrier_changes:
        carrier = current.carriers.get(carrier_change.carrier_id)
        if carrier is None:
            raise ReplayError(
                f"patch has unknown carrier {carrier_change.carrier_id!r}"
            )
        if carrier.revision != carrier_change.before_revision:
            raise ReplayError(
                "patch before carrier revision mismatch for "
                f"{carrier_change.carrier_id!r}"
            )
        carrier.revision = carrier_change.after_revision

    for representation in patch.representations_added:
        if representation.representation_id in current.representations:
            raise ReplayError(
                f"patch duplicates representation "
                f"{representation.representation_id!r}"
            )
        unknown_parents = (
            set(representation.parent_representation_ids)
            - set(current.representations)
        )
        if unknown_parents:
            raise ReplayError(
                f"representation {representation.representation_id!r} has unknown "
                f"parents {sorted(unknown_parents)!r}"
            )
        carrier = current.carriers[representation.carrier_id]
        if representation.carrier_revision != carrier.revision:
            raise ReplayError("representation has the wrong replayed carrier revision")
        current.representations[representation.representation_id] = (
            representation.model_copy(deep=True)
        )

    for observation in patch.observations_added:
        if observation.observation_id in current.observations:
            raise ReplayError(
                f"patch duplicates observation {observation.observation_id!r}"
            )
        unknown_parents = set(observation.causal_parent_event_ids) - known_event_ids
        if unknown_parents:
            raise ReplayError(
                f"observation {observation.observation_id!r} has unknown parents "
                f"{sorted(unknown_parents)!r}"
            )
        current.observations[observation.observation_id] = observation.model_copy(
            deep=True
        )
        current.inboxes.setdefault(observation.target_entity_id, []).append(
            observation.observation_id
        )

    current.revision = patch.after_revision
    current.logical_time = patch.after_logical_time
    reconstructed = CausalState.model_validate(current.model_dump(mode="json"))
    if state_digest(reconstructed) != patch.after_digest:
        raise ReplayError("patch after digest does not match reconstructed state")
    return reconstructed


def replay_committed_trajectory(
    scenario: CausalScenario,
    result: CausalRunResult,
) -> CausalState:
    """Reconstruct one completed realization without invoking mechanisms."""
    validated_scenario = CausalScenario.model_validate(
        scenario.model_dump(mode="json")
    )
    validated_result = CausalRunResult.model_validate(
        result.model_dump(mode="json")
    )
    if validated_result.scenario_id != validated_scenario.scenario_id:
        raise ReplayError("result scenario id does not match")
    if (
        validated_result.scenario_execution_fingerprint
        != scenario_execution_fingerprint(
        validated_scenario
        )
    ):
        raise ReplayError("result scenario execution fingerprint does not match")

    state = CausalState.model_validate(
        validated_scenario.initial_state.model_dump(mode="json")
    )
    if state_digest(state) != validated_result.initial_state_digest:
        raise ReplayError("result initial-state digest does not match")

    state = replay_event_prefix(state, validated_result.events)

    if state_digest(state) != validated_result.final_state_digest:
        raise ReplayError("replayed final-state digest does not match result")
    if state != validated_result.final_state:
        raise ReplayError("replayed final state does not equal recorded final state")
    return state


def _json_values_equal(left: object, right: object) -> bool:
    """Compare canonical JSON values without Boolean/integer equivalence."""
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right,
        sort_keys=True,
        separators=(",", ":"),
    )


def replay_event_prefix(
    initial_state: CausalState,
    events: Sequence[CausalEvent],
) -> CausalState:
    """Reconstruct a terminal or nonterminal canonical event prefix."""
    state = CausalState.model_validate(initial_state.model_dump(mode="json"))
    validated_events = [
        CausalEvent.model_validate(event.model_dump(mode="json"))
        for event in events
    ]
    known_event_ids: set[str] = set()
    for event in validated_events:
        if event.event_kind == "state_committed":
            if event.patch is None:
                raise ReplayError("commit event is missing its patch")
            state = apply_state_patch(
                state,
                event.patch,
                known_event_ids=known_event_ids,
            )
        if event.state_revision != state.revision:
            raise ReplayError(
                f"event {event.event_id!r} disagrees with replay state revision"
            )
        known_event_ids.add(event.event_id)
    return state
