import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git_workspace.workspace import Workspace
    from git_workspace.worktree import Worktree


def build_env(
    workspace: Workspace,
    worktree: Worktree,
    event: str | None = None,
    extra_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    env = {
        **os.environ,
        "GIT_WORKSPACE_BRANCH": worktree.branch,
        "GIT_WORKSPACE_BRANCH_NO_SLASH": worktree.branch.replace("/", "_"),
        "GIT_WORKSPACE_ROOT": str(workspace.dir),
        "GIT_WORKSPACE_NAME": workspace.dir.name,
        "GIT_WORKSPACE_BIN": str(workspace.paths.bin),
        "GIT_WORKSPACE_ASSETS": str(workspace.paths.assets),
        "GIT_WORKSPACE_WORKTREE": str(worktree.dir),
    }
    if event is not None:
        env["GIT_WORKSPACE_EVENT"] = event
    for key, value in (extra_vars or {}).items():
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = value
    return env
