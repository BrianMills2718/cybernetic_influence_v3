"""Public executable workbench backed by the existing typed simulator API."""

from __future__ import annotations

import os
from pathlib import Path

from cybernetic_influence.api import create_app


_DEFAULT_PUBLIC_ROOT = Path(__file__).resolve().parents[2] / "public" / "waltzman"
_PUBLIC_ROOT = Path(
    os.getenv("CYBERNETIC_INFLUENCE_PUBLIC_ROOT", str(_DEFAULT_PUBLIC_ROOT))
).resolve()

app = create_app(web_root=_PUBLIC_ROOT, allow_inline_styles=True)
