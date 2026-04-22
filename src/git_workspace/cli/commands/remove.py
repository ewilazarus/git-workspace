from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.hooks import HookRunner
from git_workspace.ui import console, styled_branch
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command("rm")
def remove(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose worktree should be removed. If omitted, the branch will be inferred from the current working directory.",
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
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Remove the worktree even if it has uncommitted changes",
            is_flag=True,
        ),
    ] = False,
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
    Remove a workspace worktree.

    Removes the worktree for the target branch without deleting the branch itself. The branch remains available and a new worktree can be created with `git workspace up <branch>`.

    Refuses removal if the worktree has uncommitted changes unless --force is passed.

    This command does not modify Git history or delete any branch.
    """
    workspace = Workspace.resolve(workspace_dir)
    worktree = workspace.resolve_worktree(branch)

    console.print(f"Removing {styled_branch(worktree.branch)}")

    with HookRunner(
        workspace,
        worktree,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
    ) as runner:
        runner.run_on_deactivate_hooks()
        runner.run_on_remove_hooks()

    worktree.delete(force)

    console.success("Done")
