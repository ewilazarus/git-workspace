from importlib.metadata import version
from typing import Annotated

import typer

from git_workspace.ui import console


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("git-workspace-cli"))
        raise typer.Exit()


def callback(
    plain: Annotated[
        bool,
        typer.Option("--plain", help="Disable Rich output and print plain text instead"),
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit",
        ),
    ] = False,
) -> None:
    """
    Root Typer callback for the CLI.

    Applies global options and performs early actions (e.g., version display) before command execution.
    """
    console.configure(plain)
