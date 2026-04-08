from git_workspace.errors import GitCloneError, WorkspaceCreationError, GitInitError
from pytest_mock import MockerFixture
import os
from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from git_workspace import workspace

TARGET_PATH = Path("root")
URL = "https://github.com/ewilazarus/kgoete.git"
CONFIG_URL = "https://github.com/ewilazarus/"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_dir("/")
    os.chdir("/")


@pytest.fixture
def git_clone(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(workspace.git, "clone")


@pytest.fixture
def git_init(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(workspace.git, "init")


@pytest.fixture
def rm(mocker: MockerFixture) -> MagicMock:
    return mocker.patch.object(workspace.shutil, "rmtree")


def test_when_url_and_config_url_are_provided_then_succeeds_to_create_workspace_root(
    git_clone: MagicMock,
    git_init: MagicMock,
    rm: MagicMock,
) -> None:
    workspace.create(path=TARGET_PATH, url=URL, config_url=CONFIG_URL)

    git_clone.assert_has_calls(
        [
            call(URL, target=TARGET_PATH / ".git", bare=True),
            call(CONFIG_URL, target=TARGET_PATH / ".workspace"),
        ]
    )
    git_init.assert_not_called()
    rm.assert_not_called()


def test_when_url_is_provided_and_config_url_is_omitted_then_succeeds_to_create_workspace_root(
    git_clone: MagicMock,
    git_init: MagicMock,
    rm: MagicMock,
) -> None:
    workspace.create(path=TARGET_PATH, url=URL)

    git_clone.assert_has_calls(
        [
            call(URL, target=TARGET_PATH / ".git", bare=True),
            call(
                workspace.DEFAULT_CONFIG_URL,
                target=TARGET_PATH / ".workspace",
                branch=workspace.DEFAULT_CONFIG_BRANCH,
            ),
        ]
    )
    rm.assert_called_once_with(TARGET_PATH / ".workspace" / ".git", ignore_errors=True)
    git_init.assert_called_once_with(TARGET_PATH / ".workspace", bare=False)


def test_when_url_is_omitted_and_config_url_is_provided_then_succeeds_to_create_workspace_root(
    git_init: MagicMock,
    git_clone: MagicMock,
) -> None:
    workspace.create(path=TARGET_PATH, config_url=CONFIG_URL)

    git_init.assert_called_once_with(TARGET_PATH / ".git", bare=True)
    git_clone.assert_called_once_with(CONFIG_URL, target=TARGET_PATH / ".workspace")


def test_when_url_and_config_url_are_omitted_then_succeeds_to_create_workspace_root(
    git_init: MagicMock,
    git_clone: MagicMock,
    rm: MagicMock,
) -> None:
    workspace.create(path=TARGET_PATH)

    git_init.assert_has_calls(
        [
            call(TARGET_PATH / ".git", bare=True),
            call(TARGET_PATH / ".workspace", bare=False),
        ]
    )
    git_clone.assert_called_once_with(
        workspace.DEFAULT_CONFIG_URL,
        target=TARGET_PATH / ".workspace",
        branch=workspace.DEFAULT_CONFIG_BRANCH,
    )

    rm.assert_called_once_with(TARGET_PATH / ".workspace" / ".git", ignore_errors=True)


def test_when_git_fails_to_clone_then_raise_workspace_creation_error(
    git_clone: MagicMock,
) -> None:
    git_clone.side_effect = GitCloneError("boom")

    with pytest.raises(WorkspaceCreationError):
        workspace.create(path=TARGET_PATH, url=URL, config_url=CONFIG_URL)


def test_when_git_fails_to_init_then_raise_workspace_creation_error(
    git_init: MagicMock,
) -> None:
    git_init.side_effect = GitInitError("boom")

    with pytest.raises(WorkspaceCreationError):
        workspace.create(path=TARGET_PATH)
