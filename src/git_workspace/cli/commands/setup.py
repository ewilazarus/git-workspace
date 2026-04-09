from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars

app = typer.Typer()


@app.command()
def setup(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The target git branch to be activated in the workspace. If ommited, the target git branch will be inferred from the current working directory",
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
    """
    Ensure a worktree exists and run its setup steps.

    Ensures that a worktree exists for the given branch. If the worktree does not exist, it is created first.

    Once the worktree is available, configured setup hooks are executed. These hooks can be used to install dependencies, initialize the environment, or run any other project-specific setup logic.

    In most cases, you should use `git-workspace up`, which will run this command automatically when needed.

    Use `setup` when you want to explicitly create a worktree or rerun its setup steps.
    """
    print(vars)
    pass
