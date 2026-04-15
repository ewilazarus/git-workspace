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
def mock_hook_runner(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.remove.HookRunner")


class TestRemove:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        remove(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        remove(branch=BRANCH)
        mock_workspace_resolve.return_value.resolve_worktree.assert_called_once_with(BRANCH)

    def test_creates_hook_runner_with_runtime_vars(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        remove(runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_hook_runner.assert_called_once_with(
            workspace, worktree, runtime_vars={"MY_VAR": "my_value"}
        )

    def test_creates_hook_runner_with_empty_runtime_vars_when_none(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        remove()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_hook_runner.assert_called_once_with(workspace, worktree, runtime_vars={})

    def test_runs_deactivate_hooks(self, mock_hook_runner: MagicMock) -> None:
        remove()
        mock_hook_runner.return_value.run_on_deactivate_hooks.assert_called_once()

    def test_runs_remove_hooks(self, mock_hook_runner: MagicMock) -> None:
        remove()
        mock_hook_runner.return_value.run_on_remove_hooks.assert_called_once()

    def test_deletes_worktree_with_force(self, mock_workspace_resolve: MagicMock) -> None:
        remove(force=True)
        worktree = mock_workspace_resolve.return_value.resolve_worktree.return_value
        worktree.delete.assert_called_once_with(True)

    def test_deletes_worktree_without_force(self, mock_workspace_resolve: MagicMock) -> None:
        remove(force=False)
        worktree = mock_workspace_resolve.return_value.resolve_worktree.return_value
        worktree.delete.assert_called_once_with(False)
