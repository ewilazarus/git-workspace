from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import WorkspaceLinkError
from git_workspace.manifest import Link

ROOT = Path("/workspace")
WORKTREE = ROOT / "feat" / "001"
FILES_ROOT = ROOT / ".workspace" / "files"
SOURCE = FILES_ROOT / "env"
TARGET = WORKTREE / ".env"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_file(SOURCE)
    fs.create_dir(WORKTREE)


@pytest.fixture(autouse=True)
def mock_skip_worktree(mocker: MockerFixture):
    return mocker.patch("git_workspace.git.skip_worktree")


# --- normal links ---

def test_normal_link_creates_symlink(fs: FakeFilesystem) -> None:
    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env")])

    assert TARGET.is_symlink()
    assert TARGET.readlink() == SOURCE


def test_normal_link_succeeds_if_correct_symlink_already_exists(fs: FakeFilesystem) -> None:
    TARGET.symlink_to(SOURCE)

    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env")])


def test_normal_link_fails_if_target_exists_as_file(fs: FakeFilesystem) -> None:
    fs.create_file(TARGET)

    with pytest.raises(WorkspaceLinkError):
        workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env")])


def test_normal_link_fails_if_target_is_wrong_symlink(fs: FakeFilesystem) -> None:
    other = FILES_ROOT / "other"
    fs.create_file(other)
    TARGET.symlink_to(other)

    with pytest.raises(WorkspaceLinkError):
        workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env")])


def test_normal_link_creates_parent_directories(fs: FakeFilesystem) -> None:
    nested_target = WORKTREE / "config" / "settings.json"
    source = FILES_ROOT / "settings.json"
    fs.create_file(source)

    workspace.apply_links(ROOT, WORKTREE, [Link(source="settings.json", target="config/settings.json")])

    assert nested_target.is_symlink()


def test_normal_link_does_not_call_skip_worktree(mock_skip_worktree, fs: FakeFilesystem) -> None:
    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env")])

    mock_skip_worktree.assert_not_called()


# --- override links ---

def test_override_link_creates_symlink(fs: FakeFilesystem) -> None:
    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env", override=True)])

    assert TARGET.is_symlink()
    assert TARGET.readlink() == SOURCE


def test_override_link_replaces_existing_file(fs: FakeFilesystem) -> None:
    fs.create_file(TARGET)

    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env", override=True)])

    assert TARGET.is_symlink()


def test_override_link_replaces_existing_symlink(fs: FakeFilesystem) -> None:
    other = FILES_ROOT / "other"
    fs.create_file(other)
    TARGET.symlink_to(other)

    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env", override=True)])

    assert TARGET.readlink() == SOURCE


def test_override_link_calls_skip_worktree(mock_skip_worktree, fs: FakeFilesystem) -> None:
    workspace.apply_links(ROOT, WORKTREE, [Link(source="env", target=".env", override=True)])

    mock_skip_worktree.assert_called_once_with(".env", cwd=WORKTREE)


