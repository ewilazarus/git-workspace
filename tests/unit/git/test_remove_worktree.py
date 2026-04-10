from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_workspace import git
from git_workspace.errors import WorktreeRemovalError

PATH = Path("/workspace/feat/001")


def test_happy_path(subprocess: MagicMock) -> None:
    git.remove_worktree(PATH)


def test_with_force_flag(subprocess: MagicMock) -> None:
    git.remove_worktree(PATH, force=True)


def test_when_git_fails_raises_error(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=1, stderr="not a worktree")

    with pytest.raises(WorktreeRemovalError):
        git.remove_worktree(PATH)


def test_invokes_git_correctly_without_force(subprocess: MagicMock) -> None:
    git.remove_worktree(PATH)

    subprocess.run.assert_called_with(
        ["git", "worktree", "remove", str(PATH)],
        capture_output=True,
        text=True,
        cwd=None,
    )


def test_invokes_git_correctly_with_force(subprocess: MagicMock) -> None:
    git.remove_worktree(PATH, force=True)

    subprocess.run.assert_called_with(
        ["git", "worktree", "remove", "--force", str(PATH)],
        capture_output=True,
        text=True,
        cwd=None,
    )
