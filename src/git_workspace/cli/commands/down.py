import json
from typing import Annotated

import typer

from git_workspace import hooks, workspace
from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    HookExecutionError,
    InvalidWorkspaceRootError,
    UnableToResolveBranchError,
    UnableToResolveWorkspaceRootError,
    WorktreeNotFoundError,
)
from git_workspace.manifest import read_manifest

app = typer.Typer()


@app.command()
def down(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be deactivated. If omitted, the branch will be inferred from the current working directory.",
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
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Emit structured JSON output instead of human-readable text",
            is_flag=True,
        ),
    ] = False,
) -> None:
    """
    Deactivate a worktree, running on_deactivate hooks.

    Runs on_deactivate hooks for the target branch without removing the
    worktree. Intended for use when leaving a workspace session cleanly,
    allowing hooks to tear down any session-specific state.
    """
    try:
        root_path = workspace.resolve_root_path(root)
    except (InvalidWorkspaceRootError, UnableToResolveWorkspaceRootError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    try:
        branch = branch or workspace.resolve_branch(root_path)
    except UnableToResolveBranchError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    manifest = read_manifest(root_path / ".workspace" / "manifest.toml")
    user_vars: dict[str, str] = dict(vars) if vars else {}  # type: ignore

    try:
        worktree_path = workspace.find_worktree_path(branch, cwd=root_path)
    except WorktreeNotFoundError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    try:
        hooks.run_on_deactivate_hooks(
            root=root_path,
            worktree_path=worktree_path,
            hooks=manifest.hooks,
            branch=branch,
            manifest_vars=manifest.vars,
            user_vars=user_vars,
            skip_hooks=skip_hooks,
        )
    except HookExecutionError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "branch": branch,
                    "path": str(worktree_path),
                }
            )
        )
    else:
        typer.echo(str(worktree_path))
