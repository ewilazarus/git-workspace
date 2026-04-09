import typer

app = typer.Typer()


@app.command("ls")
def list(
    root: str | None = None,
) -> None:
    """
    List workspace worktrees.

    Displays the worktrees currently managed by the workspace, including their associated branches and locations. This provides visibility into which branch workspaces exist and are available for use.

    Use this to inspect the current state of the workspace.
    """
    pass
