from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import git_workspace.operations as operations

MOCK_ENV = {"GIT_WORKSPACE_BRANCH": "main"}


@pytest.fixture(autouse=True)
def mock_compute_fingerprints(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.operations.compute_fingerprints", return_value={})


@pytest.fixture(autouse=True)
def mock_build_env(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.operations.build_env", return_value=MOCK_ENV)


@pytest.fixture(autouse=True)
def mock_ignore_manager(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.operations.IgnoreManager")


@pytest.fixture(autouse=True)
def mock_copier(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.operations.Copier")


@pytest.fixture(autouse=True)
def mock_linker(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.operations.Linker")


@pytest.fixture(autouse=True)
def mock_hook_runner(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.operations.HookRunner")
    mock.return_value.__enter__.return_value = mock.return_value
    return mock


@pytest.fixture
def worktree() -> MagicMock:
    wt = MagicMock()
    wt.is_new = False
    return wt


class TestApplyAssetsInternal:
    def test_applies_copier_and_linker_via_ignore_manager(
        self,
        worktree: MagicMock,
        mock_ignore_manager: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
    ) -> None:
        operations._apply_assets(worktree, MOCK_ENV)

        ignore = mock_ignore_manager.return_value.__enter__.return_value
        mock_copier.assert_called_once_with(worktree, ignore, MOCK_ENV)
        mock_copier.return_value.apply.assert_called_once()
        mock_linker.assert_called_once_with(worktree, ignore)
        mock_linker.return_value.apply.assert_called_once()


class TestActivateWorktree:
    def test_new_attached_applies_assets_and_runs_setup_and_attach_hooks(
        self,
        worktree: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        worktree.is_new = True

        operations.activate_worktree(worktree, runtime_vars={}, detached=False)

        mock_copier.return_value.apply.assert_called_once()
        mock_linker.return_value.apply.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_called_once()

    def test_new_detached_applies_assets_and_skips_attach_hooks(
        self,
        worktree: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        worktree.is_new = True

        operations.activate_worktree(worktree, runtime_vars={}, detached=True)

        mock_copier.return_value.apply.assert_called_once()
        mock_linker.return_value.apply.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()

    def test_existing_attached_skips_assets_and_setup_hooks(
        self,
        worktree: MagicMock,
        mock_copier: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        worktree.is_new = False

        operations.activate_worktree(worktree, runtime_vars={}, detached=False)

        mock_copier.assert_not_called()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_called_once()

    def test_existing_detached_skips_all_hooks(
        self,
        worktree: MagicMock,
        mock_copier: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        worktree.is_new = False

        operations.activate_worktree(worktree, runtime_vars={}, detached=True)

        mock_copier.assert_not_called()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()

    def test_passes_env_to_hook_runner(
        self,
        worktree: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.activate_worktree(worktree, runtime_vars={"KEY": "val"}, detached=False)
        mock_hook_runner.assert_called_once_with(worktree, env=MOCK_ENV)


class TestResetWorktree:
    def test_always_applies_assets_and_runs_setup_hooks(
        self,
        worktree: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.reset_worktree(worktree, runtime_vars={})

        mock_copier.return_value.apply.assert_called_once()
        mock_linker.return_value.apply.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()

    def test_does_not_run_attach_hooks(
        self,
        worktree: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.reset_worktree(worktree, runtime_vars={})

        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()


class TestDeactivateWorktree:
    def test_runs_detach_hooks(
        self,
        worktree: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.deactivate_worktree(worktree, runtime_vars={})

        mock_hook_runner.return_value.run_on_detach_hooks.assert_called_once()

    def test_does_not_run_other_hooks(
        self,
        worktree: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.deactivate_worktree(worktree, runtime_vars={})

        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_teardown_hooks.assert_not_called()


class TestRemoveWorktree:
    def test_runs_detach_and_teardown_hooks_then_deletes(
        self,
        worktree: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        operations.remove_worktree(worktree, runtime_vars={}, force=False)

        mock_hook_runner.return_value.run_on_detach_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_teardown_hooks.assert_called_once()
        worktree.delete.assert_called_once_with(False)

    def test_passes_force_to_delete(
        self,
        worktree: MagicMock,
    ) -> None:
        operations.remove_worktree(worktree, runtime_vars={}, force=True)

        worktree.delete.assert_called_once_with(True)
