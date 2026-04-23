from typing import Annotated

import typer
from rich.table import Table

from git_workspace.ui import console, styled_branch
from git_workspace.workspace import Workspace

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
    """
    workspace = Workspace.resolve(root)

    threshold = older_than_days
    if threshold is None:
        if workspace.manifest.prune is None:
            raise typer.BadParameter(
                "Must pass --older-than-days or define [prune] in manifest",
                param_hint="'--older-than-days'",
            )
        threshold = workspace.manifest.prune.older_than_days

    protected: set[str] = set()
    if workspace.manifest.prune:
        protected.update(workspace.manifest.prune.exclude_branches)

    candidates = [
        worktree
        for worktree in workspace.list_worktrees()
        if worktree.age_days > threshold and worktree.branch not in protected
    ]

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
        for worktree in candidates:
            console.print(f"  Removing {styled_branch(worktree.branch)}")
            worktree.delete(force=True)
        console.success("Done")
