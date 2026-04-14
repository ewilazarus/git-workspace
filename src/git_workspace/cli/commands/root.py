import typer

from git_workspace.errors import InvalidWorkspaceError, UnableToResolveWorkspaceError
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def root() -> None:
    """
    Print the workspace root path if inside a workspace, exit 1 otherwise.

    Useful for agents and scripts to detect whether git workspace commands are
    available in the current directory before deciding to use them.
    """
    try:
        workspace = Workspace.resolve(None)
    except (InvalidWorkspaceError, UnableToResolveWorkspaceError):
        raise typer.Exit(code=1)

    typer.echo(str(workspace.directory))
