from git_workspace.hooks import HookRunner
from git_workspace.workspace import Workspace
from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    GitWorkspaceError,
)

app = typer.Typer()


@app.command("rm")
def remove(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose worktree should be removed. If omitted, the branch will be inferred from the current working directory.",
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
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Remove the worktree even if it has uncommitted changes",
            is_flag=True,
        ),
    ] = False,
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
    Remove a workspace worktree.

    Removes the worktree for the target branch without deleting the branch itself. The branch remains available and a new worktree can be created with `git workspace up <branch>`.

    Refuses removal if the worktree has uncommitted changes unless --force is passed.

    This command does not modify Git history or delete any branch.
    """
    try:
        workspace = Workspace.resolve(workspace_directory)
        worktree = workspace.resolve_worktree(branch)

        hook_runner = HookRunner(
            workspace,
            worktree,
            runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        )

        hook_runner.run_on_deactivate_hooks()
        hook_runner.run_on_remove_hooks()

        worktree.delete(force)
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
