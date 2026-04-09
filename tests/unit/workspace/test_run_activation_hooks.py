from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import HookExecutionError
from git_workspace.manifest import Hooks
from git_workspace.worktree import WorktreeResult

ROOT = Path("/workspace")
WORKTREE_PATH = ROOT / "feat" / "001"
BIN_PATH = ROOT / ".workspace" / "bin"
BRANCH = "feat/001"

NEW_RESULT = WorktreeResult(path=WORKTREE_PATH, is_new=True)
EXISTING_RESULT = WorktreeResult(path=WORKTREE_PATH, is_new=False)


@pytest.fixture(autouse=True)
def mock_subprocess(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.subprocess.run", return_value=MagicMock(returncode=0))


def _executables(mock_subprocess: MagicMock) -> list[str]:
    return [call.args[0][0] for call in mock_subprocess.call_args_list]


def test_runs_after_activate_for_new_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [str(BIN_PATH / "activate.sh")]


def test_runs_after_activate_for_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, EXISTING_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [str(BIN_PATH / "activate.sh")]


def test_runs_before_activate_for_new_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_activate=["pre.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [str(BIN_PATH / "pre.sh")]


def test_runs_before_activate_for_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_activate=["pre.sh"])

    workspace.run_activation_hooks(ROOT, EXISTING_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [str(BIN_PATH / "pre.sh")]


def test_before_activate_runs_before_after_activate(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_activate=["pre.sh"], after_activate=["post.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "pre.sh"),
        str(BIN_PATH / "post.sh"),
    ]


def test_hooks_execute_in_configured_order(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_activate=["first.sh", "second.sh", "third.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "first.sh"),
        str(BIN_PATH / "second.sh"),
        str(BIN_PATH / "third.sh"),
    ]


def test_skips_hooks_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_activate=["pre.sh"], after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_skips_hooks_when_skip_hooks_is_true_for_existing_worktree(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_activate=["pre.sh"], after_activate=["activate.sh"])

    workspace.run_activation_hooks(ROOT, EXISTING_RESULT, hooks, branch=BRANCH, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_hook_failure_raises_hook_execution_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(after_activate=["activate.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)


def test_before_activate_failure_stops_execution(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(before_activate=["pre.sh"], after_activate=["post.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert mock_subprocess.call_count == 1


def test_hook_failure_stops_execution(mock_subprocess: MagicMock) -> None:
    mock_subprocess.side_effect = [MagicMock(returncode=1), MagicMock(returncode=0)]
    hooks = Hooks(after_activate=["fails.sh", "never_runs.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_activation_hooks(ROOT, NEW_RESULT, hooks, branch=BRANCH)

    assert mock_subprocess.call_count == 1


def test_no_hooks_configured_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_activation_hooks(ROOT, NEW_RESULT, Hooks(), branch=BRANCH)

    mock_subprocess.assert_not_called()
