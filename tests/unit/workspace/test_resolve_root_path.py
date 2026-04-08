import os

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from git_workspace import workspace
from git_workspace.errors import (
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
)

HOME = "/Users/ewilazarus"
WORKSPACE_BASE = f"{HOME}/Workspace"
WORKSPACE_1 = f"{WORKSPACE_BASE}/good-workspace"
WORKSPACE_2 = f"{WORKSPACE_BASE}/bad-workspace-1"
WORKSPACE_3 = f"{WORKSPACE_BASE}/bad-workspace-2"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_dir(HOME)

    fs.create_dir(f"{WORKSPACE_1}/.git")
    fs.create_file(f"{WORKSPACE_1}/.workspace/manifest.toml")
    fs.create_file(f"{WORKSPACE_1}/feat/001/README.md")
    fs.create_file(f"{WORKSPACE_1}/feat/002/README.md")

    fs.create_file(f"{WORKSPACE_2}/.workspace/manifest.toml")
    fs.create_file(f"{WORKSPACE_2}/feat/001/README.md")

    fs.create_dir(f"{WORKSPACE_3}/.git")
    fs.create_file(f"{WORKSPACE_3}/feat/001/README.md")


@pytest.mark.parametrize(
    "cwd, raw_path",
    [
        # Absolute path resolution
        (HOME, WORKSPACE_1),
        # Relative path resolution
        (WORKSPACE_BASE, "good-workspace"),
        (WORKSPACE_1, "."),
        (f"{WORKSPACE_1}/.git", ".."),
        (f"{WORKSPACE_1}/.workspace", ".."),
        (f"{WORKSPACE_1}/feat", ".."),
        (f"{WORKSPACE_1}/feat/001", "../.."),
        (f"{WORKSPACE_1}/feat/002", "../.."),
    ],
)
def test_when_user_provides_path_to_existing_valid_workspace_root_then_succeeds_to_resolve_root_path(
    cwd: str, raw_path: str
) -> None:
    os.chdir(cwd)

    expected = WORKSPACE_1
    actual = str(workspace.resolve_root_path(raw_path))

    assert actual == expected


@pytest.mark.parametrize(
    "cwd, raw_path",
    [
        # Absolute path resolution (no .git)
        (HOME, WORKSPACE_2),
        # Relative path resolution (no .git)
        (WORKSPACE_BASE, "bad-workspace-1"),
        (WORKSPACE_2, "."),
        (f"{WORKSPACE_2}/.workspace", ".."),
        (f"{WORKSPACE_2}/feat", ".."),
        (f"{WORKSPACE_2}/feat/001", "../.."),
        # Absolute path resolution (no .workspace/manifest.toml)
        (HOME, WORKSPACE_3),
        # Relative path resolution (no .workspace/manifest.toml)
        (WORKSPACE_BASE, "bad-workspace-2"),
        (WORKSPACE_3, "."),
        (f"{WORKSPACE_3}/.git", ".."),
        (f"{WORKSPACE_3}/feat", ".."),
        (f"{WORKSPACE_3}/feat/001", "../.."),
    ],
)
def test_when_user_provides_path_to_existing_invalid_workspace_root_then_fails_to_resolve_root_path(
    cwd: str, raw_path: str
) -> None:
    os.chdir(cwd)

    with pytest.raises(InvalidWorkspaceRootError):
        workspace.resolve_root_path(raw_path)


@pytest.mark.parametrize(
    "raw_path",
    [
        # Absolute invalid path resolution
        ("/i/dont/exist"),
        # Relative invalid path resolution
        ("i/dont/exist"),
    ],
)
def test_when_user_provides_non_existing_path_then_fails_to_resolve_root_path(
    raw_path: str,
) -> None:
    with pytest.raises(InvalidWorkspaceRootError):
        workspace.resolve_root_path(raw_path)


@pytest.mark.parametrize(
    "cwd",
    [
        (f"{WORKSPACE_1}/.git"),
        (f"{WORKSPACE_1}/.workspace"),
        (f"{WORKSPACE_1}/feat/001"),
        (f"{WORKSPACE_1}/feat/002"),
        (f"{WORKSPACE_1}/feat"),
        (WORKSPACE_1),
    ],
)
def test_when_implicitly_resolving_from_within_a_valid_workspace_root_then_succeeds_to_resolve_root_path(
    cwd: str,
) -> None:
    os.chdir(cwd)

    expected = WORKSPACE_1
    actual = str(workspace.resolve_root_path())

    assert actual == expected


@pytest.mark.parametrize(
    "cwd",
    [
        (f"{WORKSPACE_2}/.workspace"),
        (f"{WORKSPACE_2}/feat/001"),
        (f"{WORKSPACE_2}/feat"),
        (WORKSPACE_2),
        (f"{WORKSPACE_3}/.git"),
        (f"{WORKSPACE_3}/feat/001"),
        (f"{WORKSPACE_3}/feat"),
        (WORKSPACE_3),
        (WORKSPACE_BASE),
        (HOME),
        ("/"),
    ],
)
def test_when_implicitly_resolving_from_within_an_invalid_workspace_root_then_fails_to_resolve_root_path(
    cwd: str,
) -> None:
    os.chdir(cwd)

    with pytest.raises(UnableToResolveWorkspaceRootError):
        workspace.resolve_root_path()
