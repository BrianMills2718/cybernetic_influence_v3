"""Closed organization-like service-desk fidelity probe over frozen v3 contracts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Literal, TypeAlias, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.types import JsonValue

from cybernetic_influence.active_runtime import (
    ActiveProposal,
    ActiveRuntimeCheckpoint,
    ActiveRuntimeConfig,
    ActiveRuntimeResult,
    ActiveRuntimeSession,
    ActiveStepResult,
    ActiveSystemBinding,
    ActiveSystemInput,
    ActiveSystemSpec,
    ActionIntent,
    NativeLlmActiveSystem,
    bound_native_llm_implementation_id,
)
from cybernetic_influence.causal_core.engine import (
    ExactMechanismBinding,
    MechanismContext,
)
from cybernetic_influence.causal_core.models import (
    AnalyticalBoundary,
    CarrierState,
    CausalScenario,
    CausalState,
    ConnectionState,
    EffectDraft,
    EntityState,
    FactState,
    FactUpdate,
    FidelityNote,
    MechanismOutcome,
    MechanismSpec,
    ObservationDraft,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    representation_digest,
)

SERVICE_DESK_BOUNDARY_ID = "service_desk_view"
SERVICE_DESK_MODEL = "openrouter/openai/gpt-5.6-terra"
SERVICE_DESK_REASONING_EFFORT = "max"
SERVICE_DESK_SCAFFOLD_REASONING_EFFORT = "medium"
SERVICE_DESK_TASK = "cybernetic_influence_v3_service_desk_step"
SERVICE_DESK_SCHEDULE: tuple[tuple[int, str], ...] = (
    (0, "triager"),
    (1, "specialist"),
    (2, "supervisor"),
    (3, "triager"),
    (4, "specialist"),
    (5, "supervisor"),
    (6, "triager"),
    (7, "specialist"),
    (8, "supervisor"),
)

CUSTOMER_REPORT_ENCODING = "application/vnd.cybernetic.customer-report+json"
POLICY_ENCODING = "application/vnd.cybernetic.escalation-policy+json"
INCENTIVE_ENCODING = "application/vnd.cybernetic.incentive-statement+json"
CREDENTIAL_ENCODING = "application/vnd.cybernetic.credential-presentation+json"
ASSIGNMENT_ENCODING = "application/vnd.cybernetic.ticket-assignment+json"
DETAIL_REQUEST_ENCODING = "application/vnd.cybernetic.detail-request+json"
REMEDIATION_ENCODING = "application/vnd.cybernetic.remediation-receipt+json"
FEEDBACK_ENCODING = "application/vnd.cybernetic.customer-feedback+json"
CLOSURE_ENCODING = "application/vnd.cybernetic.closure-receipt+json"

ServiceDeskArmId: TypeAlias = Literal[
    "baseline",
    "no_direct_path",
    "speed_priority",
]
ServiceDeskCognitionProfile: TypeAlias = Literal[
    "procedural_control",
    "position_context",
]
IncentiveMode: TypeAlias = Literal["balanced", "speed_priority"]

_FORBID = ConfigDict(extra="forbid", strict=True)
_TRIAGER_SECRET = "triager_route_key_17"
_SUPERVISOR_SECRET = "supervisor_close_key_17"
_StrictModelT = TypeVar("_StrictModelT", bound="_StrictModel")


class _StrictModel(BaseModel):
    """Reject coercion and unknown fields at every service-desk boundary."""

    model_config = _FORBID


class ServiceDeskArmConfiguration(_StrictModel):
    """One intervention arm with exactly one declared topology/state change."""

    arm_id: ServiceDeskArmId
    direct_path_enabled: bool
    incentive_mode: IncentiveMode

    @model_validator(mode="after")
    def validate_arm(self) -> "ServiceDeskArmConfiguration":
        """Forbid confounded or relabeled intervention configurations."""
        expected = {
            "baseline": (True, "balanced"),
            "no_direct_path": (False, "balanced"),
            "speed_priority": (True, "speed_priority"),
        }[self.arm_id]
        if (self.direct_path_enabled, self.incentive_mode) != expected:
            raise ValueError("service-desk arm configuration is confounded")
        return self


class CustomerReport(_StrictModel):
    """One concrete customer-authored incident report."""

    document_kind: Literal["customer_report"] = "customer_report"
    ticket_id: Literal["incident_17"] = "incident_17"
    account_id: Literal["account_417"] = "account_417"
    symptom: Literal["login_fails_after_password_reset"] = (
        "login_fails_after_password_reset"
    )
    error_code: Literal["stale_session"] = "stale_session"


class EscalationPolicyStatement(_StrictModel):
    """Visible written norm that remains distinct from compiled enforcement."""

    document_kind: Literal["escalation_policy"] = "escalation_policy"
    policy_id: Literal["confirm_before_close"] = "confirm_before_close"
    revision: Literal[1] = 1
    rule: Literal["close_only_after_remediation_and_customer_confirmation"] = (
        "close_only_after_remediation_and_customer_confirmation"
    )


class IncentiveStatement(_StrictModel):
    """Concrete role-visible copy of the configured incentive mode."""

    document_kind: Literal["incentive_statement"] = "incentive_statement"
    incentive_id: Literal["service_desk_score"] = "service_desk_score"
    mode: IncentiveMode


class CredentialPresentation(_StrictModel):
    """Protected credential token used by one exact technical gateway."""

    document_kind: Literal["credential_presentation"] = "credential_presentation"
    subject_id: Literal["triager", "supervisor"]
    candidate: str = Field(min_length=1)


class RoutingRequest(_StrictModel):
    """Strict credentialed ticket-assignment action payload."""

    ticket_id: Literal["incident_17"] = "incident_17"
    assignee_id: Literal["specialist"] = "specialist"


class AssignmentNotice(_StrictModel):
    """Credential-free assignment information delivered to the specialist."""

    document_kind: Literal["assignment_notice"] = "assignment_notice"
    ticket_id: Literal["incident_17"] = "incident_17"
    assignee_id: Literal["specialist"] = "specialist"
    status: Literal["assigned"] = "assigned"


class DetailRequest(_StrictModel):
    """Specialist request for incident evidence absent from an assignment."""

    document_kind: Literal["detail_request"] = "detail_request"
    ticket_id: Literal["incident_17"] = "incident_17"
    requested_information: Literal["customer_report"] = "customer_report"


class TicketUpdateRequest(_StrictModel):
    """Triager update selected by the newly delivered source representation."""

    ticket_id: Literal["incident_17"] = "incident_17"
    update_kind: Literal["details", "feedback"]


class RemediationRequest(_StrictModel):
    """Strict specialist request to apply the stipulated remediation."""

    ticket_id: Literal["incident_17"] = "incident_17"
    remediation: Literal["invalidate_stale_session"] = "invalidate_stale_session"


class RemediationReceipt(_StrictModel):
    """Exact evidence that the stipulated remediation committed."""

    document_kind: Literal["remediation_receipt"] = "remediation_receipt"
    ticket_id: Literal["incident_17"] = "incident_17"
    remediation: Literal["invalidate_stale_session"] = "invalidate_stale_session"
    status: Literal["applied"] = "applied"


class CustomerFeedback(_StrictModel):
    """Delayed customer confirmation produced after remediation."""

    document_kind: Literal["customer_feedback"] = "customer_feedback"
    ticket_id: Literal["incident_17"] = "incident_17"
    login_restored: Literal[True] = True


class ClosureRequest(_StrictModel):
    """Strict credentialed request to close the incident."""

    ticket_id: Literal["incident_17"] = "incident_17"


class ClosureReceipt(_StrictModel):
    """Exact closure decision returned to the supervisor."""

    document_kind: Literal["closure_receipt"] = "closure_receipt"
    ticket_id: Literal["incident_17"] = "incident_17"
    status: Literal[
        "closed_confirmed",
        "denied_missing_remediation",
        "denied_missing_confirmation",
        "denied_authentication",
        "denied_authorization",
        "denied_already_closed",
    ]


TRIAGER_PERSONA = (
    "You are the frontline triager for incident_17. At logical time 0, use "
    "triager_route_out with representation triager_routing_credential and payload "
    '{"ticket_id":"incident_17","assignee_id":"specialist"}; also use '
    "triager_direct_details_out with representation customer_report and empty "
    "payload. Do each only once. If a delivered detail_request arrives later, use "
    "triager_ticket_update_out with that representation and payload "
    '{"ticket_id":"incident_17","update_kind":"details"}. If delivered customer '
    "feedback arrives, use the same output with that feedback representation and "
    'update_kind "feedback". Never claim delivery, remediation, or closure merely '
    "because you attempted an action."
)
SPECIALIST_PERSONA = (
    "You are the technical specialist assigned incident_17. An assignment notice "
    "does not contain the incident evidence. If assignment arrives without a new "
    "customer_report observation, use specialist_detail_request_out with the "
    "assignment representation and empty payload. When a customer_report arrives "
    "through either direct or ticket input, use specialist_remediation_out with that "
    "representation and payload "
    '{"ticket_id":"incident_17","remediation":"invalidate_stale_session"}. '
    "Remediate only once and never invent access to missing report details."
)
SUPERVISOR_PERSONA = (
    "You are the shift supervisor for incident_17. Written policy says close only "
    "after remediation and recorded customer confirmation. Use supervisor_close_out "
    "with representation supervisor_closure_credential and payload "
    '{"ticket_id":"incident_17"} when confirmation arrives. If your concrete '
    "incentive mode is speed_priority, you may attempt closure when remediation "
    "arrives before confirmation; the exact mechanism, not you, decides whether it "
    "commits. Do not describe a service desk or organization as a separate actor."
)
POSITION_CONTEXT_TRIAGER_PERSONA = (
    "You are a conscientious but fallible person who values helping others, useful "
    "records, and candor about uncertainty. Your choices reflect your perceptions, "
    "memories, priorities, and available capabilities."
)
POSITION_CONTEXT_SPECIALIST_PERSONA = (
    "You are a technically curious, conscientious but fallible person who values "
    "competent work and epistemic honesty. Your choices reflect your perceptions, "
    "memories, priorities, and available capabilities."
)
POSITION_CONTEXT_SUPERVISOR_PERSONA = (
    "You are a cautious but fallible person who values safety, fairness, and "
    "finishing useful work. Your response to workplace pressure varies with the "
    "circumstances. Your choices reflect your perceptions, memories, priorities, "
    "and available capabilities."
)


@dataclass(frozen=True)
class ServiceDeskFixture:
    """One closed arm's scenario, exact bindings, and active declarations."""

    arm: ServiceDeskArmConfiguration
    scenario: CausalScenario
    exact_bindings: Mapping[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]
    cognition_profile: ServiceDeskCognitionProfile = "procedural_control"
    reasoning_effort: str = SERVICE_DESK_REASONING_EFFORT


