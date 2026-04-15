from pathlib import Path

import pytest

from git_workspace.workspace import WorkspacePaths

ROOT = Path("/")


@pytest.fixture
def workspace_paths() -> WorkspacePaths:
    return WorkspacePaths(ROOT)


def test_root_path_is_maintained(workspace_paths) -> None:
    expected = ROOT
    actual = workspace_paths.root
    assert actual == expected


def test_composes_correct_config_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".workspace"
    actual = workspace_paths.config
    assert actual == expected


def test_composes_correct_assets_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".workspace" / "assets"
    actual = workspace_paths.assets
    assert actual == expected


def test_composes_correct_bin_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".workspace" / "bin"
    actual = workspace_paths.bin
    assert actual == expected


def test_composes_correct_manifest_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".workspace" / "manifest.toml"
    actual = workspace_paths.manifest
    assert actual == expected


def test_composes_correct_git_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".git"
    actual = workspace_paths.git
    assert actual == expected


def test_composes_correct_ignore_file_path(workspace_paths: WorkspacePaths) -> None:
    expected = ROOT / ".git" / "info" / "exclude"
    actual = workspace_paths.ignore_file
    assert actual == expected


def test_composes_correct_worktree_path(workspace_paths: WorkspacePaths) -> None:
    branch = "feat/GWS-001"

    expected = ROOT / "feat" / "GWS-001"
    actual = workspace_paths.worktree(branch)

    assert actual == expected
