from git_workspace.workspace import Workspace
from typing import Annotated

import typer

from git_workspace.errors import GitWorkspaceError

app = typer.Typer()


@app.command()
def clone(
    url: Annotated[
        str,
        typer.Argument(
            help="The repository URL to be cloned",
        ),
    ],
    workspace_directory: Annotated[
        str | None,
        typer.Argument(
            help='An optional name of the directory to be used. If omitted, the "humanish" part of the repository URL will be used'
        ),
    ] = None,
    config_url: Annotated[
        str | None,
        typer.Option(
            help="The configuration URL to be cloned. If ommitted, uses the default configuration"
        ),
    ] = None,
) -> None:
    """
    Clone a repository into workspace format.

    Creates a new workspace root from a remote repository. The repository is cloned as a bare repository under .git, and a configuration repository is initialized under .workspace. This establishes the workspace structure required for managing branch worktrees.

    Use this when starting from an existing remote repository.
    """
    try:
        Workspace.clone(workspace_directory, url, config_url)
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO: When code is ready remove this raise
