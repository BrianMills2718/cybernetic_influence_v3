"""Public executable workbench backed by the existing typed simulator API."""

from __future__ import annotations

import os
from pathlib import Path

from cybernetic_influence.api import create_app
from cybernetic_influence.public_spend_controls import (
    SpendControlMiddleware,
    SpendControlSettings,
    SpendLedger,
)


_DEFAULT_PUBLIC_ROOT = Path(__file__).resolve().parents[2] / "public" / "waltzman"
_PUBLIC_ROOT = Path(
    os.getenv("CYBERNETIC_INFLUENCE_PUBLIC_ROOT", str(_DEFAULT_PUBLIC_ROOT))
).resolve()

simulator = create_app(web_root=_PUBLIC_ROOT, allow_inline_styles=True)

# The public demo has no sign-in (ADR-016); spend is bounded by these controls.
_default_state = (
    Path(os.getenv("CYBERNETIC_INFLUENCE_RUNS_DIR", str(_PUBLIC_ROOT.parent / "runs")))
    .resolve()
    .parent
    / "spend_controls.json"
)
spend_ledger = SpendLedger(SpendControlSettings.from_env(_default_state))


@simulator.get("/api/public-limits")
def public_limits() -> dict[str, object]:
    """Today's usage against the public spend caps (read-only, uncapped)."""
    return spend_ledger.status()


app = SpendControlMiddleware(simulator, spend_ledger)
