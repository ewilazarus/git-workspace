from typing import Annotated

import typer

from git_workspace import workspace, worktrees
from git_workspace.errors import (
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
)

app = typer.Typer()


@app.command("ls")
def list(
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit structured JSON output instead of human-readable text",
            is_flag=True,
        ),
    ] = False,
) -> None:
    """
    List workspace worktrees.

    Displays the worktrees currently managed by the workspace, including their associated branches and locations. This provides visibility into which branch workspaces exist and are available for use.

    Use this to inspect the current state of the workspace.
    """
    try:
        root_path = workspace.resolve_root_path(root)
    except (InvalidWorkspaceRootError, UnableToResolveWorkspaceRootError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    wt_list = worktrees.list_worktrees(root_path)

    if json_output:
        typer.echo(worktrees.format_json(wt_list))
    else:
        typer.echo(worktrees.format_table(wt_list))
