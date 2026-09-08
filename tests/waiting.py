"""Wall-clock waits for background work, shared by the API test suites.

Runs, authoring jobs and experiments execute on background threads, so these
tests have to wait for one. They used to wait by counting: ``for _ in
range(200)`` with a 10ms sleep, which is a two-second deadline on real work.
Two seconds is not an assertion about the product -- it is an assertion about
how contended the machine is. Under ``make check`` (469 tests, ~20 minutes on a
shared CI runner) those budgets lose the race, and the failure surfaces as
something that reads like a product defect. The same tests pass alone in
seconds.

That happened: it left `main` red and made every unrelated pull request's check
ambiguous until someone separated it from the flake
(lrn-20260908T180032598404Z-1d82932256).

A generous wall-clock deadline costs nothing in the passing case, because the
loop still returns on the first successful poll. It differs only when the
machine is slow -- which is exactly when the counted form produced a false
failure. On a real hang it still fails, and reports what it last saw rather
than only that the wait ended.

The default is deliberately generous. A deadline here exists to turn a hang
into a legible failure, not to assert how fast the product is -- so the cost of
setting it too high is only that a genuine hang takes longer to report, while
the cost of setting it too low is a false failure on a busy machine. That is
not symmetric, and the first version of this helper got it wrong: 30 seconds
looked ample until ``test_live_worker_retains_pending_activation_before_commit``
turned out to take 25 seconds *alone*, and exceeded 30 inside the full suite.

``scripts/check_test_wait_deadlines.py`` keeps the counted form from coming
back.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

import pytest

T = TypeVar("T")

DEFAULT_TIMEOUT = 120.0
POLL_INTERVAL = 0.01


def _summarize(value: object) -> str:
    """Render just enough of the last observation to diagnose a real hang."""

    if isinstance(value, dict) and "status" in value:
        return f"status={value['status']!r}"
    text = repr(value)
    return text if len(text) <= 200 else f"{text[:200]}..."


def wait_for(
    fetch: Callable[[], T],
    predicate: Callable[[T], bool],
    *,
    description: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> T:
    """Poll ``fetch`` until ``predicate`` holds, bounded by wall clock.

    Returns the first observation satisfying ``predicate``. Fails the test with
    ``description`` and the last observation if the deadline passes first.
    """

    deadline = time.monotonic() + timeout
    while True:
        latest = fetch()
        if predicate(latest):
            return latest
        if time.monotonic() >= deadline:
            pytest.fail(f"{description} within {timeout}s; last observed {_summarize(latest)}")
        time.sleep(POLL_INTERVAL)


def wait_until(
    condition: Callable[[], bool],
    *,
    description: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Wait for a plain in-process condition, bounded by wall clock."""

    wait_for(condition, lambda value: value, description=description, timeout=timeout)
