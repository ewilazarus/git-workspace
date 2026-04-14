from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from git_workspace.workspace import WorkspaceFactory

DIRECTORY = Path("/workspace")
URL = "https://github.com/user/repo.git"
CONFIG_URL = "https://github.com/user/config.git"

GIT_PATH = DIRECTORY / ".git"
CONFIG_PATH = DIRECTORY / ".workspace"


@pytest.fixture(autouse=True)
def mock_mkdir(mocker: MockerFixture) -> None:
    mocker.patch.object(Path, "mkdir")


@pytest.fixture(autouse=True)
def mock_manifest_load(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.workspace.Manifest.load")


@pytest.fixture(autouse=True)
def mock_rmtree(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.workspace.shutil.rmtree")


@pytest.fixture
def mock_git_clone(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.git.clone")


@pytest.fixture
def mock_git_init(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.git.init")


def test_clones_bare_repo_and_config_when_both_urls_provided(
    mock_git_clone: MagicMock, mock_git_init: MagicMock
) -> None:
    WorkspaceFactory.create(DIRECTORY, url=URL, config_url=CONFIG_URL)

    mock_git_clone.assert_any_call(URL, target=GIT_PATH, bare=True)
    mock_git_clone.assert_any_call(CONFIG_URL, target=CONFIG_PATH)
    mock_git_init.assert_not_called()


def test_clones_bare_repo_and_inits_example_config_when_only_url_provided(
    mock_git_clone: MagicMock, mock_git_init: MagicMock
) -> None:
    WorkspaceFactory.create(DIRECTORY, url=URL)

    mock_git_clone.assert_any_call(URL, target=GIT_PATH, bare=True)
    mock_git_clone.assert_any_call(
        WorkspaceFactory.DEFAULT_CONFIG_URL,
        target=CONFIG_PATH,
        branch=WorkspaceFactory.DEFAULT_CONFIG_BRANCH,
    )
    mock_git_init.assert_called_once_with(CONFIG_PATH, bare=False)


def test_inits_bare_repo_and_clones_config_when_only_config_url_provided(
    mock_git_clone: MagicMock, mock_git_init: MagicMock
) -> None:
    WorkspaceFactory.create(DIRECTORY, config_url=CONFIG_URL)

    mock_git_init.assert_called_once_with(GIT_PATH, bare=True)
    mock_git_clone.assert_called_once_with(CONFIG_URL, target=CONFIG_PATH)


def test_inits_bare_repo_and_inits_example_config_when_no_urls_provided(
    mock_git_clone: MagicMock, mock_git_init: MagicMock
) -> None:
    WorkspaceFactory.create(DIRECTORY)

    mock_git_init.assert_has_calls(
        [
            call(GIT_PATH, bare=True),
            call(CONFIG_PATH, bare=False),
        ]
    )
    mock_git_clone.assert_called_once_with(
        WorkspaceFactory.DEFAULT_CONFIG_URL,
        target=CONFIG_PATH,
        branch=WorkspaceFactory.DEFAULT_CONFIG_BRANCH,
    )
