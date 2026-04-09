from unittest.mock import MagicMock

import pytest

from git_workspace import git

BRANCH = "feat/001"


@pytest.mark.parametrize("fn", [git.local_branch_exists, git.remote_branch_exists])
def test_when_git_succeeds_then_returns_true(subprocess: MagicMock, fn) -> None:
    subprocess.run.return_value = MagicMock(returncode=0)

    assert fn(BRANCH) is True


@pytest.mark.parametrize("fn", [git.local_branch_exists, git.remote_branch_exists])
def test_when_git_fails_then_returns_false(subprocess: MagicMock, fn) -> None:
    subprocess.run.return_value = MagicMock(returncode=1)

    assert fn(BRANCH) is False


def test_local_branch_exists_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0)

    git.local_branch_exists(BRANCH)

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--verify", f"refs/heads/{BRANCH}"],
        capture_output=True,
        text=True,
    )


def test_remote_branch_exists_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0)

    git.remote_branch_exists(BRANCH)

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--verify", f"refs/remotes/origin/{BRANCH}"],
        capture_output=True,
        text=True,
    )
