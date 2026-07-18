import fcntl
import os
from pathlib import Path

import pytest

from git_workspace.errors import WorkspaceLockedError
from git_workspace.workspace.lock import workspace_operation_lock
from git_workspace.workspace.state import state_file_stem


@pytest.fixture
def locks_dir(tmp_path: Path) -> Path:
    return tmp_path / "locks"


@pytest.fixture
def worktree_path(tmp_path: Path) -> Path:
    return tmp_path / "workspace" / "feature" / "auth"


class TestWorkspaceOperationLock:
    def test_acquires_and_releases(self, locks_dir: Path, worktree_path: Path) -> None:
        with workspace_operation_lock(locks_dir, worktree_path):
            pass

        with workspace_operation_lock(locks_dir, worktree_path):
            pass

    def test_fails_fast_when_already_held(self, locks_dir: Path, worktree_path: Path) -> None:
        lock_path = locks_dir / f"{state_file_stem(worktree_path)}.lock"
        locks_dir.mkdir(parents=True)

        # Hold the flock on a separate fd, as a concurrent process would.
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(WorkspaceLockedError) as excinfo:
                with workspace_operation_lock(locks_dir, worktree_path):
                    pass

            assert str(worktree_path) in str(excinfo.value)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def test_different_worktrees_do_not_contend(self, locks_dir: Path, tmp_path: Path) -> None:
        with workspace_operation_lock(locks_dir, tmp_path / "a"):
            with workspace_operation_lock(locks_dir, tmp_path / "b"):
                pass

    def test_releases_lock_on_exception(self, locks_dir: Path, worktree_path: Path) -> None:
        with pytest.raises(RuntimeError):
            with workspace_operation_lock(locks_dir, worktree_path):
                raise RuntimeError("boom")

        with workspace_operation_lock(locks_dir, worktree_path):
            pass
