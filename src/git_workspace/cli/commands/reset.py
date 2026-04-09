from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars

app = typer.Typer()


@app.command()
def reset(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be reset. If omitted, the branch will be inferred from the current working directory.",
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
    Reapply workspace configuration and setup for a branch worktree.

    This command re-syncs links, reapplies override behavior, updates the managed ignore rules, and reruns setup hooks as defined in `workspace.toml`.

    It is intended for repairing or refreshing an existing workspace when its state has drifted (e.g. missing dependencies, removed files, or updated configuration).

    This command does not modify Git history, switch branches, or discard uncommitted changes. It only restores the expected workspace state.
    """
    print(vars)
    pass
