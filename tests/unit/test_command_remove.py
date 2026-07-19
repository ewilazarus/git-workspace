from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.remove import remove
from tests.helpers import make_context

BRANCH = "feature/my-branch"
WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.remove.Workspace.resolve")
    mock.return_value.resolve_worktree.return_value.branch = BRANCH
    return mock


@pytest.fixture(autouse=True)
def mock_service_create(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.remove.WorkspaceService.create")


@pytest.fixture
def mock_service(mock_service_create: MagicMock) -> MagicMock:
    return mock_service_create.return_value


class TestRemove:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        remove(ctx=make_context(WORKSPACE_DIR))
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_worktree(self, mock_workspace_resolve: MagicMock) -> None:
        remove(ctx=make_context(), branch=BRANCH)
        mock_workspace_resolve.return_value.resolve_worktree.assert_called_once_with(BRANCH)

    def test_delegates_to_service_remove(self, mock_service: MagicMock) -> None:
        remove(ctx=make_context(), branch=BRANCH)
        mock_service.remove.assert_called_once_with(
            BRANCH,
            force=False,
            runtime_vars={},
            effective_branch=None,
        )

    def test_passes_force(self, mock_service: MagicMock) -> None:
        remove(ctx=make_context(), force=True)
        assert mock_service.remove.call_args.kwargs["force"] is True

    def test_passes_runtime_vars(self, mock_service: MagicMock) -> None:
        remove(ctx=make_context(), runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        assert mock_service.remove.call_args.kwargs["runtime_vars"] == {"MY_VAR": "my_value"}

    def test_passes_effective_branch(self, mock_service: MagicMock) -> None:
        remove(ctx=make_context(), effective_branch="gabriel/impersonated")
        assert mock_service.remove.call_args.kwargs["effective_branch"] == "gabriel/impersonated"
