from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from tests.helpers import make_context


def test_does_not_error(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    down(ctx=make_context(str(workspace.dir)), branch="main")


def test_worktree_directory_remains_after_down(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    down(ctx=make_context(str(workspace.dir)), branch="main")
    assert (workspace.dir / "main").is_dir()


def test_can_up_after_down(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    down(ctx=make_context(str(workspace.dir)), branch="main")
    up(ctx=make_context(str(workspace.dir)), branch="main")
    assert (workspace.dir / "main").is_dir()
