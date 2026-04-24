from git_workspace.assets import Copier, IgnoreManager, Linker
from git_workspace.hooks import HookRunner
from git_workspace.worktree import Worktree


def _apply_assets(worktree: Worktree) -> None:
    with IgnoreManager(worktree) as ignore:
        Copier(worktree, ignore).apply()
        Linker(worktree, ignore).apply()


def activate_worktree(
    worktree: Worktree,
    runtime_vars: dict[str, str],
    *,
    detached: bool,
) -> None:
    """
    Apply assets and run setup/attach hooks when entering a worktree.

    For new worktrees, assets are applied first and then ``on_setup`` hooks are
    run. If ``detached`` is ``False``, ``on_attach`` hooks are also run.

    :param worktree: The worktree being activated.
    :param runtime_vars: Extra variables to inject into the hook environment.
    :param detached: If ``True``, ``on_attach`` hooks are skipped.
    """
    if worktree.is_new:
        _apply_assets(worktree)

    with HookRunner(worktree, runtime_vars=runtime_vars) as hook_runner:
        if worktree.is_new:
            hook_runner.run_on_setup_hooks()

        if not detached:
            hook_runner.run_on_attach_hooks()


def reset_worktree(
    worktree: Worktree,
    runtime_vars: dict[str, str],
) -> None:
    """
    Re-apply assets and re-run ``on_setup`` hooks for an existing worktree.

    :param worktree: The worktree being reset.
    :param runtime_vars: Extra variables to inject into the hook environment.
    """
    _apply_assets(worktree)

    with HookRunner(worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_setup_hooks()


def deactivate_worktree(
    worktree: Worktree,
    runtime_vars: dict[str, str],
) -> None:
    """
    Run ``on_detach`` hooks when leaving a worktree without removing it.

    :param worktree: The worktree being deactivated.
    :param runtime_vars: Extra variables to inject into the hook environment.
    """
    with HookRunner(worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_detach_hooks()


def remove_worktree(
    worktree: Worktree,
    runtime_vars: dict[str, str],
    *,
    force: bool,
) -> None:
    """
    Run detach and teardown hooks, then delete the worktree.

    Runs ``on_detach`` hooks first, then ``on_teardown`` hooks, and finally
    removes the worktree directory.

    :param worktree: The worktree to remove.
    :param runtime_vars: Extra variables to inject into the hook environment.
    :param force: If ``True``, passes ``--force`` to the underlying ``git worktree remove`` call.
    """
    with HookRunner(worktree, runtime_vars=runtime_vars) as hook_runner:
        hook_runner.run_on_detach_hooks()
        hook_runner.run_on_teardown_hooks()

    worktree.delete(force)
