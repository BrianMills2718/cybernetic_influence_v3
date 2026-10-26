"""The pre-push hook gates on the ref being written, not the local refspec side.

`git push origin HEAD:<branch>` and `git push origin <sha>:<branch>` publish a
governed branch while the local side of the refspec is not `refs/heads/*`.
Keying the hook's filter off the local ref alone let those forms skip claim
validation entirely, while keying it off the remote ref alone would drop
`<branch>:refs/tags/<tag>`, which the hook did validate.

These tests drive `hooks/pre-push` in a throwaway repository whose
`check_push_safety.py` is a stub, so they assert which branch the hook decided
to validate without needing a coordination claim.

The fixture repository is built once per module and copied per test: a
`git init` plus commit per test case was measurable subprocess load for no
gain, and it made the same cases flaky when the suite ran in parallel.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT = REPO_ROOT / "hooks" / "pre-push"

ZERO_SHA = "0" * 40

STUB_PUSH_CHECK = """\
import json
import sys
from pathlib import Path

record = Path(__file__).resolve().parents[1] / "push-check-calls.jsonl"
with record.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\\n")
sys.exit(int(Path(__file__).with_name("stub-exit-code").read_text().strip()))
"""


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True)


@pytest.fixture(scope="module")
def _push_repo_template(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str]:
    """Build the fixture repo once, and remember its HEAD sha."""
    repo = tmp_path_factory.mktemp("pre-push-template") / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "hooks").mkdir()

    _git(repo.parent, "init", "--quiet", "repo")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.invalid")

    (repo / "scripts" / "check_push_safety.py").write_text(
        STUB_PUSH_CHECK, encoding="utf-8"
    )
    (repo / "scripts" / "stub-exit-code").write_text("0\n", encoding="utf-8")
    (repo / "hooks" / "pre-push").write_text(
        HOOK_SCRIPT.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "--no-verify", "-m", "fixture")
    _git(repo, "checkout", "--quiet", "-b", "feature-x")

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo, head


@pytest.fixture
def push_repo(_push_repo_template: tuple[Path, str], tmp_path: Path) -> Path:
    """A private copy of the fixture repo, checked out on `feature-x`."""
    template, _ = _push_repo_template
    repo = tmp_path / "repo"
    shutil.copytree(template, repo)
    return repo


@pytest.fixture
def head_sha(_push_repo_template: tuple[Path, str]) -> str:
    """HEAD of the fixture repo; identical in every copy of it."""
    return _push_repo_template[1]


def _set_stub_exit(repo: Path, code: int) -> None:
    (repo / "scripts" / "stub-exit-code").write_text(f"{code}\n", encoding="utf-8")


def _run_hook(repo: Path, refspec_lines: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "hooks" / "pre-push"), "origin", "https://example.invalid"],
        input=refspec_lines,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(repo),
    )


def _validated_branches(repo: Path) -> list[str]:
    record = repo / "push-check-calls.jsonl"
    if not record.exists():
        return []
    branches = []
    for line in record.read_text(encoding="utf-8").splitlines():
        argv = json.loads(line)
        branches.append(argv[argv.index("--branch") + 1])
    return branches


def test_branch_refspec_is_validated(push_repo: Path, head_sha: str) -> None:
    proc = _run_hook(
        push_repo, f"refs/heads/feature-x {head_sha} refs/heads/feature-x {ZERO_SHA}\n"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == ["feature-x"]


def test_head_refspec_is_validated(push_repo: Path, head_sha: str) -> None:
    # Regression: the local side is `HEAD`, but refs/heads/feature-x is still
    # the ref being published, so the claim check must run.
    proc = _run_hook(push_repo, f"HEAD {head_sha} refs/heads/feature-x {ZERO_SHA}\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == ["feature-x"]


def test_sha_refspec_is_validated(push_repo: Path, head_sha: str) -> None:
    proc = _run_hook(push_repo, f"{head_sha} {head_sha} refs/heads/feature-x {ZERO_SHA}\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == ["feature-x"]


@pytest.mark.parametrize("local_ref", ["refs/heads/feature-x", "HEAD"])
def test_push_check_refusal_fails_the_push(push_repo: Path, head_sha: str, local_ref: str) -> None:
    _set_stub_exit(push_repo, 1)
    proc = _run_hook(
        push_repo, f"{local_ref} {head_sha} refs/heads/feature-x {ZERO_SHA}\n"
    )
    assert proc.returncode != 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == ["feature-x"]


def test_branch_deletion_is_not_validated(push_repo: Path, head_sha: str) -> None:
    proc = _run_hook(
        push_repo, f"(delete) {ZERO_SHA} refs/heads/feature-x {head_sha}\n"
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == []


def test_tag_push_is_not_validated(push_repo: Path, head_sha: str) -> None:
    proc = _run_hook(push_repo, f"refs/tags/v1 {head_sha} refs/tags/v1 {ZERO_SHA}\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == []


def test_head_to_tag_push_is_not_validated(push_repo: Path, head_sha: str) -> None:
    # Neither side is a branch ref, so there is no branch claim to check. This
    # is unchanged from before the remote-ref fix.
    proc = _run_hook(push_repo, f"HEAD {head_sha} refs/tags/v1 {ZERO_SHA}\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == []


def test_branch_to_tag_push_is_still_validated(push_repo: Path, head_sha: str) -> None:
    # The remote ref is a tag, but the local side is a branch, so the push still
    # publishes branch content. Gating on the remote ref alone would have
    # dropped this case, which the pre-fix hook did validate.
    proc = _run_hook(push_repo, f"refs/heads/feature-x {head_sha} refs/tags/v1 {ZERO_SHA}\n")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _validated_branches(push_repo) == ["feature-x"]


def test_detached_head_push_is_refused(push_repo: Path, head_sha: str) -> None:
    _git(push_repo, "checkout", "--quiet", "--detach", head_sha)
    proc = _run_hook(push_repo, f"HEAD {head_sha} refs/heads/feature-x {ZERO_SHA}\n")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "only supports the checked-out branch" in proc.stderr
    assert _validated_branches(push_repo) == []


def test_push_to_other_branch_name_is_refused(push_repo: Path, head_sha: str) -> None:
    proc = _run_hook(push_repo, f"HEAD {head_sha} refs/heads/other-branch {ZERO_SHA}\n")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "Requested branch: other-branch" in proc.stderr
    assert _validated_branches(push_repo) == []
