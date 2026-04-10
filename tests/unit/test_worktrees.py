from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import worktrees
from git_workspace.git import WorktreeMetadata

ROOT = Path("/workspace")
WORKTREE_1 = ROOT / "feat" / "001"
WORKTREE_2 = ROOT / "feat" / "002"
TIMESTAMP = 1712700000


# --- normalize_branch ---

def test_normalize_branch_strips_prefix() -> None:
    result = worktrees.normalize_branch("refs/heads/feat/001")
    assert result == "feat/001"


def test_normalize_branch_handles_none() -> None:
    assert worktrees.normalize_branch(None) is None


def test_normalize_branch_handles_plain_name() -> None:
    result = worktrees.normalize_branch("feat/001")
    assert result == "feat/001"


# --- compute_age ---

def test_compute_age_returns_days(mocker: MockerFixture) -> None:
    now = 1712700000
    past = now - (3 * 86400)  # 3 days ago
    mocker.patch("git_workspace.worktrees.time.time", return_value=float(now))

    age = worktrees.compute_age(past)

    assert age == 3


def test_compute_age_returns_zero_for_today(mocker: MockerFixture) -> None:
    now = 1712700000
    mocker.patch("git_workspace.worktrees.time.time", return_value=float(now))

    age = worktrees.compute_age(now)

    assert age == 0


def test_compute_age_handles_none() -> None:
    assert worktrees.compute_age(None) is None


# --- enrich_worktree ---

def test_enrich_worktree_basic(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=WORKTREE_1, head="abc123", branch="refs/heads/feat/001")
    result = worktrees.enrich_worktree(meta)

    assert result.path == WORKTREE_1
    assert result.branch == "feat/001"
    assert result.short_id == "abc1234"
    assert result.timestamp == TIMESTAMP
    assert result.current is False


def test_enrich_worktree_marks_current(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=WORKTREE_1, head="abc123", branch="refs/heads/feat/001")
    result = worktrees.enrich_worktree(meta, current_worktree=WORKTREE_1)

    assert result.current is True


def test_enrich_worktree_detached_branch(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=WORKTREE_1, head="abc123", branch=None)
    result = worktrees.enrich_worktree(meta)

    assert result.branch is None


# --- WorktreeInfo.age_display ---

def test_age_display_today() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=0,
    )
    assert wt.age_display == "today"


def test_age_display_days() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=5,
    )
    assert wt.age_display == "5d"


def test_age_display_one_day() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=1,
    )
    assert wt.age_display == "1d"


def test_age_display_unknown() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=None,
        age_days=None,
    )
    assert wt.age_display == "unknown"


# --- format_table ---

def test_format_table_single_worktree() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = worktrees.format_table([wt])

    assert "BRANCH" in result
    assert "feat/001" in result
    assert "3d" in result
    assert "abc1234" in result


def test_format_table_marks_current() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
        current=True,
    )

    result = worktrees.format_table([wt])

    assert "*" in result


def test_format_table_empty_list() -> None:
    result = worktrees.format_table([])
    assert "No worktrees found" in result


def test_format_table_detached_worktree() -> None:
    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch=None,
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = worktrees.format_table([wt])

    assert "detached" in result


# --- format_json ---

def test_format_json_single_worktree() -> None:
    import json

    wt = worktrees.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = worktrees.format_json([wt])
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["branch"] == "feat/001"
    assert data[0]["short_id"] == "abc1234"
    assert data[0]["age_days"] == 3
    assert data[0]["current"] is False


def test_format_json_empty_list() -> None:
    import json

    result = worktrees.format_json([])
    data = json.loads(result)

    assert data == []
