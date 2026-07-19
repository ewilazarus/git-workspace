from unittest.mock import MagicMock

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace.cli.commands.prune import prune
from git_workspace.errors import UnableToResolveWorkspaceError, WorkspaceLockedError
from git_workspace.workspace.service import PruneFailure
from tests.helpers import make_context

WORKSPACE_DIR = "/workspace"


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.prune.Workspace.resolve")
    mock.return_value.manifest.prune = MagicMock()
    return mock


@pytest.fixture(autouse=True)
def mock_service_create(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.prune.WorkspaceService.create")
    mock.return_value.prune_candidates.return_value = []
    mock.return_value.prune.return_value = []
    return mock


@pytest.fixture
def mock_service(mock_service_create: MagicMock) -> MagicMock:
    return mock_service_create.return_value


def make_worktree(branch: str = "feature/old", age_days: int = 60) -> MagicMock:
    wt = MagicMock()
    wt.branch = branch
    wt.age_days = age_days
    return wt


class TestPrune:
    def test_raises_when_no_workspace_resolvable(self, mock_workspace_resolve: MagicMock) -> None:
        mock_workspace_resolve.side_effect = UnableToResolveWorkspaceError("no workspace")
        with pytest.raises(UnableToResolveWorkspaceError):
            prune(ctx=make_context())

    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        prune(ctx=make_context(WORKSPACE_DIR), older_than_days=30)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_raises_bad_parameter_when_no_threshold_and_no_manifest_prune(
        self, mock_workspace_resolve: MagicMock
    ) -> None:
        mock_workspace_resolve.return_value.manifest.prune = None
        with pytest.raises(typer.BadParameter):
            prune(ctx=make_context())

    def test_passes_threshold_to_service(self, mock_service: MagicMock) -> None:
        prune(ctx=make_context(), older_than_days=30)
        mock_service.prune_candidates.assert_called_once_with(older_than_days=30)

    def test_dry_run_does_not_prune(self, mock_service: MagicMock) -> None:
        mock_service.prune_candidates.return_value = [make_worktree()]

        prune(ctx=make_context(), older_than_days=30, dry_run=True)

        mock_service.prune.assert_not_called()

    def test_apply_prunes_candidates(self, mock_service: MagicMock) -> None:
        candidates = [make_worktree("feature/a"), make_worktree("feature/b")]
        mock_service.prune_candidates.return_value = candidates

        prune(ctx=make_context(), older_than_days=30, dry_run=False)

        mock_service.prune.assert_called_once_with(candidates)

    def test_does_not_prune_when_no_candidates(self, mock_service: MagicMock) -> None:
        prune(ctx=make_context(), older_than_days=30, dry_run=False)

        mock_service.prune.assert_not_called()

    def test_exits_non_zero_when_failures_reported(self, mock_service: MagicMock) -> None:
        worktree = make_worktree()
        mock_service.prune_candidates.return_value = [worktree]
        mock_service.prune.return_value = [
            PruneFailure(worktree=worktree, error=WorkspaceLockedError("locked"))
        ]

        with pytest.raises(typer.Exit) as excinfo:
            prune(ctx=make_context(), older_than_days=30, dry_run=False)

        assert excinfo.value.exit_code == 1
