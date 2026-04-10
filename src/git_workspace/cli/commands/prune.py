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
            help="Remove worktrees older than this many days. Takes precedence over manifest configuration",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show what would be removed without removing anything (enabled by default)",
            is_flag=True,
        ),
    ] = True,
    no_dry_run: Annotated[
        bool,
        typer.Option(
            "--no-dry-run",
            help="Actually remove worktrees instead of just showing what would be removed",
            is_flag=True,
        ),
    ] = False,
) -> None:
    """
    Remove stale workspace worktrees.

    Removes multiple worktrees that are considered stale based on workspace rules (for example, worktrees that are no longer referenced, inactive, or otherwise eligible for cleanup).

    This is a batch cleanup operation intended to keep the workspace tidy.

    Use this when you want to clean up unused worktrees efficiently.

    By default, this command shows what would be removed (dry-run mode). Pass --no-dry-run to actually remove worktrees.
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

    # Handle the mode flag
    apply_removal = no_dry_run
    if not no_dry_run and not dry_run:
        typer.echo(
            "error: either --dry-run or --no-dry-run must be specified",
            err=True,
        )
        raise typer.Exit(1)

    # Display results
    if not candidates:
        typer.echo("No stale worktrees found.")
        raise typer.Exit(0)

    if apply_removal:
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
