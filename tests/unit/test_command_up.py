from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.up import up

BRANCH = "feature/my-branch"
BASE_BRANCH = "main"
WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_activate_worktree(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.operations.activate_worktree")


class TestUp:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        up(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_or_creates_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        up(branch=BRANCH, base_branch=BASE_BRANCH)
        mock_workspace_resolve.return_value.resolve_or_create_worktree.assert_called_once_with(
            BRANCH, BASE_BRANCH
        )

    def test_activates_worktree_with_runtime_vars(
        self,
        mock_workspace_resolve: MagicMock,
        mock_activate_worktree: MagicMock,
    ) -> None:
        up(runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        mock_activate_worktree.assert_called_once_with(
            worktree, runtime_vars={"MY_VAR": "my_value"}, detached=False
        )

    def test_activates_worktree_with_empty_runtime_vars_when_none(
        self,
        mock_workspace_resolve: MagicMock,
        mock_activate_worktree: MagicMock,
    ) -> None:
        up()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        mock_activate_worktree.assert_called_once_with(worktree, runtime_vars={}, detached=False)

    def test_activates_worktree_as_detached(
        self,
        mock_workspace_resolve: MagicMock,
        mock_activate_worktree: MagicMock,
    ) -> None:
        up(detached=True)
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        mock_activate_worktree.assert_called_once_with(worktree, runtime_vars={}, detached=True)
