from git_workspace.hooks import HookRunner
from git_workspace.assets import Linker
from git_workspace.workspace import Workspace
from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    GitWorkspaceError,
)

app = typer.Typer()


@app.command()
def up(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The target git branch to be activated in the workspace",
        ),
    ] = None,
    base_branch: Annotated[
        str | None,
        typer.Option(
            "-b",
            "--base",
            help="The base branch to use when creating a new branch. If omitted, defaults to the base branch defined in the workspace manifest",
        ),
    ] = None,
    workspace_directory: Annotated[
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
    detached: Annotated[
        bool,
        typer.Option(
            "--detached",
            "-d",
            help=(
                "Skip on_attach hooks after activation. "
                "Suitable for headless or agent workflows."
            ),
            is_flag=True,
        ),
    ] = False,
) -> None:
    """
    Open a worktree, setting it up first if needed.

    Ensures that a worktree exists for the target branch and then performs
    lightweight actions to enter or resume working in that workspace.

    If the worktree does not exist, on_setup hooks run first. On every
    invocation, on_activate hooks run. Unless --detached is passed,
    on_attach hooks also run — use --detached for headless or automated
    workflows.
    """
    try:
        workspace = Workspace.resolve(workspace_directory)
        worktree = workspace.resolve_or_create_worktree(branch, base_branch)

        hook_runner = HookRunner(
            workspace,
            worktree,
            runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        )

        if worktree.is_new:
            Linker(workspace, worktree).apply()
            hook_runner.run_on_setup_hooks()

        hook_runner.run_on_activate_hooks()

        if not detached:
            hook_runner.run_on_attach_hooks()
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
