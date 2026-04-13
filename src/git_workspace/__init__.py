import typer
from git_workspace.errors import GitWorkspaceError
from git_workspace import cli


def main() -> None:
    try:
        cli.app()
    except GitWorkspaceError as e:
        typer.echo(f"ERROR: {e}")
        raise  # TODO remove when we get a more stable error system