@dataclass(frozen=True)
class _ScriptedImplementation:
    """Adapt one zero-call reference function to the active protocol."""

    implementation_id: str
    handler: Callable[[ActiveSystemInput], ActiveStepResult]

    def step(self, active_input: ActiveSystemInput) -> ActiveStepResult:
        """Return one deterministic proposal with no provider evidence."""
        return self.handler(active_input)


def service_desk_arm_configurations() -> tuple[ServiceDeskArmConfiguration, ...]:
    """Return the canonical three-arm intervention matrix."""
    return (
        ServiceDeskArmConfiguration(
            arm_id="baseline",
            direct_path_enabled=True,
            incentive_mode="balanced",
        ),
        ServiceDeskArmConfiguration(
            arm_id="no_direct_path",
            direct_path_enabled=False,
            incentive_mode="balanced",
        ),
        ServiceDeskArmConfiguration(
            arm_id="speed_priority",
            direct_path_enabled=True,
            incentive_mode="speed_priority",
        ),
    )


def service_desk_cognition_profiles() -> tuple[ServiceDeskCognitionProfile, ...]:
    """Return the closed scaffold-sensitivity factor in canonical order."""
    return ("procedural_control", "position_context")


def service_desk_personas(
    profile: ServiceDeskCognitionProfile,
) -> dict[str, str]:
    """Return one complete, closed persona set for the selected profile."""
    if profile == "procedural_control":
        return {
            "triager": TRIAGER_PERSONA,
            "specialist": SPECIALIST_PERSONA,
            "supervisor": SUPERVISOR_PERSONA,
        }
    if profile == "position_context":
        return {
            "triager": POSITION_CONTEXT_TRIAGER_PERSONA,
            "specialist": POSITION_CONTEXT_SPECIALIST_PERSONA,
            "supervisor": POSITION_CONTEXT_SUPERVISOR_PERSONA,
        }
    raise ValueError("unknown service-desk cognition profile")


def service_desk_fixture(
    arm: ServiceDeskArmConfiguration,
    *,
    boundary_label: str = "Service desk analytical view",
    cognition_profile: ServiceDeskCognitionProfile = "procedural_control",
    reasoning_effort: str = SERVICE_DESK_REASONING_EFFORT,
) -> ServiceDeskFixture:
    """Build one grounded service-desk arm without an organization executor."""
    if not reasoning_effort.strip():
        raise ValueError("service-desk reasoning effort must be nonempty")
    selected = ServiceDeskArmConfiguration.model_validate(arm.model_dump(mode="json"))
    report = CustomerReport()
    policy = EscalationPolicyStatement()
    incentive = IncentiveStatement(mode=selected.incentive_mode)
    triager_credential = CredentialPresentation(
        subject_id="triager",
        candidate=_TRIAGER_SECRET,
    )
    supervisor_credential = CredentialPresentation(
        subject_id="supervisor",
        candidate=_SUPERVISOR_SECRET,
    )
    state = CausalState(
        entities=_entities(selected),
        ports=_ports(),
        connections=_connections(selected),
        mechanisms=_mechanisms(),
        carriers=_carriers(),
        representations={
            "customer_report": _token(
                "customer_report",
                "triager_customer_report_carrier",
                CUSTOMER_REPORT_ENCODING,
                report,
                "customer",
            ),
            "triager_policy_copy": _token(
                "triager_policy_copy",
                "triager_policy_carrier",
                POLICY_ENCODING,
                policy,
                "policy_author",
            ),
            "specialist_policy_copy": _token(
                "specialist_policy_copy",
                "specialist_policy_carrier",
                POLICY_ENCODING,
                policy,
                "policy_author",
            ),
            "supervisor_policy_copy": _token(
                "supervisor_policy_copy",
                "supervisor_policy_carrier",
                POLICY_ENCODING,
                policy,
                "policy_author",
            ),
            "triager_incentive_copy": _token(
                "triager_incentive_copy",
                "triager_incentive_carrier",
                INCENTIVE_ENCODING,
                incentive,
                "incentive_ledger",
            ),
            "specialist_incentive_copy": _token(
                "specialist_incentive_copy",
                "specialist_incentive_carrier",
                INCENTIVE_ENCODING,
                incentive,
                "incentive_ledger",
            ),
            "supervisor_incentive_copy": _token(
                "supervisor_incentive_copy",
                "supervisor_incentive_carrier",
                INCENTIVE_ENCODING,
                incentive,
                "incentive_ledger",
            ),
            "triager_routing_credential": _token(
                "triager_routing_credential",
                "triager_credential_carrier",
                CREDENTIAL_ENCODING,
                triager_credential,
                "credential_authority",
                visibility="mechanism",
            ),
            "supervisor_closure_credential": _token(
                "supervisor_closure_credential",
                "supervisor_credential_carrier",
                CREDENTIAL_ENCODING,
                supervisor_credential,
                "credential_authority",
                visibility="mechanism",
            ),
        },
    )
    scenario = CausalScenario(
        scenario_id=f"service_desk_{selected.arm_id}",
        description=(
            "Nine sequential role activations resolving one concrete login incident."
        ),
        initial_state=state,
        analytical_boundaries=[
            AnalyticalBoundary(
                boundary_id=SERVICE_DESK_BOUNDARY_ID,
                label=boundary_label,
                description=(
                    "Execution-inert analyst view over three people, their records, "
                    "and concrete interaction mechanisms."
                ),
                member_refs=_boundary_members(state),
            )
        ],
        fidelity_questions=[
            "Did each role use only delivered or initially held information?",
            "Did exact mechanisms separate policy, authentication, authorization, and outcome?",
            "Did the intervention alter only its declared route or incentive state?",
            "Did the service-desk boundary remain execution inert?",
        ],
    )
    return ServiceDeskFixture(
        arm=selected,
        cognition_profile=cognition_profile,
        reasoning_effort=reasoning_effort,
        scenario=scenario,
        exact_bindings=_exact_bindings(),
        active_specs=_active_specs(
            selected,
            cognition_profile,
            reasoning_effort,
        ),
    )


