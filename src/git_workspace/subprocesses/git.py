import logging
import re
from pathlib import Path

from git_workspace.errors import (
    GitCloneError,
    GitFetchError,
    GitInitError,
    WorktreeCreationError,
    WorktreeListingError,
    WorktreeRemovalError,
)
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner

logger = logging.getLogger(__name__)

PARSE_WORKTREE_RE = re.compile(
    r"worktree (?P<directory>.+)\n"
    r"HEAD (?P<head>[a-f0-9]{40})\n"
    r"branch refs/heads/(?P<branch>.+)"
)


def clone(
    url: str,
    target: Path | None = None,
    branch: str | None = None,
    bare: bool = False,
    *,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> None:
    """
    Clones a git repository

    :param url: The url of the git repository
    :param target: The target folder to clone to
    :param branch: The branch to clone
    :param bare: Whether to clone bare or not
    :raises GitCloneError: If the clone fails
    """
    cmd: list[str | Path] = ["git", "clone"]

    if branch:
        cmd.append("-b")
        cmd.append(branch)
        cmd.append("--single-branch")
    if bare:
        cmd.append("--bare")

    cmd.append(url)

    if target:
        cmd.append(target)

    logger.debug("cloning %r -> %s", url, target or "(inferred)")
    result = runner.run(cmd, check=False)
    if not result.ok:
        logger.error("git clone failed for %r: %s", url, result.stderr.strip())
        raise GitCloneError(f"Failed to clone {url!r}")


def init(target: Path, bare: bool, *, runner: CommandRunner = DEFAULT_RUNNER) -> None:
    """
    Initializes a git repository at the provided target

    :param target: The target directory to initialize the bare git repository at
    :param bare: A flag indicating whether the repository to be initialized should
        be bare or not.
    :raises GitInitError: If the initialization fails
    """
    cmd: list[str | Path] = ["git", "init"]

    if bare:
        cmd.append("--bare")

    cmd.append(target)

    logger.debug("initializing %s repo at %s", "bare" if bare else "non-bare", target)
    result = runner.run(cmd, check=False)
    if not result.ok:
        logger.error("git init failed at %s: %s", target, result.stderr.strip())
        raise GitInitError(f"Failed to init repository at {target!r}: {result.stderr.strip()}")


def list_worktrees(cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> list[dict[str, str]]:
    logger.debug("listing worktrees in %s", cwd)
    result = runner.run(["git", "worktree", "list", "--porcelain"], cwd=cwd, check=False)
    if not result.ok:
        logger.error("git worktree list failed in %s: %s", cwd, result.stderr.strip())
        raise WorktreeListingError(f"Failed to list worktrees in {cwd!r}: {result.stderr.strip()}")

    worktrees = []
    for block in result.stdout.split("\n\n"):
        match = PARSE_WORKTREE_RE.search(block)
        if match:
            worktrees.append(match.groupdict())
    logger.debug("found %d worktree(s)", len(worktrees))
    return worktrees


def configure_remote_fetch_refspec(cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> None:
    """
    Sets the remote.origin.fetch refspec to use remote-tracking refs.

    A bare clone does not set a fetch refspec, so fetched branches never land in
    refs/remotes/origin/* and remote-branch lookups always fail. This sets it to
    '+refs/heads/*:refs/remotes/origin/*' (identical to a normal clone).
    """
    runner.run(
        ["git", "config", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"],
        cwd=cwd,
        check=False,
    )


def fetch_origin(cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> None:
    """
    Fetches from origin and prunes stale remote-tracking branches.

    :raises GitFetchError: If the fetch fails
    """
    logger.debug("fetching origin in %s", cwd)
    result = runner.run(["git", "fetch", "origin", "--prune"], cwd=cwd, check=False)
    if not result.ok:
        logger.warning("git fetch failed in %s: %s", cwd, result.stderr.strip())
        raise GitFetchError(f"Failed to fetch from origin: {result.stderr.strip()}")


def local_branch_exists(branch: str, cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> bool:
    """
    Returns whether a local branch exists

    :param branch: The branch name to check
    :param cwd: The git repository directory.
    :returns: True if the branch exists locally, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"]
    result = runner.run(cmd, cwd=cwd, check=False)
    exists = result.ok
    logger.debug("local branch %r exists: %s", branch, exists)
    return exists


def remote_branch_exists(branch: str, cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> bool:
    """
    Returns whether a branch exists on origin

    :param branch: The branch name to check
    :param cwd: The git repository directory.
    :returns: True if the branch exists on origin, False otherwise
    """
    cmd = ["git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"]
    result = runner.run(cmd, cwd=cwd, check=False)
    exists = result.ok
    logger.debug("remote branch %r exists: %s", branch, exists)
    return exists


def skip_worktree(path: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> None:
    """
    Marks a file with git update-index --skip-worktree so local changes are ignored

    Runs as a best-effort operation; failures are silently ignored since the file
    may not be tracked.

    :param path: The file path to mark
    """
    logger.debug("marking %s as skip-worktree", path)
    runner.run(["git", "update-index", "--skip-worktree", path], check=False)


def create_worktree_from_local_branch(
    worktree_dir: Path,
    branch: str,
    cwd: Path,
    *,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> None:
    """
    Creates a worktree for an existing local branch

    :param worktree_dir: The path at which to create the worktree
    :param branch: The existing local branch to check out
    :param cwd: The git repository directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    logger.debug("creating worktree for local branch %r at %s", branch, worktree_dir)
    result = runner.run(["git", "worktree", "add", worktree_dir, branch], cwd=cwd, check=False)
    if not result.ok:
        logger.error(
            "failed to create worktree for local branch %r: %s", branch, result.stderr.strip()
        )
        raise WorktreeCreationError(
            f"Failed to create worktree for local branch {branch!r} at {worktree_dir}: {result.stderr.strip()}"
        )


def create_worktree_from_remote_branch(
    worktree_dir: Path,
    branch: str,
    cwd: Path,
    *,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> None:
    """
    Creates a worktree with a new local branch tracking origin/<branch>

    :param worktree_dir: The path at which to create the worktree
    :param branch: The remote branch name to track
    :param cwd: The git repository directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    logger.debug("creating worktree tracking remote branch %r at %s", branch, worktree_dir)
    cmd: list[str | Path] = [
        "git",
        "worktree",
        "add",
        "--track",
        "-b",
        branch,
        worktree_dir,
        f"origin/{branch}",
    ]
    result = runner.run(cmd, cwd=cwd, check=False)
    if not result.ok:
        logger.error(
            "failed to create worktree for remote branch %r: %s", branch, result.stderr.strip()
        )
        raise WorktreeCreationError(
            f"Failed to create worktree for remote branch {branch!r} at {worktree_dir}: {result.stderr.strip()}"
        )


def create_worktree_new(
    worktree_dir: Path,
    branch: str,
    base_branch: str,
    cwd: Path,
    *,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> None:
    """
    Creates a worktree with a brand new local branch from a base branch.

    If the repository has no commits yet (empty repo), an orphan branch is
    created instead, since no valid base ref exists.

    :param worktree_dir: The path at which to create the worktree
    :param branch: The new branch name to create
    :param base_branch: The base branch to create from
    :param cwd: The git repository directory.
    :raises WorktreeCreationError: If the worktree cannot be created
    """
    logger.debug(
        "creating new worktree for branch %r from %r at %s", branch, base_branch, worktree_dir
    )
    cmd: list[str | Path] = ["git", "worktree", "add", "-b", branch, worktree_dir, base_branch]
    result = runner.run(cmd, cwd=cwd, check=False)
    if not result.ok:
        # Base ref doesn't exist — repo has no commits yet. Create an orphan worktree.
        logger.debug(
            "base branch %r not found, falling back to orphan worktree for %r", base_branch, branch
        )
        orphan_cmd: list[str | Path] = [
            "git",
            "worktree",
            "add",
            "--orphan",
            "-b",
            branch,
            worktree_dir,
        ]
        orphan_result = runner.run(orphan_cmd, cwd=cwd, check=False)
        if not orphan_result.ok:
            logger.error(
                "failed to create orphan worktree for branch %r: %s",
                branch,
                orphan_result.stderr.strip(),
            )
            raise WorktreeCreationError(
                f"Failed to create orphan worktree for branch {branch!r} at {worktree_dir}: {orphan_result.stderr.strip()}"
            )


def git_common_dir(path: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> Path | None:
    """
    Returns the main repository's git directory for a worktree path.

    For a linked worktree this resolves to the main repo's git dir (not the
    per-worktree admin dir). The output may be relative, so it is resolved
    against ``path``.

    :param path: A directory inside a worktree.
    :returns: The resolved common git directory, or None when ``path`` is not
        inside a git repository.
    """
    result = runner.run(["git", "rev-parse", "--git-common-dir"], cwd=path, check=False)
    if not result.ok:
        logger.debug("no git common dir for %s", path)
        return None
    common_dir = (path / result.stdout.strip()).resolve()
    logger.debug("git common dir for %s: %s", path, common_dir)
    return common_dir


def try_get_worktree_dir(*, runner: CommandRunner = DEFAULT_RUNNER) -> str | None:
    result = runner.run(["git", "rev-parse", "--show-toplevel"], check=False)
    worktree_dir = result.stdout.strip() if result.ok else None
    logger.debug("cwd worktree dir: %s", worktree_dir or "(none)")
    return worktree_dir


def get_worktree_branch(cwd: str, *, runner: CommandRunner = DEFAULT_RUNNER) -> str:
    result = runner.run(["git", "branch", "--show-current"], cwd=Path(cwd), check=False)
    branch = result.stdout.strip()
    logger.debug("current branch in %s: %r", cwd, branch)
    return branch


def prune_worktrees(cwd: Path, *, runner: CommandRunner = DEFAULT_RUNNER) -> None:
    """
    Removes stale worktree administrative files via `git worktree prune`.

    :param cwd: The git repository directory.
    """
    logger.debug("pruning stale worktrees in %s", cwd)
    runner.run(["git", "worktree", "prune"], cwd=cwd, check=False)


def remove_worktree(
    worktree_dir: Path,
    force: bool = False,
    *,
    cwd: Path,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> None:
    """
    Removes a git worktree without deleting the branch.

    :param worktree_dir: The worktree path to remove.
    :param force: If True, passes --force to git worktree remove.
    :param cwd: The git repository directory.
    :raises WorktreeRemovalError: If the removal fails.
    """
    logger.debug("removing worktree at %s (force=%s)", worktree_dir, force)
    cmd: list[str | Path] = ["git", "worktree", "remove"]

    if force:
        cmd.append("--force")

    cmd.append(worktree_dir)

    result = runner.run(cmd, cwd=cwd, check=False)
    if not result.ok:
        logger.error("failed to remove worktree at %s: %s", worktree_dir, result.stderr.strip())
        raise WorktreeRemovalError(
            f"Failed to remove worktree at {worktree_dir!r}: {result.stderr.strip()}"
        )
