from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.init import init

WORKSPACE_DIR = "/workspace"
CONFIG_URL = "https://github.com/user/config.git"


@pytest.fixture(autouse=True)
def mock_workspace_init(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.init.Workspace.init")


class TestInit:
    def test_calls_workspace_init_with_workspace_dir_and_config_url(
        self, mock_workspace_init: MagicMock
    ) -> None:
        init(workspace_dir=WORKSPACE_DIR, config_url=CONFIG_URL)
        mock_workspace_init.assert_called_once_with(WORKSPACE_DIR, CONFIG_URL)

    def test_calls_workspace_init_with_none_defaults(self, mock_workspace_init: MagicMock) -> None:
        init()
        mock_workspace_init.assert_called_once_with(None, None)
