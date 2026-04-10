"""Integration tests for error handling across commands."""
from pathlib import Path

from tests.integration.helpers import run, write_manifest


def test_up_fails_outside_workspace(tmp_path: Path) -> None:
    """up with no --root and not inside a workspace should fail."""
    result = run("up", "feat/test", cwd=tmp_path)

    assert not result.ok
    assert result.returncode != 0


def test_rm_fails_for_nonexistent_branch(repo: Path) -> None:
    result = run("rm", "feat/ghost", "-r", str(repo))

    assert not result.ok
    assert "feat/ghost" in result.stderr


def test_reset_fails_for_nonexistent_worktree(repo: Path) -> None:
    result = run("reset", "feat/ghost", "-r", str(repo))

    assert not result.ok
    assert "feat/ghost" in result.stderr


def test_prune_fails_without_threshold(repo: Path) -> None:
    result = run("prune", "-r", str(repo))

    assert not result.ok
    assert result.stderr  # Should have an informative error message


def test_commands_use_nonzero_exit_code_on_failure(repo: Path) -> None:
    for result in [
        run("rm", "feat/ghost", "-r", str(repo)),
        run("reset", "feat/ghost", "-r", str(repo)),
    ]:
        assert result.returncode != 0


def test_invalid_root_path_gives_clear_error(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist"

    result = run("ls", "-r", str(nonexistent))

    assert not result.ok
    assert result.stderr


def test_rm_reports_error_on_dirty_worktree(repo: Path) -> None:
    run("up", "feat/dirty", "-r", str(repo))
    (repo / "feat" / "dirty" / "dirty.txt").write_text("change\n")

    result = run("rm", "feat/dirty", "-r", str(repo))

    assert not result.ok
    assert "uncommitted" in result.stderr.lower() or "dirty" in result.stderr.lower() or "changes" in result.stderr.lower()
