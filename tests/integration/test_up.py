import subprocess
from pathlib import Path

from conftest import _GIT_ENV, Setup

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


def test_up_checks_out_remote_only_branch(setup: Setup, tmp_path: Path) -> None:
    """Bug 1: branch that only exists on the remote should be checked out, not recreated from main."""
    setup()
    repo_path = tmp_path / "repo"
    workspace_dir = tmp_path / "workspace"

    Workspace.clone(
        workspace_dir=str(workspace_dir),
        url=str(repo_path),
        config_url=str(tmp_path / "configs" / "minimal"),
    )

    # Simulate a colleague pushing a new branch with a unique file to the remote
    subprocess.run(
        ["git", "checkout", "-b", "feature/colleague"],
        cwd=repo_path,
        capture_output=True,
        env=_GIT_ENV,
    )
    (repo_path / "colleague_file.txt").write_text("colleague's work")
    subprocess.run(
        ["git", "add", "colleague_file.txt"], cwd=repo_path, capture_output=True, env=_GIT_ENV
    )
    subprocess.run(
        ["git", "commit", "-m", "colleague commit"],
        cwd=repo_path,
        capture_output=True,
        env=_GIT_ENV,
    )
    subprocess.run(["git", "checkout", "main"], cwd=repo_path, capture_output=True, env=_GIT_ENV)

    # Run up on the colleague's branch — it only exists on the remote at this point
    up(branch="feature/colleague", workspace_dir=str(workspace_dir))

    worktree_path = workspace_dir / "feature" / "colleague"
    assert worktree_path.is_dir()
    assert (worktree_path / "colleague_file.txt").read_text() == "colleague's work"


def test_new_branch_forks_from_latest_remote_main(setup: Setup, tmp_path: Path) -> None:
    """Bug 2: a new branch must fork from the remote's latest main, not a stale local copy."""
    setup()
    repo_path = tmp_path / "repo"
    workspace_dir = tmp_path / "workspace"

    Workspace.clone(
        workspace_dir=str(workspace_dir),
        url=str(repo_path),
        config_url=str(tmp_path / "configs" / "minimal"),
    )

    # Check out main worktree so that refs/heads/main is locked inside the workspace
    up(branch="main", workspace_dir=str(workspace_dir))

    # Add a new commit to the remote's main AFTER the workspace was created
    (repo_path / "new_remote_file.txt").write_text("new remote work")
    subprocess.run(
        ["git", "add", "new_remote_file.txt"], cwd=repo_path, capture_output=True, env=_GIT_ENV
    )
    subprocess.run(
        ["git", "commit", "-m", "new remote commit"],
        cwd=repo_path,
        capture_output=True,
        env=_GIT_ENV,
    )

    # Create a brand-new branch — it must fork from the latest remote main
    up(branch="feature/new", workspace_dir=str(workspace_dir))

    worktree_path = workspace_dir / "feature" / "new"
    assert worktree_path.is_dir()
    # The file added to remote main after cloning must be present in the new branch
    assert (worktree_path / "new_remote_file.txt").exists()
