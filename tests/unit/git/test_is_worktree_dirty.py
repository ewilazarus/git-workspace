from pathlib import Path
from unittest.mock import MagicMock

from git_workspace import git

PATH = Path("/workspace/feat/001")


def test_returns_true_when_git_reports_changes(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout=" M modified.py\n")

    assert git.is_worktree_dirty(PATH) is True


def test_returns_false_when_git_reports_clean(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="")

    assert git.is_worktree_dirty(PATH) is False


def test_returns_false_when_output_is_only_whitespace(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="   \n")

    assert git.is_worktree_dirty(PATH) is False


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="")

    git.is_worktree_dirty(PATH)

    subprocess.run.assert_called_with(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd=str(PATH),
    )
