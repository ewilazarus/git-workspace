from dataclasses import dataclass
from importlib.metadata import version
from typing import Annotated

import typer

from git_workspace.ui import console


@dataclass
class Context:
    workspace_dir: str | None


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("git-workspace-cli"))
        raise typer.Exit()


def callback(
    ctx: typer.Context,
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
    Root Typer callback for the CLI.

    Applies global options and performs early actions (e.g., version display) before command execution.
    """
    console.configure(plain)

    if workspace_dir is not None and ctx.invoked_subcommand in {"cache", "clone", "init"}:
        console.warning(
            f"-r/--root is not needed for '{ctx.invoked_subcommand}' and will be ignored."
        )

    ctx.obj = Context(workspace_dir)
