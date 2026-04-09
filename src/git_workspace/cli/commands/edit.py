from typing import Annotated

import typer

app = typer.Typer()


@app.command()
def edit(
    root: Annotated[
        str | None,
        typer.Option(
            "-r",
            "--root",
            help="The path to the workspace root. If omitted, the workspace root will be inferred from the current working directory",
        ),
    ] = None,
) -> None:
    """
    Open the repository's `.workspace` directory in the configured editor.

    This directory contains the workspace blueprint, including `workspace.toml`, hook scripts, and any linked or override files that define how branch workspaces are prepared and activated.

    The editor is resolved using standard environment variables (e.g. VISUAL or EDITOR). The command does not modify any files—it only launches the editor.
    """
    pass
