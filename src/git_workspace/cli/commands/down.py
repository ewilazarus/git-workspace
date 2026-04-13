from git_workspace.workspace import Workspace
from git_workspace.hooks import HookRunner
from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    GitWorkspaceError,
)

app = typer.Typer()


@app.command()
def down(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be deactivated. If omitted, the branch will be inferred from the current working directory.",
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
    Deactivate a workspace worktree.

    Intended for use when leaving a workspace session cleanly, allowing
    any session-specific state to be torn down.
    """
    try:
        workspace = Workspace.resolve(workspace_dir)
        worktree = workspace.resolve_worktree(branch)

        HookRunner(
            workspace,
            worktree,
            runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        ).run_on_deactivate_hooks()
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
