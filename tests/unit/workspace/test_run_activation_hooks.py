from pathlib import Path
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import HookExecutionError
from git_workspace.manifest import Hooks
from git_workspace.worktree import WorktreeResult

ROOT = Path("/workspace")
WORKTREE_PATH = ROOT / "feat" / "001"
BIN_PATH = ROOT / ".workspace" / "bin"

NEW_RESULT = WorktreeResult(path=WORKTREE_PATH, is_new=True)
EXISTING_RESULT = WorktreeResult(path=WORKTREE_PATH, is_new=False)


@pytest.fixture(autouse=True)
def mock_subprocess(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.subprocess.run", return_value=MagicMock(returncode=0))


def test_runs_for_new_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks)

    mock_subprocess.assert_called_once_with([str(BIN_PATH / "activate.sh")], cwd=str(WORKTREE_PATH))


def test_runs_for_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, EXISTING_RESULT, hooks)

    mock_subprocess.assert_called_once_with([str(BIN_PATH / "activate.sh")], cwd=str(WORKTREE_PATH))


def test_hooks_execute_in_configured_order(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["first.sh", "second.sh", "third.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks)

    assert mock_subprocess.call_args_list == [
        call([str(BIN_PATH / "first.sh")], cwd=str(WORKTREE_PATH)),
        call([str(BIN_PATH / "second.sh")], cwd=str(WORKTREE_PATH)),
        call([str(BIN_PATH / "third.sh")], cwd=str(WORKTREE_PATH)),
    ]


def test_skips_hooks_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_skips_hooks_when_skip_hooks_is_true_for_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, EXISTING_RESULT, hooks, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_hook_failure_raises_hook_execution_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(after_activate=["activate.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks)


def test_hook_failure_stops_execution(mock_subprocess: MagicMock) -> None:
    mock_subprocess.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
    hooks = Hooks(after_activate=["fails.sh", "never_runs.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks)

    assert mock_subprocess.call_count == 1


def test_no_hooks_configured_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_activation_hooks(ROOT, NEW_RESULT, Hooks())

    mock_subprocess.assert_not_called()
