from git_workspace.errors import GitCloneError
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import git

GIT_URL = "https://example.com"
TARGET_PATH = "target"


@pytest.fixture
def subprocess(mocker: MockerFixture) -> MagicMock:
    subprocess = mocker.patch("git_workspace.git.subprocess")
    subprocess.run.return_value = MagicMock(returncode=0)
    return subprocess


def test_happy_path(subprocess: MagicMock) -> None:
    try:
        git.clone(GIT_URL)
    except GitCloneError:
        pytest.fail("Shouldn't have raised a git clone error")


def test_when_git_fails_then_raises_git_clone_error(
    subprocess: MagicMock,
) -> None:
    subprocess.run.return_value = MagicMock(returncode=1)

    with pytest.raises(GitCloneError):
        git.clone(GIT_URL)


def test_when_passing_bare_flag_then_invokes_git_correctly(
    subprocess: MagicMock,
) -> None:
    git.clone(GIT_URL, bare=True)

    subprocess.run.assert_called_with(
        ["git", "clone", GIT_URL, "--bare"],
        capture_output=True,
        text=True,
    )


def test_when_passing_target_path_then_invokes_git_correctly(
    subprocess: MagicMock,
) -> None:
    git.clone(GIT_URL, target=TARGET_PATH)

    subprocess.run.assert_called_with(
        ["git", "clone", GIT_URL, TARGET_PATH],
        capture_output=True,
        text=True,
    )


def test_when_passing_bare_flag_and_target_path_then_invokes_git_correctly(
    subprocess: MagicMock,
) -> None:
    git.clone(GIT_URL, target=TARGET_PATH, bare=True)

    subprocess.run.assert_called_with(
        ["git", "clone", GIT_URL, "--bare", TARGET_PATH],
        capture_output=True,
        text=True,
    )
