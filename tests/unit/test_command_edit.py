from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.edit import edit

WORKSPACE_DIR = "/workspace"
CONFIG_PATH = Path("/workspace/.workspace")


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.edit.Workspace.resolve")
    mock.return_value.paths.config = CONFIG_PATH
    return mock


@pytest.fixture(autouse=True)
def mock_click_edit(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.edit.click.edit")


class TestEdit:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        edit(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_opens_config_path_in_editor(
        self,
        mock_click_edit: MagicMock,
    ) -> None:
        edit()
        mock_click_edit.assert_called_once_with(filename=str(CONFIG_PATH))
