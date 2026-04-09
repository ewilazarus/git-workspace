import pytest
from pytest_mock import MockerFixture

from git_workspace import worktree


@pytest.fixture(autouse=True)
def mock_origin_head(mocker: MockerFixture):
    return mocker.patch("git_workspace.git.get_origin_head", return_value=None)


def test_explicit_wins_over_all(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_origin_head", return_value="develop")

    result = worktree.resolve_base_branch(
        explicit="my-base",
        manifest_base_branch="manifest-base",
    )

    assert result == "my-base"


def test_manifest_base_branch_wins_over_origin_head(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_origin_head", return_value="develop")

    result = worktree.resolve_base_branch(manifest_base_branch="manifest-base")

    assert result == "manifest-base"


def test_origin_head_wins_over_main_fallback(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.git.get_origin_head", return_value="develop")

    result = worktree.resolve_base_branch()

    assert result == "develop"


def test_falls_back_to_main_when_nothing_else_available() -> None:
    result = worktree.resolve_base_branch()

    assert result == "main"
