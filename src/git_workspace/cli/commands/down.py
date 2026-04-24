from typing import Annotated

import typer

from git_workspace import operations
from git_workspace.cli.parsers import parse_vars
from git_workspace.ui import console, styled_branch
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def down(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be deactivated. If omitted, the branch will be inferred from the current working directory.",
        ),
    ] = None,
    workspace_dir: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    runtime_vars: Annotated[
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
    Deactivate a workspace worktree.

    Intended for use when leaving a workspace session cleanly, allowing
    any session-specific state to be torn down.
    """
    workspace = Workspace.resolve(workspace_dir)
    worktree = workspace.resolve_worktree(branch)

    console.print(f"Deactivating {styled_branch(worktree.branch)}")

    operations.deactivate_worktree(
        worktree,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
    )

    console.success("Done")
