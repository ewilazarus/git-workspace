from unittest.mock import MagicMock

import pytest
import typer

from git_workspace.cli.commands.exec import exec_cmd
from git_workspace.cli.commands.up import up
from git_workspace.errors import WorktreeResolutionError
from git_workspace.workspace import Workspace


def _make_ctx(args: list[str]) -> MagicMock:
    ctx = MagicMock(spec=typer.Context)
    ctx.args = args
    return ctx


def test_runs_command_in_worktree_directory(workspace: Workspace, tmp_path) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    output_file = tmp_path / "output.txt"
    exec_cmd(
        branch="main",
        ctx=_make_ctx(["sh", "-c", f"pwd > {output_file}"]),
        workspace_dir=str(workspace.dir),
    )
    assert output_file.read_text().strip() == str(workspace.dir / "main")


def test_injects_git_workspace_env_vars(workspace: Workspace, tmp_path) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    output_file = tmp_path / "branch.txt"
    exec_cmd(
        branch="main",
        ctx=_make_ctx(["sh", "-c", f"echo $GIT_WORKSPACE_BRANCH > {output_file}"]),
        workspace_dir=str(workspace.dir),
    )
    assert output_file.read_text().strip() == "main"


def test_propagates_nonzero_exit_code(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    with pytest.raises(typer.Exit) as exc_info:
        exec_cmd(
            branch="main",
            ctx=_make_ctx(["sh", "-c", "exit 42"]),
            workspace_dir=str(workspace.dir),
        )
    assert exc_info.value.exit_code == 42


def test_creates_worktree_when_force(workspace: Workspace, tmp_path) -> None:
    output_file = tmp_path / "output.txt"
    exec_cmd(
        branch="main",
        ctx=_make_ctx(["sh", "-c", f"pwd > {output_file}"]),
        workspace_dir=str(workspace.dir),
        force=True,
    )
    assert (workspace.dir / "main").is_dir()
    assert output_file.read_text().strip() == str(workspace.dir / "main")


def test_reraises_resolution_error_when_user_declines(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("git_workspace.cli.commands.exec.typer.confirm", lambda *a, **kw: False)
    with pytest.raises(WorktreeResolutionError):
        exec_cmd(
            branch="nonexistent-branch",
            ctx=_make_ctx(["echo", "hello"]),
            workspace_dir=str(workspace.dir),
        )
