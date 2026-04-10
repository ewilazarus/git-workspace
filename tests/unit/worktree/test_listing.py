from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import worktree
from git_workspace.git import WorktreeMetadata
from git_workspace.utils import format_json, format_table

ROOT = Path("/workspace")
WORKTREE_1 = ROOT / "feat" / "001"
WORKTREE_2 = ROOT / "feat" / "002"
TIMESTAMP = 1712700000


# --- normalize_branch ---

def test_normalize_branch_strips_prefix() -> None:
    result = worktree.normalize_branch("refs/heads/feat/001")
    assert result == "feat/001"


def test_normalize_branch_handles_none() -> None:
    assert worktree.normalize_branch(None) is None


def test_normalize_branch_handles_plain_name() -> None:
    result = worktree.normalize_branch("feat/001")
    assert result == "feat/001"


# --- compute_age ---

def test_compute_age_returns_days(mocker: MockerFixture) -> None:
    now = 1712700000
    past = now - (3 * 86400)  # 3 days ago
    mocker.patch("git_workspace.worktree.time.time", return_value=float(now))

    age = worktree.compute_age(past)

    assert age == 3


def test_compute_age_returns_zero_for_today(mocker: MockerFixture) -> None:
    now = 1712700000
    mocker.patch("git_workspace.worktree.time.time", return_value=float(now))

    age = worktree.compute_age(now)

    assert age == 0


def test_compute_age_handles_none() -> None:
    assert worktree.compute_age(None) is None


# --- enrich_worktree ---

def test_enrich_worktree_basic(mocker: MockerFixture) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.__eq__ = lambda self, other: False

    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=mock_path, head="abc123", branch="refs/heads/feat/001")
    result = worktree.enrich_worktree(meta)

    assert result.branch == "feat/001"
    assert result.short_id == "abc1234"
    assert result.timestamp == TIMESTAMP
    assert result.current is False


def test_enrich_worktree_marks_current(mocker: MockerFixture) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.__eq__ = lambda self, other: other is mock_path

    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=mock_path, head="abc123", branch="refs/heads/feat/001")
    result = worktree.enrich_worktree(meta, current_worktree=mock_path)

    assert result.current is True


def test_enrich_worktree_detached_branch(mocker: MockerFixture) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.__eq__ = lambda self, other: False

    mocker.patch("git_workspace.git.get_short_commit_id", return_value="abc1234")
    mocker.patch("git_workspace.git.get_commit_timestamp", return_value=TIMESTAMP)

    meta = WorktreeMetadata(path=mock_path, head="abc123", branch=None)
    result = worktree.enrich_worktree(meta)

    assert result.branch is None


def test_enrich_worktree_missing_path(mocker: MockerFixture) -> None:
    mock_path = MagicMock()
    mock_path.exists.return_value = False
    mock_path.__eq__ = lambda self, other: False

    get_short_commit_id_mock = mocker.patch("git_workspace.git.get_short_commit_id")
    get_commit_timestamp_mock = mocker.patch("git_workspace.git.get_commit_timestamp")

    meta = WorktreeMetadata(path=mock_path, head="abc123", branch="refs/heads/feat/001")
    result = worktree.enrich_worktree(meta)

    assert result.branch == "feat/001"
    assert result.short_id is None
    assert result.timestamp is None
    assert result.age_days is None
    get_short_commit_id_mock.assert_not_called()
    get_commit_timestamp_mock.assert_not_called()


# --- WorktreeInfo.age_display ---

def test_age_display_today() -> None:
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=0,
    )
    assert wt.age_display == "today"


def test_age_display_days() -> None:
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=5,
    )
    assert wt.age_display == "5d"


def test_age_display_one_day() -> None:
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=1,
    )
    assert wt.age_display == "1d"


def test_age_display_unknown() -> None:
    wt = worktree.WorktreeInfo(
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
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = format_table([wt])

    assert "BRANCH" in result
    assert "feat/001" in result
    assert "3d" in result
    assert "abc1234" in result


def test_format_table_marks_current() -> None:
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
        current=True,
    )

    result = format_table([wt])

    assert "*" in result


def test_format_table_empty_list() -> None:
    result = format_table([])
    assert "No worktrees found" in result


def test_format_table_detached_worktree() -> None:
    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch=None,
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = format_table([wt])

    assert "detached" in result


# --- format_json ---

def test_format_json_single_worktree() -> None:
    import json

    wt = worktree.WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=3,
    )

    result = format_json([wt])
    data = json.loads(result)

    assert len(data) == 1
    assert data[0]["branch"] == "feat/001"
    assert data[0]["short_id"] == "abc1234"
    assert data[0]["age_days"] == 3
    assert data[0]["current"] is False


def test_format_json_empty_list() -> None:
    import json

    result = format_json([])
    data = json.loads(result)

    assert data == []
