from pathlib import Path
from typing import Annotated

import typer

from git_workspace import workspace

app = typer.Typer()


@app.command()
def init(
    path: Annotated[
        str, typer.Argument(help="The path in which to init the workspace")
    ],
    config_url: Annotated[
        str | None,
        typer.Option(
            help="The configuration URL to be cloned. If ommitted, defaults to the example configuration URL",
        ),
    ] = None,
) -> None:
    """
    Initialize a repository in workspace format.

    Creates a new workspace root for a repository that does not yet exist remotely. A bare repository is initialized under .git, and a configuration directory is created under .workspace.

    Use this when starting a new project from scratch using the workspace model.
    """
    resolved_path = Path(path)
    workspace.create(resolved_path, config_url=config_url)
