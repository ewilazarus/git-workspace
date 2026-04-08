from pathlib import Path
from git_workspace.cli.parsers import parse_vars
from typing import Annotated
import typer

app = typer.Typer()


@app.command()
def setup(
    branch: Annotated[
        str,
        typer.Argument(
            help="The target git branch to be activated in the workspace",
        ),
    ],
    base_branch: Annotated[
        str | None,
        typer.Option(
            "-b",
            "--base",
            help="The base branch to use when creating a new branch. If omitted, defaults to the base branch defined in the workspace manifesto",
        ),
    ] = None,
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force/--no-force",
            help="A flag indicating whether to checkout a branch that's already in use.",
        ),
    ] = False,
    vars: Annotated[
        list[str] | None,
        typer.Option(
            "-v",
            "--var",
            help="A variable that will be forwarded to the workspace's hook scripts. May be specified multiple times",
            callback=parse_vars,
        ),
    ] = None,
) -> None:
    print(vars)
    pass
