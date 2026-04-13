from git_workspace.workspace import Workspace
from git_workspace.errors import (
    GitWorkspaceError,
)
from typing import Annotated

import click
import typer

app = typer.Typer()


@app.command()
def edit(
    workspace_dir: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
) -> None:
    """
    Open the repository's `.workspace` directory in the configured editor.

    This directory contains the workspace blueprint, including `workspace.toml`, hook scripts, and any linked or override files that define how branch workspaces are prepared and activated.

    The editor is resolved using standard environment variables (e.g. VISUAL or EDITOR). The command does not modify any files—it only launches the editor.
    """
    try:
        workspace = Workspace.resolve(workspace_dir)
        click.edit(
            filename=str(workspace.directory / ".workspace"),
        )
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
