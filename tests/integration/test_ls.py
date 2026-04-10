"""Integration tests for the ls command."""
import json
from pathlib import Path

from tests.integration.helpers import run


def test_lists_all_worktrees(repo: Path) -> None:
    run("up", "feat/001", "-r", str(repo))
    run("up", "feat/002", "-r", str(repo))

    result = run("ls", "-r", str(repo))

    assert result.ok, result.stderr
    assert "feat/001" in result.stdout
    assert "feat/002" in result.stdout


def test_displays_worktree_paths(repo: Path) -> None:
    run("up", "feat/001", "-r", str(repo))

    result = run("ls", "-r", str(repo))

    assert str(repo / "feat" / "001") in result.stdout


def test_includes_age_field(repo: Path) -> None:
    run("up", "feat/001", "-r", str(repo))

    result = run("ls", "-r", str(repo))

    assert result.ok
    # Age is shown as "today", "Nd", or "unknown" — just verify column header present
    assert "AGE" in result.stdout


def test_json_output_structure(repo: Path) -> None:
    run("up", "feat/json", "-r", str(repo))

    result = run("ls", "-r", str(repo), "--json")

    assert result.ok, result.stderr
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    entry = next((e for e in data if e["branch"] == "feat/json"), None)
    assert entry is not None
    assert "path" in entry
    assert "age_days" in entry
    assert "current" in entry


def test_json_empty_list(repo: Path) -> None:
    # Repo with no additional worktrees (only main)
    result = run("ls", "-r", str(repo), "--json")

    assert result.ok
    data = json.loads(result.stdout)
    assert isinstance(data, list)


def test_marks_current_worktree(repo: Path) -> None:
    run("up", "feat/current", "-r", str(repo))
    worktree = repo / "feat" / "current"

    result = run("ls", cwd=worktree)

    assert result.ok, result.stderr
    # The current worktree should be marked with *
    assert "*" in result.stdout


def test_stable_output_with_multiple_worktrees(repo: Path) -> None:
    run("up", "feat/aaa", "-r", str(repo))
    run("up", "feat/bbb", "-r", str(repo))
    run("up", "feat/ccc", "-r", str(repo))

    result = run("ls", "-r", str(repo))

    assert result.ok
    # All three should appear
    for branch in ("feat/aaa", "feat/bbb", "feat/ccc"):
        assert branch in result.stdout