def service_desk_runtime_config() -> ActiveRuntimeConfig:
    """Return the predeclared nine-call per-run budget envelope."""
    return ActiveRuntimeConfig(
        per_call_budget=0.05,
        per_run_budget=0.50,
        max_actions_per_system=2,
        max_observations_per_system=10,
        max_private_state_bytes=32_768,
    )


def service_desk_native_bindings(
    fixture: ServiceDeskFixture,
    *,
    trace_id_prefix: str,
) -> dict[str, ActiveSystemBinding]:
    """Bind the three retained direct-OpenAI policies through the shared adapter."""
    personas = service_desk_personas(fixture.cognition_profile)
    return {
        spec.active_system_id: ActiveSystemBinding(
            spec.implementation_id,
            NativeLlmActiveSystem.from_bound_configuration(
                implementation_family_id=f"native_service_{spec.active_system_id}_v1",
                persona=personas[spec.active_system_id],
                model=SERVICE_DESK_MODEL,
                task=SERVICE_DESK_TASK,
                trace_id_prefix=trace_id_prefix,
                reasoning_effort=fixture.reasoning_effort,
                max_memory_entries=32,
                max_output_tokens=1024,
                decision_wire_contract="openai-json-payload-wire.v2",
            ),
        )
        for spec in fixture.active_specs
    }


def service_desk_scripted_bindings(
    fixture: ServiceDeskFixture,
) -> dict[str, ActiveSystemBinding]:
    """Return zero-call reference policies for deterministic preflight controls."""
    policies = {
        "triager": _scripted_triager,
        "specialist": _scripted_specialist,
        "supervisor": _scripted_supervisor,
    }
    bindings: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        policy = policies[spec.active_system_id]
        implementation_id = spec.implementation_id

        def bound_policy(
            active_input: ActiveSystemInput,
            *,
            selected_policy: Callable[[ActiveSystemInput], ActiveStepResult] = policy,
            selected_implementation_id: str = implementation_id,
        ) -> ActiveStepResult:
            result = selected_policy(active_input)
            proposal = result.proposal.model_copy(
                update={"implementation_id": selected_implementation_id}
            )
            return result.model_copy(update={"proposal": proposal})

        bindings[spec.active_system_id] = ActiveSystemBinding(
            implementation_id,
            _ScriptedImplementation(implementation_id, bound_policy),
        )
    return bindings


def run_service_desk(
    fixture: ServiceDeskFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
    checkpoint_observer: Callable[[ActiveRuntimeCheckpoint], None] | None = None,
) -> ActiveRuntimeResult:
    """Execute the fixed schedule and optionally expose each forensic prefix."""
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id=run_id,
        config=service_desk_runtime_config(),
    )
    for logical_time, participant_id in SERVICE_DESK_SCHEDULE:
        try:
            session.activate([participant_id], logical_time=logical_time)
        except Exception:
            if checkpoint_observer is not None:
                checkpoint_observer(session.checkpoint())
            raise
        if checkpoint_observer is not None:
            checkpoint_observer(session.checkpoint())
    return session.complete()


def _entities(arm: ServiceDeskArmConfiguration) -> dict[str, EntityState]:
    return {
        "customer": EntityState(
            entity_id="customer",
            entity_kind="person",
            description="Person reporting one post-reset login failure.",
        ),
        "triager": EntityState(
            entity_id="triager",
            entity_kind="person",
            description="Frontline person receiving and routing the report.",
        ),
        "specialist": EntityState(
            entity_id="specialist",
            entity_kind="person",
            description="Technical person able to apply the stipulated remediation.",
        ),
        "supervisor": EntityState(
            entity_id="supervisor",
            entity_kind="person",
            description="Person with a credentialed incident-closure interface.",
        ),
        "policy_author": EntityState(
            entity_id="policy_author",
            entity_kind="person",
            description="Author of the visible escalation-policy document.",
        ),
        "incident_17": EntityState(
            entity_id="incident_17",
            entity_kind="incident_record",
            description="Concrete ticket database record for account_417.",
            attributes={
                "status": FactState(value="new"),
                "assigned_to": FactState(value=None),
                "details_recorded": FactState(value=False),
                "remediated": FactState(value=False),
                "feedback_recorded": FactState(value=False),
                "closure_attempts": FactState(value=0),
                "denied_closure_attempts": FactState(value=0),
            },
        ),
        "written_policy_document": EntityState(
            entity_id="written_policy_document",
            entity_kind="document",
            description="Persistent written confirm-before-close norm.",
        ),
        "credential_authority": EntityState(
            entity_id="credential_authority",
            entity_kind="authentication_service",
            description="Exact protected credential comparison state machine.",
            attributes={
                "triager_verifier": FactState(
                    value=_TRIAGER_SECRET,
                    visibility="mechanism",
                ),
                "supervisor_verifier": FactState(
                    value=_SUPERVISOR_SECRET,
                    visibility="mechanism",
                ),
                "failed_authentications": FactState(value=0),
            },
        ),
        "compiled_authority": EntityState(
            entity_id="compiled_authority",
            entity_kind="authorization_service",
            description="Compiled routing and closure authority, not policy prose.",
            attributes={
                "allowed_router_ids": FactState(
                    value=["triager"],
                    visibility="mechanism",
                ),
                "allowed_closer_ids": FactState(
                    value=["supervisor"],
                    visibility="mechanism",
                ),
            },
        ),
        "remediation_service": EntityState(
            entity_id="remediation_service",
            entity_kind="service",
            description="Exact stale-session invalidation mechanism substrate.",
        ),
        "incentive_ledger": EntityState(
            entity_id="incentive_ledger",
            entity_kind="ledger",
            description="Concrete configured incentive and closure-attempt record.",
            attributes={
                "mode": FactState(value=arm.incentive_mode),
                "confirmed_closures": FactState(value=0),
                "speed_attempts_before_confirmation": FactState(value=0),
            },
        ),
    }


def _ports() -> dict[str, PortState]:
    specifications = (
        ("triager_route_out", "triager", "output", "routing_request"),
        ("routing_request_in", "compiled_authority", "input", "routing_request"),
        ("assignment_notice_out", "exact_ticket_routing", "output", "assignment_notice"),
        ("specialist_assignment_in", "specialist", "input", "assignment_notice"),
        ("triager_direct_details_out", "triager", "output", "incident_details"),
        ("specialist_direct_details_in", "specialist", "input", "incident_details"),
        ("specialist_detail_request_out", "specialist", "output", "detail_request"),
        ("triager_detail_request_in", "triager", "input", "detail_request"),
        ("triager_ticket_update_out", "triager", "output", "ticket_update"),
        ("ticket_update_in", "incident_17", "input", "ticket_update"),
        ("ticket_details_out", "exact_ticket_update", "output", "incident_details"),
        ("specialist_ticket_details_in", "specialist", "input", "incident_details"),
        ("specialist_remediation_out", "specialist", "output", "remediation_request"),
        ("remediation_request_in", "remediation_service", "input", "remediation_request"),
        ("remediation_status_out", "exact_remediation", "output", "remediation_status"),
        ("supervisor_remediation_in", "supervisor", "input", "remediation_status"),
        ("customer_feedback_out", "exact_remediation", "output", "customer_feedback"),
        ("triager_customer_feedback_in", "triager", "input", "customer_feedback"),
        ("ticket_confirmation_out", "exact_ticket_update", "output", "ticket_confirmation"),
        ("supervisor_confirmation_in", "supervisor", "input", "ticket_confirmation"),
        ("supervisor_close_out", "supervisor", "output", "closure_request"),
        ("closure_request_in", "compiled_authority", "input", "closure_request"),
        ("closure_receipt_out", "exact_ticket_closure", "output", "closure_receipt"),
        ("supervisor_closure_receipt_in", "supervisor", "input", "closure_receipt"),
    )
    return {
        port_id: PortState(
            port_id=port_id,
            owner_ref=owner,
            direction=cast(Literal["input", "output"], direction),
            effect_type=effect_type,
            description=_port_description(port_id),
        )
        for port_id, owner, direction, effect_type in specifications
    }


