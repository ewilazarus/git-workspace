import subprocess
from typing import Annotated

import typer

from git_workspace import operations
from git_workspace.env import build_env
from git_workspace.errors import InvalidInputError, WorktreeResolutionError
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command(
    "exec",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def exec_cmd(
    branch: Annotated[
        str,
        typer.Argument(
            help="The branch whose worktree should run the command.",
        ),
    ],
    ctx: typer.Context,
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
            "-f",
            is_flag=True,
            help="Create the worktree without prompting if it does not exist.",
        ),
    ] = False,
) -> None:
    """
    Run an arbitrary command inside a worktree.

    If the worktree for BRANCH does not exist, prompts to create it first
    (equivalent to `up --detached`). Use --force to skip the prompt.
    """
    command = ctx.args
    if not command:
        raise InvalidInputError(
            "No command provided. Use: git-workspace exec <BRANCH> -- <COMMAND>"
        )

    workspace = Workspace.resolve(workspace_dir)

    try:
        worktree = (
            workspace.resolve_or_create_worktree(branch, None)
            if force
            else workspace.resolve_worktree(branch)
        )
    except WorktreeResolutionError:
        if typer.confirm(
            f"Worktree for branch {branch!r} does not exist. Create it?",
            default=False,
        ):
            worktree = workspace.resolve_or_create_worktree(branch, None)
        else:
            raise

    if worktree.is_new:
        operations.activate_worktree(workspace, worktree, runtime_vars={}, detached=True)

    result = subprocess.run(command, cwd=worktree.dir, env=build_env(workspace, worktree))
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
