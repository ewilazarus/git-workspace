from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.up import up
from tests.helpers import make_context

BRANCH = "feature/my-branch"
BASE_BRANCH = "main"
WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_service_create(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.up.WorkspaceService.create")


@pytest.fixture(autouse=True)
def mock_worktree_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.up.Worktree.resolve")
    mock.return_value.branch = BRANCH
    return mock


@pytest.fixture
def mock_service(mock_service_create: MagicMock) -> MagicMock:
    return mock_service_create.return_value


class TestUp:
    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        up(ctx=make_context(WORKSPACE_DIR), branch=BRANCH)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_builds_service_for_resolved_workspace(
        self, mock_workspace_resolve: MagicMock, mock_service_create: MagicMock
    ) -> None:
        up(ctx=make_context(), branch=BRANCH)
        mock_service_create.assert_called_once_with(mock_workspace_resolve.return_value)

    def test_delegates_to_service_up(self, mock_service: MagicMock) -> None:
        up(ctx=make_context(), branch=BRANCH, base_branch=BASE_BRANCH)
        mock_service.up.assert_called_once_with(
            BRANCH,
            base_branch=BASE_BRANCH,
            runtime_vars={},
            detached=False,
            effective_branch=None,
        )

    def test_resolves_branch_from_cwd_when_omitted(
        self,
        mock_workspace_resolve: MagicMock,
        mock_worktree_resolve: MagicMock,
        mock_service: MagicMock,
    ) -> None:
        up(ctx=make_context())
        mock_worktree_resolve.assert_called_once_with(mock_workspace_resolve.return_value, None)
        assert mock_service.up.call_args.args[0] == BRANCH

    def test_passes_runtime_vars(self, mock_service: MagicMock) -> None:
        up(ctx=make_context(), branch=BRANCH, runtime_vars=RUNTIME_VARS)  # ty:ignore[invalid-argument-type]
        assert mock_service.up.call_args.kwargs["runtime_vars"] == {"MY_VAR": "my_value"}

    def test_passes_detached(self, mock_service: MagicMock) -> None:
        up(ctx=make_context(), branch=BRANCH, detached=True)
        assert mock_service.up.call_args.kwargs["detached"] is True

    def test_passes_effective_branch(self, mock_service: MagicMock) -> None:
        up(ctx=make_context(), branch=BRANCH, effective_branch="gabriel/impersonated")
        assert mock_service.up.call_args.kwargs["effective_branch"] == "gabriel/impersonated"
