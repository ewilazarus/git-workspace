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
            help="The base branch to use when creating a new branch. If omitted, defaults to the base branch defined in the workspace manifest",
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
    attach: Annotated[
        bool,
        typer.Option(
            "--attached/--detached",
            "-a/-d",
            help=(
                "Control whether on_attach hooks run after activation. "
                "--attached (default) runs on_attach hooks, intended for interactive sessions. "
                "--detached skips on_attach hooks, suitable for headless or agent workflows."
            ),
        ),
    ] = True,
    skip_hooks: Annotated[
        bool,
        typer.Option(
            help="Skip execution of all workspace hooks",
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

    Ensures that a worktree exists for the target branch and then performs
    lightweight actions to enter or resume working in that workspace.

    If the worktree does not exist, on_setup hooks run first. On every
    invocation, on_activate hooks run. In attached mode (default),
    on_attach hooks also run — use --detached to suppress them for
    headless or automated workflows.
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

    plan = resolve_up_plan(
        branch=branch,
        explicit_base_branch=base_branch,
        manifest_base_branch=manifest.base_branch,
        cwd=root_path,
    )

    try:
        if plan.action == UpAction.RESUME:
            assert plan.existing_worktree_path is not None
            result = resume_worktree(plan.existing_worktree_path)
        elif plan.action == UpAction.CREATE_FROM_LOCAL:
            result = create_worktree_from_local(root_path, branch, cwd=root_path)
        elif plan.action == UpAction.CREATE_FROM_REMOTE:
            result = create_worktree_from_remote(root_path, branch, cwd=root_path)
        else:
            assert plan.base_branch is not None
            result = create_worktree_from_base(
                root_path, branch, plan.base_branch, cwd=root_path
            )
    except WorktreeCreationError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    if result.is_new:
        try:
            workspace.setup_worktree(
                root=root_path,
                worktree_path=result.path,
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

    try:
        hooks.run_on_activate_hooks(
            root=root_path,
            worktree_path=result.path,
            hooks=manifest.hooks,
            branch=branch,
            manifest_vars=manifest.vars,
            user_vars=user_vars,
            skip_hooks=skip_hooks,
        )
        if attach:
            hooks.run_on_attach_hooks(
                root=root_path,
                worktree_path=result.path,
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
                    "attached": attach,
                }
            )
        )
    else:
        typer.echo(str(result.path))
