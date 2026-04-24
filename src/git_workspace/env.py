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
    """
    Build the environment dict for hook and exec invocations within a worktree.

    Starts from the current process environment and layers in ``GIT_WORKSPACE_*``
    variables. Each key in ``extra_vars`` is normalized to uppercase with
    non-alphanumeric characters replaced by underscores and exposed as
    ``GIT_WORKSPACE_VAR_<NORMALIZED_KEY>``.

    :param workspace: The workspace the worktree belongs to.
    :param worktree: The worktree for which the environment is being built.
    :param event: If set, exposed as ``GIT_WORKSPACE_EVENT``.
    :param extra_vars: Manifest-level variables to expose as ``GIT_WORKSPACE_VAR_*`` entries.
    :returns: A copy of the current process environment with all ``GIT_WORKSPACE_*`` keys set.
    """
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
