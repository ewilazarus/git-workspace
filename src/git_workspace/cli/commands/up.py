import json
from typing import Annotated

import typer

from git_workspace import workspace
from git_workspace.cli.parsers import parse_vars
from git_workspace.errors import (
    HookExecutionError,
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    WorkspaceLinkError,
    WorktreeCreationError,
)
from git_workspace.manifest import read_manifest
from git_workspace.worktree import (
    UpAction,
    create_worktree_from_base,
    create_worktree_from_local,
    create_worktree_from_remote,
    resolve_up_plan,
    resume_worktree,
)

app = typer.Typer()


@app.command()
def up(
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
            help="The base branch to use when creating a new branch. If omitted, defaults to the base branch defined in the workspace manifesto",
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
    Open a worktree, setting it up first if needed.

    Ensures that a worktree exists for the target branch and then performs lightweight actions to enter or resume working in that workspace (for example, opening a session, editor, or environment).

    If the worktree does not exist, setup is executed first. If it already exists, only the lightweight activation steps are performed.

    This is the primary command for day-to-day usage.
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

    manifest = read_manifest(root_path / ".workspace" / "manifest.toml")
    user_vars: dict[str, str] = dict(vars) if vars else {}  # type: ignore

    plan = resolve_up_plan(
        branch=branch,
        explicit_base_branch=base_branch,
        manifest_base_branch=manifest.base_branch,
    )

    try:
        if plan.action == UpAction.RESUME:
            assert plan.existing_worktree_path is not None
            result = resume_worktree(plan.existing_worktree_path)
        elif plan.action == UpAction.CREATE_FROM_LOCAL:
            result = create_worktree_from_local(root_path, branch)
        elif plan.action == UpAction.CREATE_FROM_REMOTE:
            result = create_worktree_from_remote(root_path, branch)
        else:
            assert plan.base_branch is not None
            result = create_worktree_from_base(root_path, branch, plan.base_branch)
    except WorktreeCreationError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    try:
        workspace.apply_links(root_path, result.path, manifest.links)
    except WorkspaceLinkError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    non_override_targets = [link.target for link in manifest.links if not link.override]
    workspace.sync_exclude_block(result.path, non_override_targets)

    try:
        workspace.run_setup_hooks(
            root=root_path,
            worktree_result=result,
            hooks=manifest.hooks,
            branch=branch,
            manifest_vars=manifest.vars,
            user_vars=user_vars,
            skip_hooks=skip_hooks,
        )
        workspace.run_activation_hooks(
            root=root_path,
            worktree_result=result,
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
                    "path": str(result.path),
                    "is_new": result.is_new,
                }
            )
        )
    else:
        typer.echo(str(result.path))
