import os
from pathlib import Path
import re
import subprocess

import structlog

from git_workspace.errors import HookExecutionError
from git_workspace.manifest import Hooks

logger = structlog.get_logger(__name__)


def build_hook_env(
    branch: str,
    root: Path,
    worktree_path: Path,
    event: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Builds the environment dict for hook execution.

    Standard context vars (GIT_WORKSPACE_BRANCH, _ROOT, _WORKTREE, _EVENT) are always
    set. Manifest vars are applied next, then CLI user vars override them.
    All user-defined variable names are normalized to uppercase.

    :param branch: The target branch name
    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param event: The lifecycle event name (e.g. "on_setup", "on_activate")
    :param manifest_vars: Variables defined in the workspace manifest
    :param user_vars: Variables provided by the CLI, overriding manifest vars
    :returns: A merged environment dict suitable for passing to subprocess
    """
    env = {
        **os.environ,
        "GIT_WORKSPACE_BRANCH": branch,
        "GIT_WORKSPACE_BRANCH_NO_SLASH": branch.replace("/", "_"),
        "GIT_WORKSPACE_ROOT": str(root),
        "GIT_WORKSPACE_WORKTREE": str(worktree_path),
        "GIT_WORKSPACE_EVENT": event,
    }
    for key, value in (manifest_vars or {}).items():
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = value
    for key, value in (user_vars or {}).items():
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = value
    return env


def _run_hooks(
    root: Path,
    worktree_path: Path,
    hook_names: list[str],
    event: str,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
) -> None:
    log = logger.bind(event=event, worktree=str(worktree_path))

    if not hook_names:
        log.debug("No hooks to run")
        return

    bin_path = root / ".workspace" / "bin"
    env = build_hook_env(
        branch=branch,
        root=root,
        worktree_path=worktree_path,
        event=event,
        manifest_vars=manifest_vars,
        user_vars=user_vars,
    )

    for hook_name in hook_names:
        log.debug("Running hook", hook=hook_name)
        result = subprocess.run([str(bin_path / hook_name)], cwd=str(worktree_path), env=env)
        if result.returncode != 0:
            log.debug("Hook failed", hook=hook_name, exit_code=result.returncode)
            raise HookExecutionError(
                f"Hook {hook_name!r} failed with exit code {result.returncode}"
            )
        log.debug("Hook succeeded", hook=hook_name)


def run_on_setup_hooks(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_setup hooks for a worktree.

    Callers are responsible for deciding when this is appropriate (e.g. only
    for newly created worktrees in `up`, unconditionally in `reset`).

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_setup hooks: skip_hooks=True")
        return

    log.debug("Running on_setup hooks")
    _run_hooks(root, worktree_path, hooks.on_setup, "on_setup", branch, manifest_vars, user_vars)
    log.debug("on_setup hooks completed")


def run_on_activate_hooks(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_activate hooks on every up invocation (new and resumed).

    Suppressed only when skip_hooks is True.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_activate hooks: skip_hooks=True")
        return

    log.debug("Running on_activate hooks")
    _run_hooks(root, worktree_path, hooks.on_activate, "on_activate", branch, manifest_vars, user_vars)
    log.debug("on_activate hooks completed")


def run_on_attach_hooks(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_attach hooks when up is invoked in attached mode.

    Not called in detached mode. Suppressed by skip_hooks.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_attach hooks: skip_hooks=True")
        return

    log.debug("Running on_attach hooks")
    _run_hooks(root, worktree_path, hooks.on_attach, "on_attach", branch, manifest_vars, user_vars)
    log.debug("on_attach hooks completed")


def run_on_remove_hooks(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_remove hooks when a worktree is removed.

    Runs before the worktree is deleted so the hook can inspect its state.
    Hook failures abort removal — the worktree is not touched.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_remove hooks: skip_hooks=True")
        return

    log.debug("Running on_remove hooks")
    _run_hooks(root, worktree_path, hooks.on_remove, "on_remove", branch, manifest_vars, user_vars)
    log.debug("on_remove hooks completed")