def _connections(arm: ServiceDeskArmConfiguration) -> dict[str, ConnectionState]:
    specifications = (
        ("triager_to_routing", "triager_route_out", "routing_request_in", True),
        ("routing_to_specialist", "assignment_notice_out", "specialist_assignment_in", True),
        (
            "triager_direct_to_specialist",
            "triager_direct_details_out",
            "specialist_direct_details_in",
            arm.direct_path_enabled,
        ),
        ("specialist_request_to_triager", "specialist_detail_request_out", "triager_detail_request_in", True),
        ("triager_to_ticket", "triager_ticket_update_out", "ticket_update_in", True),
        ("ticket_details_to_specialist", "ticket_details_out", "specialist_ticket_details_in", True),
        ("specialist_to_remediation", "specialist_remediation_out", "remediation_request_in", True),
        ("remediation_to_supervisor", "remediation_status_out", "supervisor_remediation_in", True),
        ("feedback_to_triager", "customer_feedback_out", "triager_customer_feedback_in", True),
        ("confirmation_to_supervisor", "ticket_confirmation_out", "supervisor_confirmation_in", True),
        ("supervisor_to_closure", "supervisor_close_out", "closure_request_in", True),
        ("closure_receipt_to_supervisor", "closure_receipt_out", "supervisor_closure_receipt_in", True),
    )
    return {
        connection_id: ConnectionState(
            connection_id=connection_id,
            source_port_id=source,
            target_port_id=target,
            enabled=enabled,
            description=f"Concrete service-desk route {connection_id}.",
        )
        for connection_id, source, target, enabled in specifications
    }


def _mechanisms() -> dict[str, MechanismSpec]:
    delivery_specs = {
        "exact_assignment_delivery": (
            "specialist_assignment_in",
            "specialist_assignment_buffer",
            "specialist",
        ),
        "exact_direct_details_delivery": (
            "specialist_direct_details_in",
            "specialist_direct_details_buffer",
            "specialist",
        ),
        "exact_ticket_details_delivery": (
            "specialist_ticket_details_in",
            "specialist_ticket_details_buffer",
            "specialist",
        ),
        "exact_remediation_status_delivery": (
            "supervisor_remediation_in",
            "supervisor_remediation_buffer",
            "supervisor",
        ),
        "exact_feedback_delivery": (
            "triager_customer_feedback_in",
            "triager_feedback_buffer",
            "triager",
        ),
        "exact_confirmation_delivery": (
            "supervisor_confirmation_in",
            "supervisor_confirmation_buffer",
            "supervisor",
        ),
        "exact_closure_receipt_delivery": (
            "supervisor_closure_receipt_in",
            "supervisor_closure_buffer",
            "supervisor",
        ),
    }
    mechanisms = {
        mechanism_id: MechanismSpec(
            mechanism_id=mechanism_id,
            mechanism_kind="representation_delivery",
            implementation_id="exact_service_delivery_v1",
            description="Copy one typed representation to one declared role input.",
            input_port_ids=[port_id],
            write_carrier_ids=[carrier_id],
            observation_target_ids=[target_id],
            substrate_refs=[target_id, carrier_id],
            invariant_ids=["delivery_valid"],
            fidelity=_fidelity("Exact point-to-point representation delivery."),
        )
        for mechanism_id, (port_id, carrier_id, target_id) in delivery_specs.items()
    }
    mechanisms.update(
        {
            "exact_ticket_routing": MechanismSpec(
                mechanism_id="exact_ticket_routing",
                mechanism_kind="authenticated_ticket_routing",
                implementation_id="exact_ticket_routing_v1",
                description="Authenticate triager credential and apply compiled routing authority.",
                input_port_ids=["routing_request_in"],
                output_port_ids=["assignment_notice_out"],
                read_fact_ids=[
                    "credential_authority.triager_verifier",
                    "credential_authority.failed_authentications",
                    "compiled_authority.allowed_router_ids",
                    "incident_17.status",
                    "incident_17.assigned_to",
                ],
                write_fact_ids=[
                    "credential_authority.failed_authentications",
                    "incident_17.status",
                    "incident_17.assigned_to",
                ],
                write_carrier_ids=["assignment_notice_buffer"],
                substrate_refs=[
                    "credential_authority",
                    "compiled_authority",
                    "incident_17",
                    "assignment_notice_buffer",
                ],
                invariant_ids=["ticket_routing_valid"],
                fidelity=_fidelity("Exact authentication and compiled assignment for one ticket."),
            ),
            "exact_detail_request_delivery": MechanismSpec(
                mechanism_id="exact_detail_request_delivery",
                mechanism_kind="detail_request_delivery",
                implementation_id="exact_detail_request_delivery_v1",
                description="Create and deliver one typed request for missing incident details.",
                input_port_ids=["triager_detail_request_in"],
                write_carrier_ids=["triager_detail_request_buffer"],
                observation_target_ids=["triager"],
                substrate_refs=["triager", "triager_detail_request_buffer"],
                invariant_ids=["detail_request_valid"],
                fidelity=_fidelity("Exact specialist-to-triager detail request."),
            ),
            "exact_ticket_update": MechanismSpec(
                mechanism_id="exact_ticket_update",
                mechanism_kind="ticket_record_update",
                implementation_id="exact_ticket_update_v1",
                description="Record requested details or delivered customer confirmation.",
                input_port_ids=["ticket_update_in"],
                output_port_ids=["ticket_details_out", "ticket_confirmation_out"],
                read_fact_ids=[
                    "incident_17.assigned_to",
                    "incident_17.details_recorded",
                    "incident_17.remediated",
                    "incident_17.feedback_recorded",
                ],
                write_fact_ids=[
                    "incident_17.details_recorded",
                    "incident_17.feedback_recorded",
                ],
                write_carrier_ids=[
                    "ticket_details_buffer",
                    "ticket_confirmation_buffer",
                ],
                substrate_refs=[
                    "incident_17",
                    "ticket_details_buffer",
                    "ticket_confirmation_buffer",
                ],
                invariant_ids=["ticket_update_valid"],
                fidelity=_fidelity("Exact update of two declared ticket evidence fields."),
            ),
            "exact_remediation": MechanismSpec(
                mechanism_id="exact_remediation",
                mechanism_kind="incident_remediation",
                implementation_id="exact_remediation_v1",
                description="Apply one stipulated stale-session invalidation after grounded evidence.",
                input_port_ids=["remediation_request_in"],
                output_port_ids=["remediation_status_out", "customer_feedback_out"],
                read_fact_ids=[
                    "incident_17.assigned_to",
                    "incident_17.status",
                    "incident_17.remediated",
                ],
                write_fact_ids=["incident_17.status", "incident_17.remediated"],
                write_carrier_ids=[
                    "remediation_receipt_buffer",
                    "customer_feedback_buffer",
                ],
                substrate_refs=[
                    "incident_17",
                    "remediation_service",
                    "remediation_receipt_buffer",
                    "customer_feedback_buffer",
                ],
                invariant_ids=["remediation_valid"],
                fidelity=_fidelity("Exact discrete stale-session invalidation."),
            ),
            "exact_ticket_closure": MechanismSpec(
                mechanism_id="exact_ticket_closure",
                mechanism_kind="authenticated_ticket_closure",
                implementation_id="exact_ticket_closure_v1",
                description="Authenticate, authorize, enforce quality preconditions, and score closure.",
                input_port_ids=["closure_request_in"],
                output_port_ids=["closure_receipt_out"],
                read_fact_ids=[
                    "credential_authority.supervisor_verifier",
                    "credential_authority.failed_authentications",
                    "compiled_authority.allowed_closer_ids",
                    "incident_17.status",
                    "incident_17.assigned_to",
                    "incident_17.remediated",
                    "incident_17.feedback_recorded",
                    "incident_17.closure_attempts",
                    "incident_17.denied_closure_attempts",
                    "incentive_ledger.mode",
                    "incentive_ledger.confirmed_closures",
                    "incentive_ledger.speed_attempts_before_confirmation",
                ],
                write_fact_ids=[
                    "credential_authority.failed_authentications",
                    "incident_17.status",
                    "incident_17.closure_attempts",
                    "incident_17.denied_closure_attempts",
                    "incentive_ledger.confirmed_closures",
                    "incentive_ledger.speed_attempts_before_confirmation",
                ],
                write_carrier_ids=["closure_receipt_buffer"],
                substrate_refs=[
                    "credential_authority",
                    "compiled_authority",
                    "incident_17",
                    "incentive_ledger",
                    "closure_receipt_buffer",
                ],
                invariant_ids=["ticket_closure_valid"],
                fidelity=_fidelity("Exact authentication, authorization, and quality-gated closure."),
            ),
        }
    )
    return mechanisms


