from dataclasses import dataclass
import subprocess
from pathlib import Path

import structlog

from git_workspace.errors import GitCloneError, GitInitError

logger = structlog.get_logger(__name__)


def clone(
    url: str,
    target: Path | None = None,
    branch: str | None = None,
    bare: bool = False,
) -> None:
    """
    Clones a git repository

    :param url: The url of the git repository
    :param target: The target folder to clone to
    :param branch: The branch to clone
    :param bare: Whether to clone bare or not
    :raises GitCloneError: If the clone fails
    """
    log = logger.bind(url=url, target=target, bare=bare)

    cmd = ["git", "clone"]

    if branch:
        cmd.append("-b")
        cmd.append(branch)
        cmd.append("--single-branch")
    if bare:
        cmd.append("--bare")

    cmd.append(url)

    if target:
        cmd.append(str(target))

    log.debug("Attempting to clone git repository")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitCloneError(f"Failed to clone {url!r}")

    log.debug("Git repository cloned successfully")


def init(target: Path, bare: bool) -> None:
    """
    Initializes a git repository at the provided target

    :param target: The target directory to initialize the bare git repository at
    :param bare: A flag indicating whether the repository to be initialized should
        be bare or not.
    :raises GitInitError: If the initialization fails
    """
    log = logger.bind(target=target, bare=bare)

    cmd = ["git", "init"]

    if bare:
        cmd.append("--bare")

    cmd.append(str(target))

    log.debug("Attempting to initialize a git repository")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitInitError("Failed to init repository")

    log.debug("Git repository initialized successfully")


@dataclass
class WorktreeMetadata:
    path: Path
    head: str
    branch: str


def list_worktrees_metadata() -> list[WorktreeMetadata]:
    raise NotImplementedError
