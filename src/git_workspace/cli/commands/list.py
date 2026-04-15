from typing import Annotated

import typer
from rich.table import Table

from git_workspace.ui import console
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command("ls")
def list(
    workspace_dir: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
) -> None:
    """
    List workspace worktrees.

    Displays the worktrees currently managed by the workspace, including their associated branches and locations. This provides visibility into which branch workspaces exist and are available for use.

    Use this to inspect the current state of the workspace.
    """
    workspace = Workspace.resolve(workspace_dir)
    worktrees = workspace.list_worktrees()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Branch", style="branch", no_wrap=True)
    table.add_column("Path", style="path")
    table.add_column("Age", style="dim", no_wrap=True)

    for worktree in sorted(worktrees, key=lambda w: (w.age_days, w.branch)):
        age = f"{worktree.age_days}d"
        table.add_row(worktree.branch, str(worktree.dir), age)

    console.print(table)