def _carriers() -> dict[str, CarrierState]:
    owners = {
        "triager_customer_report_carrier": "triager",
        "triager_policy_carrier": "triager",
        "specialist_policy_carrier": "specialist",
        "supervisor_policy_carrier": "supervisor",
        "triager_incentive_carrier": "triager",
        "specialist_incentive_carrier": "specialist",
        "supervisor_incentive_carrier": "supervisor",
        "triager_credential_carrier": "triager",
        "supervisor_credential_carrier": "supervisor",
        "assignment_notice_buffer": "exact_ticket_routing",
        "specialist_assignment_buffer": "exact_assignment_delivery",
        "specialist_direct_details_buffer": "exact_direct_details_delivery",
        "triager_detail_request_buffer": "exact_detail_request_delivery",
        "ticket_details_buffer": "exact_ticket_update",
        "specialist_ticket_details_buffer": "exact_ticket_details_delivery",
        "remediation_receipt_buffer": "exact_remediation",
        "supervisor_remediation_buffer": "exact_remediation_status_delivery",
        "customer_feedback_buffer": "exact_remediation",
        "triager_feedback_buffer": "exact_feedback_delivery",
        "ticket_confirmation_buffer": "exact_ticket_update",
        "supervisor_confirmation_buffer": "exact_confirmation_delivery",
        "closure_receipt_buffer": "exact_ticket_closure",
        "supervisor_closure_buffer": "exact_closure_receipt_delivery",
    }
    return {
        carrier_id: CarrierState(
            carrier_id=carrier_id,
            owner_ref=owner,
            medium="service_desk_record",
            locator=f"service_desk/{carrier_id}",
            visibility=(
                "mechanism" if "credential_carrier" in carrier_id else "public"
            ),
        )
        for carrier_id, owner in owners.items()
    }


def _active_specs(
    arm: ServiceDeskArmConfiguration,
    cognition_profile: ServiceDeskCognitionProfile,
    reasoning_effort: str,
) -> tuple[ActiveSystemSpec, ...]:
    personas = service_desk_personas(cognition_profile)

    def implementation_id(active_system_id: str) -> str:
        return bound_native_llm_implementation_id(
            implementation_family_id=f"native_service_{active_system_id}_v1",
            persona=personas[active_system_id],
            model=SERVICE_DESK_MODEL,
            task=SERVICE_DESK_TASK,
            reasoning_effort=reasoning_effort,
            max_memory_entries=32,
            max_output_tokens=1024,
            decision_wire_contract="openai-json-payload-wire.v2",
        )

    common_memory: list[JsonValue] = [
        {
            "logical_time": 0,
            "kind": "written_policy",
            "content": _render(EscalationPolicyStatement()),
        },
        {
            "logical_time": 0,
            "kind": "incentive",
            "content": _render(IncentiveStatement(mode=arm.incentive_mode)),
        },
    ]
    position_memory: dict[str, list[JsonValue]] = {
        "triager": [],
        "specialist": [],
        "supervisor": [],
    }
    if cognition_profile == "position_context":
        position_memory = {
            "triager": [
                {
                    "logical_time": 0,
                    "kind": "autobiographical_memory",
                    "content": (
                        "I accepted employment in the frontline triager position "
                        "and was assigned incident_17. I believe coworkers generally "
                        "expect a person occupying this position to coordinate "
                        "intake, help incident information reach appropriate "
                        "technical staff, and keep ticket records useful."
                    ),
                }
            ],
            "specialist": [
                {
                    "logical_time": 0,
                    "kind": "autobiographical_memory",
                    "content": (
                        "I accepted employment in the technical specialist position "
                        "and was assigned incident_17. I believe coworkers generally "
                        "expect a person occupying this position to investigate and "
                        "remedy technical problems using the evidence they can obtain."
                    ),
                }
            ],
            "supervisor": [
                {
                    "logical_time": 0,
                    "kind": "autobiographical_memory",
                    "content": (
                        "I accepted employment in the shift supervisor position and "
                        "was assigned oversight of incident_17. I believe coworkers "
                        "generally expect a person occupying this position to oversee "
                        "safe incident resolution and apply the written closure policy."
                    ),
                }
            ],
        }
    return (
        ActiveSystemSpec(
            active_system_id="triager",
            entity_id="triager",
            implementation_id=implementation_id("triager"),
            description="Bounded frontline triage policy.",
            observation_port_ids=[
                "triager_detail_request_in",
                "triager_customer_feedback_in",
            ],
            output_port_ids=[
                "triager_route_out",
                "triager_direct_details_out",
                "triager_ticket_update_out",
            ],
            output_port_representation_sources={
                "triager_ticket_update_out": [
                    "triager_detail_request_in",
                    "triager_customer_feedback_in",
                ]
            },
            output_port_initial_representation_ids={
                "triager_route_out": ["triager_routing_credential"],
                "triager_direct_details_out": ["customer_report"],
            },
            output_port_unavailable_when={
                "triager_route_out": {
                    "incident_17.assigned_to": "specialist",
                },
                "triager_direct_details_out": {
                    "incident_17.assigned_to": "specialist",
                },
            },
            initial_representation_ids=[
                "customer_report",
                "triager_policy_copy",
                "triager_incentive_copy",
                "triager_routing_credential",
            ],
            initial_private_state={
                "memory": [
                    *common_memory,
                    *position_memory["triager"],
                    {
                        "logical_time": 0,
                        "kind": "customer_report",
                        "content": _render(CustomerReport()),
                    },
                ]
            },
        ),
        ActiveSystemSpec(
            active_system_id="specialist",
            entity_id="specialist",
            implementation_id=implementation_id("specialist"),
            description="Bounded technical diagnosis/remediation policy.",
            observation_port_ids=[
                "specialist_assignment_in",
                "specialist_direct_details_in",
                "specialist_ticket_details_in",
            ],
            output_port_ids=[
                "specialist_detail_request_out",
                "specialist_remediation_out",
            ],
            output_port_representation_sources={
                "specialist_detail_request_out": ["specialist_assignment_in"],
                "specialist_remediation_out": [
                    "specialist_direct_details_in",
                    "specialist_ticket_details_in",
                ],
            },
            initial_representation_ids=[
                "specialist_policy_copy",
                "specialist_incentive_copy",
            ],
            initial_private_state={
                "memory": [*common_memory, *position_memory["specialist"]]
            },
        ),
        ActiveSystemSpec(
            active_system_id="supervisor",
            entity_id="supervisor",
            implementation_id=implementation_id("supervisor"),
            description="Bounded shift supervision and closure policy.",
            observation_port_ids=[
                "supervisor_remediation_in",
                "supervisor_confirmation_in",
                "supervisor_closure_receipt_in",
            ],
            output_port_ids=["supervisor_close_out"],
            output_port_initial_representation_ids={
                "supervisor_close_out": ["supervisor_closure_credential"],
            },
            initial_representation_ids=[
                "supervisor_policy_copy",
                "supervisor_incentive_copy",
                "supervisor_closure_credential",
            ],
            initial_private_state={
                "memory": [*common_memory, *position_memory["supervisor"]]
            },
        ),
    )


