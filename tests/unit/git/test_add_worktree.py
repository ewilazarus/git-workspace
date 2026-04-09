from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_workspace import git
from git_workspace.errors import WorktreeCreationError

PATH = Path("/workspace/feat/001")
BRANCH = "feat/001"
BASE = "main"


def test_add_worktree_happy_path(subprocess: MagicMock) -> None:
    git.add_worktree(PATH, BRANCH)


def test_add_worktree_when_git_fails_raises_error(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=1, stderr="already exists")

    with pytest.raises(WorktreeCreationError):
        git.add_worktree(PATH, BRANCH)


def test_add_worktree_invokes_git_correctly(subprocess: MagicMock) -> None:
    git.add_worktree(PATH, BRANCH)

    subprocess.run.assert_called_with(
        ["git", "worktree", "add", str(PATH), BRANCH],
        capture_output=True,
        text=True,
    )


def test_add_worktree_tracking_remote_happy_path(subprocess: MagicMock) -> None:
    git.add_worktree_tracking_remote(PATH, BRANCH)


def test_add_worktree_tracking_remote_when_git_fails_raises_error(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=1, stderr="no such remote branch")

    with pytest.raises(WorktreeCreationError):
        git.add_worktree_tracking_remote(PATH, BRANCH)


def test_add_worktree_tracking_remote_invokes_git_correctly(subprocess: MagicMock) -> None:
    git.add_worktree_tracking_remote(PATH, BRANCH)

    subprocess.run.assert_called_with(
        ["git", "worktree", "add", "--track", "-b", BRANCH, str(PATH), f"origin/{BRANCH}"],
        capture_output=True,
        text=True,
    )


def test_add_worktree_new_branch_happy_path(subprocess: MagicMock) -> None:
    git.add_worktree_new_branch(PATH, BRANCH, BASE)


def test_add_worktree_new_branch_when_git_fails_raises_error(subprocess: MagicMock) -> None:
    # First call is is_empty_repo (returncode=0 → not empty), second is the worktree add (returncode=1 → fail)
    subprocess.run.side_effect = [
        MagicMock(returncode=0),
        MagicMock(returncode=1, stderr="invalid base"),
    ]

    with pytest.raises(WorktreeCreationError):
        git.add_worktree_new_branch(PATH, BRANCH, BASE)


def test_add_worktree_new_branch_invokes_git_correctly(subprocess: MagicMock) -> None:
    git.add_worktree_new_branch(PATH, BRANCH, BASE)

    subprocess.run.assert_called_with(
        ["git", "worktree", "add", "-b", BRANCH, str(PATH), BASE],
        capture_output=True,
        text=True,
    )


def test_add_worktree_new_branch_in_empty_repo_uses_orphan(subprocess: MagicMock) -> None:
    # is_empty_repo returns True (returncode=1 for rev-parse HEAD), worktree add succeeds
    subprocess.run.side_effect = [
        MagicMock(returncode=1),
        MagicMock(returncode=0),
    ]

    git.add_worktree_new_branch(PATH, BRANCH, BASE)

    subprocess.run.assert_called_with(
        ["git", "worktree", "add", "--orphan", "-b", BRANCH, str(PATH)],
        capture_output=True,
        text=True,
    )


def test_add_worktree_new_branch_in_empty_repo_when_git_fails_raises_error(subprocess: MagicMock) -> None:
    subprocess.run.side_effect = [
        MagicMock(returncode=1),
        MagicMock(returncode=1, stderr="fatal: orphan error"),
    ]

    with pytest.raises(WorktreeCreationError):
        git.add_worktree_new_branch(PATH, BRANCH, BASE)
