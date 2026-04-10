from typing import Annotated

import typer

from git_workspace import workspace
from git_workspace.manifest import read_manifest
from git_workspace.worktree import (
    select_prune_candidates,
    resolve_prune_threshold,
    list_worktrees,
)
from git_workspace.git import remove_worktree
from git_workspace.errors import (
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    WorktreeRemovalError,
)

app = typer.Typer()


@app.command("prune")
def prune(
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
    older_than_days: Annotated[
        int | None,
        typer.Option(
            "--older-than-days",
            help="Remove worktrees whose HEAD commit is older than this many days. Takes precedence over manifest configuration. Age is measured by commit timestamp, not worktree creation time.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Show what would be removed without removing anything (enabled by default)",
        ),
    ] = True,
) -> None:
    """
    Remove stale workspace worktrees based on HEAD commit age.

    This command identifies and removes worktrees whose HEAD commit is older than
    a specified threshold. It is intended to keep the workspace tidy by cleaning up
    long-inactive branches.
    """
    # Resolve the workspace root
    try:
        root_path = workspace.resolve_root_path(root)
    except (InvalidWorkspaceRootError, UnableToResolveWorkspaceRootError) as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    # Read manifest to get prune configuration
    manifest_path = root_path / ".workspace" / "manifest.toml"
    manifest = read_manifest(manifest_path)

    # Resolve the prune threshold
    try:
        threshold = resolve_prune_threshold(
            explicit=older_than_days,
            manifest=manifest,
        )
    except ValueError as e:
        typer.echo(f"error: {e}", err=True)
        raise typer.Exit(1)

    # List all worktrees
    worktrees = list_worktrees(root_path)

    # Get excluded branches from manifest
    exclude_branches = []
    if manifest.prune:
        exclude_branches = manifest.prune.exclude_branches

    # Select candidates
    candidates = select_prune_candidates(
        worktrees,
        threshold_days=threshold,
        exclude_branches=exclude_branches,
    )

    # Display results
    if not candidates:
        typer.echo("No stale worktrees found.")
        raise typer.Exit(0)

    if not dry_run:
        typer.echo(f"Removing {len(candidates)} stale worktrees:")
        failures = []
        for candidate in candidates:
            try:
                remove_worktree(candidate.path, force=True)
                age_str = (
                    f"{candidate.age_days}d"
                    if candidate.age_days is not None
                    else "unknown age"
                )
                branch_str = candidate.branch or "detached"
                typer.echo(f"  ✓ {branch_str} ({age_str}) at {candidate.path}")
            except WorktreeRemovalError as e:
                age_str = (
                    f"{candidate.age_days}d"
                    if candidate.age_days is not None
                    else "unknown age"
                )
                branch_str = candidate.branch or "detached"
                typer.echo(
                    f"  ✗ {branch_str} ({age_str}) at {candidate.path}: {e}",
                    err=True,
                )
                failures.append(candidate)

        if failures:
            typer.echo(
                f"\nerror: failed to remove {len(failures)}/{len(candidates)} worktrees",
                err=True,
            )
            raise typer.Exit(1)
    else:
        typer.echo(
            f"[dry-run] Would remove {len(candidates)} stale worktree{'s' if len(candidates) != 1 else ''}:"
        )
        for candidate in candidates:
            age_str = (
                f"{candidate.age_days}d"
                if candidate.age_days is not None
                else "unknown age"
            )
            branch_str = candidate.branch or "detached"
            typer.echo(f"  • {branch_str} ({age_str}) at {candidate.path}")
