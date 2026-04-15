from typing import Annotated

import typer

from git_workspace.assets import Copier, IgnoreManager, Linker
from git_workspace.cli.parsers import parse_vars
from git_workspace.hooks import HookRunner
from git_workspace.ui import console, print_success, styled_branch
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def reset(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be reset. If omitted, the branch will be inferred from the current working directory.",
        ),
    ] = None,
    workspace_dir: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    runtime_vars: Annotated[
        list[str] | None,
        typer.Option(
            "-v",
            "--var",
            help="A variable that will be forwarded to the workspace's hook scripts. May be specified multiple times",
            callback=parse_vars,
        ),
    ] = None,
) -> None:
    """
    Reapply configuration and setup for a workspace worktree.

    Re-applies copies and links from the manifest, updates the managed
    ignore rules, and reruns setup hooks.

    Intended for repairing or refreshing an existing workspace when its
    state has drifted (e.g. missing dependencies, removed files, or
    updated configuration). Does not modify Git history, switch branches,
    or discard uncommitted changes.
    """
    workspace = Workspace.resolve(workspace_dir)
    worktree = workspace.resolve_worktree(branch)

    console.print(f"Resetting {styled_branch(worktree.branch)}")

    with IgnoreManager(workspace) as ignore:
        Copier(workspace, worktree, ignore).apply()
        Linker(workspace, worktree, ignore).apply()

    HookRunner(
        workspace,
        worktree,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
    ).run_on_setup_hooks()

    print_success("Done")
