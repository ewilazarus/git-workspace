from pathlib import Path
from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.ui import console, styled_path
from git_workspace.workspace import Workspace
from git_workspace.workspace.core import WorkspaceResolver
from git_workspace.workspace.models import ProviderKind
from git_workspace.workspace.service import WorkspaceService

app = typer.Typer()


@app.command()
def prepare(
    ctx: typer.Context,
    path: Annotated[
        str | None,
        typer.Argument(
            help="Path to the worktree to prepare. Defaults to the current working directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force/--no-force",
            help="Re-run preparation even if the worktree is already prepared",
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
    Prepare an existing worktree.

    Applies copies and links from the manifest and runs on_setup hooks for a worktree that already exists — regardless of which tool created it. Works from any path inside the worktree, including worktrees created directly with `git worktree add` or by external tools.

    Skips preparation when the worktree is already prepared; pass --force to re-run it. Never creates a worktree, never runs on_attach hooks, and is safe to retry after a failure.
    """
    target = (Path(path) if path else Path.cwd()).expanduser().resolve()

    if ctx.obj.workspace_dir is not None:
        workspace = Workspace.resolve(ctx.obj.workspace_dir)
    else:
        workspace = WorkspaceResolver.resolve_from_worktree(target)

    console.print(f"Preparing {styled_path(target)}")

    # Preparation must work anywhere (CI, external hosts) with git alone, so
    # the import step is pinned to the native provider regardless of backend.
    service = WorkspaceService.create(workspace, provider_kind=ProviderKind.NATIVE_GIT)
    outcome = service.prepare_path(
        target,
        force=force,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        effective_branch=effective_branch,
    )

    if outcome.skipped:
        console.success("Already prepared (use --force to re-run setup)")
    else:
        console.success("Done")
