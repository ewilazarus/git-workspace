from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.clone import clone

URL = "https://github.com/user/repo.git"
WORKSPACE_DIR = "/workspace"
CONFIG_URL = "https://github.com/user/config.git"


@pytest.fixture(autouse=True)
def mock_workspace_clone(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.clone.Workspace.clone")


class TestClone:
    def test_calls_workspace_clone_with_all_params(self, mock_workspace_clone: MagicMock) -> None:
        clone(url=URL, workspace_dir=WORKSPACE_DIR, config_url=CONFIG_URL)
        mock_workspace_clone.assert_called_once_with(WORKSPACE_DIR, URL, CONFIG_URL)

    def test_calls_workspace_clone_with_none_defaults(
        self, mock_workspace_clone: MagicMock
    ) -> None:
        clone(url=URL)
        mock_workspace_clone.assert_called_once_with(None, URL, None)
