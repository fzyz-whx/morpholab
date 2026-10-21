import subprocess
from pathlib import Path

import pytest

from scripts.verify_remote import VerificationError, verify_remote


def run_git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    local.mkdir()
    run_git(tmp_path, "init", "--bare", str(remote))
    run_git(local, "init", "--initial-branch=main")
    run_git(local, "config", "user.name", "Offline Test")
    run_git(local, "config", "user.email", "offline@example.invalid")
    run_git(local, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "fixture")
    run_git(local, "remote", "add", "origin", str(remote))
    run_git(local, "push", "--set-upstream", "origin", "main")
    return local


def test_live_remote_match_and_unpushed_commit(repository: Path) -> None:
    assert verify_remote(repository) == run_git(repository, "rev-parse", "HEAD")
    run_git(repository, "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "second")
    with pytest.raises(VerificationError, match="differs"):
        verify_remote(repository)


def test_missing_remote_branch_is_failure(repository: Path) -> None:
    run_git(repository, "config", "branch.main.merge", "refs/heads/missing")
    with pytest.raises(VerificationError, match="Git command failed"):
        verify_remote(repository)


def test_detached_head_is_failure(repository: Path) -> None:
    run_git(repository, "checkout", "--detach")
    with pytest.raises(VerificationError, match="Git command failed"):
        verify_remote(repository)


def test_command_failure_does_not_expose_remote_details(repository: Path) -> None:
    sensitive = "private-credential-fixture"
    run_git(repository, "remote", "set-url", "origin", str(repository / sensitive))
    with pytest.raises(VerificationError) as failure:
        verify_remote(repository)
    assert sensitive not in str(failure.value)
    assert str(repository) not in str(failure.value)
