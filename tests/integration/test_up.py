from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_creates_worktree_directory_for_existing_branch(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_worktree_is_on_correct_branch(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    branch_file = workspace.dir / "main" / ".git"
    assert branch_file.exists()


def test_creates_worktree_for_new_branch(workspace: Workspace) -> None:
    up(branch="feature/new", base_branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "feature" / "new").is_dir()


def test_up_is_idempotent(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    up(branch="main", workspace_dir=str(workspace.dir))
    assert (workspace.dir / "main").is_dir()


def test_multiple_worktrees_can_coexist(workspace: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace.dir))
    up(
        branch="feature/second",
        base_branch="main",
        workspace_dir=str(workspace.dir),
    )
    assert (workspace.dir / "main").is_dir()
    assert (workspace.dir / "feature" / "second").is_dir()
