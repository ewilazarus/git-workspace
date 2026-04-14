from git_workspace.errors import InvalidWorkspaceError
from pathlib import Path
from git_workspace.workspace import WorkspaceValidator
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

WORKSPACE_HAPPY = "/happy"
WORKSPACE_NOT_DIRECTORY = "/not-directory"
WORKSPACE_GIT_ABSENT = "/git-absent"
WORKSPACE_CONFIG_ABSENT = "/config-absent"
WORKSPACE_MANIFEST_ABSENT = "/manifest-absent"


@pytest.fixture(autouse=True)
def filesystem(fs: FakeFilesystem) -> None:
    fs.create_dir(f"{WORKSPACE_HAPPY}/.git")
    fs.create_file(f"{WORKSPACE_HAPPY}/.workspace/manifest.toml")
    fs.create_file(f"{WORKSPACE_GIT_ABSENT}/.workspace/manifest.toml")
    fs.create_dir(f"{WORKSPACE_CONFIG_ABSENT}/.git")
    fs.create_dir(f"{WORKSPACE_MANIFEST_ABSENT}/.git")
    fs.create_dir(f"{WORKSPACE_MANIFEST_ABSENT}/.workspace")


def test_happy_path() -> None:
    root = Path(WORKSPACE_HAPPY)
    WorkspaceValidator.validate(root)


def test_raises_when_path_is_not_a_directory() -> None:
    root = Path(WORKSPACE_NOT_DIRECTORY)
    with pytest.raises(InvalidWorkspaceError):
        WorkspaceValidator.validate(root)


def test_raises_when_relative_git_dir_absent() -> None:
    root = Path(WORKSPACE_GIT_ABSENT)
    with pytest.raises(InvalidWorkspaceError):
        WorkspaceValidator.validate(root)


def test_raises_when_relative_config_dir_absent() -> None:
    root = Path(WORKSPACE_CONFIG_ABSENT)
    with pytest.raises(InvalidWorkspaceError):
        WorkspaceValidator.validate(root)


def test_raises_when_relative_manifest_absent() -> None:
    root = Path(WORKSPACE_MANIFEST_ABSENT)
    with pytest.raises(InvalidWorkspaceError):
        WorkspaceValidator.validate(root)
