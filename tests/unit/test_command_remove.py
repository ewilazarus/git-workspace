from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.remove import remove

BRANCH = "feature/my-branch"
WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.remove.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_remove_worktree(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.remove.operations.remove_worktree")


class TestRemove:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        remove(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        remove(branch=BRANCH)
        mock_workspace_resolve.return_value.resolve_worktree.assert_called_once_with(BRANCH)

    def test_removes_worktree_with_runtime_vars(
        self,
        mock_workspace_resolve: MagicMock,
        mock_remove_worktree: MagicMock,
    ) -> None:
        remove(runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_remove_worktree.assert_called_once_with(
            worktree, runtime_vars={"MY_VAR": "my_value"}, force=False
        )

    def test_removes_worktree_with_empty_runtime_vars_when_none(
        self,
        mock_workspace_resolve: MagicMock,
        mock_remove_worktree: MagicMock,
    ) -> None:
        remove()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_remove_worktree.assert_called_once_with(worktree, runtime_vars={}, force=False)

    def test_removes_worktree_with_force(
        self,
        mock_workspace_resolve: MagicMock,
        mock_remove_worktree: MagicMock,
    ) -> None:
        remove(force=True)
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_remove_worktree.assert_called_once_with(worktree, runtime_vars={}, force=True)
