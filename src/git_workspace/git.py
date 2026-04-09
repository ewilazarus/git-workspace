from dataclasses import dataclass
import subprocess
from pathlib import Path

import structlog

from git_workspace.errors import GitCloneError, GitFetchError, GitInitError, WorktreeCreationError

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
    """
    Returns metadata for all worktrees in the current repository

    Uses git worktree list --porcelain and parses each block by key rather than
    line position. Detached worktrees are ignored.

    :returns: A list of WorktreeMetadata with path and branch for each worktree
    """
    cmd = ["git", "worktree", "list", "--porcelain"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []

    worktrees = []
    for block in result.stdout.split("\n\n"):
        block = block.strip()
        if not block:
            continue

        fields: dict[str, str] = {}
        for line in block.splitlines():
            if " " in line:
                key, _, value = line.partition(" ")
                fields[key] = value
            else:
                fields[line] = ""

        if "branch" not in fields:
            continue

        branch = fields["branch"].removeprefix("refs/heads/")
        worktrees.append(
            WorktreeMetadata(
                path=Path(fields["worktree"]),
                head=fields["HEAD"],
                branch=branch,
            )
        )

    return worktrees


def has_remote(name: str = "origin") -> bool:
    """Returns True if the given remote is configured."""
    result = subprocess.run(["git", "remote"], capture_output=True, text=True)
    return name in result.stdout.split()


def is_empty_repo() -> bool:
    """
    Returns True if the repository has no commits yet.

    :returns: True if the repo is empty (no commits), False otherwise
    """
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.returncode != 0


def fetch_origin() -> None:
    """
    Fetches from origin and prunes stale remote-tracking branches

    :raises GitFetchError: If the fetch fails
    """
    cmd = ["git", "fetch", "origin", "--prune"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitFetchError(f"Failed to fetch from origin: {result.stderr.strip()}")


def get_origin_head() -> str | None:
    """
    Returns the default branch on origin by resolving origin/HEAD

    :returns: The default branch name (e.g. "main"), or None if origin/HEAD is not set
    """
    cmd = ["git", "symbolic-ref", "refs/remotes/origin/HEAD"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None
    return result.stdout.strip().removeprefix("refs/remotes/origin/")


def local_branch_exists(branch: str) -> bool:
    """
    Returns whether a local branch exists

    :param branch: The branch name to check
    :returns: True if the branch exists locally, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", f"refs/heads/{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def remote_branch_exists(branch: str) -> bool:
    """
    Returns whether a branch exists on origin

    :param branch: The branch name to check
    :returns: True if the branch exists on origin, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0


def skip_worktree(path: str, cwd: Path) -> None:
    """
    Marks a file with git update-index --skip-worktree so local changes are ignored

    Runs as a best-effort operation; failures are silently ignored since the file
    may not be tracked.

    :param path: The file path relative to the worktree root
    :param cwd: The worktree root directory
    """
    subprocess.run(
        ["git", "update-index", "--skip-worktree", path],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def add_worktree(path: Path, branch: str) -> None:
    """
    Creates a worktree for an existing local branch

    :param path: The path at which to create the worktree
    :param branch: The existing local branch to check out
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    cmd = ["git", "worktree", "add", str(path), branch]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise WorktreeCreationError(
            f"Failed to create worktree for branch {branch!r} at {path!r}: {result.stderr.strip()}"
        )


def add_worktree_tracking_remote(path: Path, branch: str) -> None:
    """
    Creates a worktree with a new local branch tracking origin/<branch>

    :param path: The path at which to create the worktree
    :param branch: The remote branch name to track
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    cmd = ["git", "worktree", "add", "--track", "-b", branch, str(path), f"origin/{branch}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise WorktreeCreationError(
            f"Failed to create worktree tracking origin/{branch!r} at {path!r}: {result.stderr.strip()}"
        )


def add_worktree_new_branch(path: Path, branch: str, base: str) -> None:
    """
    Creates a worktree with a brand new local branch from a base branch.

    If the repository has no commits yet (empty repo), an orphan branch is
    created instead, since no valid base ref exists.

    :param path: The path at which to create the worktree
    :param branch: The new branch name to create
    :param base: The base branch to create from
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    if is_empty_repo():
        cmd = ["git", "worktree", "add", "--orphan", "-b", branch, str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise WorktreeCreationError(
                f"Failed to create orphan worktree for branch {branch!r} at {path!r}: {result.stderr.strip()}"
            )
        return

    cmd = ["git", "worktree", "add", "-b", branch, str(path), base]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise WorktreeCreationError(
            f"Failed to create worktree with new branch {branch!r} from {base!r} at {path!r}: {result.stderr.strip()}"
        )


def get_worktree_root(cwd: Path | None = None) -> Path | None:
    """
    Returns the root path of the worktree the given directory belongs to

    :param cwd: Directory to run git from. If None, uses the current directory.
    :returns: The worktree root path, or None if not inside a worktree
    """
    cmd = ["git", "rev-parse", "--show-toplevel"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def get_current_branch(cwd: Path | None = None) -> str | None:
    """
    Returns the name of the currently checked out branch

    :param cwd: Directory to run git from. If None, uses the current directory.
    :returns: The branch name, or None if HEAD is detached or the command fails
    """
    cmd = ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    if result.returncode != 0:
        return None
    branch = result.stdout.strip()
    return branch if branch != "HEAD" else None
