import typer

from git_workspace.doctor import run_checks
from git_workspace.ui import console
from git_workspace.workspace import Workspace

app = typer.Typer()


@app.command()
def doctor(
    workspace_dir: str | None = typer.Option(None, "--root", "-r", help="Workspace root path"),
) -> None:
    """
    Inspect a workspace for inconsistencies.

    Checks the manifest, assets, hooks, and live worktree state and reports any errors or warnings. Exits 1 if any errors are found.
    """
    workspace = Workspace.resolve(workspace_dir)

    findings = run_checks(workspace)

    if not findings:
        console.success("Workspace is healthy.")
        return

    has_error = False
    for f in findings:
        if f.level == "error":
            has_error = True
            console.error(f.message)
        else:
            console.warning(f.message)

    if has_error:
        raise typer.Exit(code=1)
