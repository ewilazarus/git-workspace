from unittest.mock import MagicMock

import pytest

from git_workspace import git
from git_workspace.errors import GitFetchError


def test_happy_path(subprocess: MagicMock) -> None:
    git.fetch_origin()


def test_when_git_fails_then_raises_git_fetch_error(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=1, stderr="connection refused")

    with pytest.raises(GitFetchError):
        git.fetch_origin()


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    git.fetch_origin()

    subprocess.run.assert_called_with(
        ["git", "fetch", "origin", "--prune"],
        capture_output=True,
        text=True,
        cwd=None,
    )
