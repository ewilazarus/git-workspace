from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.errors import WorktreeResolutionError
from git_workspace.workspace.models import ManagedWorktree, ProviderKind
from git_workspace.workspace.worktree import Worktree

BRANCH = "feat/GWS-001"
BASE_BRANCH = "main"
WORKSPACE_DIR = Path("/workspace")
WORKTREE_DIR = Path("/workspace/feat/GWS-001")


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKSPACE_DIR
    mock.manifest.base_branch = BASE_BRANCH
    mock.paths.worktree.return_value = WORKTREE_DIR
    mock.provider.kind = ProviderKind.NATIVE_GIT
    return mock


@pytest.fixture
def worktree(workspace: MagicMock) -> Worktree:
    return Worktree(workspace=workspace, dir=WORKTREE_DIR, branch=BRANCH)


def managed(branch: str = BRANCH, directory: Path = WORKTREE_DIR) -> ManagedWorktree:
    return ManagedWorktree(
        repository_path=WORKSPACE_DIR,
        worktree_path=directory,
        branch=branch,
        provider_kind=ProviderKind.NATIVE_GIT,
    )


class TestList:
    @pytest.fixture(autouse=True)
    def mock_directory_birthtime(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch(
            "git_workspace.workspace.worktree.directory_birthtime",
            return_value=datetime(2025, 1, 1),
        )

    def test_delegates_to_provider_with_workspace_directory(self, workspace: MagicMock) -> None:
        workspace.provider.list.return_value = []

        Worktree.list(workspace)

        workspace.provider.list.assert_called_once_with(workspace.dir)

    def test_constructs_worktree_for_each_managed_worktree(self, workspace: MagicMock) -> None:
        workspace.provider.list.return_value = [managed()]

        result = Worktree.list(workspace)

        assert len(result) == 1
        assert result[0].workspace is workspace
        assert result[0].dir == WORKTREE_DIR.resolve()
        assert result[0].branch == BRANCH
        assert result[0].is_new is False
        assert result[0].timestamp == datetime(2025, 1, 1)


class TestResolve:
    def test_returns_existing_worktree_when_branch_provided_and_found(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=worktree)

        result = Worktree.resolve(workspace, BRANCH)

        assert result is worktree

    def test_raises_when_branch_provided_but_not_found(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=None)

        with pytest.raises(WorktreeResolutionError):
            Worktree.resolve(workspace, BRANCH)

    def test_delegates_to_resolve_from_cwd_when_no_branch(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mock_resolve_from_cwd = mocker.patch.object(
            Worktree, "_resolve_from_cwd", return_value=worktree
        )

        Worktree.resolve(workspace, None)

        mock_resolve_from_cwd.assert_called_once_with(workspace)

    def test_returns_cwd_result_when_no_branch(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_resolve_from_cwd", return_value=worktree)

        result = Worktree.resolve(workspace, None)

        assert result is worktree
