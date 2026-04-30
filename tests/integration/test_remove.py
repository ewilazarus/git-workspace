from git_workspace.cli.commands.remove import remove
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from tests.helpers import make_context


def test_removes_worktree_directory(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    remove(ctx=make_context(str(workspace.dir)), branch="main")
    assert not (workspace.dir / "main").exists()


def test_removes_worktree_with_force(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    remove(ctx=make_context(str(workspace.dir)), branch="main", force=True)
    assert not (workspace.dir / "main").exists()


def test_cleans_up_empty_intermediary_directories(workspace: Workspace) -> None:
    up(
        ctx=make_context(str(workspace.dir)),
        branch="feature/cleanup",
        base_branch="main",
    )
    remove(ctx=make_context(str(workspace.dir)), branch="feature/cleanup")
    assert not (workspace.dir / "feature").exists()


def test_worktree_can_be_recreated_after_remove(workspace: Workspace) -> None:
    up(ctx=make_context(str(workspace.dir)), branch="main")
    remove(ctx=make_context(str(workspace.dir)), branch="main")
    up(ctx=make_context(str(workspace.dir)), branch="main")
    assert (workspace.dir / "main").is_dir()
