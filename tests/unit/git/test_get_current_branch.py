from pathlib import Path
from unittest.mock import MagicMock

from git_workspace import git

CWD = Path("/workspace/feat/001")


def test_happy_path(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="feat/001\n")

    result = git.get_current_branch(CWD)

    assert result == "feat/001"


def test_when_git_fails_then_returns_none(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=128)

    result = git.get_current_branch(CWD)

    assert result is None


def test_when_head_is_detached_then_returns_none(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="HEAD\n")

    result = git.get_current_branch(CWD)

    assert result is None


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="feat/001\n")

    git.get_current_branch(CWD)

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(CWD),
    )


def test_when_no_cwd_then_passes_none_to_subprocess(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="feat/001\n")

    git.get_current_branch()

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        cwd=None,
    )
