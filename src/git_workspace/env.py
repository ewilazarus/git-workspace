import os
from collections.abc import Callable
from typing import TYPE_CHECKING

from git_workspace.utils import normalize_variable_name

if TYPE_CHECKING:
    from git_workspace.worktree import Worktree

_BASE_VAR_BUILDERS: tuple[tuple[str, Callable[[Worktree], str]], ...] = (
    ("GIT_WORKSPACE_BRANCH", lambda wt: wt.branch),
    ("GIT_WORKSPACE_BRANCH_NO_SLASH", lambda wt: wt.branch.replace("/", "_")),
    ("GIT_WORKSPACE_ROOT", lambda wt: str(wt.workspace.dir)),
    ("GIT_WORKSPACE_NAME", lambda wt: wt.workspace.dir.name),
    ("GIT_WORKSPACE_BIN", lambda wt: str(wt.workspace.paths.bin)),
    ("GIT_WORKSPACE_ASSETS", lambda wt: str(wt.workspace.paths.assets)),
    ("GIT_WORKSPACE_WORKTREE", lambda wt: str(wt.dir)),
    ("GIT_WORKSPACE_CACHE_DIR", lambda wt: str(wt.workspace.paths.cache)),
)

BASE_VAR_KEYS: frozenset[str] = frozenset(key for key, _ in _BASE_VAR_BUILDERS)

VAR_PREFIX = "GIT_WORKSPACE_VAR_"
FINGERPRINT_VAR_PREFIX = "GIT_WORKSPACE_FINGERPRINT_"


def _vars(worktree: Worktree, runtime_vars: dict[str, str] | None) -> dict[str, str]:
    manifest_vars = worktree.workspace.manifest.vars or {}
    runtime_vars = runtime_vars or {}

    return {**manifest_vars, **runtime_vars}


def build_env(
    worktree: Worktree,
    runtime_vars: dict[str, str] | None = None,
    fingerprint_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Build the environment dict for hook and exec invocations within a worktree.

    Starts from the current process environment and layers in ``GIT_WORKSPACE_*``
    variables. Each key in ``vars`` is normalized to uppercase with
    non-alphanumeric characters replaced by underscores and exposed as
    ``GIT_WORKSPACE_VAR_<NORMALIZED_KEY>``. Each key in ``fingerprint_vars``
    is similarly normalized and exposed as ``GIT_WORKSPACE_FINGERPRINT_<NORMALIZED_KEY>``.

    :param worktree: The worktree for which the environment is being built.
    :param runtime_vars: Runtime variables to expose as ``GIT_WORKSPACE_VAR_*`` entries.
    :param fingerprint_vars: Pre-computed fingerprints keyed by raw name to expose
        as ``GIT_WORKSPACE_FINGERPRINT_*`` entries.
    :returns: A copy of the current process environment with all ``GIT_WORKSPACE_*`` keys set.
    """
    env = {
        **os.environ,
        **{key: builder(worktree) for key, builder in _BASE_VAR_BUILDERS},
    }

    for key, value in _vars(worktree, runtime_vars).items():
        normalized = normalize_variable_name(key)
        env[f"{VAR_PREFIX}{normalized}"] = str(value)

    for key, value in (fingerprint_vars or {}).items():
        normalized = normalize_variable_name(key)
        env[f"{FINGERPRINT_VAR_PREFIX}{normalized}"] = str(value)

    return env