def _exact_bindings() -> dict[str, ExactMechanismBinding]:
    bindings = {
        mechanism_id: ExactMechanismBinding(
            implementation_id="exact_service_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        )
        for mechanism_id in (
            "exact_assignment_delivery",
            "exact_direct_details_delivery",
            "exact_ticket_details_delivery",
            "exact_remediation_status_delivery",
            "exact_feedback_delivery",
            "exact_confirmation_delivery",
            "exact_closure_receipt_delivery",
        )
    }
    bindings.update(
        {
            "exact_ticket_routing": ExactMechanismBinding(
                implementation_id="exact_ticket_routing_v1",
                handler=_exact_ticket_routing,
                invariant_checkers={"ticket_routing_valid": _ticket_routing_valid},
            ),
            "exact_detail_request_delivery": ExactMechanismBinding(
                implementation_id="exact_detail_request_delivery_v1",
                handler=_exact_detail_request,
                invariant_checkers={"detail_request_valid": _detail_request_valid},
            ),
            "exact_ticket_update": ExactMechanismBinding(
                implementation_id="exact_ticket_update_v1",
                handler=_exact_ticket_update,
                invariant_checkers={"ticket_update_valid": _ticket_update_valid},
            ),
            "exact_remediation": ExactMechanismBinding(
                implementation_id="exact_remediation_v1",
                handler=_exact_remediation,
                invariant_checkers={"remediation_valid": _remediation_valid},
            ),
            "exact_ticket_closure": ExactMechanismBinding(
                implementation_id="exact_ticket_closure_v1",
                handler=_exact_ticket_closure,
                invariant_checkers={"ticket_closure_valid": _ticket_closure_valid},
            ),
        }
    )
    return bindings


def _exact_ticket_routing(context: MechanismContext) -> MechanismOutcome:
    credential = _parse_representation(context, CREDENTIAL_ENCODING, CredentialPresentation)
    request = RoutingRequest.model_validate(context.effect.payload)
    authenticated = (
        credential.subject_id == "triager"
        and credential.candidate == context.read("credential_authority.triager_verifier")
    )
    authorized = "triager" in _string_list(
        context.read("compiled_authority.allowed_router_ids")
    )
    if not authenticated:
        failures = _int_value(context.read("credential_authority.failed_authentications"))
        return MechanismOutcome(
            outcome_code="routing_denied_authentication",
            updates=[FactUpdate(fact_id="credential_authority.failed_authentications", value=failures + 1)],
        )
    if not authorized:
        return MechanismOutcome(outcome_code="routing_denied_authorization")
    if context.read("incident_17.assigned_to") is not None:
        return MechanismOutcome(outcome_code="routing_denied_already_assigned")
    notice = AssignmentNotice(ticket_id=request.ticket_id, assignee_id=request.assignee_id)
    representation_id = f"assignment_notice_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="ticket_assigned",
        updates=[
            FactUpdate(fact_id="incident_17.assigned_to", value="specialist"),
            FactUpdate(fact_id="incident_17.status", value="assigned"),
        ],
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="assignment_notice_buffer",
                encoding=ASSIGNMENT_ENCODING,
                content=_render(notice),
                actual_source_ref="compiled_authority",
                parent_representation_ids=[_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="assignment_notice_out",
                effect_type="assignment_notice",
                representation_id=representation_id,
                payload={},
            )
        ],
    )


def _exact_delivery(context: MechanismContext) -> MechanismOutcome:
    source = _representation(context)
    carrier_id, target_id = _delivery_target(context.mechanism.mechanism_id)
    copied_id = f"{target_id}_{context.target_port.port_id}_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="representation_delivered",
        representations=[
            RepresentationDraft(
                representation_id=copied_id,
                carrier_id=carrier_id,
                encoding=source.encoding,
                content=source.content,
                actual_source_ref=source.actual_source_ref,
                parent_representation_ids=[source.representation_id],
            )
        ],
        observations=[
            ObservationDraft(
                target_entity_id=target_id,
                via_port_id=context.target_port.port_id,
                apparent_content=source.content,
                apparent_source_ref=_apparent_source(context.target_port.port_id),
                representation_id=copied_id,
            )
        ],
    )


def _exact_detail_request(context: MechanismContext) -> MechanismOutcome:
    _parse_representation(context, ASSIGNMENT_ENCODING, AssignmentNotice)
    if context.effect.payload:
        raise ValueError("detail request payload must be empty")
    request = DetailRequest()
    representation_id = f"detail_request_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="detail_request_delivered",
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="triager_detail_request_buffer",
                encoding=DETAIL_REQUEST_ENCODING,
                content=_render(request),
                actual_source_ref="specialist",
                parent_representation_ids=[_representation(context).representation_id],
            )
        ],
        observations=[
            ObservationDraft(
                target_entity_id="triager",
                via_port_id="triager_detail_request_in",
                apparent_content=_render(request),
                apparent_source_ref="specialist",
                representation_id=representation_id,
            )
        ],
    )


def _exact_ticket_update(context: MechanismContext) -> MechanismOutcome:
    request = TicketUpdateRequest.model_validate(context.effect.payload)
    source = _representation(context)
    if context.read("incident_17.assigned_to") != "specialist":
        raise ValueError("ticket update requires an assigned specialist")
    if request.update_kind == "details":
        _require_encoding(source, DETAIL_REQUEST_ENCODING)
        DetailRequest.model_validate_json(source.content)
        report = CustomerReport()
        representation_id = f"ticket_details_{context.route_event_id}"
        return MechanismOutcome(
            outcome_code="ticket_details_recorded",
            updates=[FactUpdate(fact_id="incident_17.details_recorded", value=True)],
            representations=[
                RepresentationDraft(
                    representation_id=representation_id,
                    carrier_id="ticket_details_buffer",
                    encoding=CUSTOMER_REPORT_ENCODING,
                    content=_render(report),
                    actual_source_ref="customer",
                    parent_representation_ids=[source.representation_id],
                )
            ],
            effects=[
                EffectDraft(
                    output_port_id="ticket_details_out",
                    effect_type="incident_details",
                    representation_id=representation_id,
                    payload={},
                )
            ],
        )
    _require_encoding(source, FEEDBACK_ENCODING)
    CustomerFeedback.model_validate_json(source.content)
    if context.read("incident_17.remediated") is not True:
        raise ValueError("feedback cannot be recorded before remediation")
    representation_id = f"ticket_confirmation_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="customer_feedback_recorded",
        updates=[FactUpdate(fact_id="incident_17.feedback_recorded", value=True)],
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="ticket_confirmation_buffer",
                encoding=FEEDBACK_ENCODING,
                content=source.content,
                actual_source_ref=source.actual_source_ref,
                parent_representation_ids=[source.representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="ticket_confirmation_out",
                effect_type="ticket_confirmation",
                representation_id=representation_id,
                payload={},
            )
        ],
    )


def _exact_remediation(context: MechanismContext) -> MechanismOutcome:
    report = _parse_representation(context, CUSTOMER_REPORT_ENCODING, CustomerReport)
    request = RemediationRequest.model_validate(context.effect.payload)
    if report.ticket_id != request.ticket_id:
        raise ValueError("remediation report and request ticket differ")
    if context.read("incident_17.assigned_to") != "specialist":
        raise ValueError("remediation requires specialist assignment")
    if context.read("incident_17.remediated") is True:
        return MechanismOutcome(outcome_code="remediation_denied_already_applied")
    receipt = RemediationReceipt()
    feedback = CustomerFeedback()
    receipt_id = f"remediation_receipt_{context.route_event_id}"
    feedback_id = f"customer_feedback_{context.route_event_id}"
    parent_id = _representation(context).representation_id
    return MechanismOutcome(
        outcome_code="remediation_applied",
        updates=[
            FactUpdate(fact_id="incident_17.remediated", value=True),
            FactUpdate(fact_id="incident_17.status", value="remediated"),
        ],
        representations=[
            RepresentationDraft(
                representation_id=receipt_id,
                carrier_id="remediation_receipt_buffer",
                encoding=REMEDIATION_ENCODING,
                content=_render(receipt),
                actual_source_ref="remediation_service",
                parent_representation_ids=[parent_id],
            ),
            RepresentationDraft(
                representation_id=feedback_id,
                carrier_id="customer_feedback_buffer",
                encoding=FEEDBACK_ENCODING,
                content=_render(feedback),
                actual_source_ref="customer",
                parent_representation_ids=[parent_id],
            ),
        ],
        effects=[
            EffectDraft(
                output_port_id="remediation_status_out",
                effect_type="remediation_status",
                representation_id=receipt_id,
                payload={},
            ),
            EffectDraft(
                output_port_id="customer_feedback_out",
                effect_type="customer_feedback",
                representation_id=feedback_id,
                payload={},
            ),
        ],
    )


