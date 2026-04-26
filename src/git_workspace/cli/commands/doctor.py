from typing import Annotated

import typer

from git_workspace.doctor import run_checks
from git_workspace.ui import confirm, console
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def doctor(
    workspace_dir: Annotated[
        str | None,
        typer.Option("--root", "-r", help="Workspace root path"),
    ] = None,
    fix: Annotated[
        bool,
        typer.Option("--fix", "-f", help="Apply auto fixes silently; prompt for interactive ones"),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-confirm interactive fixes (implies --fix)"),
    ] = False,
) -> None:
    """
    Inspect a workspace for inconsistencies.

    Checks the manifest, assets, hooks, and live worktree state and reports any
    errors or warnings. Exits 1 if any errors are found.

    Pass --fix to apply safe fixes automatically and be prompted for destructive
    ones. Add --yes to skip all prompts (useful in CI).
    """
    if yes:
        fix = True

    workspace = Workspace.resolve(workspace_dir)
    findings = run_checks(workspace)

    if not findings:
        console.success("Workspace is healthy.")
        return

    if not fix:
        has_error = False
        for f in findings:
            if f.level == "error":
                has_error = True
                console.error(f.message)
            else:
                console.warning(f.message)
        if has_error:
            raise typer.Exit(code=1)
        return

    applied = 0
    skipped = 0
    failed = 0

    for f in findings:
        if f.level == "error":
            console.error(f.message)
        else:
            console.warning(f.message)

        if f.fix is None:
            continue

        should_apply = f.fix.kind == "auto" or yes or confirm(f"  → {f.fix.label}?")
        if should_apply:
            try:
                f.fix.apply()
                console.print(f"  [success]→ Fixed:[/success] {f.fix.label}")
                applied += 1
            except Exception as e:
                console.print(f"  [error]→ Fix failed:[/error] {e}")
                failed += 1
        else:
            console.print(f"  [dim]→ Skipped: {f.fix.label}[/dim]")
            skipped += 1

    parts = []
    if applied:
        parts.append(f"{applied} fixed")
    if skipped:
        parts.append(f"{skipped} skipped")
    if failed:
        parts.append(f"{failed} failed")
    if parts:
        console.print("  " + ", ".join(parts))

    remaining = run_checks(Workspace(workspace.dir))
    if not remaining:
        console.success("Workspace is healthy.")
    elif any(f.level == "error" for f in remaining):
        raise typer.Exit(code=1)
