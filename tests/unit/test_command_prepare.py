from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cli.commands.prepare import prepare
from git_workspace.workspace.service import PrepareOutcome
from tests.helpers import make_context

WORKSPACE_DIR = "/workspace"
RUNTIME_VARS: list[tuple[str, str]] = [("MY_VAR", "my_value")]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.prepare.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_resolve_from_worktree(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "git_workspace.cli.commands.prepare.WorkspaceResolver.resolve_from_worktree"
    )


@pytest.fixture(autouse=True)
def mock_service_create(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.prepare.WorkspaceService.create")
    mock.return_value.prepare_path.return_value = PrepareOutcome(record=MagicMock(), skipped=False)
    return mock


@pytest.fixture
def mock_service(mock_service_create: MagicMock) -> MagicMock:
    return mock_service_create.return_value


class TestPrepare:
    def test_discovers_workspace_from_target_path(
        self, tmp_path: Path, mock_resolve_from_worktree: MagicMock
    ) -> None:
        prepare(ctx=make_context(), path=str(tmp_path))

        mock_resolve_from_worktree.assert_called_once_with(tmp_path.resolve())

    def test_explicit_root_overrides_discovery(
        self, mock_workspace_resolve: MagicMock, mock_resolve_from_worktree: MagicMock
    ) -> None:
        prepare(ctx=make_context(WORKSPACE_DIR), path="/somewhere")

        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)
        mock_resolve_from_worktree.assert_not_called()

    def test_defaults_to_cwd(
        self, mocker: MockerFixture, mock_resolve_from_worktree: MagicMock
    ) -> None:
        cwd = Path("/current/dir")
        mocker.patch("git_workspace.cli.commands.prepare.Path.cwd", return_value=cwd)

        prepare(ctx=make_context())

        mock_resolve_from_worktree.assert_called_once_with(cwd)

    def test_delegates_to_service_prepare_path(
        self, tmp_path: Path, mock_service: MagicMock
    ) -> None:
        prepare(ctx=make_context(), path=str(tmp_path))

        mock_service.prepare_path.assert_called_once_with(
            tmp_path.resolve(),
            force=False,
            runtime_vars={},
            effective_branch=None,
        )

    def test_passes_force(self, tmp_path: Path, mock_service: MagicMock) -> None:
        prepare(ctx=make_context(), path=str(tmp_path), force=True)

        assert mock_service.prepare_path.call_args.kwargs["force"] is True

    def test_passes_runtime_vars_and_effective_branch(
        self, tmp_path: Path, mock_service: MagicMock
    ) -> None:
        prepare(
            ctx=make_context(),
            path=str(tmp_path),
            runtime_vars=RUNTIME_VARS,  # ty:ignore[invalid-argument-type]
            effective_branch="release/x",
        )

        assert mock_service.prepare_path.call_args.kwargs["runtime_vars"] == {"MY_VAR": "my_value"}
        assert mock_service.prepare_path.call_args.kwargs["effective_branch"] == "release/x"
