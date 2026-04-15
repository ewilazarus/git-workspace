from git_workspace.cli.commands.up import up
from git_workspace.cli.commands.remove import remove
from git_workspace.workspace import Workspace


def test_removes_worktree_directory(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    remove(branch="main", workspace_dir=str(workspace.dir))
    assert not (workspace.dir / "main").exists()


def test_removes_worktree_with_force(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    remove(branch="main", workspace_dir=str(workspace.dir), force=True)
    assert not (workspace.dir / "main").exists()


def test_cleans_up_empty_intermediary_directories(workspace: Workspace) -> None:
    up(
        branch="feature/cleanup",
        base_branch="main",
        workspace_dir=str(workspace.dir),
    )
    remove(branch="feature/cleanup", workspace_dir=str(workspace.dir))
    assert not (workspace.dir / "feature").exists()


def test_worktree_can_be_recreated_after_remove(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    remove(branch="main", workspace_dir=str(workspace.dir))
    up(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()
