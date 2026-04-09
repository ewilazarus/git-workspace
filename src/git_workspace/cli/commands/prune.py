import typer

app = typer.Typer()


@app.command()
def prune(
    root: str | None = None,
) -> None:
    """
    Remove stale workspace worktrees.

    Removes multiple worktrees that are considered stale based on workspace rules (for example, worktrees that are no longer referenced, inactive, or otherwise eligible for cleanup).

    This is a batch cleanup operation intended to keep the workspace tidy.

    Use this when you want to clean up unused worktrees efficiently.
    """
    pass
