from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.hooks import HookRunner

BRANCH = "feat/GWS-001"
WORKSPACE_DIR = Path("/workspace")
WORKSPACE_NAME = "workspace"
WORKTREE_DIR = Path("/workspace/feat/GWS-001")
BIN_DIR = Path("/workspace/.workspace/bin")
ASSETS_DIR = Path("/workspace/.workspace/assets")

HOOKS_ON_SETUP = ["setup.sh"]
HOOKS_ON_ACTIVATE = ["activate.sh"]
HOOKS_ON_ATTACH = ["attach.sh"]
HOOKS_ON_DEACTIVATE = ["deactivate.sh"]
HOOKS_ON_REMOVE = ["remove.sh"]


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKSPACE_DIR
    mock.paths.bin = BIN_DIR
    mock.paths.assets = ASSETS_DIR
    mock.manifest.vars = {}
    mock.manifest.hooks.on_setup = HOOKS_ON_SETUP
    mock.manifest.hooks.on_activate = HOOKS_ON_ACTIVATE
    mock.manifest.hooks.on_attach = HOOKS_ON_ATTACH
    mock.manifest.hooks.on_deactivate = HOOKS_ON_DEACTIVATE
    mock.manifest.hooks.on_remove = HOOKS_ON_REMOVE
    return mock


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKTREE_DIR
    mock.branch = BRANCH
    return mock


@pytest.fixture
def hook_runner(workspace: MagicMock, worktree: MagicMock) -> HookRunner:
    return HookRunner(workspace, worktree, {})


@pytest.fixture(autouse=True)
def mock_bin_is_file(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("pathlib.Path.is_file", return_value=True)


@pytest.fixture(autouse=True)
def mock_popen(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.hooks.subprocess.Popen")
    mock.return_value.__enter__.return_value.returncode = 0
    return mock


class TestResolveCommand:
    def test_runs_bin_script_when_file_exists(
        self,
        hook_runner: HookRunner,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"})

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "setup.sh")
        assert mock_popen.call_args.kwargs["shell"] is True
        assert mock_popen.call_args.kwargs["executable"] == "/usr/bin/zsh"

    def test_runs_inline_command_when_no_bin_script(
        self,
        hook_runner: HookRunner,
        mock_bin_is_file: MagicMock,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_bin_is_file.return_value = False
        mocker.patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"})

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == "setup.sh"
        assert mock_popen.call_args.kwargs["shell"] is True
        assert mock_popen.call_args.kwargs["executable"] == "/usr/bin/zsh"

    def test_falls_back_to_sh_when_shell_not_set(
        self,
        hook_runner: HookRunner,
        mock_bin_is_file: MagicMock,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_bin_is_file.return_value = False
        mocker.patch.dict("os.environ", {}, clear=True)

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.kwargs["executable"] == "sh"


class TestRunOnSetupHooks:
    def test_runs_hooks_from_on_setup_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "setup.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_SETUP"


class TestRunOnActivateHooks:
    def test_runs_hooks_from_on_activate_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_activate_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "activate.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_activate_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_ACTIVATE"


class TestRunOnAttachHooks:
    def test_runs_hooks_from_on_attach_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_attach_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "attach.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_attach_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_ATTACH"


class TestRunOnDeactivateHooks:
    def test_runs_hooks_from_on_deactivate_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_deactivate_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "deactivate.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_deactivate_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_DEACTIVATE"


class TestRunOnRemoveHooks:
    def test_runs_hooks_from_on_remove_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_remove_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "remove.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_remove_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_REMOVE"
