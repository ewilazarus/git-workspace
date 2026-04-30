from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.list import list
from tests.helpers import make_context

WORKSPACE_DIR = "/workspace"


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.list.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_typer_echo(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.list.typer.echo")


class TestList:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        list(ctx=make_context(WORKSPACE_DIR))
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_lists_worktrees(self, mock_workspace_resolve: MagicMock) -> None:
        list(ctx=make_context())
        mock_workspace_resolve.return_value.list_worktrees.assert_called_once()
