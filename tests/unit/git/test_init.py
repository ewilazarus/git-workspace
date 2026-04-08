from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_workspace import git
from git_workspace.errors import GitInitError

TARGET_PATH = Path(".git")


def test_when_passing_true_bare_flag_then_invokes_git_correctly(
    subprocess: MagicMock,
) -> None:
    git.init(TARGET_PATH, bare=True)

    subprocess.run.assert_called_with(
        ["git", "init", "--bare", TARGET_PATH.as_posix()],
        capture_output=True,
        text=True,
    )


def test_when_passing_false_bare_flag_then_invokes_git_correctly(
    subprocess: MagicMock,
) -> None:
    git.init(TARGET_PATH, bare=False)

    subprocess.run.assert_called_with(
        ["git", "init", TARGET_PATH.as_posix()],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("bare", [(True,), (False,)])
def test_when_git_fails_then_raises_git_init_error(
    subprocess: MagicMock, bare: bool
) -> None:
    subprocess.run.return_value = MagicMock(returncode=1)

    with pytest.raises(GitInitError):
        git.init(TARGET_PATH, bare=bare)
