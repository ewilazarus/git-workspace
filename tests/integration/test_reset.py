from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_does_not_error(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    reset(branch="main", workspace_dir=str(workspace.dir))


def test_worktree_directory_remains_after_reset(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    reset(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_reset_is_idempotent(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    reset(branch="main", workspace_dir=str(workspace.dir))
    reset(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()
