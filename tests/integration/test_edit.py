import pytest

from git_workspace.cli.commands.edit import edit
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from tests.helpers import make_context


def test_opens_config_directory_without_error(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EDITOR", "true")
    monkeypatch.setenv("VISUAL", "true")
    up(ctx=make_context(str(workspace.dir)), branch="main")
    edit(ctx=make_context(str(workspace.dir)))


def test_config_directory_still_exists_after_edit(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EDITOR", "true")
    monkeypatch.setenv("VISUAL", "true")
    edit(ctx=make_context(str(workspace.dir)))
    assert workspace.paths.config.is_dir()
