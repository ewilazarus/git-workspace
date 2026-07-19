from typing import Annotated

import typer

from git_workspace.cli.parsers import parse_vars
from git_workspace.ui import console, styled_branch, styled_path
from git_workspace.workspace import Workspace
from git_workspace.workspace.models import PresenterKind, ProviderKind
from git_workspace.workspace.service import WorkspaceService
from git_workspace.workspace.worktree import Worktree

app = typer.Typer()


@app.command()
def up(
    ctx: typer.Context,
    branch: Annotated[
        str | None,
        typer.Argument(
            help="The target git branch to be activated in the workspace",
        ),
    ] = None,
    base_branch: Annotated[
        str | None,
        typer.Option(
            "-b",
            "--base",
            help="The base branch to use when creating a new branch. If omitted, defaults to the base branch defined in the workspace manifest",
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
    detached: Annotated[
        bool,
        typer.Option(
            "--detached/--no-detached",
            "-d",
            help=(
                "Skip on_attach hooks after activation. Suitable for headless or agent workflows."
            ),
        ),
    ] = False,
    effective_branch: Annotated[
        str | None,
        typer.Option(
            "-a",
            "--as",
            help="Treat the worktree as if it were on this branch when evaluating hook conditions. Does not change the actual branch or GIT_WORKSPACE_BRANCH.",
        ),
    ] = None,
    output: Annotated[
        bool,
        typer.Option(
            "--output/--no-output",
            "-o",
            help="Print the worktree path to stdout and suppress all other output.",
        ),
    ] = False,
    backend: Annotated[
        str | None,
        typer.Option(
            "--backend",
            help="Backend preset to use: native, herdr, or auto (verified environment detection). Overrides the manifest's [workspace] configuration.",
        ),
    ] = None,
    provider: Annotated[
        ProviderKind | None,
        typer.Option(
            "--provider",
            help="Explicit worktree provider; overrides the backend preset's provider.",
        ),
    ] = None,
    presenter: Annotated[
        PresenterKind | None,
        typer.Option(
            "--presenter",
            help="Explicit workspace presenter; overrides the backend preset's presenter.",
        ),
    ] = None,
    focus: Annotated[
        bool,
        typer.Option(
            "--focus/--no-focus",
            help="Focus the workspace presentation after activation (when the backend has a presenter).",
        ),
    ] = True,
) -> None:
    """
    Spawns a worktree, setting it up first if needed.

    Ensures that a worktree exists for the target branch and then performs lightweight actions to enter or resume working in that workspace.

    If the worktree does not exist, copies and links from the manifest are applied first, followed by on_setup hooks. Unless --detached is passed, on_attach hooks also run — use --detached for headless or automated workflows.
    """
    workspace = Workspace.resolve(ctx.obj.workspace_dir)
    if branch is None:
        branch = Worktree.resolve(workspace, None).branch

    console.print(f"Activating {styled_branch(branch)}")

    service = WorkspaceService.create(
        workspace,
        backend_name=backend,
        provider_kind=provider,
        presenter_kind=presenter,
    )
    worktree = service.up(
        branch,
        base_branch=base_branch,
        runtime_vars=dict(runtime_vars or []),  # ty:ignore[no-matching-overload]
        detached=detached,
        effective_branch=effective_branch,
        focus=focus,
    )

    console.success(f"Worktree ready at {styled_path(worktree.dir)}")

    if output:
        typer.echo(str(worktree.dir))
