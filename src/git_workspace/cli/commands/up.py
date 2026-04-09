from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars

app = typer.Typer()


@app.command()
def up(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The target git branch to be activated in the workspace",
        ),
    ] = None,
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
            help="A flag indicating whether to checkout a branch that's already in use",
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
    skip_hooks: Annotated[
        bool,
        typer.Option(
            help="Skip execution of workspace hooks",
        ),
    ] = False,
) -> None:
    """
    Open a worktree, setting it up first if needed.

    Ensures that a worktree exists for the target branch and then performs lightweight actions to enter or resume working in that workspace (for example, opening a session, editor, or environment).

    If the worktree does not exist, setup is executed first. If it already exists, only the lightweight activation steps are performed.

    This is the primary command for day-to-day usage.
    """
    print(vars)
    pass
