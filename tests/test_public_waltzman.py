"""Focused contract for the read-only Waltzman stakeholder page."""

from html.parser import HTMLParser
from pathlib import Path
import plistlib


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "public" / "waltzman" / "index.html"
PLIST = ROOT / "deploy" / "com.cybernetic-influence.waltzman-public.plist"


class _PageShape(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1_count = 0
        self.table_body_rows = 0
        self._in_tbody = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "h1":
            self.h1_count += 1
        elif tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self.table_body_rows += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False


def test_public_page_is_a_bounded_five_trajectory_handoff() -> None:
    page = PAGE.read_text(encoding="utf-8")
    shape = _PageShape()
    shape.feed(page)

    assert shape.h1_count == 1
    assert shape.table_body_rows == 5
    assert "Disrupting coordination without winning belief" in page
    assert "12 autonomous LLM roles" in page
    assert "180 completed participant calls" in page
    assert "synthetic demonstration" in page
    assert "not an effect estimate" in page
    assert "Question for discussion" in page
    for run_id in (
        "run_593ca1c425f2",
        "run_0b5e20260805",
        "run_c688aa8121fe",
        "run_7eae20260805",
        "run_ca9a20260805",
    ):
        assert run_id in page

    lowered = page.lower()
    for internal_surface in (
        "localhost",
        "tail9c321e",
        "/api/",
        "run history",
        "service desk",
        "play live simulation",
    ):
        assert internal_surface not in lowered


def test_public_launch_agent_serves_only_the_static_page() -> None:
    plist_bytes = PLIST.read_bytes()
    plistlib.loads(plist_bytes)
    plist = plist_bytes.decode("utf-8")

    assert "com.cybernetic-influence.waltzman-public" in plist
    assert "http.server" in plist
    assert "8621" in plist
    assert "127.0.0.1" in plist
    assert "__PROJECT_ROOT__/public/waltzman" in plist
    assert "CYBERNETIC_INFLUENCE_LIVE" not in plist
    assert "OPENROUTER" not in plist
