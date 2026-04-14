from git_workspace.workspace import Workspace
from git_workspace.ui import console, print_success, styled_path
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def init(
    workspace_dir: Annotated[
        str | None,
        "directory",
        typer.Argument(
            help="The directory in which to initialize the workspace. If ommitted, will default to the current working directory"
        ),
    ] = None,
    config_url: Annotated[
        str | None,
        typer.Option(
            help="The configuration URL to be cloned. If ommitted, uses the default configuration"
        ),
    ] = None,
    output: Annotated[
        bool,
        typer.Option(
            "-o",
            "--output",
            is_flag=True,
            help="Print the workspace root path to stdout and suppress all other output.",
        ),
    ] = False,
) -> None:
    """
    Initialize a repository in workspace format.

    Creates a new workspace root for a repository that does not yet exist remotely. A bare repository is initialized under .git, and a configuration directory is created under .workspace.

    Use this when starting a new project from scratch using the workspace model.
    """
    console.print("Initialising workspace...")
    workspace = Workspace.init(workspace_dir, config_url)
    print_success(f"Workspace ready at {styled_path(workspace.directory)}")

    if output:
        typer.echo(str(workspace.directory))