def _exact_ticket_closure(context: MechanismContext) -> MechanismOutcome:
    credential = _parse_representation(context, CREDENTIAL_ENCODING, CredentialPresentation)
    ClosureRequest.model_validate(context.effect.payload)
    status = _closure_status(context, credential)
    attempts = _int_value(context.read("incident_17.closure_attempts"))
    denied = _int_value(context.read("incident_17.denied_closure_attempts"))
    speed_attempts = _int_value(
        context.read("incentive_ledger.speed_attempts_before_confirmation")
    )
    updates = [FactUpdate(fact_id="incident_17.closure_attempts", value=attempts + 1)]
    if status == "denied_authentication":
        failures = _int_value(context.read("credential_authority.failed_authentications"))
        updates.append(FactUpdate(fact_id="credential_authority.failed_authentications", value=failures + 1))
    if status.startswith("denied_"):
        updates.append(FactUpdate(fact_id="incident_17.denied_closure_attempts", value=denied + 1))
        if (
            context.read("incentive_ledger.mode") == "speed_priority"
            and context.read("incident_17.feedback_recorded") is not True
        ):
            updates.append(
                FactUpdate(
                    fact_id="incentive_ledger.speed_attempts_before_confirmation",
                    value=speed_attempts + 1,
                )
            )
    else:
        closures = _int_value(context.read("incentive_ledger.confirmed_closures"))
        updates.extend(
            [
                FactUpdate(fact_id="incident_17.status", value="closed_confirmed"),
                FactUpdate(fact_id="incentive_ledger.confirmed_closures", value=closures + 1),
            ]
        )
    receipt = ClosureReceipt(status=status)
    representation_id = f"closure_receipt_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=updates,
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
                carrier_id="closure_receipt_buffer",
                encoding=CLOSURE_ENCODING,
                content=_render(receipt),
                actual_source_ref="compiled_authority",
                parent_representation_ids=[_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="closure_receipt_out",
                effect_type="closure_receipt",
                representation_id=representation_id,
                payload={},
            )
        ],
    )


def _closure_status(
    context: MechanismContext,
    credential: CredentialPresentation,
) -> Literal[
    "closed_confirmed",
    "denied_missing_remediation",
    "denied_missing_confirmation",
    "denied_authentication",
    "denied_authorization",
    "denied_already_closed",
]:
    if (
        credential.subject_id != "supervisor"
        or credential.candidate
        != context.read("credential_authority.supervisor_verifier")
    ):
        return "denied_authentication"
    if "supervisor" not in _string_list(
        context.read("compiled_authority.allowed_closer_ids")
    ):
        return "denied_authorization"
    if context.read("incident_17.status") == "closed_confirmed":
        return "denied_already_closed"
    if context.read("incident_17.remediated") is not True:
        return "denied_missing_remediation"
    if context.read("incident_17.feedback_recorded") is not True:
        return "denied_missing_confirmation"
    return "closed_confirmed"


def _delivery_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        source = _representation(context)
        carrier_id, target_id = _delivery_target(context.mechanism.mechanism_id)
    except (KeyError, ValueError):
        return False
    return (
        outcome.outcome_code == "representation_delivered"
        and len(outcome.representations) == 1
        and len(outcome.observations) == 1
        and not outcome.updates
        and not outcome.effects
        and outcome.representations[0].carrier_id == carrier_id
        and outcome.representations[0].encoding == source.encoding
        and outcome.representations[0].content == source.content
        and outcome.representations[0].parent_representation_ids
        == [source.representation_id]
        and outcome.observations[0].target_entity_id == target_id
        and outcome.observations[0].via_port_id == context.target_port.port_id
        and outcome.observations[0].representation_id
        == outcome.representations[0].representation_id
    )


def _ticket_routing_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        credential = _parse_representation(context, CREDENTIAL_ENCODING, CredentialPresentation)
        RoutingRequest.model_validate(context.effect.payload)
    except (ValueError, TypeError):
        return False
    authenticated = credential.candidate == context.read("credential_authority.triager_verifier")
    if not authenticated:
        return outcome.outcome_code == "routing_denied_authentication" and not outcome.effects
    if "triager" not in _string_list(context.read("compiled_authority.allowed_router_ids")):
        return outcome.outcome_code == "routing_denied_authorization" and not outcome.updates
    if context.read("incident_17.assigned_to") is not None:
        return outcome.outcome_code == "routing_denied_already_assigned" and not outcome.updates
    return (
        outcome.outcome_code == "ticket_assigned"
        and {item.fact_id: item.value for item in outcome.updates}
        == {"incident_17.assigned_to": "specialist", "incident_17.status": "assigned"}
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
        and outcome.effects[0].output_port_id == "assignment_notice_out"
    )


def _detail_request_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        _parse_representation(context, ASSIGNMENT_ENCODING, AssignmentNotice)
    except (ValueError, TypeError):
        return False
    return (
        not context.effect.payload
        and outcome.outcome_code == "detail_request_delivered"
        and len(outcome.representations) == 1
        and len(outcome.observations) == 1
        and outcome.observations[0].target_entity_id == "triager"
        and not outcome.updates
        and not outcome.effects
    )


def _ticket_update_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        request = TicketUpdateRequest.model_validate(context.effect.payload)
        source = _representation(context)
    except (ValueError, TypeError):
        return False
    if request.update_kind == "details":
        return (
            source.encoding == DETAIL_REQUEST_ENCODING
            and outcome.outcome_code == "ticket_details_recorded"
            and {item.fact_id: item.value for item in outcome.updates}
            == {"incident_17.details_recorded": True}
            and len(outcome.effects) == 1
            and outcome.effects[0].output_port_id == "ticket_details_out"
        )
    return (
        source.encoding == FEEDBACK_ENCODING
        and context.read("incident_17.remediated") is True
        and outcome.outcome_code == "customer_feedback_recorded"
        and {item.fact_id: item.value for item in outcome.updates}
        == {"incident_17.feedback_recorded": True}
        and len(outcome.effects) == 1
        and outcome.effects[0].output_port_id == "ticket_confirmation_out"
    )


def _remediation_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        _parse_representation(context, CUSTOMER_REPORT_ENCODING, CustomerReport)
        RemediationRequest.model_validate(context.effect.payload)
    except (ValueError, TypeError):
        return False
    if context.read("incident_17.remediated") is True:
        return outcome.outcome_code == "remediation_denied_already_applied" and not outcome.updates
    return (
        context.read("incident_17.assigned_to") == "specialist"
        and outcome.outcome_code == "remediation_applied"
        and {item.fact_id: item.value for item in outcome.updates}
        == {"incident_17.remediated": True, "incident_17.status": "remediated"}
        and len(outcome.representations) == 2
        and {item.output_port_id for item in outcome.effects}
        == {"remediation_status_out", "customer_feedback_out"}
    )


def _ticket_closure_valid(context: MechanismContext, outcome: MechanismOutcome) -> bool:
    try:
        credential = _parse_representation(context, CREDENTIAL_ENCODING, CredentialPresentation)
        ClosureRequest.model_validate(context.effect.payload)
        expected = _closure_status(context, credential)
    except (ValueError, TypeError):
        return False
    updates = {item.fact_id: item.value for item in outcome.updates}
    return (
        outcome.outcome_code == expected
        and updates.get("incident_17.closure_attempts")
        == _int_value(context.read("incident_17.closure_attempts")) + 1
        and (expected != "closed_confirmed" or updates.get("incident_17.status") == "closed_confirmed")
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
        and outcome.effects[0].output_port_id == "closure_receipt_out"
    )


def _scripted_triager(item: ActiveSystemInput) -> ActiveStepResult:
    actions: list[ActionIntent] = []
    if item.logical_time == 0:
        actions = [
            ActionIntent(
                output_port_id="triager_route_out",
                representation_id="triager_routing_credential",
                payload=RoutingRequest().model_dump(mode="json"),
                public_summary="Triager attempted authenticated ticket assignment.",
            ),
            ActionIntent(
                output_port_id="triager_direct_details_out",
                representation_id="customer_report",
                payload={},
                public_summary="Triager sent the customer report on the direct path.",
            ),
        ]
    else:
        for observation in item.observations:
            if observation.representation_id is None:
                continue
            if _content_kind(observation.apparent_content) == "detail_request":
                actions.append(
                    ActionIntent(
                        output_port_id="triager_ticket_update_out",
                        representation_id=observation.representation_id,
                        payload=TicketUpdateRequest(update_kind="details").model_dump(mode="json"),
                        public_summary="Triager recorded requested incident details in the ticket.",
                    )
                )
            elif _content_kind(observation.apparent_content) == "customer_feedback":
                actions.append(
                    ActionIntent(
                        output_port_id="triager_ticket_update_out",
                        representation_id=observation.representation_id,
                        payload=TicketUpdateRequest(update_kind="feedback").model_dump(mode="json"),
                        public_summary="Triager recorded the delivered customer confirmation.",
                    )
                )
    return _scripted_result(item, actions, "Triager processed only newly available evidence.")


