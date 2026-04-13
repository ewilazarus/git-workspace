from git_workspace.workspace import Workspace
from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def clone(
    url: Annotated[
        str,
        typer.Argument(
            help="The repository URL to be cloned",
        ),
    ],
    workspace_dir: Annotated[
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
    Workspace.clone(workspace_dir, url, config_url)
