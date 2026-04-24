import os
from typing import TYPE_CHECKING

from git_workspace.utils import normalize_variable_name

if TYPE_CHECKING:
    from git_workspace.worktree import Worktree


def build_env(
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

    :param worktree: The worktree for which the environment is being built.
    :param event: If set, exposed as ``GIT_WORKSPACE_EVENT``.
    :param extra_vars: Manifest-level variables to expose as ``GIT_WORKSPACE_VAR_*`` entries.
    :returns: A copy of the current process environment with all ``GIT_WORKSPACE_*`` keys set.
    """
    env = {
        **os.environ,
        "GIT_WORKSPACE_BRANCH": worktree.branch,
        "GIT_WORKSPACE_BRANCH_NO_SLASH": worktree.branch.replace("/", "_"),
        "GIT_WORKSPACE_ROOT": str(worktree.workspace.dir),
        "GIT_WORKSPACE_NAME": worktree.workspace.dir.name,
        "GIT_WORKSPACE_BIN": str(worktree.workspace.paths.bin),
        "GIT_WORKSPACE_ASSETS": str(worktree.workspace.paths.assets),
        "GIT_WORKSPACE_WORKTREE": str(worktree.dir),
        "GIT_WORKSPACE_EVENT": event or "",
    }

    for key, value in (extra_vars or {}).items():
        normalized = normalize_variable_name(key)
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = str(value)

    return env
