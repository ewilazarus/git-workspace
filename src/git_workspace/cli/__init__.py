import typer

from git_workspace.cli.callbacks import callback
from git_workspace.cli.commands import (
    cache_command,
    clone_command,
    doctor_command,
    down_command,
    edit_command,
    init_command,
    list_command,
    prune_command,
    remove_command,
    reset_command,
    up_command,
)

app = typer.Typer(
    no_args_is_help=True,
    callback=callback,
    help="""
    Manage isolated git worktrees for a repository.

    A workspace consists of a shared bare repository and a set of per-branch worktrees, each with its own local environment and configuration.

    The primary command is `up`, which spawns a git worktree, setting it up first if needed.

    ⧉  https://github.com/ewilazarus/git-workspace
    """,
)

app.add_typer(cache_command, name="cache")
app.add_typer(clone_command)
app.add_typer(doctor_command)
app.add_typer(down_command)
app.add_typer(edit_command)
app.add_typer(init_command)
app.add_typer(list_command)
app.add_typer(prune_command)
app.add_typer(remove_command)
app.add_typer(reset_command)
app.add_typer(up_command)
