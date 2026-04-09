from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import worktree
from git_workspace.errors import GitFetchError
from git_workspace.git import WorktreeMetadata
from git_workspace.worktree import UpAction, UpPlan

BRANCH = "feat/001"
BASE = "main"
WORKTREE_PATH = Path("/workspace/feat/001")


@pytest.fixture(autouse=True)
def git_mocks(mocker: MockerFixture):
    mocker.patch("git_workspace.git.list_worktrees_metadata", return_value=[])
    mocker.patch("git_workspace.git.local_branch_exists", return_value=False)
    mocker.patch("git_workspace.git.remote_branch_exists", return_value=False)
    mocker.patch("git_workspace.git.has_remote", return_value=True)
    mocker.patch("git_workspace.git.fetch_origin")
    mocker.patch("git_workspace.git.get_origin_head", return_value=None)


def test_when_worktree_exists_then_resumes(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.list_worktrees_metadata",
        return_value=[WorktreeMetadata(path=WORKTREE_PATH, head="abc123", branch=BRANCH)],
    )

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.RESUME, branch=BRANCH, existing_worktree_path=WORKTREE_PATH)


def test_existing_worktree_wins_over_local_branch(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.list_worktrees_metadata",
        return_value=[WorktreeMetadata(path=WORKTREE_PATH, head="abc123", branch=BRANCH)],
    )
    mocker.patch("git_workspace.git.local_branch_exists", return_value=True)

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan.action == UpAction.RESUME


def test_when_local_branch_exists_then_creates_from_local(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.local_branch_exists", return_value=True)

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.CREATE_FROM_LOCAL, branch=BRANCH)


def test_local_branch_wins_over_remote_branch(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.local_branch_exists", return_value=True)
    mocker.patch("git_workspace.git.remote_branch_exists", return_value=True)

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan.action == UpAction.CREATE_FROM_LOCAL


def test_when_remote_branch_exists_then_creates_from_remote(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.remote_branch_exists", return_value=True)

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=BRANCH)
    mocker.patch("git_workspace.git.fetch_origin").assert_not_called()


def test_when_remote_branch_found_after_fetch_then_creates_from_remote(
    mocker: MockerFixture,
) -> None:
    mocker.patch(
        "git_workspace.git.remote_branch_exists",
        side_effect=[False, True],
    )

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=BRANCH)


def test_fetch_is_called_only_after_all_local_and_known_remote_checks_fail(
    mocker: MockerFixture,
) -> None:
    fetch_mock = mocker.patch("git_workspace.git.fetch_origin")

    worktree.resolve_up_plan(BRANCH)

    fetch_mock.assert_called_once()


def test_fetch_is_not_called_when_local_branch_exists(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.local_branch_exists", return_value=True)
    fetch_mock = mocker.patch("git_workspace.git.fetch_origin")

    worktree.resolve_up_plan(BRANCH)

    fetch_mock.assert_not_called()


def test_fetch_is_not_called_when_worktree_exists(mocker: MockerFixture) -> None:
    mocker.patch(
        "git_workspace.git.list_worktrees_metadata",
        return_value=[WorktreeMetadata(path=WORKTREE_PATH, head="abc123", branch=BRANCH)],
    )
    fetch_mock = mocker.patch("git_workspace.git.fetch_origin")

    worktree.resolve_up_plan(BRANCH)

    fetch_mock.assert_not_called()


def test_when_branch_not_found_anywhere_then_creates_from_base() -> None:
    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.CREATE_FROM_BASE, branch=BRANCH, base_branch="main")


def test_explicit_base_branch_is_used_when_creating_from_base() -> None:
    plan = worktree.resolve_up_plan(BRANCH, explicit_base_branch="develop")

    assert plan.action == UpAction.CREATE_FROM_BASE
    assert plan.base_branch == "develop"


def test_fetch_error_propagates(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.fetch_origin", side_effect=GitFetchError("fetch failed"))

    with pytest.raises(GitFetchError):
        worktree.resolve_up_plan(BRANCH)


def test_fetch_is_not_called_when_no_remote(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.has_remote", return_value=False)
    fetch_mock = mocker.patch("git_workspace.git.fetch_origin")

    worktree.resolve_up_plan(BRANCH)

    fetch_mock.assert_not_called()


def test_when_no_remote_and_branch_not_found_then_creates_from_base(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.has_remote", return_value=False)

    plan = worktree.resolve_up_plan(BRANCH)

    assert plan == UpPlan(action=UpAction.CREATE_FROM_BASE, branch=BRANCH, base_branch="main")
