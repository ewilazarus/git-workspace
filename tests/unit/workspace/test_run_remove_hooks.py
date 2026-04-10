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


# --- run_before_remove_hooks ---

def test_before_remove_runs_configured_hooks(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_remove=["teardown.sh", "notify.sh"])

    workspace.run_before_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "teardown.sh"),
        str(BIN_PATH / "notify.sh"),
    ]


def test_before_remove_skips_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(before_remove=["teardown.sh"])

    workspace.run_before_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_before_remove_hook_failure_raises_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(before_remove=["teardown.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_before_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)


def test_before_remove_no_hooks_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_before_remove_hooks(ROOT, WORKTREE_PATH, Hooks(), branch=BRANCH)

    mock_subprocess.assert_not_called()


# --- run_after_remove_hooks ---

def test_after_remove_runs_configured_hooks(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_remove=["cleanup.sh"])

    workspace.run_after_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [str(BIN_PATH / "cleanup.sh")]


def test_after_remove_skips_when_skip_hooks_is_true(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_remove=["cleanup.sh"])

    workspace.run_after_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH, skip_hooks=True)

    mock_subprocess.assert_not_called()


def test_after_remove_hook_failure_raises_error(mock_subprocess: MagicMock) -> None:
    mock_subprocess.return_value = MagicMock(returncode=1)
    hooks = Hooks(after_remove=["cleanup.sh"])

    with pytest.raises(HookExecutionError):
        workspace.run_after_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)


def test_after_remove_no_hooks_runs_nothing(mock_subprocess: MagicMock) -> None:
    workspace.run_after_remove_hooks(ROOT, WORKTREE_PATH, Hooks(), branch=BRANCH)

    mock_subprocess.assert_not_called()


def test_after_remove_hooks_execute_in_configured_order(mock_subprocess: MagicMock) -> None:
    hooks = Hooks(after_remove=["first.sh", "second.sh", "third.sh"])

    workspace.run_after_remove_hooks(ROOT, WORKTREE_PATH, hooks, branch=BRANCH)

    assert _executables(mock_subprocess) == [
        str(BIN_PATH / "first.sh"),
        str(BIN_PATH / "second.sh"),
        str(BIN_PATH / "third.sh"),
    ]
