import typer

app = typer.Typer()


@app.command("rm")
def remove(
    branch: str | None = None,
    root: str | None = None,
    force: bool = False,
) -> None:
    """
    Remove a workspace worktree.

    Removes a specific worktree associated with a branch from the workspace. This deletes the local workspace for that branch but does not affect the underlying repository or remote branches.

    Use this to manually clean up a branch workspace you no longer need.
    """
    pass
