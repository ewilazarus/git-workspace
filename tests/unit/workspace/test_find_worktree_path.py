from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import WorktreeNotFoundError
from git_workspace.git import WorktreeMetadata

BRANCH = "feat/001"
WORKTREE_PATH = Path("/workspace/feat/001")


@pytest.fixture(autouse=True)
def mock_list_worktrees(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.list_worktrees_metadata",
        return_value=[
            WorktreeMetadata(path=WORKTREE_PATH, head="abc123", branch=BRANCH),
        ],
    )


def test_returns_path_for_existing_branch() -> None:
    result = workspace.find_worktree_path(BRANCH)

    assert result == WORKTREE_PATH


def test_raises_when_no_worktree_exists(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.list_worktrees_metadata", return_value=[])

    with pytest.raises(WorktreeNotFoundError):
        workspace.find_worktree_path(BRANCH)


def test_error_message_suggests_up_command(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.list_worktrees_metadata", return_value=[])

    with pytest.raises(WorktreeNotFoundError, match="up"):
        workspace.find_worktree_path(BRANCH)


def test_does_not_match_different_branch(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.list_worktrees_metadata",
        return_value=[
            WorktreeMetadata(path=Path("/workspace/feat/002"), head="abc123", branch="feat/002"),
        ],
    )

    with pytest.raises(WorktreeNotFoundError):
        workspace.find_worktree_path(BRANCH)
