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
def mock_hook_runner(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.up.HookRunner")
    mock.return_value.__enter__.return_value = mock.return_value
    return mock


@pytest.fixture(autouse=True)
def mock_ignore_manager(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.IgnoreManager")


@pytest.fixture(autouse=True)
def mock_copier(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.Copier")


@pytest.fixture(autouse=True)
def mock_linker(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.Linker")


class TestUp:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        up(workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_or_creates_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        up(branch=BRANCH, base_branch=BASE_BRANCH)
        mock_workspace_resolve.return_value.resolve_or_create_worktree.assert_called_once_with(
            BRANCH, BASE_BRANCH
        )

    def test_creates_hook_runner_with_runtime_vars(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        up(runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        mock_hook_runner.assert_called_once_with(
            workspace, worktree, runtime_vars={"MY_VAR": "my_value"}
        )

    def test_creates_hook_runner_with_empty_runtime_vars_when_none(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        up()
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        mock_hook_runner.assert_called_once_with(workspace, worktree, runtime_vars={})

    def test_applies_assets_and_runs_setup_hooks_when_worktree_is_new(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
        mock_ignore_manager: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
    ) -> None:
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        worktree.is_new = True

        up()

        ignore = mock_ignore_manager.return_value.__enter__.return_value
        mock_copier.assert_called_once_with(workspace, worktree, ignore)
        mock_copier.return_value.apply.assert_called_once()
        mock_linker.assert_called_once_with(workspace, worktree, ignore)
        mock_linker.return_value.apply.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()

    def test_skips_assets_and_setup_hooks_when_worktree_is_not_new(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
    ) -> None:
        workspace = mock_workspace_resolve.return_value
        worktree = workspace.resolve_or_create_worktree.return_value
        worktree.is_new = False

        up()

        mock_copier.assert_not_called()
        mock_linker.assert_not_called()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()

    def test_always_runs_activate_hooks(
        self,
        mock_workspace_resolve: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        up()
        mock_hook_runner.return_value.run_on_activate_hooks.assert_called_once()

    def test_runs_attach_hooks_when_not_detached(
        self,
        mock_hook_runner: MagicMock,
    ) -> None:
        up(detached=False)
        mock_hook_runner.return_value.run_on_attach_hooks.assert_called_once()

    def test_skips_attach_hooks_when_detached(
        self,
        mock_hook_runner: MagicMock,
    ) -> None:
        up(detached=True)
        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()
