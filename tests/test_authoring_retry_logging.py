"""The retry-cause log must name the field, or it is not worth having.

Half the authoring retries on the deployment are this project's validation
refusing the model's draft, and the most common one -- 27 of 88 -- reported only
"Input should be a valid string" with no field, in any log or table. The fix
reads the loc off the exception at llm_client's existing on_retry seam.

These tests force that path deterministically. Waiting for a real retry to prove
it is not a test; it is asking someone else to trigger the failure.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from pydantic import ValidationError

from cybernetic_influence.general_simulation.authoring import (
    _call_with_deadline,
    _log_retry_cause,
)
from cybernetic_influence.general_simulation.authoring_models import (
    GeneralProposalEnvelopeV1,
)


def _real_validation_error() -> ValidationError:
    """The exact shape the deployment kept failing on, from the real schema."""
    with pytest.raises(ValidationError) as caught:
        GeneralProposalEnvelopeV1.model_validate({"proposal": {"title": 123}})
    return caught.value


class _StructuredValidationRetryLike(Exception):
    """Mirrors llm_client's retry exception: message drops the loc, object keeps it."""

    def __init__(self, validation_error: ValidationError) -> None:
        self.validation_error = validation_error
        first = validation_error.errors()[0]["msg"]
        super().__init__(
            f"Pydantic validation failed on provider-accepted response: "
            f"{validation_error.error_count()} error(s). First: {first}"
        )


def test_retry_log_names_the_field_the_message_omits(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = _real_validation_error()
    exc = _StructuredValidationRetryLike(error)

    # The exception's own message is what used to reach the log, and it is why
    # this failure class was undiagnosable. It names one error out of nineteen,
    # and the string failure that dominated the deployment log is the fourth --
    # so "First: ..." did not even report the error anyone needed to see.
    assert error.error_count() > 5
    assert "First: Field required" in str(exc)
    assert "proposal.title" not in str(exc)
    assert "Input should be a valid string" not in str(exc)

    with caplog.at_level(logging.WARNING):
        _log_retry_cause(0, exc, 1.5)

    logged = caplog.text
    assert "proposal.title: Input should be a valid string" in logged
    assert "attempt 1" in logged


def test_retry_log_falls_back_to_the_exception_when_there_is_no_validation_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        _log_retry_cause(1, RuntimeError("Provider response was not valid JSON."), 0.5)
    assert "attempt 2" in caplog.text
    assert "Provider response was not valid JSON." in caplog.text
    assert "RuntimeError" in caplog.text


def test_call_with_deadline_actually_passes_on_retry_through() -> None:
    """The log helper is useless if the callback never reaches llm_client."""
    seen: dict[str, Any] = {}

    def fake_call(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
        seen.update(kwargs)
        return ("parsed", "meta")

    _call_with_deadline(fake_call, "model", [], response_model=object)
    assert seen.get("on_retry") is _log_retry_cause


def test_a_caller_supplied_on_retry_is_not_overridden() -> None:
    def mine(attempt: int, exc: Exception, delay: float) -> None:
        del attempt, exc, delay

    seen: dict[str, Any] = {}

    def fake_call(*args: Any, **kwargs: Any) -> tuple[Any, Any]:
        seen.update(kwargs)
        return ("parsed", "meta")

    _call_with_deadline(fake_call, "model", [], on_retry=mine)
    assert seen.get("on_retry") is mine
