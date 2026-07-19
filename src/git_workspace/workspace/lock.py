import fcntl
import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from git_workspace.errors import WorkspaceLockedError
from git_workspace.workspace.state import state_file_stem

logger = logging.getLogger(__name__)


@contextmanager
def workspace_operation_lock(locks_dir: Path, worktree_path: Path) -> Iterator[None]:
    """
    Holds an exclusive, non-blocking lifecycle lock for a canonical worktree
    path while a mutating operation (up/prepare/down/rm/prune) runs.

    A second caller fails fast instead of waiting. Lock files are never
    deleted: unlink-then-flock is racy, and empty lock files are harmless.

    :raises WorkspaceLockedError: If another operation holds the lock.
    """
    locks_dir.mkdir(parents=True, exist_ok=True)
    lock_path = locks_dir / f"{state_file_stem(worktree_path)}.lock"

    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise WorkspaceLockedError(
            f"Another workspace operation is already running for:\n{worktree_path}"
        ) from None

    logger.debug("acquired workspace lock: %s", lock_path)
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        logger.debug("released workspace lock: %s", lock_path)
