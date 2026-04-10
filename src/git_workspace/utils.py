import json
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from git_workspace.errors import InvalidInputError

if TYPE_CHECKING:
    from git_workspace.worktree import WorktreeInfo


def extract_humanish_suffix(url: str) -> str:
    """
    Extracts a human-readable suffix from a URL.

    Examples:
    - https://github.com/ewilazarus/dotfiles -> dotfiles
    - https://github.com/ewilazarus/dotfiles.git -> dotfiles
    - git@github.com:ewilazarus/dotfiles -> dotfiles
    - https://example.com/archive.tar.gz -> archive

    :param url: The URL to have the suffix extracted from
    :return: The extracted suffix
    :raises InvalidInputError: If no valid suffix can be extracted
    """
    if not url:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    # Handle SCP-like URLs such as git@github.com:user/repo
    if "://" not in url and "@" in url and ":" in url:
        path = url.split(":", 1)[1]
    else:
        path = urlparse(url).path

    path = path.rstrip("/")

    if not path:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    name = PurePosixPath(path).name

    if not name:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    while True:
        stem = PurePosixPath(name).stem
        if stem == name:
            break
        name = stem

    if not name:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    return name


def format_table(worktrees_list: list["WorktreeInfo"]) -> str:
    """
    Formats worktrees as a human-readable table.

    :param worktrees_list: List of WorktreeInfo records
    :returns: Formatted table string
    """
    if not worktrees_list:
        return "No worktrees found."

    rows = [("BRANCH", "AGE", "COMMIT", "PATH")]

    for wt in worktrees_list:
        marker = " *" if wt.current else ""
        branch_col = (wt.branch or "detached") + marker
        age_col = wt.age_display
        commit_col = wt.short_id or "unknown"
        path_col = str(wt.path)

        rows.append((branch_col, age_col, commit_col, path_col))

    col_widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]

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


def format_json(worktrees_list: list["WorktreeInfo"]) -> str:
    """
    Formats worktrees as JSON.

    :param worktrees_list: List of WorktreeInfo records
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
        for wt in worktrees_list
    ]
    return json.dumps(data, indent=2)
