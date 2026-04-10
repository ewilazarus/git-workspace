"""Integration tests for the prune command."""
import json
import subprocess
from pathlib import Path

from tests.integration.helpers import run, write_manifest


def _backdate_commit(repo: Path, worktree: Path, days: int) -> None:
    """Force the HEAD commit timestamp back by the given number of days."""
    seconds = days * 86400
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H"],
        cwd=str(worktree),
        capture_output=True,
        text=True,
        check=True,
    )
    sha = result.stdout.strip()
    # Amend with an old author/committer date using git filter-branch alternative
    import time
    old_date = int(time.time()) - seconds
    date_str = str(old_date)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit",
         f"--date={date_str}", "-c", sha],
        cwd=str(worktree),
        capture_output=True,
        env={**__import__("os").environ, "GIT_COMMITTER_DATE": date_str},
    )


def test_dry_run_by_default_removes_nothing(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 1\n')
    run("up", "feat/stale", "-r", str(repo))

    result = run("prune", "-r", str(repo))

    assert result.ok, result.stderr
    # dry-run by default — worktree should still exist
    assert (repo / "feat" / "stale").exists()


def test_dry_run_output_says_would_remove(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 0\n')
    run("up", "feat/stale", "-r", str(repo))

    result = run("prune", "-r", str(repo))

    assert result.ok
    assert "dry-run" in result.stdout.lower() or "would remove" in result.stdout.lower()


def test_apply_mode_removes_candidates(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 0\n')
    run("up", "feat/stale", "-r", str(repo))
    assert (repo / "feat" / "stale").is_dir()

    result = run("prune", "-r", str(repo), "--apply")

    assert result.ok, result.stderr
    assert not (repo / "feat" / "stale").exists()


def test_preserves_branch_after_removal(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 0\n')
    run("up", "feat/pruned", "-r", str(repo))

    run("prune", "-r", str(repo), "--apply")

    result = subprocess.run(
        ["git", "branch"],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )
    assert "feat/pruned" in result.stdout


def test_does_not_prune_young_worktrees(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 30\n')
    run("up", "feat/fresh", "-r", str(repo))

    result = run("prune", "-r", str(repo), "--apply")

    assert result.ok
    # Not pruned because it's brand new (0 days old < 30 day threshold)
    assert (repo / "feat" / "fresh").exists()


def test_cli_threshold_overrides_manifest(repo: Path) -> None:
    # Manifest says 30 days, CLI says 0 — CLI should win
    write_manifest(repo, '[prune]\nolder_than_days = 30\n')
    run("up", "feat/override", "-r", str(repo))

    result = run("prune", "-r", str(repo), "--older-than-days", "0", "--apply")

    assert result.ok, result.stderr
    assert not (repo / "feat" / "override").exists()


def test_excludes_branches_in_manifest(repo: Path) -> None:
    write_manifest(
        repo,
        '[prune]\nolder_than_days = 0\nexclude_branches = ["feat/protected"]\n',
    )
    run("up", "feat/protected", "-r", str(repo))
    run("up", "feat/notprotected", "-r", str(repo))

    run("prune", "-r", str(repo), "--apply")

    assert (repo / "feat" / "protected").exists()
    assert not (repo / "feat" / "notprotected").exists()


def test_cleans_empty_parent_dirs_after_prune(repo: Path) -> None:
    write_manifest(repo, '[prune]\nolder_than_days = 0\n')
    run("up", "feat/cleanup", "-r", str(repo))

    run("prune", "-r", str(repo), "--apply")

    assert not (repo / "feat").exists()


def test_fails_without_threshold(repo: Path) -> None:
    # No manifest prune config, no CLI flag — should fail
    result = run("prune", "-r", str(repo))

    assert not result.ok
    assert "threshold" in result.stderr.lower() or "older-than-days" in result.stderr.lower()
