import re
import subprocess
from pathlib import Path

import structlog

from git_workspace.errors import (
    GitCloneError,
    GitFetchError,
    GitInitError,
    WorktreeCreationError,
    WorktreeRemovalError,
    WorktreeListingError,
)

logger = structlog.get_logger(__name__)

PARSE_WORKTREE_RE = re.compile(
    r"worktree (?P<directory>.+)\n"
    r"HEAD (?P<head>[a-f0-9]{40})\n"
    r"branch refs/head/(?P<branch>.+)"
)


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


def list_worktrees(path: str) -> list[dict[str, str]]:
    cmd = ["git", "worktree", "list", "--porcelain"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=path)
    if result.returncode != 0:
        raise WorktreeListingError("failed to list worktrees")

    worktrees = []
    for block in result.stdout.split("\n\n"):
        match = PARSE_WORKTREE_RE.search(block)
        if match:
            worktrees.append(match.groupdict())
    return worktrees


def fetch_origin() -> None:
    """
    Fetches from origin and prunes stale remote-tracking branches

    :raises GitFetchError: If the fetch fails
    """
    cmd = ["git", "fetch", "origin", "--prune"]
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise GitFetchError(f"Failed to fetch from origin: {result.stderr.strip()}")


def local_branch_exists(workspace_directory: str, branch: str) -> bool:
    """
    Returns whether a local branch exists

    :param branch: The branch name to check
    :param cwd: The git repository directory. If None, uses the current directory.
    :returns: True if the branch exists locally, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"]
    result = subprocess.run(cmd, cwd=workspace_directory)
    return result.returncode == 0


def remote_branch_exists(workspace_directory: str, branch: str) -> bool:
    """
    Returns whether a branch exists on origin

    :param branch: The branch name to check
    :param cwd: The git repository directory. If None, uses the current directory.
    :returns: True if the branch exists on origin, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"]
    result = subprocess.run(cmd, cwd=workspace_directory)
    return result.returncode == 0


def skip_worktree(path: Path) -> None:
    """
    Marks a file with git update-index --skip-worktree so local changes are ignored

    Runs as a best-effort operation; failures are silently ignored since the file
    may not be tracked.

    :param path: The file path relative to the worktree root
    :param cwd: The worktree root directory
    """
    subprocess.run(
        ["git", "update-index", "--skip-worktree", str(path)],
        capture_output=True,
        text=True,
    )


def add_worktree(
    workspace_directory: str, worktree_directory: str, branch: str
) -> None:
    """
    Creates a worktree for an existing local branch

    :param path: The path at which to create the worktree
    :param branch: The existing local branch to check out
    :param cwd: The git repository directory. If None, uses the current directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    cmd = ["git", "worktree", "add", worktree_directory, branch]
    result = subprocess.run(cmd, cwd=workspace_directory)
    if result.returncode != 0:
        raise WorktreeCreationError()


def add_worktree_tracking_remote(
    workspace_directory: str, worktree_directory: str, branch: str
) -> None:
    """
    Creates a worktree with a new local branch tracking origin/<branch>

    :param path: The path at which to create the worktree
    :param branch: The remote branch name to track
    :param cwd: The git repository directory. If None, uses the current directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    cmd = [
        "git",
        "worktree",
        "add",
        "--track",
        "-b",
        branch,
        worktree_directory,
        f"origin/{branch}",
    ]
    result = subprocess.run(cmd, cwd=workspace_directory)
    if result.returncode != 0:
        raise WorktreeCreationError()


def add_worktree_new_branch(
    workspace_directory: str,
    worktree_directory: str,
    branch: str,
    base_branch: str,
) -> None:
    """
    Creates a worktree with a brand new local branch from a base branch.

    If the repository has no commits yet (empty repo), an orphan branch is
    created instead, since no valid base ref exists.

    :param path: The path at which to create the worktree
    :param branch: The new branch name to create
    :param base: The base branch to create from
    :param cwd: The git repository directory. If None, uses the current directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    cmd = ["git", "worktree", "add", "-b", branch, worktree_directory, base_branch]
    result = subprocess.run(cmd, cwd=workspace_directory)
    if result.returncode != 0:
        raise WorktreeCreationError()


def try_get_worktree_directory() -> str | None:
    cmd = ["git", "rev-parse", "--top-level"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def get_worktree_branch(worktree_directory: str) -> str:
    cmd = ["git", "branch", "--show-current"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=worktree_directory,
    )
    return result.stdout.strip()


def remove_worktree(worktree_directory: str, force: bool = False) -> None:
    """
    Removes a git worktree without deleting the branch.

    :param path: The worktree path to remove
    :param force: If True, passes --force to git worktree remove
    :param cwd: The git repository directory. If None, uses the current directory.
    :raises WorktreeRemovalError: If the removal fails
    """
    cmd = ["git", "worktree", "remove"]

    if force:
        cmd.append("--force")

    cmd.append(worktree_directory)

    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise WorktreeRemovalError()
