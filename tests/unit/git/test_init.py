from unittest.mock import MagicMock

import pytest

from git_workspace import git
from git_workspace.errors import GitInitError

TARGET_PATH = ".git"


def test_happy_path(subprocess: MagicMock) -> None:
    git.init(TARGET_PATH)


def test_when_git_fails_then_raises_git_init_error(
    subprocess: MagicMock,
) -> None:
    subprocess.run.return_value = MagicMock(returncode=1)

    with pytest.raises(GitInitError):
        git.init(TARGET_PATH)
