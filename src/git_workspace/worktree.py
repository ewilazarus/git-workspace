import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from git_workspace import git
from git_workspace.errors import WorktreeCreationError  # noqa: F401 — re-exported for callers
from git_workspace.manifest import Manifest

import structlog

logger = structlog.get_logger(__name__)


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
        return UpPlan(
            action=UpAction.RESUME, branch=branch, existing_worktree_path=matching.path
        )

    if git.local_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_LOCAL, branch=branch)

    if git.remote_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=branch)

    if git.has_remote():
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


@dataclass
class WorktreeInfo:
    """Information about a workspace worktree."""

    path: Path
    branch: str | None
    head: str
    short_id: str | None
    timestamp: int | None
    age_days: int | None
    current: bool = False

    @property
    def age_display(self) -> str:
        """Returns a human-readable age string."""
        if self.age_days is None:
            return "unknown"
        if self.age_days == 0:
            return "today"
        if self.age_days == 1:
            return "1d"
        return f"{self.age_days}d"


def normalize_branch(branch_ref: str | None) -> str | None:
    """
    Converts a Git branch ref into a user-facing branch name.

    Strips refs/heads/ prefix if present.

    :param branch_ref: The raw branch ref (e.g. "refs/heads/feat/001")
    :returns: The normalized branch name, or None if not a branch ref
    """
    if branch_ref is None:
        return None
    return branch_ref.removeprefix("refs/heads/")


def compute_age(timestamp: int | None) -> int | None:
    """
    Computes the age in days from a commit timestamp.

    :param timestamp: Unix timestamp of the commit
    :returns: Age in days, or None if timestamp is unavailable
    """
    if timestamp is None:
        return None
    now = int(time.time())
    return (now - timestamp) // 86400


def enrich_worktree(
    worktree_meta: git.WorktreeMetadata,
    current_worktree: Path | None = None,
) -> WorktreeInfo:
    """
    Enriches a worktree metadata record with additional computed fields.

    :param worktree_meta: The base metadata from git
    :param current_worktree: The current worktree path, if any
    :returns: Enriched WorktreeInfo
    """
    log = logger.bind(path=str(worktree_meta.path), branch=worktree_meta.branch)

    branch = normalize_branch(worktree_meta.branch)

    short_id = None
    timestamp = None
    if worktree_meta.path.exists():
        short_id = git.get_short_commit_id(worktree_meta.path)
        timestamp = git.get_commit_timestamp(worktree_meta.path)
    else:
        log.debug("Worktree path does not exist")

    age_days = compute_age(timestamp)
    is_current = worktree_meta.path == current_worktree

    return WorktreeInfo(
        path=worktree_meta.path,
        branch=branch,
        head=worktree_meta.head,
        short_id=short_id,
        timestamp=timestamp,
        age_days=age_days,
        current=is_current,
    )


def list_worktrees(root: Path, current_cwd: Path | None = None) -> list[WorktreeInfo]:
    """
    Lists all worktrees in the workspace, enriched with computed fields.

    :param root: The workspace root path
    :param current_cwd: The current working directory (for detecting current worktree)
    :returns: List of enriched WorktreeInfo records, sorted by current first then by path
    """
    log = logger.bind(root=str(root))
    log.debug("Listing worktrees")

    if current_cwd is None:
        current_cwd = Path.cwd().resolve()

    metadata = git.list_worktrees_metadata(cwd=root)
    log.debug("Found worktrees", count=len(metadata))

    current_worktree = None
    try:
        current_worktree = current_cwd.resolve()
        for wt_meta in metadata:
            if wt_meta.path == current_worktree:
                break
        else:
            current_worktree = None
    except (OSError, ValueError):
        current_worktree = None

    worktrees_list = [
        enrich_worktree(wt_meta, current_worktree=current_worktree)
        for wt_meta in metadata
    ]

    worktrees_list.sort(key=lambda wt: (not wt.current, str(wt.path)))

    return worktrees_list


@dataclass
class PruneCandidate:
    """A worktree eligible for pruning."""

    path: Path
    branch: str | None
    age_days: int | None


def resolve_prune_threshold(
    explicit: int | None = None,
    manifest: Manifest | None = None,
) -> int | None:
    """
    Resolves the prune threshold in days.

    Resolution order:
    1. Explicit value from CLI (e.g. --older-than-days)
    2. Threshold from workspace manifest
    3. No threshold (None)

    :param explicit: Age threshold explicitly provided by the user
    :param manifest: The workspace manifest
    :returns: The age threshold in days, or None if not specified
    :raises ValueError: If the threshold is invalid (negative or non-integer)
    """
    if explicit is not None:
        if explicit < 0:
            raise ValueError("older-than-days must be non-negative")
        return explicit
    if manifest and manifest.prune and manifest.prune.older_than_days is not None:
        threshold = manifest.prune.older_than_days
        if threshold < 0:
            raise ValueError("older-than-days in manifest must be non-negative")
        return threshold
    return None


def select_prune_candidates(
    worktrees: list[WorktreeInfo],
    threshold_days: int | None,
    exclude_branches: list[str] | None = None,
) -> list[PruneCandidate]:
    """
    Selects worktrees eligible for pruning based on age and exclusion rules.

    A worktree is a candidate if:
    - Its age (in days) exceeds the threshold
    - Its branch is not in the exclusion list
    - It has a valid age (age_days is not None)

    :param worktrees: List of enriched worktree records
    :param threshold_days: Age threshold in days (None means no threshold)
    :param exclude_branches: Branch names that should never be pruned
    :returns: List of PruneCandidate records sorted by age descending
    """
    if exclude_branches is None:
        exclude_branches = []

    log = logger.bind(threshold=threshold_days, exclude_branches=exclude_branches)
    log.debug("Selecting prune candidates")

    candidates = []
    for wt in worktrees:
        # Skip worktrees with invalid age
        if wt.age_days is None:
            log.debug("Skipping worktree with unknown age", path=str(wt.path))
            continue

        # Skip excluded branches
        if wt.branch in exclude_branches:
            log.debug(
                "Skipping excluded branch",
                path=str(wt.path),
                branch=wt.branch,
            )
            continue

        # Skip current worktree
        if wt.current:
            log.debug("Skipping current worktree", path=str(wt.path))
            continue

        # Check age threshold
        if threshold_days is None or wt.age_days >= threshold_days:
            candidates.append(
                PruneCandidate(
                    path=wt.path,
                    branch=wt.branch,
                    age_days=wt.age_days,
                )
            )
            log.debug(
                "Added candidate",
                path=str(wt.path),
                branch=wt.branch,
                age_days=wt.age_days,
            )

    # Sort by age descending
    candidates.sort(key=lambda c: c.age_days or 0, reverse=True)

    log.debug("Selected candidates", count=len(candidates))
    return candidates
