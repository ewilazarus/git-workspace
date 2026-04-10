"""Integration tests for the reset command."""
from pathlib import Path

from tests.integration.helpers import run, write_manifest, write_hook


def test_fails_if_worktree_does_not_exist(repo: Path) -> None:
    result = run("reset", "feat/nonexistent", "-r", str(repo))

    assert not result.ok
    assert "feat/nonexistent" in result.stderr


def test_reapplies_links(repo: Path) -> None:
    link_src = repo / ".workspace" / "files" / "config.txt"
    link_src.parent.mkdir(parents=True)
    link_src.write_text("shared config\n")
    write_manifest(repo, '[[link]]\nsource = "config.txt"\ntarget = "config.txt"\n')

    run("up", "feat/reset-test", "-r", str(repo))
    # Remove the link to simulate drift
    link_target = repo / "feat" / "reset-test" / "config.txt"
    link_target.unlink(missing_ok=True)

    result = run("reset", "feat/reset-test", "-r", str(repo))

    assert result.ok, result.stderr
    assert link_target.exists() or link_target.is_symlink()


def test_reruns_reset_hooks(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["mark_reset"]\n')
    marker = repo / ".workspace" / "reset_count"
    write_hook(repo, "mark_reset", f'#!/bin/sh\necho x >> {marker}\n')

    run("up", "feat/reset-test", "-r", str(repo))
    run("reset", "feat/reset-test", "-r", str(repo))

    count = len(marker.read_text().strip().splitlines()) if marker.exists() else 0
    assert count == 2


def test_skip_hooks_prevents_hook_execution(repo: Path) -> None:
    write_manifest(repo, '[hooks]\nafter_setup = ["mark_reset"]\n')
    marker = repo / ".workspace" / "reset_count"
    write_hook(repo, "mark_reset", f'#!/bin/sh\necho x >> {marker}\n')

    run("up", "feat/reset-test", "-r", str(repo))
    run("reset", "feat/reset-test", "-r", str(repo), "--skip-hooks")

    # Should have only run once (from up, not reset)
    count = len(marker.read_text().strip().splitlines()) if marker.exists() else 0
    assert count == 1


def test_supports_branch_inference_from_cwd(repo: Path) -> None:
    run("up", "feat/infer", "-r", str(repo))
    worktree = repo / "feat" / "infer"

    result = run("reset", cwd=worktree)

    assert result.ok, result.stderr
