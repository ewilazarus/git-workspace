from typing import Annotated

import typer

from git_workspace import workspace
from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    HookExecutionError,
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    WorkspaceLinkError,
    WorktreeNotFoundError,
)
from git_workspace.manifest import read_manifest

app = typer.Typer()


@app.command()
def reset(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose workspace should be reset. If omitted, the branch will be inferred from the current working directory.",
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
) -> None:
    """
    Reapply workspace configuration and setup for a branch worktree.

    This command re-syncs links, reapplies override behavior, updates the managed ignore rules, and reruns setup hooks as defined in `workspace.toml`.

    It is intended for repairing or refreshing an existing workspace when its state has drifted (e.g. missing dependencies, removed files, or updated configuration).

    This command does not modify Git history, switch branches, or discard uncommitted changes. It only restores the expected workspace state.
    """
    try:
        root_path = workspace.resolve_root_path(root)
    except (InvalidWorkspaceRootError, UnableToResolveWorkspaceRootError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    if branch is None:
        branch = workspace.resolve_branch(root_path)
        if branch is None:
            typer.echo(
                "error: branch could not be inferred from the current directory; provide it explicitly",
                err=True,
            )
            raise typer.Exit(1)

    try:
        worktree_path = workspace.find_worktree_path(branch, cwd=root_path)
    except WorktreeNotFoundError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    manifest = read_manifest(root_path / ".workspace" / "manifest.toml")
    user_vars: dict[str, str] = dict(vars) if vars else {}  # type: ignore

    try:
        workspace.setup_worktree(
            root=root_path,
            worktree_path=worktree_path,
            links=manifest.links,
            hooks=manifest.hooks,
            branch=branch,
            manifest_vars=manifest.vars,
            user_vars=user_vars,
            skip_hooks=skip_hooks,
        )
    except (WorkspaceLinkError, HookExecutionError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    typer.echo(str(worktree_path))
