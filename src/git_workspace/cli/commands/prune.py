from typing import Annotated

import typer
from rich.table import Table

from git_workspace.ui import console, styled_branch
from git_workspace.workspace import Workspace
from git_workspace.workspace.service import WorkspaceService

app = typer.Typer()


@app.command("prune")
def prune(
    ctx: typer.Context,
    older_than_days: Annotated[
        int | None,
        typer.Option(
            "--older-than-days",
            help="Remove worktrees older than this many days. Takes precedence over manifest configuration.",
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
    Remove stale workspace worktrees.

    Identifies and removes worktrees older than a specified threshold. The age threshold is taken from --older-than-days if provided, otherwise from the [prune] section in the manifest. Branches listed in exclude_branches are never removed regardless of age.

    Runs in dry-run mode by default. Pass --apply to actually remove worktrees.

    Removal goes through the full lifecycle: on_detach and on_teardown hooks run for each worktree before it is deleted. A failing worktree is skipped and pruning continues; failures are reported at the end.
    """
    workspace = Workspace.resolve(ctx.obj.workspace_dir)

    if older_than_days is None and workspace.manifest.prune is None:
        raise typer.BadParameter(
            "Must pass --older-than-days or define [prune] in manifest",
            param_hint="'--older-than-days'",
        )

    service = WorkspaceService.create(workspace)
    candidates = service.prune_candidates(older_than_days=older_than_days)

    if not candidates:
        console.success("Nothing to prune")
        return

    if dry_run:
        console.print(f"Would remove [bold]{len(candidates)}[/bold] worktree(s):")
        table = Table(show_header=True, header_style="bold")
        table.add_column("Branch", style="branch", no_wrap=True)
        table.add_column("Path", style="path")
        table.add_column("Age", style="dim", no_wrap=True)
        for worktree in candidates:
            table.add_row(worktree.branch, str(worktree.dir), f"{worktree.age_days}d")
        console.print(table)
    else:
        console.print(f"Pruning [bold]{len(candidates)}[/bold] worktree(s)...")
        failures = service.prune(candidates)

        if failures:
            for failure in failures:
                console.warning(
                    f"Failed to remove {styled_branch(failure.worktree.branch)}: {failure.error}"
                )
            console.error(f"Pruned with {len(failures)} failure(s)")
            raise typer.Exit(code=1)

        console.success("Done")
