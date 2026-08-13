"""Waltzman-informed, evidence-stepped analysis of a general run.

These are within-simulation diagnostic signals, not validated measurements.
"""

from __future__ import annotations

from collections import Counter

from .compiler import CompiledGeneralSimulationV1
from .models import GeneralGroupSimulationResult


def project_waltzman_analysis(
    compiled: CompiledGeneralSimulationV1,
    result: GeneralGroupSimulationResult,
) -> dict[str, object]:
    proposal = compiled.proposal
    people = {person.entity_id for person in proposal.people}
    representations = proposal.information_extension.representations if proposal.information_extension else []
    broadcast = [item for item in representations if set(item.recipient_ids) == people]
    targeted = [item for item in representations if set(item.recipient_ids) != people]
    actor_calls = [item for item in result.model_calls if item.role == "actor"]
    stated_risks: list[tuple[str, str]] = []
    dependencies: Counter[str] = Counter()
    coordination_intents = 0
    explicit_source_mentions: list[tuple[str, str]] = []
    source_names = {item.apparent_source.lower(): item.apparent_source for item in representations}
    for receipt in actor_calls:
        intent = receipt.structured_output.get("intent", {})
        rationale = str(intent.get("stated_rationale", ""))
        if rationale:
            stated_risks.append((receipt.trace_id, rationale))
        for target in intent.get("target_refs", []):
            dependencies[str(target)] += 1
        action_text = " ".join(
            str(intent.get(key, ""))
            for key in ("action", "purpose", "expected_effect", "stated_rationale")
        ).lower()
        if any(term in action_text for term in ("coordinate", "joint", "convene", "shared")):
            coordination_intents += 1
        for lowered, source in source_names.items():
            if lowered in action_text:
                explicit_source_mentions.append((receipt.trace_id, source))
    transaction_refs = [
        f"transaction:{item.transaction.transaction_id}" for item in result.transition_evidence
    ]
    accepted = sum(item.validation.accepted for item in result.transition_evidence)
    findings = [
        {
            "finding_id": "input_topology",
            "label": "Input topology",
            "value": f"{len(broadcast)} broadcast and {len(targeted)} targeted representations were configured.",
            "method": "Compare each representation's explicit recipient set with the complete actor set.",
            "evidence_refs": [f"representation:{item.representation_id}" for item in representations],
            "uncertainty": "This measures configured exposure, not attention, belief, persuasion, or causal effect.",
            "limitation": "Channel timing and recipient configuration are analyst-authored.",
        },
        {
            "finding_id": "stated_source_reliance",
            "label": "Explicit source reliance",
            "value": (
                "; ".join(f"{source} ({trace_id})" for trace_id, source in explicit_source_mentions)
                if explicit_source_mentions
                else "No actor explicitly named a configured apparent source in its retained action rationale."
            ),
            "method": "Match configured apparent-source labels against retained actor action, purpose, expected-effect, and rationale text.",
            "evidence_refs": [item.trace_id for item in actor_calls],
            "uncertainty": "Absence of an explicit mention does not establish that a source had no influence.",
            "limitation": "This is a literal retained-text check, not a latent trust measure.",
        },
        {
            "finding_id": "stated_risk",
            "label": "Stated risk and concern evidence",
            "value": f"{len(stated_risks)} actor rationales retained scenario-specific risk or concern language.",
            "method": "Retain actor-stated rationales without assigning a hidden global risk score.",
            "evidence_refs": [trace_id for trace_id, _ in stated_risks],
            "uncertainty": "Rationales are model-produced statements and may not exhaust private interpretation.",
            "limitation": "No claim is made that this operationalizes perceived risk as a validated construct.",
        },
        {
            "finding_id": "blocking_dependencies",
            "label": "Named dependencies",
            "value": ", ".join(
                f"{target} ({count})" for target, count in dependencies.most_common(8)
            ) or "No target dependencies were named.",
            "method": "Count canonical target references in retained semantic action intents.",
            "evidence_refs": [item.trace_id for item in actor_calls],
            "uncertainty": "A frequently named target may be important, contested, convenient, or merely salient.",
            "limitation": "Reference frequency is not causal centrality.",
        },
        {
            "finding_id": "coordination_readiness",
            "label": "Coordination-readiness signal",
            "value": (
                f"{coordination_intents} of {len(actor_calls)} actor intents proposed joint or coordinating action; "
                f"{accepted} of {len(result.transition_evidence)} joint transactions committed."
            ),
            "method": "Combine a transparent coordination-term check over intents with exact validator outcomes.",
            "evidence_refs": [item.trace_id for item in actor_calls] + transaction_refs,
            "uncertainty": "This is a diagnostic signal inside one execution, not a temporal invariant or calibrated readiness measure.",
            "limitation": "A rejected transaction may reflect schema inconsistency rather than social unwillingness to coordinate.",
        },
    ]
    return {
        "framework": "Waltzman-informed diagnostic projection",
        "scope": "one retained synthetic execution",
        "method": "Derive inspectable signals from configured information routes, actor outputs, semantic intents, and validator receipts.",
        "findings": findings,
        "interpretation_boundary": (
            "These findings describe this configured AI-agent trajectory. They do not estimate "
            "human behavior, establish a causal invariant, or validate a theory of influence."
        ),
        "configuration_digest": result.proposal_digest,
        "registry_digest": result.registry_digest,
    }
