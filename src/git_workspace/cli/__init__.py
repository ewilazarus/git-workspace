from importlib.metadata import version
from typing import Annotated

import typer

from git_workspace.cli.commands.clone import app as clone_command
from git_workspace.cli.commands.doctor import app as doctor_command
from git_workspace.cli.commands.down import app as down_command
from git_workspace.cli.commands.edit import app as edit_command
from git_workspace.cli.commands.exec import app as exec_command
from git_workspace.cli.commands.init import app as init_command
from git_workspace.cli.commands.list import app as list_command
from git_workspace.cli.commands.prune import app as prune_command
from git_workspace.cli.commands.remove import app as remove_command
from git_workspace.cli.commands.reset import app as reset_command
from git_workspace.cli.commands.root import app as root_command
from git_workspace.cli.commands.up import app as up_command
from git_workspace.ui import console

HELP = """
Manage isolated git worktrees for a repository.

A workspace consists of a shared bare repository and a set of per-branch worktrees, each with its own local environment and configuration.

The primary command is `up`, which spawns a git worktree, setting it up first if needed.

⧉  https://github.com/ewilazarus/git-workspace
"""

app = typer.Typer(help=HELP, no_args_is_help=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(version("git-workspace-cli"))
        raise typer.Exit()


@app.callback()
def _callback(
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
    console.configure(plain)


app.add_typer(clone_command)
app.add_typer(doctor_command)
app.add_typer(down_command)
app.add_typer(edit_command)
app.add_typer(exec_command)
app.add_typer(init_command)
app.add_typer(list_command)
app.add_typer(prune_command)
app.add_typer(remove_command)
app.add_typer(reset_command)
app.add_typer(root_command)
app.add_typer(up_command)
