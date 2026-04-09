from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from git_workspace import workspace

WORKTREE = Path("/workspace/feat/001")
GIT_DIR = Path("/workspace/.git/worktrees/feat-001")
EXCLUDE_PATH = GIT_DIR / "info" / "exclude"

MANAGED_BEGIN = "# BEGIN git-workspace managed"
MANAGED_END = "# END git-workspace managed"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_dir(GIT_DIR / "info")
    fs.create_file(WORKTREE / ".git", contents=f"gitdir: {GIT_DIR}\n")


def test_writes_managed_block(fs: FakeFilesystem) -> None:
    workspace.sync_exclude_block(WORKTREE, [".env", "local.json"])

    content = EXCLUDE_PATH.read_text()
    assert MANAGED_BEGIN in content
    assert ".env" in content
    assert "local.json" in content
    assert MANAGED_END in content


def test_idempotent_on_repeated_runs(fs: FakeFilesystem) -> None:
    workspace.sync_exclude_block(WORKTREE, [".env"])
    workspace.sync_exclude_block(WORKTREE, [".env"])

    content = EXCLUDE_PATH.read_text()
    assert content.count(MANAGED_BEGIN) == 1
    assert content.count(".env") == 1


def test_leaves_unrelated_entries_untouched(fs: FakeFilesystem) -> None:
    EXCLUDE_PATH.write_text("*.pyc\n__pycache__\n")

    workspace.sync_exclude_block(WORKTREE, [".env"])

    content = EXCLUDE_PATH.read_text()
    assert "*.pyc" in content
    assert "__pycache__" in content


def test_replaces_existing_managed_block(fs: FakeFilesystem) -> None:
    EXCLUDE_PATH.write_text(
        f"{MANAGED_BEGIN}\nold-entry\n{MANAGED_END}\n"
    )

    workspace.sync_exclude_block(WORKTREE, ["new-entry"])

    content = EXCLUDE_PATH.read_text()
    assert "old-entry" not in content
    assert "new-entry" in content


def test_creates_exclude_file_if_missing(fs: FakeFilesystem) -> None:
    workspace.sync_exclude_block(WORKTREE, [".env"])

    assert EXCLUDE_PATH.exists()


def test_empty_targets_writes_empty_managed_block(fs: FakeFilesystem) -> None:
    workspace.sync_exclude_block(WORKTREE, [])

    content = EXCLUDE_PATH.read_text()
    assert MANAGED_BEGIN in content
    assert MANAGED_END in content
