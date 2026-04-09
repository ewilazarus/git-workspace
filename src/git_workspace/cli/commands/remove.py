from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars

app = typer.Typer()


@app.command("rm")
def remove(
    branch: str | None = None,
    root: str | None = None,
    force: bool = False,
    vars: Annotated[
        list[str] | None,
        typer.Option(
            "-v",
            "--var",
            help="A variable that will be forwarded to the workspace's hook scripts. May be specified multiple times",
            callback=parse_vars,
        ),
    ] = None,
    skip_hooks: Annotated[
        bool,
        typer.Option(
            help="Skip execution of workspace hooks",
        ),
    ] = False,
) -> None:
    """
    Remove a workspace worktree.

    Removes a specific worktree associated with a branch from the workspace. This deletes the local workspace for that branch but does not affect the underlying repository or remote branches.

    Use this to manually clean up a branch workspace you no longer need.
    """
    pass
