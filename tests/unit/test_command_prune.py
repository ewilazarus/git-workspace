from unittest.mock import MagicMock

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace.cli.commands.prune import prune
from git_workspace.errors import UnableToResolveWorkspaceError

WORKSPACE_DIR = "/workspace"


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.prune.Workspace.resolve")
    mock.return_value.manifest.prune = None
    mock.return_value.list_worktrees.return_value = []
    return mock


def make_worktree(branch: str = "feature/old", age_days: int = 60) -> MagicMock:
    wt = MagicMock()
    wt.branch = branch
    wt.age_days = age_days
    return wt


class TestPrune:
    def test_raises_when_no_workspace_resolvable(self, mock_workspace_resolve: MagicMock) -> None:
        mock_workspace_resolve.side_effect = UnableToResolveWorkspaceError("no workspace")
        with pytest.raises(UnableToResolveWorkspaceError):
            prune()

    def test_resolves_workspace(self, mock_workspace_resolve: MagicMock) -> None:
        prune(root=WORKSPACE_DIR, older_than_days=30)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_raises_bad_parameter_when_no_threshold_and_no_manifest_prune(
        self, mock_workspace_resolve: MagicMock
    ) -> None:
        mock_workspace_resolve.return_value.manifest.prune = None
        with pytest.raises(typer.BadParameter):
            prune()

    def test_uses_older_than_days_arg_as_threshold(self, mock_workspace_resolve: MagicMock) -> None:
        within_threshold = make_worktree(age_days=5)
        beyond_threshold = make_worktree(age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [
            within_threshold,
            beyond_threshold,
        ]

        prune(older_than_days=30, dry_run=False)

        within_threshold.delete.assert_not_called()
        beyond_threshold.delete.assert_called_once_with(force=True)

    def test_uses_manifest_prune_threshold_when_arg_not_provided(
        self, mock_workspace_resolve: MagicMock
    ) -> None:
        prune_config = MagicMock()
        prune_config.older_than_days = 30
        prune_config.exclude_branches = []
        mock_workspace_resolve.return_value.manifest.prune = prune_config
        old_wt = make_worktree(age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [old_wt]

        prune(dry_run=False)

        old_wt.delete.assert_called_once_with(force=True)

    def test_older_than_days_arg_takes_precedence_over_manifest(
        self, mock_workspace_resolve: MagicMock
    ) -> None:
        prune_config = MagicMock()
        prune_config.older_than_days = 90
        prune_config.exclude_branches = []
        mock_workspace_resolve.return_value.manifest.prune = prune_config
        wt = make_worktree(age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [wt]

        # manifest threshold=90 would exclude wt (age=60), but arg threshold=30 includes it
        prune(older_than_days=30, dry_run=False)

        wt.delete.assert_called_once_with(force=True)

    def test_excludes_protected_branches_from_candidates(
        self, mock_workspace_resolve: MagicMock
    ) -> None:
        prune_config = MagicMock()
        prune_config.older_than_days = 30
        prune_config.exclude_branches = ["main"]
        mock_workspace_resolve.return_value.manifest.prune = prune_config
        protected_wt = make_worktree(branch="main", age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [protected_wt]

        prune(dry_run=False)

        protected_wt.delete.assert_not_called()

    def test_dry_run_does_not_delete_worktrees(self, mock_workspace_resolve: MagicMock) -> None:
        old_wt = make_worktree(age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [old_wt]

        prune(older_than_days=30, dry_run=True)

        old_wt.delete.assert_not_called()

    def test_apply_deletes_each_candidate(self, mock_workspace_resolve: MagicMock) -> None:
        wt1 = make_worktree(branch="feature/a", age_days=60)
        wt2 = make_worktree(branch="feature/b", age_days=60)
        mock_workspace_resolve.return_value.list_worktrees.return_value = [wt1, wt2]

        prune(older_than_days=30, dry_run=False)

        wt1.delete.assert_called_once_with(force=True)
        wt2.delete.assert_called_once_with(force=True)
