from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.workspace.preparer import WorkspacePreparer

MOCK_ENV = {"GIT_WORKSPACE_BRANCH": "main"}
WORKTREE_DIR = Path("/workspace/main")
BRANCH = "main"


@pytest.fixture(autouse=True)
def mock_compute_fingerprints(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.preparer.compute_fingerprints", return_value={})


@pytest.fixture(autouse=True)
def mock_build_env(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.preparer.build_env", return_value=MOCK_ENV)


@pytest.fixture(autouse=True)
def mock_ignore_manager(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.preparer.IgnoreManager")


@pytest.fixture(autouse=True)
def mock_copier(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.preparer.Copier")


@pytest.fixture(autouse=True)
def mock_linker(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.preparer.Linker")


@pytest.fixture(autouse=True)
def mock_hook_runner(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.workspace.preparer.HookRunner")
    mock.return_value.__enter__.return_value = mock.return_value
    return mock


@pytest.fixture
def workspace() -> MagicMock:
    return MagicMock()


@pytest.fixture
def preparer(workspace: MagicMock) -> WorkspacePreparer:
    return WorkspacePreparer(workspace)


class TestPrepare:
    def test_applies_assets_and_runs_setup_hooks(
        self,
        preparer: WorkspacePreparer,
        mock_ignore_manager: MagicMock,
        mock_copier: MagicMock,
        mock_linker: MagicMock,
        mock_hook_runner: MagicMock,
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH)

        ignore = mock_ignore_manager.return_value.__enter__.return_value
        worktree = mock_copier.call_args.args[0]
        mock_copier.assert_called_once_with(worktree, ignore, MOCK_ENV)
        mock_copier.return_value.apply.assert_called_once()
        mock_linker.assert_called_once_with(worktree, ignore)
        mock_linker.return_value.apply.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_called_once()

    def test_does_not_run_attach_hooks(
        self, preparer: WorkspacePreparer, mock_hook_runner: MagicMock
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH)

        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()

    def test_builds_context_from_path_and_branch(
        self, preparer: WorkspacePreparer, workspace: MagicMock, mock_hook_runner: MagicMock
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH)

        worktree = mock_hook_runner.call_args.args[0]
        assert worktree.workspace is workspace
        assert worktree.dir == WORKTREE_DIR
        assert worktree.branch == BRANCH

    def test_passes_env_and_effective_branch_to_hook_runner(
        self, preparer: WorkspacePreparer, mock_hook_runner: MagicMock
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH)

        assert mock_hook_runner.call_args.kwargs["env"] == MOCK_ENV
        assert mock_hook_runner.call_args.kwargs["effective_branch"] == BRANCH

    def test_effective_branch_overrides_hook_conditions(
        self, preparer: WorkspacePreparer, mock_hook_runner: MagicMock
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH, effective_branch="release/x")

        assert mock_hook_runner.call_args.kwargs["effective_branch"] == "release/x"

    def test_forwards_runtime_vars_to_env(
        self, preparer: WorkspacePreparer, mock_build_env: MagicMock
    ) -> None:
        preparer.prepare(WORKTREE_DIR, BRANCH, runtime_vars={"KEY": "val"})

        assert mock_build_env.call_args.args[1] == {"KEY": "val"}


class TestAttach:
    def test_runs_only_attach_hooks(
        self, preparer: WorkspacePreparer, mock_copier: MagicMock, mock_hook_runner: MagicMock
    ) -> None:
        preparer.attach(WORKTREE_DIR, BRANCH)

        mock_copier.assert_not_called()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()


class TestDetach:
    def test_runs_only_detach_hooks(
        self, preparer: WorkspacePreparer, mock_hook_runner: MagicMock
    ) -> None:
        preparer.detach(WORKTREE_DIR, BRANCH)

        mock_hook_runner.return_value.run_on_detach_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_setup_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_attach_hooks.assert_not_called()
        mock_hook_runner.return_value.run_on_teardown_hooks.assert_not_called()


class TestTeardown:
    def test_runs_only_teardown_hooks(
        self, preparer: WorkspacePreparer, mock_copier: MagicMock, mock_hook_runner: MagicMock
    ) -> None:
        preparer.teardown(WORKTREE_DIR, BRANCH)

        mock_copier.assert_not_called()
        mock_hook_runner.return_value.run_on_teardown_hooks.assert_called_once()
        mock_hook_runner.return_value.run_on_detach_hooks.assert_not_called()
