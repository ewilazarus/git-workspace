from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from git_workspace import workspace

ROOT = Path("/workspace")


def test_removes_empty_parent(fs: FakeFilesystem) -> None:
    worktree = ROOT / "feat" / "001"
    fs.create_dir(ROOT / "feat")

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert not (ROOT / "feat").exists()


def test_removes_multiple_empty_parents(fs: FakeFilesystem) -> None:
    worktree = ROOT / "a" / "b" / "c"
    fs.create_dir(ROOT / "a" / "b")

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert not (ROOT / "a").exists()


def test_stops_at_non_empty_parent(fs: FakeFilesystem) -> None:
    worktree = ROOT / "feat" / "001"
    fs.create_dir(ROOT / "feat")
    fs.create_file(ROOT / "feat" / "002" / "some_file.txt")

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert (ROOT / "feat").exists()


def test_stops_at_root(fs: FakeFilesystem) -> None:
    worktree = ROOT / "solo"
    fs.create_dir(ROOT)

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert ROOT.exists()


def test_does_nothing_when_parent_does_not_exist(fs: FakeFilesystem) -> None:
    worktree = ROOT / "feat" / "001"
    fs.create_dir(ROOT)

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert ROOT.exists()


def test_sibling_worktree_prevents_removal(fs: FakeFilesystem) -> None:
    worktree = ROOT / "feat" / "001"
    fs.create_dir(ROOT / "feat" / "002")

    workspace.cleanup_empty_parent_dirs(worktree, stop_at=ROOT)

    assert (ROOT / "feat").exists()
