from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.reset import reset

BRANCH = "feature/my-branch"
WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.reset.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_hook_runner(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.reset.HookRunner")


@pytest.fixture(autouse=True)
def mock_linker(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.reset.Linker")


class TestReset:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        reset(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        reset(branch=BRANCH)
        mock_workspace_resolve.return_value.resolve_worktree.assert_called_once_with(BRANCH)

    def test_applies_linker(
        self,
        mock_workspace_resolve: MagicMock,
        mock_linker: MagicMock,
    ) -> None:
        reset()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_linker.assert_called_once_with(workspace, worktree)
        mock_linker.return_value.apply.assert_called_once()

    def test_creates_hook_runner_with_runtime_vars(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        reset(runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
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
        reset()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_worktree.return_value
        mock_hook_runner.assert_called_once_with(workspace, worktree, runtime_vars={})

    def test_runs_setup_hooks(self, mock_hook_runner: MagicMock) -> None:
        reset()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()
