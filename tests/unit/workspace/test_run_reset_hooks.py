from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import HookExecutionError
from git_workspace.manifest import Hooks

ROOT = Path("/workspace")
WORKTREE_PATH = ROOT / "feat" / "001"
BIN_PATH = ROOT / ".workspace" / "bin"
BRANCH = "feat/001"


@pytest.fixture(autouse=True)
def mock_subprocess(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.subprocess.run", return_value=MagicMock(returncode=0))


def _executables(mock_subprocess: MagicMock) -> list[str]:
    return [call.args[0][0] for call in mock_subprocess.call_args_list]


def test_runs_after_setup_hooks(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh", "configure.sh"])

    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "install.sh"),
        str(BIN_PATH / "configure.sh"),
    ]


def test_always_runs_hooks_not_just_first_time(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh"])

    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)
    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert mock_subprocess.call_count == 2


def test_hooks_execute_in_configured_order(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["first.sh", "second.sh", "third.sh"])

    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "first.sh"),
        str(BIN_PATH / "second.sh"),
        str(BIN_PATH / "third.sh"),
    ]


def test_skips_hooks_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh"])

    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_hook_failure_raises_hook_execution_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(after_setup=["install.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)


def test_hook_failure_stops_execution(mock_subprocess: MagicMock) -> None:
    mock_subprocess.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
    hooks = Hooks(after_setup=["fails.sh", "never_runs.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_reset_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert mock_subprocess.call_count == 1


def test_no_hooks_configured_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_reset_hooks(ROOT, WORKTREE_PATH, Hooks(), branch=BRANCH)

    mock_subprocess.assert_not_called()
