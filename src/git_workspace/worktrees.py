"""Utilities for listing and formatting worktree information."""

import json
import time
from dataclasses import dataclass
from pathlib import Path

import structlog

from git_workspace import git

logger = structlog.get_logger(__name__)


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
    branch = normalize_branch(worktree_meta.branch)
    short_id = git.get_short_commit_id(worktree_meta.path)
    timestamp = git.get_commit_timestamp(worktree_meta.path)
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

    metadata = git.list_worktrees_metadata()
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

    worktrees = [
        enrich_worktree(wt_meta, current_worktree=current_worktree)
        for wt_meta in metadata
    ]

    worktrees.sort(key=lambda wt: (not wt.current, str(wt.path)))

    return worktrees


def format_table(worktrees: list[WorktreeInfo]) -> str:
    """
    Formats worktrees as a human-readable table.

    :param worktrees: List of WorktreeInfo records
    :returns: Formatted table string
    """
    if not worktrees:
        return "No worktrees found."

    rows = [("BRANCH", "AGE", "COMMIT", "PATH")]

    for wt in worktrees:
        marker = " *" if wt.current else ""
        branch_col = (wt.branch or "detached") + marker
        age_col = wt.age_display
        commit_col = wt.short_id or "unknown"
        path_col = str(wt.path)

        rows.append((branch_col, age_col, commit_col, path_col))

    col_widths = [
        max(len(row[i]) for row in rows)
        for i in range(len(rows[0]))
    ]

    lines = []
    for i, row in enumerate(rows):
        if i == 0:
            line = "  ".join(f"{row[j]:<{col_widths[j]}}" for j in range(len(row)))
            lines.append(line)
            lines.append("  ".join("-" * col_widths[j] for j in range(len(row))))
        else:
            line = "  ".join(f"{row[j]:<{col_widths[j]}}" for j in range(len(row)))
            lines.append(line)

    return "\n".join(lines)


def format_json(worktrees: list[WorktreeInfo]) -> str:
    """
    Formats worktrees as JSON.

    :param worktrees: List of WorktreeInfo records
    :returns: JSON string
    """
    data = [
        {
            "branch": wt.branch,
            "path": str(wt.path),
            "head": wt.head,
            "short_id": wt.short_id,
            "age_days": wt.age_days,
            "current": wt.current,
        }
        for wt in worktrees
    ]
    return json.dumps(data, indent=2)
