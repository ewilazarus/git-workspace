from typing import Annotated

import typer

from git_workspace import operations
from git_workspace.cli.parsers import parse_vars
from git_workspace.ui import console, styled_branch
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def reset(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be reset. If omitted, the branch will be inferred from the current working directory.",
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
    effective_branch: Annotated[
        str | None,
        typer.Option(
            "-a",
            "--as",
            help="Treat the worktree as if it were on this branch when evaluating hook conditions. Does not change the actual branch or GIT_WORKSPACE_BRANCH.",
        ),
    ] = None,
) -> None:
    """
    Reapply configuration and setup for a workspace worktree.

    Re-applies copies and links from the manifest, updates the managed ignore rules, and reruns setup hooks.

    Intended for repairing or refreshing an existing workspace when its state has drifted (e.g. missing dependencies, removed files, or updated configuration). Does not modify Git history, switch branches, or discard uncommitted changes.
    """
    workspace = Workspace.resolve(workspace_dir)
    worktree = workspace.resolve_worktree(branch)

    console.print(f"Resetting {styled_branch(worktree.branch)}")

    operations.reset_worktree(
        worktree,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        effective_branch=effective_branch,
    )

    console.success("Done")
