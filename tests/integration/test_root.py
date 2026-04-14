import pytest
import typer

from git_workspace.cli.commands.root import root
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_prints_workspace_root_when_cwd_is_workspace(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(workspace.directory)
    root()
    assert capsys.readouterr().out.strip() == str(workspace.directory)


def test_prints_workspace_root_when_cwd_is_worktree(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    up(branch="main", workspace_dir=str(workspace.directory))
    monkeypatch.chdir(workspace.directory / "main")
    root()
    assert capsys.readouterr().out.strip() == str(workspace.directory)


def test_exits_with_1_when_not_in_workspace(
    tmp_path: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(typer.Exit) as exc_info:
        root()
    assert exc_info.value.exit_code == 1
