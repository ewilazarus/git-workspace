import re
import subprocess
from pathlib import Path

import typer

from git_workspace.ui import console
from git_workspace.workspace import Workspace

app = typer.Typer()

_COMPOSE_FILENAMES = (
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
)

_PROJECT_NAME_FALLBACK = "workspace"


def _find_compose_file(config_dir: Path) -> Path | None:
    for name in _COMPOSE_FILENAMES:
        candidate = config_dir / name
        if candidate.is_file():
            return candidate
    return None


def _slugify_project_name(name: str) -> str:
    # Docker compose project names must match ^[a-z0-9][a-z0-9_-]*$.
    # Lowercase, collapse invalid chars to '-', strip leading '-'/'_' so the
    # first character is guaranteed to be alphanumeric.
    slug = re.sub(r"[^a-z0-9_-]+", "-", name.lower()).lstrip("-_")
    return slug or _PROJECT_NAME_FALLBACK


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def compose(ctx: typer.Context) -> None:
    """
    Run docker compose against the workspace's shared compose file.

    Looks for a compose file under `<WORKSPACE_ROOT>/.workspace/` (one of compose.yaml, compose.yml, docker-compose.yaml, docker-compose.yml) and invokes `docker compose -p <workspace-name> -f <file> <args>`. All arguments are forwarded verbatim to docker compose. The project name is derived from the workspace directory name, slugified to match docker compose's naming rules.
    """
    workspace = Workspace.resolve(ctx.obj.workspace_dir)
    compose_file = _find_compose_file(workspace.paths.config)
    if compose_file is None:
        console.error(
            f"No compose file found under {workspace.paths.config}. "
            f"Expected one of: {', '.join(_COMPOSE_FILENAMES)}"
        )
        raise typer.Exit(code=1)

    project_name = _slugify_project_name(workspace.dir.name)

    cmd = [
        "docker",
        "compose",
        "-p",
        project_name,
        "-f",
        str(compose_file),
        *ctx.args,
    ]

    try:
        result = subprocess.run(cmd, cwd=workspace.paths.config)
    except FileNotFoundError as e:
        console.error("docker is not installed or not on PATH")
        raise typer.Exit(code=1) from e

    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)
