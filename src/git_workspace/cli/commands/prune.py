from typing import Annotated

import typer

app = typer.Typer()


@app.command("prune")
def prune(
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    older_than_days: Annotated[
        int | None,
        typer.Option(
            "--older-than-days",
            help="Remove worktrees whose HEAD commit is older than this many days. Takes precedence over manifest configuration. Age is measured by commit timestamp, not worktree creation time.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Show what would be removed without removing anything (enabled by default)",
        ),
    ] = True,
) -> None:
    """
    Remove stale workspace worktrees based on HEAD commit age.

    This command identifies and removes worktrees whose HEAD commit is older than
    a specified threshold. It is intended to keep the workspace tidy by cleaning up
    long-inactive branches.
    """
    raise NotImplementedError
