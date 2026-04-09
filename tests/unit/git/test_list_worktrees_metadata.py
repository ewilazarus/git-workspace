from pathlib import Path
from unittest.mock import MagicMock

from git_workspace import git
from git_workspace.git import WorktreeMetadata

PORCELAIN_OUTPUT = """\
worktree /workspace/.git
HEAD abc123def456abc123def456abc123def456abc123
bare

worktree /workspace/feat/001
HEAD def456abc123def456abc123def456abc123def456
branch refs/heads/feat/001

worktree /workspace/feat/002
HEAD 789abc123def789abc123def789abc123def789abc
branch refs/heads/feat/002

worktree /workspace/detached
HEAD 111aaa222bbb333ccc444ddd555eee666fff777aaa
detached

"""


def test_happy_path(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout=PORCELAIN_OUTPUT)

    result = git.list_worktrees_metadata()

    assert result == [
        WorktreeMetadata(path=Path("/workspace/feat/001"), head="def456abc123def456abc123def456abc123def456", branch="feat/001"),
        WorktreeMetadata(path=Path("/workspace/feat/002"), head="789abc123def789abc123def789abc123def789abc", branch="feat/002"),
    ]


def test_ignores_detached_worktrees(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout=PORCELAIN_OUTPUT)

    result = git.list_worktrees_metadata()

    assert all(wt.branch != "HEAD" for wt in result)


def test_ignores_bare_worktrees(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout=PORCELAIN_OUTPUT)

    result = git.list_worktrees_metadata()

    assert all(str(wt.path) != "/workspace/.git" for wt in result)


def test_when_git_fails_then_returns_empty_list(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=128, stdout="")

    result = git.list_worktrees_metadata()

    assert result == []


def test_when_no_worktrees_then_returns_empty_list(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="")

    result = git.list_worktrees_metadata()

    assert result == []


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="")

    git.list_worktrees_metadata()

    subprocess.run.assert_called_with(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
