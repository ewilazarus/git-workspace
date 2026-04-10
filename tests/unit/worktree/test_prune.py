from pathlib import Path
from unittest.mock import MagicMock

import pytest

from git_workspace.worktree import (
    resolve_prune_threshold,
    select_prune_candidates,
    WorktreeInfo,
    PruneCandidate,
)
from git_workspace.manifest import Manifest, Prune


ROOT = Path("/workspace")
WORKTREE_1 = ROOT / "feat" / "001"
WORKTREE_2 = ROOT / "feat" / "002"
WORKTREE_3 = ROOT / "feat" / "003"
TIMESTAMP = 1712700000


# --- resolve_prune_threshold ---


def test_resolve_prune_threshold_explicit() -> None:
    result = resolve_prune_threshold(explicit=14)
    assert result == 14


def test_resolve_prune_threshold_manifest() -> None:
    manifest = Manifest(
        version=1,
        base_branch="main",
        prune=Prune(older_than_days=30),
    )
    result = resolve_prune_threshold(manifest=manifest)
    assert result == 30


def test_resolve_prune_threshold_explicit_overrides_manifest() -> None:
    manifest = Manifest(
        version=1,
        base_branch="main",
        prune=Prune(older_than_days=30),
    )
    result = resolve_prune_threshold(explicit=14, manifest=manifest)
    assert result == 14


def test_resolve_prune_threshold_none() -> None:
    result = resolve_prune_threshold()
    assert result is None


def test_resolve_prune_threshold_invalid_explicit() -> None:
    with pytest.raises(ValueError):
        resolve_prune_threshold(explicit=-1)


def test_resolve_prune_threshold_invalid_manifest() -> None:
    manifest = Manifest(
        version=1,
        base_branch="main",
        prune=Prune(older_than_days=-1),
    )
    with pytest.raises(ValueError):
        resolve_prune_threshold(manifest=manifest)


# --- select_prune_candidates ---


def test_select_prune_candidates_empty() -> None:
    candidates = select_prune_candidates([], threshold_days=7)
    assert candidates == []


def test_select_prune_candidates_single_candidate() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=14,
    )
    candidates = select_prune_candidates([wt], threshold_days=7)
    assert len(candidates) == 1
    assert candidates[0].path == WORKTREE_1
    assert candidates[0].branch == "feat/001"
    assert candidates[0].age_days == 14


def test_select_prune_candidates_skips_young() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=5,
    )
    candidates = select_prune_candidates([wt], threshold_days=7)
    assert candidates == []


def test_select_prune_candidates_skips_excluded() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="main",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=14,
    )
    candidates = select_prune_candidates(
        [wt], threshold_days=7, exclude_branches=["main"]
    )
    assert candidates == []


def test_select_prune_candidates_skips_current() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=14,
        current=True,
    )
    candidates = select_prune_candidates([wt], threshold_days=7)
    assert candidates == []


def test_select_prune_candidates_skips_unknown_age() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id=None,
        timestamp=None,
        age_days=None,
    )
    candidates = select_prune_candidates([wt], threshold_days=7)
    assert candidates == []


def test_select_prune_candidates_no_threshold() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=1,
    )
    candidates = select_prune_candidates([wt], threshold_days=None)
    assert len(candidates) == 1


def test_select_prune_candidates_multiple() -> None:
    wt1 = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=14,
    )
    wt2 = WorktreeInfo(
        path=WORKTREE_2,
        branch="feat/002",
        head="def456",
        short_id="def4567",
        timestamp=TIMESTAMP,
        age_days=7,
    )
    wt3 = WorktreeInfo(
        path=WORKTREE_3,
        branch="feat/003",
        head="ghi789",
        short_id="ghi7890",
        timestamp=TIMESTAMP,
        age_days=3,
    )
    candidates = select_prune_candidates([wt1, wt2, wt3], threshold_days=7)
    assert len(candidates) == 2
    # Should be sorted by age descending
    assert candidates[0].age_days == 14
    assert candidates[1].age_days == 7


def test_select_prune_candidates_sorts_by_age() -> None:
    wt1 = WorktreeInfo(
        path=WORKTREE_1,
        branch="feat/001",
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=5,
    )
    wt2 = WorktreeInfo(
        path=WORKTREE_2,
        branch="feat/002",
        head="def456",
        short_id="def4567",
        timestamp=TIMESTAMP,
        age_days=20,
    )
    wt3 = WorktreeInfo(
        path=WORKTREE_3,
        branch="feat/003",
        head="ghi789",
        short_id="ghi7890",
        timestamp=TIMESTAMP,
        age_days=10,
    )
    candidates = select_prune_candidates([wt1, wt2, wt3], threshold_days=5)
    ages = [c.age_days for c in candidates]
    assert ages == [20, 10, 5]


def test_select_prune_candidates_detached_branch() -> None:
    wt = WorktreeInfo(
        path=WORKTREE_1,
        branch=None,
        head="abc123",
        short_id="abc1234",
        timestamp=TIMESTAMP,
        age_days=14,
    )
    candidates = select_prune_candidates([wt], threshold_days=7)
    assert len(candidates) == 1
    assert candidates[0].branch is None
