"""Integration tests for the up command."""
from pathlib import Path

from tests.integration.helpers import git_branch, git_commit, git_add, run, write_manifest, write_hook


def test_creates_worktree_for_new_branch(repo: Path) -> None:
    result = run("up", "feat/new", "-r", str(repo))

    assert result.ok, result.stderr
    assert (repo / "feat" / "new").is_dir()


def test_creates_worktree_from_existing_local_branch(repo: Path) -> None:
    git_branch(repo, "feat/existing")

    result = run("up", "feat/existing", "-r", str(repo))

    assert result.ok, result.stderr
    assert (repo / "feat" / "existing").is_dir()


def test_resumes_existing_worktree_without_recreating(repo: Path) -> None:
    run("up", "feat/resume", "-r", str(repo))
    sentinel = repo / "feat" / "resume" / "sentinel"
    sentinel.write_text("keep me")

    result = run("up", "feat/resume", "-r", str(repo))

    assert result.ok, result.stderr
    assert sentinel.exists(), "Worktree was recreated instead of resumed"


def test_outputs_worktree_path(repo: Path) -> None:
    result = run("up", "feat/new", "-r", str(repo))

    assert result.ok, result.stderr
    assert str(repo / "feat" / "new") in result.stdout


def test_runs_setup_hooks_on_first_creation(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["mark_setup"]\n')
    write_hook(repo, "mark_setup", "#!/bin/sh\ntouch $GIT_WORKSPACE_WORKTREE/setup_ran\n")

    run("up", "feat/new", "-r", str(repo))

    assert (repo / "feat" / "new" / "setup_ran").exists()


def test_does_not_run_setup_hooks_on_resume(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["mark_setup"]\n')
    marker = repo / ".workspace" / "setup_count"

    write_hook(
        repo,
        "mark_setup",
        f'#!/bin/sh\necho x >> {marker}\n',
    )

    run("up", "feat/resume", "-r", str(repo))
    run("up", "feat/resume", "-r", str(repo))

    count = len(marker.read_text().strip().splitlines()) if marker.exists() else 0
    assert count == 1, f"Expected setup to run once, ran {count} times"


def test_runs_activation_hooks_on_every_invocation(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_activate = ["mark_activate"]\n')
    marker = repo / ".workspace" / "activate_count"

    write_hook(
        repo,
        "mark_activate",
        f'#!/bin/sh\necho x >> {marker}\n',
    )

    run("up", "feat/hooks", "-r", str(repo))
    run("up", "feat/hooks", "-r", str(repo))

    count = len(marker.read_text().strip().splitlines()) if marker.exists() else 0
    assert count == 2, f"Expected activation to run twice, ran {count} times"


def test_skip_hooks_prevents_hook_execution(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["mark_setup"]\n')
    write_hook(repo, "mark_setup", "#!/bin/sh\ntouch $GIT_WORKSPACE_WORKTREE/setup_ran\n")

    run("up", "feat/new", "-r", str(repo), "--skip-hooks")

    assert not (repo / "feat" / "new" / "setup_ran").exists()


def test_supports_base_branch_override(repo: Path) -> None:
    # Create a feature branch off main and commit something on it
    git_branch(repo, "base-branch")

    result = run("up", "feat/from-base", "-r", str(repo), "--base", "base-branch")

    assert result.ok, result.stderr
    assert (repo / "feat" / "from-base").is_dir()
