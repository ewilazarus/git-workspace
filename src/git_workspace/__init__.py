import typer
from git_workspace.errors import GitWorkspaceError
from git_workspace import cli
from git_workspace.ui import print_error


def main() -> None:
    try:
        cli.app()
    except GitWorkspaceError as e:
        print_error(str(e))
        raise typer.Exit(
            code=1
        ) from e  # TODO keep this reraise until a more stable error system
