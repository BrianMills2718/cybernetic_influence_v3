"""Synthetic purchase-to-payment probe with a declared coarse processor."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Literal, TypeAlias, TypeVar, cast

from pydantic import BaseModel, ConfigDict
from pydantic.types import JsonValue

from cybernetic_influence.active_runtime import (
    ActiveProposal,
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
    PlacementState,
    PlaceState,
    PortState,
    RepresentationDraft,
    RepresentationToken,
    SpatialLinkState,
    representation_digest,
)

PURCHASE_PAYMENT_MODEL = "openrouter/openai/gpt-5.6-terra"
PURCHASE_PAYMENT_REASONING_EFFORT = "medium"
PURCHASE_PAYMENT_TASK = "cybernetic_influence_v3_purchase_payment_step"
PURCHASE_PAYMENT_SCHEDULE: tuple[tuple[int, str], ...] = (
    (0, "requester"),
    (1, "approver"),
    (2, "ap_clerk"),
    (3, "ap_clerk"),
)

PURCHASE_REQUEST_ENCODING = "application/vnd.cybernetic.purchase-request+json"
INVOICE_ENCODING = "application/vnd.cybernetic.invoice+json"
APPROVAL_POLICY_ENCODING = "application/vnd.cybernetic.approval-policy+json"
SIGNING_AUTHORITY_ENCODING = (
    "application/vnd.cybernetic.signing-authority+json"
)
REVIEW_PACKAGE_ENCODING = "application/vnd.cybernetic.purchase-review+json"
RECORDED_APPROVAL_ENCODING = (
    "application/vnd.cybernetic.recorded-approval+json"
)
PAYMENT_INSTRUCTION_ENCODING = (
    "application/vnd.cybernetic.payment-instruction+json"
)
PAYMENT_GATE_RESULT_ENCODING = (
    "application/vnd.cybernetic.payment-gate-result+json"
)
PAYMENT_RESULT_ENCODING = "application/vnd.cybernetic.payment-result+json"

PurchasePaymentArmId: TypeAlias = Literal[
    "settled",
    "approval_denied",
    "processor_declined",
]
ProcessorResponse: TypeAlias = Literal["settled", "declined"]
PaymentGateStatus: TypeAlias = Literal["authorized", "denied"]

_FORBID = ConfigDict(extra="forbid", strict=True)
_StrictModelT = TypeVar("_StrictModelT", bound="_StrictModel")


class _StrictModel(BaseModel):
    model_config = _FORBID


class PurchasePaymentArmConfiguration(_StrictModel):
    arm_id: PurchasePaymentArmId
    amount_cents: int
    processor_response: ProcessorResponse


class PurchaseRequest(_StrictModel):
    document_kind: Literal["purchase_request"] = "purchase_request"
    request_id: Literal["purchase_17"] = "purchase_17"
    requester_id: Literal["requester"] = "requester"
    vendor_id: Literal["vendor_41"] = "vendor_41"
    amount_cents: int
    purpose: Literal["replacement_sensor"] = "replacement_sensor"


class Invoice(_StrictModel):
    document_kind: Literal["invoice"] = "invoice"
    invoice_id: Literal["invoice_17"] = "invoice_17"
    request_id: str
    vendor_id: Literal["vendor_41"] = "vendor_41"
    amount_cents: int


class ApprovalPolicy(_StrictModel):
    document_kind: Literal["approval_policy"] = "approval_policy"
    policy_id: Literal["purchase_limit_policy"] = "purchase_limit_policy"
    maximum_amount_cents: Literal[500_000] = 500_000
    authorized_approver_ids: tuple[Literal["approver"], ...] = ("approver",)


class SigningAuthority(_StrictModel):
    document_kind: Literal["signing_authority"] = "signing_authority"
    approver_id: Literal["approver"] = "approver"
    active: bool = True


class ReviewPackage(_StrictModel):
    document_kind: Literal["review_package"] = "review_package"
    request_id: Literal["purchase_17"] = "purchase_17"
    invoice_id: Literal["invoice_17"] = "invoice_17"
    requester_id: Literal["requester"] = "requester"
    vendor_id: Literal["vendor_41"] = "vendor_41"
    amount_cents: int
    purpose: Literal["replacement_sensor"] = "replacement_sensor"


class ApprovalAttempt(_StrictModel):
    approved: bool
    reason: str


class RecordedApproval(_StrictModel):
    document_kind: Literal["recorded_approval"] = "recorded_approval"
    request_id: Literal["purchase_17"] = "purchase_17"
    invoice_id: Literal["invoice_17"] = "invoice_17"
    approver_id: Literal["approver"] = "approver"
    amount_cents: int
    approved: bool
    signer_authorized: bool
    reason: str


class PaymentInstruction(_StrictModel):
    document_kind: Literal["payment_instruction"] = "payment_instruction"
    request_id: Literal["purchase_17"] = "purchase_17"
    invoice_id: Literal["invoice_17"] = "invoice_17"
    vendor_id: Literal["vendor_41"] = "vendor_41"
    amount_cents: int


class PaymentGateResult(_StrictModel):
    document_kind: Literal["payment_gate_result"] = "payment_gate_result"
    request_id: Literal["purchase_17"] = "purchase_17"
    status: PaymentGateStatus
    reason_code: str


class PaymentResult(_StrictModel):
    document_kind: Literal["payment_result"] = "payment_result"
    request_id: Literal["purchase_17"] = "purchase_17"
    invoice_id: Literal["invoice_17"] = "invoice_17"
    status: ProcessorResponse


class PurchasePaymentReadout(_StrictModel):
    approval_status: str
    gate_status: str
    processor_status: str
    processor_executed: bool
    final_status: str


REQUESTER_PERSONA = (
    "You are a conscientious but fallible person who requested a replacement "
    "sensor from vendor_41. You remember initiating purchase_17 and retaining "
    "its invoice. You generally try to submit accurate records through the "
    "interfaces available to you; you do not know whether later approval, "
    "internal control, or external settlement will succeed."
)
APPROVER_PERSONA = (
    "You are a conscientious but fallible person occupying a purchase-approver "
    "position. You remember that the copied policy permits you to approve "
    "matching purchases up to $5,000. You consider the delivered package and "
    "record your own decision; the policy is context you interpret, not a mind "
    "that decides for you."
)
AP_CLERK_PERSONA = (
    "You are a conscientious but fallible accounts-payable clerk. You remember "
    "that payment should be requested only from a delivered positive recorded "
    "approval for a matching invoice. You do not assume that internal "
    "authorization guarantees external settlement."
)


@dataclass(frozen=True)
class PurchasePaymentFixture:
    arm: PurchasePaymentArmConfiguration
    scenario: CausalScenario
    exact_bindings: Mapping[str, ExactMechanismBinding]
    active_specs: tuple[ActiveSystemSpec, ...]


@dataclass(frozen=True)
class _ScriptedImplementation:
    implementation_id: str
    handler: Callable[[ActiveSystemInput], ActiveStepResult]

    def step(self, active_input: ActiveSystemInput) -> ActiveStepResult:
        return self.handler(active_input)


def purchase_payment_arm_configurations(
) -> tuple[PurchasePaymentArmConfiguration, ...]:
    return (
        PurchasePaymentArmConfiguration(
            arm_id="settled",
            amount_cents=120_000,
            processor_response="settled",
        ),
        PurchasePaymentArmConfiguration(
            arm_id="approval_denied",
            amount_cents=600_000,
            processor_response="settled",
        ),
        PurchasePaymentArmConfiguration(
            arm_id="processor_declined",
            amount_cents=120_000,
            processor_response="declined",
        ),
    )


def purchase_payment_fixture(
    arm: PurchasePaymentArmConfiguration,
    *,
    invoice_request_id: str = "purchase_17",
    invoice_amount_cents: int | None = None,
    signer_active: bool = True,
) -> PurchasePaymentFixture:
    selected = PurchasePaymentArmConfiguration.model_validate(
        arm.model_dump(mode="json")
    )
    request = PurchaseRequest(amount_cents=selected.amount_cents)
    invoice = Invoice(
        request_id=invoice_request_id,
        amount_cents=(
            selected.amount_cents
            if invoice_amount_cents is None
            else invoice_amount_cents
        ),
    )
    policy = ApprovalPolicy()
    signing_authority = SigningAuthority(active=signer_active)
    state = CausalState(
        entities=_entities(selected),
        places=_places(),
        placements=_placements(),
        spatial_links=_spatial_links(),
        ports=_ports(),
        connections=_connections(),
        mechanisms=_mechanisms(),
        carriers=_carriers(),
        representations={
            "purchase_request_copy": _token(
                "purchase_request_copy",
                "requester_request_carrier",
                PURCHASE_REQUEST_ENCODING,
                request,
                "requester",
            ),
            "invoice_copy": _token(
                "invoice_copy",
                "invoice_carrier",
                INVOICE_ENCODING,
                invoice,
                "vendor_41",
            ),
            "approval_policy_copy": _token(
                "approval_policy_copy",
                "approval_policy_carrier",
                APPROVAL_POLICY_ENCODING,
                policy,
                "policy_author",
            ),
            "signing_authority_copy": _token(
                "signing_authority_copy",
                "signing_authority_carrier",
                SIGNING_AUTHORITY_ENCODING,
                signing_authority,
                "authority_registry",
                visibility="mechanism",
            ),
        },
    )
    scenario = CausalScenario(
        scenario_id=f"purchase_payment_{selected.arm_id}",
        description=(
            "One synthetic purchase moves from a requester through human "
            "approval and exact internal control to a coarsely represented "
            "external payment processor."
        ),
        time_unit="minute",
        initial_state=state,
        analytical_boundaries=_analytical_boundaries(state),
        fidelity_questions=[
            "Did people act only on initially retained or delivered information?",
            "Did the policy copy remain evidence rather than an executor?",
            "Did exact internal control remain distinct from external settlement?",
            "Did the coarse processor avoid invented internal explanations?",
            "Did every organizational-scale view remain execution-inert?",
        ],
    )
    return PurchasePaymentFixture(
        arm=selected,
        scenario=scenario,
        exact_bindings=_exact_bindings(),
        active_specs=_active_specs(selected),
    )


def purchase_payment_runtime_config() -> ActiveRuntimeConfig:
    return ActiveRuntimeConfig(
        per_call_budget=0.05,
        per_run_budget=0.30,
        max_actions_per_system=1,
        max_observations_per_system=8,
        max_private_state_bytes=24_576,
    )


def purchase_payment_native_bindings(
    fixture: PurchasePaymentFixture,
    *,
    trace_id_prefix: str,
) -> dict[str, ActiveSystemBinding]:
    personas = {
        "requester": REQUESTER_PERSONA,
        "approver": APPROVER_PERSONA,
        "ap_clerk": AP_CLERK_PERSONA,
    }
    return {
        spec.active_system_id: ActiveSystemBinding(
            spec.implementation_id,
            NativeLlmActiveSystem.from_bound_configuration(
                implementation_family_id=(
                    f"native_purchase_{spec.active_system_id}_v1"
                ),
                persona=personas[spec.active_system_id],
                model=PURCHASE_PAYMENT_MODEL,
                task=PURCHASE_PAYMENT_TASK,
                trace_id_prefix=trace_id_prefix,
                reasoning_effort=PURCHASE_PAYMENT_REASONING_EFFORT,
                max_memory_entries=20,
                max_output_tokens=768,
                decision_wire_contract="openai-json-payload-wire.v2",
            ),
        )
        for spec in fixture.active_specs
    }


def purchase_payment_scripted_bindings(
    fixture: PurchasePaymentFixture,
    *,
    force_payment_request: bool = False,
) -> dict[str, ActiveSystemBinding]:
    handlers: dict[str, Callable[[ActiveSystemInput], ActiveStepResult]] = {
        "requester": _scripted_requester,
        "approver": _scripted_approver,
        "ap_clerk": lambda item: _scripted_ap_clerk(
            item,
            force_payment_request=force_payment_request,
        ),
    }
    bindings: dict[str, ActiveSystemBinding] = {}
    for spec in fixture.active_specs:
        handler = handlers[spec.active_system_id]

        def bound(
            active_input: ActiveSystemInput,
            *,
            selected_handler: Callable[
                [ActiveSystemInput], ActiveStepResult
            ] = handler,
            implementation_id: str = spec.implementation_id,
        ) -> ActiveStepResult:
            result = selected_handler(active_input)
            return result.model_copy(
                update={
                    "proposal": result.proposal.model_copy(
                        update={"implementation_id": implementation_id}
                    )
                }
            )

        bindings[spec.active_system_id] = ActiveSystemBinding(
            spec.implementation_id,
            _ScriptedImplementation(spec.implementation_id, bound),
        )
    return bindings


def run_purchase_payment(
    fixture: PurchasePaymentFixture,
    bindings: Mapping[str, ActiveSystemBinding],
    *,
    run_id: str,
) -> ActiveRuntimeResult:
    session = ActiveRuntimeSession(
        fixture.scenario,
        fixture.exact_bindings,
        fixture.active_specs,
        bindings,
        run_id=run_id,
        config=purchase_payment_runtime_config(),
    )
    for logical_time, participant_id in PURCHASE_PAYMENT_SCHEDULE:
        session.activate([participant_id], logical_time=logical_time)
    return session.complete()


def build_purchase_payment_readout(
    result: ActiveRuntimeResult,
) -> PurchasePaymentReadout:
    state = result.core_result.final_state
    approval_status = str(
        state.fact("approval_register.last_decision").value
    )
    gate_status = str(state.fact("payment_control.last_gate_result").value)
    processor_status = str(
        state.fact("payment_processor.last_status").value
    )
    processor_executed = any(
        event.mechanism_id == "coarse_payment_processor"
        for event in result.core_result.events
    )
    if processor_status == "settled":
        final_status = "settled"
    elif processor_status == "declined":
        final_status = "processor_declined"
    elif gate_status == "denied":
        final_status = "gate_denied"
    elif approval_status in {"denied", "signer_rejected"}:
        final_status = "approval_denied"
    else:
        final_status = "not_paid"
    return PurchasePaymentReadout(
        approval_status=approval_status,
        gate_status=gate_status,
        processor_status=processor_status,
        processor_executed=processor_executed,
        final_status=final_status,
    )


def purchase_payment_summary(
    readout: PurchasePaymentReadout,
) -> tuple[str, str]:
    if readout.final_status == "settled":
        return (
            "Payment settled",
            "The requester submitted matching purchase and invoice records. "
            "The approver recorded a positive decision, the exact internal "
            "control authorized the instruction, and the coarse external "
            "processor returned settled.",
        )
    if readout.final_status == "processor_declined":
        return (
            "External processor declined payment",
            "The human approval and exact internal control both passed. The "
            "coarsely represented processor returned declined; this model "
            "does not contain enough processor internals to explain why.",
        )
    if readout.final_status == "gate_denied":
        return (
            "Internal control denied payment",
            "A payment was attempted, but the exact internal control rejected "
            "the available approval, policy, request, invoice, or signer "
            "evidence before any processor instruction was emitted.",
        )
    return (
        "Purchase was not approved",
        "The approver recorded a denial from the delivered package and copied "
        "policy context. No payment request or external processor execution "
        "followed.",
    )


def _entities(
    arm: PurchasePaymentArmConfiguration,
) -> dict[str, EntityState]:
    return {
        "requester": EntityState(
            entity_id="requester",
            entity_kind="person",
            description="Person who initiated purchase_17.",
        ),
        "approver": EntityState(
            entity_id="approver",
            entity_kind="person",
            description="Person occupying the purchase-approver position.",
        ),
        "ap_clerk": EntityState(
            entity_id="ap_clerk",
            entity_kind="person",
            description="Person occupying the accounts-payable clerk position.",
        ),
        "vendor_41": EntityState(
            entity_id="vendor_41",
            entity_kind="external_party",
            description="External vendor named by the retained invoice.",
        ),
        "purchase_17": EntityState(
            entity_id="purchase_17",
            entity_kind="purchase_record",
            description="Persistent record for the synthetic purchase.",
            attributes={"status": FactState(value="draft")},
        ),
        "invoice_17": EntityState(
            entity_id="invoice_17",
            entity_kind="document",
            description="Concrete invoice referring to purchase_17.",
        ),
        "approval_policy_document": EntityState(
            entity_id="approval_policy_document",
            entity_kind="document",
            description="Concrete copy of the purchase approval policy.",
        ),
        "policy_author": EntityState(
            entity_id="policy_author",
            entity_kind="person",
            description="Person who authored the retained policy copy.",
        ),
        "authority_registry": EntityState(
            entity_id="authority_registry",
            entity_kind="state_machine",
            description="Protected record of active signing authority.",
        ),
        "approval_register": EntityState(
            entity_id="approval_register",
            entity_kind="state_machine",
            description="Record that retains the approver's attempted decision.",
            attributes={"last_decision": FactState(value="not_recorded")},
        ),
        "payment_control": EntityState(
            entity_id="payment_control",
            entity_kind="state_machine",
            description=(
                "Exact internal control over policy, signer, request, and "
                "invoice evidence."
            ),
            attributes={
                "last_gate_result": FactState(value="not_attempted")
            },
        ),
        "payment_processor": EntityState(
            entity_id="payment_processor",
            entity_kind="state_machine",
            description=(
                "Coarse external processor preserving only instruction/result "
                "behavior for this scenario."
            ),
            attributes={
                "response_mode": FactState(
                    value=arm.processor_response,
                    visibility="mechanism",
                ),
                "last_status": FactState(value="not_attempted"),
            },
        ),
    }


def _places() -> dict[str, PlaceState]:
    return {
        "enterprise_office": PlaceState(
            place_id="enterprise_office",
            place_kind="facility",
            description="Office containing the two internal work areas.",
        ),
        "operating_area": PlaceState(
            place_id="operating_area",
            place_kind="office_area",
            description="Area occupied by the requester and approver.",
            parent_place_id="enterprise_office",
        ),
        "finance_area": PlaceState(
            place_id="finance_area",
            place_kind="office_area",
            description="Area occupied by accounts payable and its records.",
            parent_place_id="enterprise_office",
        ),
    }


def _placements() -> dict[str, PlacementState]:
    return {
        "requester": PlacementState(
            entity_id="requester",
            place_id="operating_area",
        ),
        "approver": PlacementState(
            entity_id="approver",
            place_id="operating_area",
        ),
        "ap_clerk": PlacementState(
            entity_id="ap_clerk",
            place_id="finance_area",
        ),
        "purchase_17": PlacementState(
            entity_id="purchase_17",
            place_id="operating_area",
        ),
        "invoice_17": PlacementState(
            entity_id="invoice_17",
            place_id="operating_area",
        ),
        "approval_policy_document": PlacementState(
            entity_id="approval_policy_document",
            place_id="operating_area",
        ),
        "approval_register": PlacementState(
            entity_id="approval_register",
            place_id="operating_area",
        ),
        "payment_control": PlacementState(
            entity_id="payment_control",
            place_id="finance_area",
        ),
    }


def _spatial_links() -> dict[str, SpatialLinkState]:
    return {
        "office_corridor": SpatialLinkState(
            spatial_link_id="office_corridor",
            endpoint_a_place_id="operating_area",
            endpoint_b_place_id="finance_area",
            link_kind="corridor",
            description=(
                "Physical adjacency between work areas; it does not carry the "
                "digital purchase records or imply authority."
            ),
        )
    }


def _ports() -> dict[str, PortState]:
    specifications = (
        (
            "requester_submit_out",
            "requester",
            "output",
            "purchase_submission",
            "Submit the retained purchase request and matching invoice. "
            'Required payload: {"invoice_id":"invoice_17"}.',
        ),
        (
            "purchase_intake_in",
            "purchase_17",
            "input",
            "purchase_submission",
            "Receive one purchase submission.",
        ),
        (
            "review_package_out",
            "exact_purchase_intake",
            "output",
            "review_package",
            "Emit the exact copied review package.",
        ),
        (
            "approver_review_in",
            "approver",
            "input",
            "review_package",
            "Deliver the review package to the approver.",
        ),
        (
            "approver_decision_out",
            "approver",
            "output",
            "approval_attempt",
            "Record your approve-or-deny decision. Required payload: "
            '{"approved":true|false,"reason":"concise reason"}.',
        ),
        (
            "approval_record_in",
            "approval_register",
            "input",
            "approval_attempt",
            "Receive the approver's attempted decision.",
        ),
        (
            "recorded_approval_out",
            "exact_approval_recording",
            "output",
            "recorded_approval",
            "Emit the signed recorded decision.",
        ),
        (
            "ap_approval_in",
            "ap_clerk",
            "input",
            "recorded_approval",
            "Deliver the recorded decision to accounts payable.",
        ),
        (
            "ap_payment_out",
            "ap_clerk",
            "output",
            "payment_request",
            "Request payment using a delivered positive recorded approval. "
            "Required payload: {}.",
        ),
        (
            "payment_gate_in",
            "payment_control",
            "input",
            "payment_request",
            "Receive a payment request for exact internal checking.",
        ),
        (
            "payment_instruction_out",
            "exact_payment_gate",
            "output",
            "payment_instruction",
            "Emit one internally authorized payment instruction.",
        ),
        (
            "processor_instruction_in",
            "payment_processor",
            "input",
            "payment_instruction",
            "Receive an authorized instruction at the coarse processor boundary.",
        ),
        (
            "payment_result_out",
            "coarse_payment_processor",
            "output",
            "payment_result",
            "Emit the coarse processor result.",
        ),
        (
            "ap_payment_result_in",
            "ap_clerk",
            "input",
            "payment_result",
            "Deliver the external processor result to accounts payable.",
        ),
        (
            "payment_gate_result_out",
            "exact_payment_gate",
            "output",
            "payment_gate_result",
            "Emit a denied internal-control result.",
        ),
        (
            "ap_gate_result_in",
            "ap_clerk",
            "input",
            "payment_gate_result",
            "Deliver an internal-control denial to accounts payable.",
        ),
    )
    return {
        port_id: PortState(
            port_id=port_id,
            owner_ref=owner,
            direction=cast(Literal["input", "output"], direction),
            effect_type=effect_type,
            description=description,
        )
        for port_id, owner, direction, effect_type, description in specifications
    }


def _connections() -> dict[str, ConnectionState]:
    specifications = (
        (
            "requester_to_intake",
            "requester_submit_out",
            "purchase_intake_in",
        ),
        (
            "intake_to_approver",
            "review_package_out",
            "approver_review_in",
        ),
        (
            "approver_to_register",
            "approver_decision_out",
            "approval_record_in",
        ),
        (
            "register_to_ap",
            "recorded_approval_out",
            "ap_approval_in",
        ),
        ("ap_to_gate", "ap_payment_out", "payment_gate_in"),
        (
            "gate_to_processor",
            "payment_instruction_out",
            "processor_instruction_in",
        ),
        (
            "processor_to_ap",
            "payment_result_out",
            "ap_payment_result_in",
        ),
        (
            "gate_denial_to_ap",
            "payment_gate_result_out",
            "ap_gate_result_in",
        ),
    )
    return {
        connection_id: ConnectionState(
            connection_id=connection_id,
            source_port_id=source,
            target_port_id=target,
            description=f"Concrete purchase-to-payment route {connection_id}.",
        )
        for connection_id, source, target in specifications
    }


def _mechanisms() -> dict[str, MechanismSpec]:
    internal = _internal_fidelity()
    delivery = _delivery_fidelity()
    return {
        "exact_purchase_intake": MechanismSpec(
            mechanism_id="exact_purchase_intake",
            mechanism_kind="document_intake",
            implementation_id="exact_purchase_intake_v1",
            description=(
                "Copy matching request and invoice fields into a review package."
            ),
            input_port_ids=["purchase_intake_in"],
            output_port_ids=["review_package_out"],
            read_fact_ids=["purchase_17.status"],
            read_representation_ids=["invoice_copy"],
            write_fact_ids=["purchase_17.status"],
            write_carrier_ids=["review_package_buffer"],
            substrate_refs=[
                "purchase_17",
                "invoice_17",
                "review_package_buffer",
            ],
            invariant_ids=["purchase_intake_valid"],
            fidelity=internal,
        ),
        "exact_review_delivery": MechanismSpec(
            mechanism_id="exact_review_delivery",
            mechanism_kind="representation_delivery",
            implementation_id="exact_purchase_delivery_v1",
            description="Deliver the review package to the approver.",
            input_port_ids=["approver_review_in"],
            write_carrier_ids=["approver_review_buffer"],
            observation_target_ids=["approver"],
            substrate_refs=["approver", "approver_review_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=delivery,
        ),
        "exact_approval_recording": MechanismSpec(
            mechanism_id="exact_approval_recording",
            mechanism_kind="signed_decision_recording",
            implementation_id="exact_approval_recording_v1",
            description=(
                "Verify signer authority and retain the person's attempted "
                "approval decision."
            ),
            input_port_ids=["approval_record_in"],
            output_port_ids=["recorded_approval_out"],
            read_fact_ids=["approval_register.last_decision"],
            read_representation_ids=["signing_authority_copy"],
            write_fact_ids=["approval_register.last_decision"],
            write_carrier_ids=["recorded_approval_buffer"],
            substrate_refs=[
                "approval_register",
                "authority_registry",
                "recorded_approval_buffer",
            ],
            invariant_ids=["approval_recording_valid"],
            fidelity=internal,
        ),
        "exact_approval_delivery": MechanismSpec(
            mechanism_id="exact_approval_delivery",
            mechanism_kind="representation_delivery",
            implementation_id="exact_purchase_delivery_v1",
            description="Deliver the recorded approval to accounts payable.",
            input_port_ids=["ap_approval_in"],
            write_carrier_ids=["ap_approval_buffer"],
            observation_target_ids=["ap_clerk"],
            substrate_refs=["ap_clerk", "ap_approval_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=delivery,
        ),
        "exact_payment_gate": MechanismSpec(
            mechanism_id="exact_payment_gate",
            mechanism_kind="payment_control",
            implementation_id="exact_payment_gate_v1",
            description=(
                "Check recorded decision, policy, signer, request, and invoice "
                "before emitting an external instruction."
            ),
            input_port_ids=["payment_gate_in"],
            output_port_ids=[
                "payment_instruction_out",
                "payment_gate_result_out",
            ],
            read_fact_ids=["payment_control.last_gate_result"],
            read_representation_ids=[
                "purchase_request_copy",
                "invoice_copy",
                "approval_policy_copy",
                "signing_authority_copy",
            ],
            write_fact_ids=["payment_control.last_gate_result"],
            write_carrier_ids=[
                "payment_instruction_buffer",
                "payment_gate_result_buffer",
            ],
            substrate_refs=[
                "payment_control",
                "payment_instruction_buffer",
                "payment_gate_result_buffer",
            ],
            invariant_ids=["payment_gate_valid"],
            fidelity=internal,
        ),
        "exact_gate_result_delivery": MechanismSpec(
            mechanism_id="exact_gate_result_delivery",
            mechanism_kind="representation_delivery",
            implementation_id="exact_purchase_delivery_v1",
            description="Deliver an internal-control denial to accounts payable.",
            input_port_ids=["ap_gate_result_in"],
            write_carrier_ids=["ap_gate_result_buffer"],
            observation_target_ids=["ap_clerk"],
            substrate_refs=["ap_clerk", "ap_gate_result_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=delivery,
        ),
        "coarse_payment_processor": MechanismSpec(
            mechanism_id="coarse_payment_processor",
            mechanism_kind="coarse_external_processor",
            implementation_id="stipulated_payment_processor_v1",
            description=(
                "Return only a stipulated settlement status for one authorized "
                "instruction; internal processor causes are omitted."
            ),
            input_port_ids=["processor_instruction_in"],
            output_port_ids=["payment_result_out"],
            read_fact_ids=[
                "payment_processor.response_mode",
                "payment_processor.last_status",
            ],
            write_fact_ids=["payment_processor.last_status"],
            write_carrier_ids=["payment_result_buffer"],
            substrate_refs=[
                "payment_processor",
                "payment_result_buffer",
            ],
            invariant_ids=["processor_result_valid"],
            fidelity=_processor_fidelity(),
        ),
        "exact_payment_result_delivery": MechanismSpec(
            mechanism_id="exact_payment_result_delivery",
            mechanism_kind="representation_delivery",
            implementation_id="exact_purchase_delivery_v1",
            description="Deliver the coarse processor result to accounts payable.",
            input_port_ids=["ap_payment_result_in"],
            write_carrier_ids=["ap_payment_result_buffer"],
            observation_target_ids=["ap_clerk"],
            substrate_refs=["ap_clerk", "ap_payment_result_buffer"],
            invariant_ids=["delivery_valid"],
            fidelity=delivery,
        ),
    }


def _carriers() -> dict[str, CarrierState]:
    owners = {
        "requester_request_carrier": "requester",
        "invoice_carrier": "invoice_17",
        "approval_policy_carrier": "approval_policy_document",
        "signing_authority_carrier": "authority_registry",
        "review_package_buffer": "exact_purchase_intake",
        "approver_review_buffer": "exact_review_delivery",
        "recorded_approval_buffer": "exact_approval_recording",
        "ap_approval_buffer": "exact_approval_delivery",
        "payment_instruction_buffer": "exact_payment_gate",
        "payment_gate_result_buffer": "exact_payment_gate",
        "ap_gate_result_buffer": "exact_gate_result_delivery",
        "payment_result_buffer": "coarse_payment_processor",
        "ap_payment_result_buffer": "exact_payment_result_delivery",
    }
    return {
        carrier_id: CarrierState(
            carrier_id=carrier_id,
            owner_ref=owner,
            medium="purchase_payment_record",
            locator=f"purchase_payment/{carrier_id}",
            visibility=(
                "mechanism"
                if carrier_id == "signing_authority_carrier"
                else "public"
            ),
        )
        for carrier_id, owner in owners.items()
    }


def _active_specs(
    arm: PurchasePaymentArmConfiguration,
) -> tuple[ActiveSystemSpec, ...]:
    request = PurchaseRequest(amount_cents=arm.amount_cents)
    invoice = Invoice(
        request_id="purchase_17",
        amount_cents=arm.amount_cents,
    )
    policy = ApprovalPolicy()
    personas = {
        "requester": REQUESTER_PERSONA,
        "approver": APPROVER_PERSONA,
        "ap_clerk": AP_CLERK_PERSONA,
    }

    def implementation_id(active_system_id: str) -> str:
        return bound_native_llm_implementation_id(
            implementation_family_id=(
                f"native_purchase_{active_system_id}_v1"
            ),
            persona=personas[active_system_id],
            model=PURCHASE_PAYMENT_MODEL,
            task=PURCHASE_PAYMENT_TASK,
            reasoning_effort=PURCHASE_PAYMENT_REASONING_EFFORT,
            max_memory_entries=20,
            max_output_tokens=768,
            decision_wire_contract="openai-json-payload-wire.v2",
        )

    return (
        ActiveSystemSpec(
            active_system_id="requester",
            entity_id="requester",
            implementation_id=implementation_id("requester"),
            description="Bounded purchase-requester decision process.",
            output_port_ids=["requester_submit_out"],
            output_port_initial_representation_ids={
                "requester_submit_out": ["purchase_request_copy"],
            },
            initial_representation_ids=["purchase_request_copy"],
            initial_private_state={
                "memory": [
                    _memory("autobiographical_memory", REQUESTER_PERSONA),
                    _memory("purchase_request", _render(request)),
                    _memory("invoice", _render(invoice)),
                ]
            },
        ),
        ActiveSystemSpec(
            active_system_id="approver",
            entity_id="approver",
            implementation_id=implementation_id("approver"),
            description="Bounded human purchase-approval decision process.",
            observation_port_ids=["approver_review_in"],
            output_port_ids=["approver_decision_out"],
            output_port_representation_sources={
                "approver_decision_out": ["approver_review_in"],
            },
            initial_private_state={
                "memory": [
                    _memory("autobiographical_memory", APPROVER_PERSONA),
                    _memory("written_policy", _render(policy)),
                ]
            },
        ),
        ActiveSystemSpec(
            active_system_id="ap_clerk",
            entity_id="ap_clerk",
            implementation_id=implementation_id("ap_clerk"),
            description="Bounded accounts-payable decision process.",
            observation_port_ids=[
                "ap_approval_in",
                "ap_gate_result_in",
                "ap_payment_result_in",
            ],
            output_port_ids=["ap_payment_out"],
            output_port_representation_sources={
                "ap_payment_out": ["ap_approval_in"],
            },
            initial_private_state={
                "memory": [
                    _memory("autobiographical_memory", AP_CLERK_PERSONA),
                    _memory("invoice", _render(invoice)),
                ]
            },
        ),
    )


def _exact_bindings() -> dict[str, ExactMechanismBinding]:
    return {
        "exact_purchase_intake": ExactMechanismBinding(
            implementation_id="exact_purchase_intake_v1",
            handler=_exact_purchase_intake,
            invariant_checkers={
                "purchase_intake_valid": _purchase_intake_valid
            },
        ),
        "exact_review_delivery": ExactMechanismBinding(
            implementation_id="exact_purchase_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
        "exact_approval_recording": ExactMechanismBinding(
            implementation_id="exact_approval_recording_v1",
            handler=_exact_approval_recording,
            invariant_checkers={
                "approval_recording_valid": _approval_recording_valid
            },
        ),
        "exact_approval_delivery": ExactMechanismBinding(
            implementation_id="exact_purchase_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
        "exact_payment_gate": ExactMechanismBinding(
            implementation_id="exact_payment_gate_v1",
            handler=_exact_payment_gate,
            invariant_checkers={"payment_gate_valid": _payment_gate_valid},
        ),
        "exact_gate_result_delivery": ExactMechanismBinding(
            implementation_id="exact_purchase_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
        "coarse_payment_processor": ExactMechanismBinding(
            implementation_id="stipulated_payment_processor_v1",
            handler=_coarse_payment_processor,
            invariant_checkers={
                "processor_result_valid": _processor_result_valid
            },
        ),
        "exact_payment_result_delivery": ExactMechanismBinding(
            implementation_id="exact_purchase_delivery_v1",
            handler=_exact_delivery,
            invariant_checkers={"delivery_valid": _delivery_valid},
        ),
    }


def _exact_purchase_intake(context: MechanismContext) -> MechanismOutcome:
    request = _parse_trigger(
        context,
        PURCHASE_REQUEST_ENCODING,
        PurchaseRequest,
    )
    invoice_representation = context.read_representation("invoice_copy")
    _require_encoding(invoice_representation, INVOICE_ENCODING)
    invoice = Invoice.model_validate_json(invoice_representation.content)
    submitted_invoice_id = context.effect.payload.get("invoice_id")
    matched = (
        submitted_invoice_id == invoice.invoice_id
        and invoice.request_id == request.request_id
        and invoice.vendor_id == request.vendor_id
        and invoice.amount_cents == request.amount_cents
    )
    if not matched:
        return MechanismOutcome(
            outcome_code="submission_rejected",
            updates=[
                FactUpdate(
                    fact_id="purchase_17.status",
                    value="submission_rejected",
                )
            ],
        )
    package = ReviewPackage(amount_cents=request.amount_cents)
    representation_id = f"review_package_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="submitted",
        updates=[
            FactUpdate(fact_id="purchase_17.status", value="submitted")
        ],
        representations=[
            _draft(
                representation_id,
                "review_package_buffer",
                REVIEW_PACKAGE_ENCODING,
                package,
                "exact_purchase_intake",
                [
                    _trigger_representation(context).representation_id,
                    invoice_representation.representation_id,
                ],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="review_package_out",
                effect_type="review_package",
                representation_id=representation_id,
            )
        ],
    )


def _exact_approval_recording(
    context: MechanismContext,
) -> MechanismOutcome:
    package = _parse_trigger(
        context,
        REVIEW_PACKAGE_ENCODING,
        ReviewPackage,
    )
    attempt = ApprovalAttempt.model_validate(context.effect.payload)
    signing_representation = context.read_representation(
        "signing_authority_copy"
    )
    _require_encoding(
        signing_representation,
        SIGNING_AUTHORITY_ENCODING,
    )
    authority = SigningAuthority.model_validate_json(
        signing_representation.content
    )
    signer_authorized = authority.active and authority.approver_id == "approver"
    approved = attempt.approved and signer_authorized
    status = (
        "approved"
        if approved
        else ("signer_rejected" if not signer_authorized else "denied")
    )
    recorded = RecordedApproval(
        amount_cents=package.amount_cents,
        approved=approved,
        signer_authorized=signer_authorized,
        reason=attempt.reason,
    )
    representation_id = f"recorded_approval_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            FactUpdate(
                fact_id="approval_register.last_decision",
                value=status,
            )
        ],
        representations=[
            _draft(
                representation_id,
                "recorded_approval_buffer",
                RECORDED_APPROVAL_ENCODING,
                recorded,
                "approval_register",
                [
                    _trigger_representation(context).representation_id,
                    signing_representation.representation_id,
                ],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="recorded_approval_out",
                effect_type="recorded_approval",
                representation_id=representation_id,
            )
        ],
    )


def _exact_payment_gate(context: MechanismContext) -> MechanismOutcome:
    recorded = _parse_trigger(
        context,
        RECORDED_APPROVAL_ENCODING,
        RecordedApproval,
    )
    request = _read_representation(
        context,
        "purchase_request_copy",
        PURCHASE_REQUEST_ENCODING,
        PurchaseRequest,
    )
    invoice = _read_representation(
        context,
        "invoice_copy",
        INVOICE_ENCODING,
        Invoice,
    )
    policy = _read_representation(
        context,
        "approval_policy_copy",
        APPROVAL_POLICY_ENCODING,
        ApprovalPolicy,
    )
    authority = _read_representation(
        context,
        "signing_authority_copy",
        SIGNING_AUTHORITY_ENCODING,
        SigningAuthority,
    )
    reason_code = _payment_gate_reason(
        recorded,
        request,
        invoice,
        policy,
        authority,
    )
    authorized = reason_code == "authorized"
    status: PaymentGateStatus = "authorized" if authorized else "denied"
    if authorized:
        instruction = PaymentInstruction(amount_cents=request.amount_cents)
        representation_id = f"payment_instruction_{context.route_event_id}"
        return MechanismOutcome(
            outcome_code=status,
            updates=[
                FactUpdate(
                    fact_id="payment_control.last_gate_result",
                    value=status,
                )
            ],
            representations=[
                _draft(
                    representation_id,
                    "payment_instruction_buffer",
                    PAYMENT_INSTRUCTION_ENCODING,
                    instruction,
                    "payment_control",
                    [
                        _trigger_representation(context).representation_id,
                        "purchase_request_copy",
                        "invoice_copy",
                        "approval_policy_copy",
                        "signing_authority_copy",
                    ],
                )
            ],
            effects=[
                EffectDraft(
                    output_port_id="payment_instruction_out",
                    effect_type="payment_instruction",
                    representation_id=representation_id,
                )
            ],
        )
    denial = PaymentGateResult(status="denied", reason_code=reason_code)
    representation_id = f"payment_gate_result_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            FactUpdate(
                fact_id="payment_control.last_gate_result",
                value=status,
            )
        ],
        representations=[
            _draft(
                representation_id,
                "payment_gate_result_buffer",
                PAYMENT_GATE_RESULT_ENCODING,
                denial,
                "payment_control",
                [_trigger_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="payment_gate_result_out",
                effect_type="payment_gate_result",
                representation_id=representation_id,
            )
        ],
    )


def _coarse_payment_processor(
    context: MechanismContext,
) -> MechanismOutcome:
    instruction = _parse_trigger(
        context,
        PAYMENT_INSTRUCTION_ENCODING,
        PaymentInstruction,
    )
    raw_status = context.read("payment_processor.response_mode")
    if raw_status not in {"settled", "declined"}:
        raise ValueError("unsupported coarse processor response")
    status = cast(ProcessorResponse, raw_status)
    result = PaymentResult(status=status)
    representation_id = f"payment_result_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code=status,
        updates=[
            FactUpdate(
                fact_id="payment_processor.last_status",
                value=status,
            )
        ],
        representations=[
            _draft(
                representation_id,
                "payment_result_buffer",
                PAYMENT_RESULT_ENCODING,
                result,
                "payment_processor",
                [_trigger_representation(context).representation_id],
            )
        ],
        effects=[
            EffectDraft(
                output_port_id="payment_result_out",
                effect_type="payment_result",
                representation_id=representation_id,
            )
        ],
    )


def _exact_delivery(context: MechanismContext) -> MechanismOutcome:
    source = _trigger_representation(context)
    carrier_id, target_id = {
        "exact_review_delivery": ("approver_review_buffer", "approver"),
        "exact_approval_delivery": ("ap_approval_buffer", "ap_clerk"),
        "exact_gate_result_delivery": ("ap_gate_result_buffer", "ap_clerk"),
        "exact_payment_result_delivery": (
            "ap_payment_result_buffer",
            "ap_clerk",
        ),
    }[context.mechanism.mechanism_id]
    representation_id = f"delivered_{context.route_event_id}"
    return MechanismOutcome(
        outcome_code="representation_delivered",
        representations=[
            RepresentationDraft(
                representation_id=representation_id,
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
                apparent_source_ref=source.actual_source_ref,
                representation_id=representation_id,
            )
        ],
    )


def _purchase_intake_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        request = _parse_trigger(
            context,
            PURCHASE_REQUEST_ENCODING,
            PurchaseRequest,
        )
        invoice = _read_representation(
            context,
            "invoice_copy",
            INVOICE_ENCODING,
            Invoice,
        )
    except (TypeError, ValueError):
        return False
    matched = (
        context.effect.payload.get("invoice_id") == invoice.invoice_id
        and invoice.request_id == request.request_id
        and invoice.vendor_id == request.vendor_id
        and invoice.amount_cents == request.amount_cents
    )
    if not matched:
        return (
            outcome.outcome_code == "submission_rejected"
            and len(outcome.updates) == 1
            and not outcome.representations
            and not outcome.effects
        )
    return (
        outcome.outcome_code == "submitted"
        and len(outcome.updates) == 1
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
        and {
            _trigger_representation(context).representation_id,
            "invoice_copy",
        }
        <= set(outcome.representations[0].parent_representation_ids)
    )


def _approval_recording_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        package = _parse_trigger(
            context,
            REVIEW_PACKAGE_ENCODING,
            ReviewPackage,
        )
        attempt = ApprovalAttempt.model_validate(context.effect.payload)
        authority = _read_representation(
            context,
            "signing_authority_copy",
            SIGNING_AUTHORITY_ENCODING,
            SigningAuthority,
        )
    except (TypeError, ValueError):
        return False
    signer_authorized = authority.active and authority.approver_id == "approver"
    expected = (
        "approved"
        if attempt.approved and signer_authorized
        else ("signer_rejected" if not signer_authorized else "denied")
    )
    return (
        package.request_id == "purchase_17"
        and outcome.outcome_code == expected
        and len(outcome.updates) == 1
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
    )


def _payment_gate_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        recorded = _parse_trigger(
            context,
            RECORDED_APPROVAL_ENCODING,
            RecordedApproval,
        )
        request = _read_representation(
            context,
            "purchase_request_copy",
            PURCHASE_REQUEST_ENCODING,
            PurchaseRequest,
        )
        invoice = _read_representation(
            context,
            "invoice_copy",
            INVOICE_ENCODING,
            Invoice,
        )
        policy = _read_representation(
            context,
            "approval_policy_copy",
            APPROVAL_POLICY_ENCODING,
            ApprovalPolicy,
        )
        authority = _read_representation(
            context,
            "signing_authority_copy",
            SIGNING_AUTHORITY_ENCODING,
            SigningAuthority,
        )
    except (TypeError, ValueError):
        return False
    authorized = (
        _payment_gate_reason(
            recorded,
            request,
            invoice,
            policy,
            authority,
        )
        == "authorized"
    )
    expected = "authorized" if authorized else "denied"
    return (
        outcome.outcome_code == expected
        and len(outcome.updates) == 1
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
        and (
            outcome.effects[0].output_port_id
            == (
                "payment_instruction_out"
                if authorized
                else "payment_gate_result_out"
            )
        )
    )


def _processor_result_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        _parse_trigger(
            context,
            PAYMENT_INSTRUCTION_ENCODING,
            PaymentInstruction,
        )
    except (TypeError, ValueError):
        return False
    expected = context.read("payment_processor.response_mode")
    return (
        expected in {"settled", "declined"}
        and outcome.outcome_code == expected
        and len(outcome.updates) == 1
        and len(outcome.representations) == 1
        and len(outcome.effects) == 1
        and outcome.representations[0].parent_representation_ids
        == [_trigger_representation(context).representation_id]
    )


def _delivery_valid(
    context: MechanismContext,
    outcome: MechanismOutcome,
) -> bool:
    try:
        source = _trigger_representation(context)
    except ValueError:
        return False
    return (
        outcome.outcome_code == "representation_delivered"
        and not outcome.updates
        and not outcome.effects
        and len(outcome.representations) == 1
        and len(outcome.observations) == 1
        and outcome.representations[0].content == source.content
        and outcome.observations[0].representation_id
        == outcome.representations[0].representation_id
    )


def _scripted_requester(item: ActiveSystemInput) -> ActiveStepResult:
    actions = (
        [
            ActionIntent(
                output_port_id="requester_submit_out",
                representation_id="purchase_request_copy",
                payload={"invoice_id": "invoice_17"},
                public_summary=(
                    "Submit purchase_17 and invoice_17 for review."
                ),
            )
        ]
        if item.logical_time == 0
        else []
    )
    return _scripted_result(
        item,
        actions,
        "Requester submitted only the retained purchase records.",
    )


def _scripted_approver(item: ActiveSystemInput) -> ActiveStepResult:
    package_observation = next(
        (
            observation
            for observation in item.observations
            if _document_kind(observation.apparent_content)
            == "review_package"
        ),
        None,
    )
    actions: list[ActionIntent] = []
    if (
        package_observation is not None
        and package_observation.representation_id is not None
    ):
        package = ReviewPackage.model_validate_json(
            package_observation.apparent_content
        )
        approved = package.amount_cents <= ApprovalPolicy().maximum_amount_cents
        actions.append(
            ActionIntent(
                output_port_id="approver_decision_out",
                representation_id=package_observation.representation_id,
                payload={
                    "approved": approved,
                    "reason": (
                        "within copied approval limit"
                        if approved
                        else "exceeds copied approval limit"
                    ),
                },
                public_summary=(
                    "Approve purchase_17 within the copied limit."
                    if approved
                    else "Deny purchase_17 above the copied limit."
                ),
            )
        )
    return _scripted_result(
        item,
        actions,
        "Approver interpreted the delivered package and copied policy.",
    )


def _scripted_ap_clerk(
    item: ActiveSystemInput,
    *,
    force_payment_request: bool,
) -> ActiveStepResult:
    approval_observation = next(
        (
            observation
            for observation in item.observations
            if _document_kind(observation.apparent_content)
            == "recorded_approval"
        ),
        None,
    )
    actions: list[ActionIntent] = []
    if (
        approval_observation is not None
        and approval_observation.representation_id is not None
    ):
        approval = RecordedApproval.model_validate_json(
            approval_observation.apparent_content
        )
        if approval.approved or force_payment_request:
            actions.append(
                ActionIntent(
                    output_port_id="ap_payment_out",
                    representation_id=approval_observation.representation_id,
                    payload={},
                    public_summary=(
                        "Request payment from the delivered recorded approval."
                    ),
                )
            )
    return _scripted_result(
        item,
        actions,
        "Accounts payable used only the delivered recorded decision.",
    )


def _scripted_result(
    item: ActiveSystemInput,
    actions: list[ActionIntent],
    content: str,
) -> ActiveStepResult:
    memory = item.private_state.get("memory")
    if not isinstance(memory, list):
        raise TypeError("purchase-payment memory must be a list")
    return ActiveStepResult(
        proposal=ActiveProposal(
            active_system_id=item.active_system_id,
            implementation_id=_implementation_id(item.active_system_id),
            private_state={
                "memory": [
                    *memory,
                    {
                        "logical_time": item.logical_time,
                        "kind": "scripted_step",
                        "content": content,
                    },
                ]
            },
            actions=actions,
        )
    )


def _implementation_id(active_system_id: str) -> str:
    personas = {
        "requester": REQUESTER_PERSONA,
        "approver": APPROVER_PERSONA,
        "ap_clerk": AP_CLERK_PERSONA,
    }
    return bound_native_llm_implementation_id(
        implementation_family_id=f"native_purchase_{active_system_id}_v1",
        persona=personas[active_system_id],
        model=PURCHASE_PAYMENT_MODEL,
        task=PURCHASE_PAYMENT_TASK,
        reasoning_effort=PURCHASE_PAYMENT_REASONING_EFFORT,
        max_memory_entries=20,
        max_output_tokens=768,
        decision_wire_contract="openai-json-payload-wire.v2",
    )


def _payment_gate_reason(
    recorded: RecordedApproval,
    request: PurchaseRequest,
    invoice: Invoice,
    policy: ApprovalPolicy,
    authority: SigningAuthority,
) -> str:
    if not recorded.approved:
        return "recorded_decision_not_approved"
    if not recorded.signer_authorized:
        return "recorded_signer_not_authorized"
    if not authority.active or authority.approver_id != recorded.approver_id:
        return "current_signing_authority_invalid"
    if recorded.approver_id not in policy.authorized_approver_ids:
        return "approver_not_named_by_policy"
    if (
        recorded.request_id != request.request_id
        or recorded.invoice_id != invoice.invoice_id
        or invoice.request_id != request.request_id
    ):
        return "document_identifiers_mismatch"
    if (
        recorded.amount_cents != request.amount_cents
        or invoice.amount_cents != request.amount_cents
    ):
        return "document_amounts_mismatch"
    if request.amount_cents > policy.maximum_amount_cents:
        return "amount_exceeds_policy_limit"
    return "authorized"


def _analytical_boundaries(
    state: CausalState,
) -> list[AnalyticalBoundary]:
    operating_members = {
        "requester",
        "approver",
        "purchase_17",
        "invoice_17",
        "approval_policy_document",
        "approval_register",
        "requester_submit_out",
        "purchase_intake_in",
        "review_package_out",
        "approver_review_in",
        "approver_decision_out",
        "approval_record_in",
        "recorded_approval_out",
        "requester_request_carrier",
        "invoice_carrier",
        "approval_policy_carrier",
        "review_package_buffer",
        "approver_review_buffer",
        "recorded_approval_buffer",
        "purchase_request_copy",
        "invoice_copy",
        "approval_policy_copy",
        "exact_purchase_intake",
        "exact_review_delivery",
        "exact_approval_recording",
    }
    finance_members = {
        "ap_clerk",
        "approval_register",
        "payment_control",
        "payment_processor",
        "ap_approval_in",
        "ap_payment_out",
        "payment_gate_in",
        "payment_instruction_out",
        "processor_instruction_in",
        "payment_result_out",
        "ap_payment_result_in",
        "payment_gate_result_out",
        "ap_gate_result_in",
        "ap_approval_buffer",
        "payment_instruction_buffer",
        "payment_gate_result_buffer",
        "ap_gate_result_buffer",
        "payment_result_buffer",
        "ap_payment_result_buffer",
        "exact_approval_delivery",
        "exact_payment_gate",
        "exact_gate_result_delivery",
        "coarse_payment_processor",
        "exact_payment_result_delivery",
    }
    all_node_refs = (
        set(state.entities)
        | set(state.places)
        | set(state.ports)
        | set(state.mechanisms)
        | set(state.carriers)
        | set(state.representations)
    )
    return [
        AnalyticalBoundary(
            boundary_id="operating_unit_view",
            label="Operating unit view",
            description=(
                "Execution-inert view over originating people, documents, "
                "approval record, and local interfaces."
            ),
            member_refs=sorted(operating_members),
        ),
        AnalyticalBoundary(
            boundary_id="finance_operations_view",
            label="Finance operations view",
            description=(
                "Execution-inert view over accounts payable, internal payment "
                "control, and the coarse processor boundary."
            ),
            member_refs=sorted(finance_members),
        ),
        AnalyticalBoundary(
            boundary_id="purchase_to_payment_view",
            label="Purchase-to-payment view",
            description=(
                "Execution-inert superset over the complete retained workflow."
            ),
            member_refs=sorted(all_node_refs),
        ),
    ]


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


def _draft(
    representation_id: str,
    carrier_id: str,
    encoding: str,
    model: BaseModel,
    source_ref: str,
    parents: list[str],
) -> RepresentationDraft:
    return RepresentationDraft(
        representation_id=representation_id,
        carrier_id=carrier_id,
        encoding=encoding,
        content=_render(model),
        actual_source_ref=source_ref,
        parent_representation_ids=parents,
    )


def _parse_trigger(
    context: MechanismContext,
    encoding: str,
    model: type[_StrictModelT],
) -> _StrictModelT:
    representation = _trigger_representation(context)
    _require_encoding(representation, encoding)
    return model.model_validate_json(representation.content)


def _read_representation(
    context: MechanismContext,
    representation_id: str,
    encoding: str,
    model: type[_StrictModelT],
) -> _StrictModelT:
    representation = context.read_representation(representation_id)
    _require_encoding(representation, encoding)
    return model.model_validate_json(representation.content)


def _trigger_representation(
    context: MechanismContext,
) -> RepresentationToken:
    if context.representation is None:
        raise ValueError("purchase-payment mechanism requires a representation")
    return context.representation


def _require_encoding(
    representation: RepresentationToken,
    encoding: str,
) -> None:
    if representation.encoding != encoding:
        raise ValueError("purchase-payment representation has the wrong encoding")


def _document_kind(content: str) -> str:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return "unknown"
    if not isinstance(parsed, dict):
        return "unknown"
    kind = parsed.get("document_kind")
    return kind if isinstance(kind, str) else "unknown"


def _memory(kind: str, content: str) -> dict[str, JsonValue]:
    return {"logical_time": 0, "kind": kind, "content": content}


def _render(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )


def _internal_fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction=(
            "Discrete document copying, signer recording, and internal payment "
            "control over one synthetic purchase."
        ),
        assumptions=[
            "One request, invoice, policy copy, signing record, and payment attempt."
        ],
        known_omissions=[
            "Accounting periods, taxes, goods receipt, duplicate detection, and audit review."
        ],
        validation_basis=[
            "Matched intervention arms, exact invariants, replay, and trace review."
        ],
    )


def _delivery_fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction="Immediate typed digital delivery through declared routes.",
        assumptions=["Declared enabled routes deliver without corruption."],
        known_omissions=["Network latency, retries, outages, and mailbox behavior."],
        validation_basis=["Representation lineage and observation-delivery tests."],
    )


def _processor_fidelity() -> FidelityNote:
    return FidelityNote(
        abstraction=(
            "Stipulated instruction-to-status behavior at an external payment "
            "processor boundary."
        ),
        assumptions=[
            "One internally authorized instruction receives one settled or declined result."
        ],
        known_omissions=[
            "Accounts, balances, fraud models, counterparties, banking networks, "
            "queues, retries, and the causal reason for a decline.",
            "This representation cannot answer why the external processor returned "
            "its status.",
        ],
        validation_basis=[
            "Typed request/result compatibility, exact lineage, matched settle/"
            "decline arms, and explicit non-claim review."
        ],
    )
