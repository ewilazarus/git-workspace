from git_workspace.workspace import Workspace
from typing import Annotated

import typer

from git_workspace.errors import (
    GitWorkspaceError,
)

app = typer.Typer()


@app.command("ls")
def list(
    workspace_directory: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
) -> None:
    """
    List workspace worktrees.

    Displays the worktrees currently managed by the workspace, including their associated branches and locations. This provides visibility into which branch workspaces exist and are available for use.

    Use this to inspect the current state of the workspace.
    """
    try:
        workspace = Workspace.resolve(workspace_directory)
        worktrees = workspace.list_worktrees()

        # TODO we need to make this better (maybe use rich's tables?)
        typer.echo(worktrees)
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
