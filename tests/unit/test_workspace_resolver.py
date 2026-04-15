import os
from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockerFixture

from git_workspace.errors import InvalidWorkspaceError, UnableToResolveWorkspaceError
from git_workspace.workspace import WorkspaceResolver

WORKSPACE = "/Users/ewilzarus/Workspaces/git-workspace"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_dir(f"{WORKSPACE}/.git")
    fs.create_file(f"{WORKSPACE}/.workspace/manifest.toml")
    fs.create_dir("/")


@pytest.fixture(autouse=True)
def manifest_load(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.workspace.Manifest.load")


@pytest.mark.parametrize("raw_workspace_dir", [WORKSPACE, None])
def test_happy_path(raw_workspace_dir: str | None) -> None:
    os.chdir(WORKSPACE)
    workspace = WorkspaceResolver.resolve(raw_workspace_dir)

    expected = Path(WORKSPACE)
    actual = workspace.paths.root

    assert actual == expected


def test_raises_when_invalid_dir() -> None:
    with pytest.raises(InvalidWorkspaceError):
        WorkspaceResolver.resolve("/something-else")


@pytest.mark.parametrize("raw_workspace_dir", ["/", None])
def test_raises_when_not_root_or_descendant(raw_workspace_dir: str | None) -> None:
    if raw_workspace_dir is None:
        os.chdir("/")

    with pytest.raises(UnableToResolveWorkspaceError):
        WorkspaceResolver.resolve(raw_workspace_dir)
