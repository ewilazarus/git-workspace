from git_workspace.cli.commands.up import up
from git_workspace.cli.commands.down import down
from git_workspace.workspace import Workspace


def test_does_not_error(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    down(branch="main", workspace_dir=str(workspace.dir))


def test_worktree_directory_remains_after_down(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    down(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_can_up_after_down(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    down(branch="main", workspace_dir=str(workspace.dir))
    up(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()
