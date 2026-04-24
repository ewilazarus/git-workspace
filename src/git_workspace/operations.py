from git_workspace.assets import Copier, IgnoreManager, Linker
from git_workspace.hooks import HookRunner
from git_workspace.workspace import Workspace
from git_workspace.worktree import Worktree


def _apply_assets(workspace: Workspace, worktree: Worktree) -> None:
    with IgnoreManager(workspace) as ignore:
        Copier(workspace, worktree, ignore).apply()
        Linker(workspace, worktree, ignore).apply()


def activate_worktree(
    workspace: Workspace,
    worktree: Worktree,
    runtime_vars: dict[str, str],
    *,
    detached: bool,
) -> None:
    if worktree.is_new:
        _apply_assets(workspace, worktree)

    with HookRunner(workspace, worktree, runtime_vars=runtime_vars) as hook_runner:
        if worktree.is_new:
            hook_runner.run_on_setup_hooks()

        hook_runner.run_on_activate_hooks()

        if not detached:
            hook_runner.run_on_attach_hooks()


def reset_worktree(
    workspace: Workspace,
    worktree: Worktree,
    runtime_vars: dict[str, str],
) -> None:
    _apply_assets(workspace, worktree)

    with HookRunner(workspace, worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_setup_hooks()


def deactivate_worktree(
    workspace: Workspace,
    worktree: Worktree,
    runtime_vars: dict[str, str],
) -> None:
    with HookRunner(workspace, worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_deactivate_hooks()


def remove_worktree(
    workspace: Workspace,
    worktree: Worktree,
    runtime_vars: dict[str, str],
    *,
    force: bool,
) -> None:
    with HookRunner(workspace, worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_deactivate_hooks()
        hook_runner.run_on_remove_hooks()

    worktree.delete(force)
