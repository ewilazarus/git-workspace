from typing import Annotated

import typer

from git_workspace import git, workspace
from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    HookExecutionError,
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    WorktreeDirtyError,
    WorktreeNotFoundError,
    WorktreeRemovalError,
)
from git_workspace.manifest import read_manifest

app = typer.Typer()


@app.command("rm")
def remove(
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The branch whose worktree should be removed. If omitted, the branch will be inferred from the current working directory.",
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
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Remove the worktree even if it has uncommitted changes",
        ),
    ] = False,
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
    Remove a workspace worktree.

    Removes the worktree for the target branch without deleting the branch itself. The branch remains available and a new worktree can be created with `git workspace up <branch>`.

    Refuses removal if the worktree has uncommitted changes unless --force is passed.

    This command does not modify Git history or delete any branch.
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
        worktree_path = workspace.find_worktree_path(branch)
    except WorktreeNotFoundError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    if not force and git.is_worktree_dirty(worktree_path):
        typer.echo(
            f"error: worktree for {branch!r} at {worktree_path} has uncommitted changes; "
            "commit or stash them, or pass --force to remove anyway",
            err=True,
        )
        raise typer.Exit(1)

    manifest = read_manifest(root_path / ".workspace" / "manifest.toml")
    user_vars: dict[str, str] = dict(vars) if vars else {}  # type: ignore

    try:
        workspace.run_before_remove_hooks(
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

    try:
        git.remove_worktree(worktree_path, force=force)
    except WorktreeRemovalError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    try:
        workspace.run_after_remove_hooks(
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

    typer.echo(f"Removed worktree for {branch!r} (branch preserved)")
