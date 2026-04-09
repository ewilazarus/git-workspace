from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from git_workspace import git
from git_workspace.errors import WorktreeCreationError  # noqa: F401 — re-exported for callers



class UpAction(Enum):
    RESUME = auto()
    CREATE_FROM_LOCAL = auto()
    CREATE_FROM_REMOTE = auto()
    CREATE_FROM_BASE = auto()


@dataclass
class UpPlan:
    action: UpAction
    branch: str
    base_branch: str | None = None
    existing_worktree_path: Path | None = None


@dataclass
class WorktreeResult:
    path: Path
    is_new: bool


def resolve_base_branch(
    explicit: str | None = None,
    manifest_base_branch: str | None = None,
) -> str:
    """
    Resolves the base branch to use when creating a new local branch

    Resolution order:
    1. Explicit value provided by the caller (e.g. CLI --base option)
    2. base_branch from the workspace manifest
    3. Default branch inferred from origin/HEAD
    4. Hardcoded fallback: "main"

    :param explicit: Branch name explicitly requested by the user
    :param manifest_base_branch: base_branch value from the workspace manifest
    :returns: The resolved base branch name
    """
    if explicit is not None:
        return explicit
    if manifest_base_branch is not None:
        return manifest_base_branch
    origin_head = git.get_origin_head()
    if origin_head is not None:
        return origin_head
    return "main"


def resolve_up_plan(
    branch: str,
    explicit_base_branch: str | None = None,
    manifest_base_branch: str | None = None,
) -> UpPlan:
    """
    Determines what the up command should do for a given branch

    Resolution order:
    1. If an existing worktree already tracks the branch → RESUME
    2. If a local branch exists → CREATE_FROM_LOCAL
    3. If a remote branch exists (known refs) → CREATE_FROM_REMOTE
    4. Fetch origin, then retry remote check → CREATE_FROM_REMOTE
    5. Otherwise → CREATE_FROM_BASE

    :param branch: The target branch name
    :param explicit_base_branch: Base branch explicitly provided by the caller
    :param manifest_base_branch: Base branch from the workspace manifest
    :returns: An UpPlan describing the action to take
    """
    worktrees = git.list_worktrees_metadata()
    matching = next((wt for wt in worktrees if wt.branch == branch), None)
    if matching:
        return UpPlan(action=UpAction.RESUME, branch=branch, existing_worktree_path=matching.path)

    if git.local_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_LOCAL, branch=branch)

    if git.remote_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=branch)

    git.fetch_origin()

    if git.remote_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=branch)

    base = resolve_base_branch(
        explicit=explicit_base_branch,
        manifest_base_branch=manifest_base_branch,
    )
    return UpPlan(action=UpAction.CREATE_FROM_BASE, branch=branch, base_branch=base)


def _worktree_path(root: Path, branch: str) -> Path:
    return root / branch


def resume_worktree(worktree_path: Path) -> WorktreeResult:
    """
    Returns the result for an existing worktree without performing any setup

    :param worktree_path: The path to the existing worktree
    :returns: A WorktreeResult with is_new=False
    """
    return WorktreeResult(path=worktree_path, is_new=False)


def create_worktree_from_local(root: Path, branch: str) -> WorktreeResult:
    """
    Creates a worktree for an existing local branch at the canonical path

    :param root: The workspace root path
    :param branch: The existing local branch to check out
    :raises WorktreeCreationError: If the worktree cannot be created
    :returns: A WorktreeResult with is_new=True
    """
    path = _worktree_path(root, branch)
    git.add_worktree(path, branch)
    return WorktreeResult(path=path, is_new=True)


def create_worktree_from_remote(root: Path, branch: str) -> WorktreeResult:
    """
    Creates a worktree with a new local tracking branch from origin/<branch>

    :param root: The workspace root path
    :param branch: The remote branch name to track
    :raises WorktreeCreationError: If the worktree cannot be created
    :returns: A WorktreeResult with is_new=True
    """
    path = _worktree_path(root, branch)
    git.add_worktree_tracking_remote(path, branch)
    return WorktreeResult(path=path, is_new=True)


def create_worktree_from_base(root: Path, branch: str, base: str) -> WorktreeResult:
    """
    Creates a worktree with a brand new local branch from a base branch

    :param root: The workspace root path
    :param branch: The new branch name to create
    :param base: The base branch to create from
    :raises WorktreeCreationError: If the worktree cannot be created
    :returns: A WorktreeResult with is_new=True
    """
    path = _worktree_path(root, branch)
    git.add_worktree_new_branch(path, branch, base)
    return WorktreeResult(path=path, is_new=True)


