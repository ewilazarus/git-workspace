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


def test_runs_after_setup_hooks_for_new_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh", "configure.sh"])

    workspace.run_setup_hooks(ROOT, NEW_RESULT, hooks)

    assert mock_subprocess.call_count == 2
    mock_subprocess.assert_any_call([str(BIN_PATH / "install.sh")], cwd=str(WORKTREE_PATH))
    mock_subprocess.assert_any_call([str(BIN_PATH / "configure.sh")], cwd=str(WORKTREE_PATH))


def test_hooks_execute_in_configured_order(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["first.sh", "second.sh", "third.sh"])

    workspace.run_setup_hooks(ROOT, NEW_RESULT, hooks)

    assert mock_subprocess.call_args_list == [
        call([str(BIN_PATH / "first.sh")], cwd=str(WORKTREE_PATH)),
        call([str(BIN_PATH / "second.sh")], cwd=str(WORKTREE_PATH)),
        call([str(BIN_PATH / "third.sh")], cwd=str(WORKTREE_PATH)),
    ]


def test_skips_hooks_when_resuming_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh"])

    workspace.run_setup_hooks(ROOT, EXISTING_RESULT, hooks)

    mock_subprocess.assert_not_called()


def test_skips_hooks_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_setup=["install.sh"])

    workspace.run_setup_hooks(ROOT, NEW_RESULT, hooks, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_hook_failure_raises_hook_execution_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(after_setup=["install.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_setup_hooks(ROOT, NEW_RESULT, hooks)


def test_hook_failure_stops_execution(mock_subprocess: MagicMock) -> None:
    mock_subprocess.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
    hooks = Hooks(after_setup=["fails.sh", "never_runs.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_setup_hooks(ROOT, NEW_RESULT, hooks)

    assert mock_subprocess.call_count == 1


def test_no_hooks_configured_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_setup_hooks(ROOT, NEW_RESULT, Hooks())

    mock_subprocess.assert_not_called()