def _scripted_specialist(item: ActiveSystemInput) -> ActiveStepResult:
    actions: list[ActionIntent] = []
    details = next(
        (
            observation
            for observation in item.observations
            if _content_kind(observation.apparent_content) == "customer_report"
        ),
        None,
    )
    assignment = next(
        (
            observation
            for observation in item.observations
            if _content_kind(observation.apparent_content) == "assignment_notice"
        ),
        None,
    )
    if details is not None:
        actions = [
            ActionIntent(
                output_port_id="specialist_remediation_out",
                representation_id=details.representation_id,
                payload=RemediationRequest().model_dump(mode="json"),
                public_summary="Specialist attempted the evidence-grounded remediation.",
            )
        ]
    elif assignment is not None:
        actions = [
            ActionIntent(
                output_port_id="specialist_detail_request_out",
                representation_id=assignment.representation_id,
                payload={},
                public_summary="Specialist requested the missing customer report.",
            )
        ]
    return _scripted_result(item, actions, "Specialist used only assigned and delivered incident evidence.")


def _scripted_supervisor(item: ActiveSystemInput) -> ActiveStepResult:
    memory_text = json.dumps(item.private_state, sort_keys=True)
    kinds = {_content_kind(observation.apparent_content) for observation in item.observations}
    should_close = "customer_feedback" in kinds or (
        "remediation_receipt" in kinds and "speed_priority" in memory_text
    )
    actions = (
        [
            ActionIntent(
                output_port_id="supervisor_close_out",
                representation_id="supervisor_closure_credential",
                payload=ClosureRequest().model_dump(mode="json"),
                public_summary="Supervisor attempted authenticated ticket closure.",
            )
        ]
        if should_close
        else []
    )
    return _scripted_result(item, actions, "Supervisor separated attempted closure from mechanism outcome.")


def _scripted_result(
    item: ActiveSystemInput,
    actions: list[ActionIntent],
    note: str,
) -> ActiveStepResult:
    memory = item.private_state.get("memory")
    if not isinstance(memory, list):
        raise TypeError("scripted service-desk memory must be a list")
    next_memory: list[JsonValue] = [
        *memory,
        {"logical_time": item.logical_time, "kind": "scripted_step", "content": note},
    ]
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id=item.active_system_id,
            implementation_id=_spec_implementation_id(item.active_system_id),
            private_state={"memory": next_memory},
            actions=actions,
        )
    )


def _spec_implementation_id(active_system_id: str) -> str:
    personas = {
        "triager": TRIAGER_PERSONA,
        "specialist": SPECIALIST_PERSONA,
        "supervisor": SUPERVISOR_PERSONA,
    }
    return bound_native_llm_implementation_id(
        implementation_family_id=f"native_service_{active_system_id}_v1",
        persona=personas[active_system_id],
        model=SERVICE_DESK_MODEL,
        task=SERVICE_DESK_TASK,
        reasoning_effort=SERVICE_DESK_REASONING_EFFORT,
        max_memory_entries=32,
        max_output_tokens=1024,
        decision_wire_contract="openai-json-payload-wire.v2",
    )


def _token(
    representation_id: str,
    carrier_id: str,
    encoding: str,
    model: BaseModel,
    source_ref: str,
    *,
    visibility: Literal["public", "analyst", "mechanism"] = "public",
) -> RepresentationToken:
    content = _render(model)
    return RepresentationToken(
        representation_id=representation_id,
        carrier_id=carrier_id,
        carrier_revision=0,
        encoding=encoding,
        content=content,
        content_hash=representation_digest(content),
        actual_source_ref=source_ref,
        visibility=visibility,
    )


def _parse_representation(
    context: MechanismContext,
    encoding: str,
    model: type[_StrictModelT],
) -> _StrictModelT:
    representation = _representation(context)
    _require_encoding(representation, encoding)
    return model.model_validate_json(representation.content)


def _representation(context: MechanismContext) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("service-desk mechanism requires a representation")
    return context.representation


def _require_encoding(representation: RepresentationToken, encoding: str) -> None:
    if representation.encoding != encoding:
        raise ValueError("service-desk representation has the wrong encoding")


def _delivery_target(mechanism_id: str) -> tuple[str, str]:
    return {
        "exact_assignment_delivery": ("specialist_assignment_buffer", "specialist"),
        "exact_direct_details_delivery": ("specialist_direct_details_buffer", "specialist"),
        "exact_ticket_details_delivery": ("specialist_ticket_details_buffer", "specialist"),
        "exact_remediation_status_delivery": ("supervisor_remediation_buffer", "supervisor"),
        "exact_feedback_delivery": ("triager_feedback_buffer", "triager"),
        "exact_confirmation_delivery": ("supervisor_confirmation_buffer", "supervisor"),
        "exact_closure_receipt_delivery": ("supervisor_closure_buffer", "supervisor"),
    }[mechanism_id]


def _apparent_source(port_id: str) -> str:
    return {
        "specialist_assignment_in": "compiled_authority",
        "specialist_direct_details_in": "triager",
        "specialist_ticket_details_in": "incident_17",
        "supervisor_remediation_in": "remediation_service",
        "triager_customer_feedback_in": "customer",
        "supervisor_confirmation_in": "incident_17",
        "supervisor_closure_receipt_in": "compiled_authority",
    }[port_id]


def _boundary_members(state: CausalState) -> list[str]:
    return sorted(
        [
            "triager",
            "specialist",
            "supervisor",
            "incident_17",
            "written_policy_document",
            "incentive_ledger",
            *state.ports,
            *state.mechanisms,
            *state.carriers,
            *state.representations,
        ]
    )


def _content_kind(content: str) -> str:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(parsed, dict):
        return "unknown"
    value = parsed.get("document_kind")
    return value if isinstance(value, str) else "unknown"


def _string_list(value: JsonValue) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError("compiled authority list must contain strings")
    return cast(list[str], value)


def _int_value(value: JsonValue) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("service-desk counter must be an integer")
    return value


def _render(model: BaseModel) -> str:
    return json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _fidelity(abstraction: str) -> FidelityNote:
    return FidelityNote(
        abstraction=abstraction,
        assumptions=["The configured discrete incident and role interfaces are stipulated."],
        known_omissions=[
            "Real authentication, networking, ticket platforms, diagnosis, timing, and customer behavior."
        ],
        validation_basis=["Matched controls, exact replay, intervention twins, and trace review."],
    )


def _port_description(port_id: str) -> str:
    action_contracts = {
        "triager_route_out": (
            "Route incident_17 using the routing credential. Required payload: "
            '{"ticket_id":"incident_17","assignee_id":"specialist"}.'
        ),
        "triager_direct_details_out": (
            "Send the selected customer_report representation directly to the "
            "specialist. Required payload: {}."
        ),
        "triager_ticket_update_out": (
            "Update incident_17 from the selected delivered representation. "
            "Required payload: "
            '{"ticket_id":"incident_17","update_kind":"details"} for a '
            "detail_request, or "
            '{"ticket_id":"incident_17","update_kind":"feedback"} for '
            "customer_feedback."
        ),
        "specialist_detail_request_out": (
            "Request missing incident details using the selected assignment "
            "representation. Required payload: {}."
        ),
        "specialist_remediation_out": (
            "Request the stipulated stale-session remediation using the selected "
            "customer_report representation. Required payload: "
            '{"ticket_id":"incident_17","remediation":"invalidate_stale_session"}.'
        ),
        "supervisor_close_out": (
            "Attempt authenticated closure using only the supervisor closure "
            'credential. Required payload: {"ticket_id":"incident_17"}.'
        ),
    }
    return action_contracts.get(
        port_id,
        f"Concrete typed service-desk interface {port_id}.",
    )


__all__ = [
    "CUSTOMER_REPORT_ENCODING",
    "CustomerFeedback",
    "CustomerReport",
    "DetailRequest",
    "EscalationPolicyStatement",
    "IncentiveStatement",
    "RemediationReceipt",
    "SERVICE_DESK_BOUNDARY_ID",
    "SERVICE_DESK_MODEL",
    "SERVICE_DESK_REASONING_EFFORT",
    "SERVICE_DESK_SCAFFOLD_REASONING_EFFORT",
    "SERVICE_DESK_SCHEDULE",
    "SERVICE_DESK_TASK",
    "ServiceDeskArmConfiguration",
    "ServiceDeskCognitionProfile",
    "ServiceDeskFixture",
    "service_desk_arm_configurations",
    "service_desk_cognition_profiles",
    "service_desk_fixture",
    "service_desk_native_bindings",
    "service_desk_personas",
    "service_desk_runtime_config",
    "service_desk_scripted_bindings",
    "run_service_desk",
]
