#!/usr/bin/env python3
"""Fail when a test waits on an iteration count instead of wall-clock time.

`CLAUDE.md` has said since 2026-09-06 that polling for a background run must
wait on wall-clock time and never on an iteration count, and it names the exact
shape: a fixed ``for _ in range(200)`` with a 10ms sleep is a two-second
deadline on real work. That rule was written in the same commit that fixed two
such tests -- and five more instances of the literal pattern survived in
`tests/test_api.py`. One of them went on to fail `main`'s own CI, which made
every unrelated pull request's red check ambiguous until someone separated it
from that one.

A prohibition nothing executes only fires when a person happens to reread the
instruction file, which is never the moment they are writing the next poll
loop. This is the mechanism that makes the rule fire at the moment it is
broken.

The check is deliberately narrow: a `for` loop over a *literal* `range(...)`
whose body calls `time.sleep`. A count-bounded loop that does not sleep is not
a deadline, and a sleep outside a counted loop is not this pattern. Use
`tests/test_api.py`'s `wait_for_run` helper, or any wall-clock deadline, and
this check stays quiet.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"


def _calls_sleep(node: ast.AST) -> bool:
    """Return whether this subtree calls ``time.sleep`` or a bare ``sleep``."""

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == "sleep":
            return True
        if isinstance(func, ast.Name) and func.id == "sleep":
            return True
    return False


def _is_literal_range(node: ast.expr) -> bool:
    """Return whether the iterable is ``range(<constant>)``."""

    if not isinstance(node, ast.Call):
        return False
    if not (isinstance(node.func, ast.Name) and node.func.id == "range"):
        return False
    return all(isinstance(arg, ast.Constant) for arg in node.args)


def find_violations(path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, source_line)`` for each counted sleep-poll in one file."""

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    found: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source, filename=str(path))):
        if not isinstance(node, ast.For):
            continue
        if not _is_literal_range(node.iter):
            continue
        if not any(_calls_sleep(stmt) for stmt in node.body):
            continue
        found.append((node.lineno, lines[node.lineno - 1].strip()))
    return found


def main() -> int:
    violations: list[tuple[Path, int, str]] = []
    for path in sorted(TESTS.rglob("test_*.py")):
        for lineno, text in find_violations(path):
            violations.append((path, lineno, text))

    if not violations:
        print(f"test-wait deadlines: no counted sleep-polls in {TESTS.name}/")
        return 0

    print("Counted sleep-polls found. These are deadlines measured in iterations,")
    print("so they pass alone and fail under a loaded suite. Wait on wall-clock")
    print("time instead -- see wait_for_run in tests/test_api.py.\n")
    for path, lineno, text in violations:
        print(f"  {path.relative_to(ROOT)}:{lineno}: {text}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
