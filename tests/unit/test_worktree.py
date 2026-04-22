from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.errors import WorktreeResolutionError
from git_workspace.worktree import Worktree

BRANCH = "feat/GWS-001"
BASE_BRANCH = "main"
WORKTREE_DIR = Path("/workspace/feat/GWS-001")


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = Path("/workspace")
    mock.paths.root = Path("/workspace")
    mock.manifest.base_branch = BASE_BRANCH
    return mock


@pytest.fixture
def worktree(workspace: MagicMock) -> Worktree:
    return Worktree(workspace=workspace, dir=WORKTREE_DIR, branch=BRANCH)


class TestList:
    @pytest.fixture
    def mock_git_list_worktrees(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.worktree.git.list_worktrees")

    @pytest.fixture(autouse=True)
    def mock_directory_birthtime(self, mocker: MockerFixture) -> MagicMock:
        from datetime import datetime

        return mocker.patch(
            "git_workspace.worktree._directory_birthtime",
            return_value=datetime(2025, 1, 1),
        )

    def test_calls_git_list_worktrees_with_workspace_directory(
        self, workspace: MagicMock, mock_git_list_worktrees: MagicMock
    ) -> None:
        mock_git_list_worktrees.return_value = []

        Worktree.list(workspace)

        mock_git_list_worktrees.assert_called_once_with(cwd=workspace.dir)

    def test_constructs_worktree_for_each_raw_result(
        self, workspace: MagicMock, mock_git_list_worktrees: MagicMock
    ) -> None:
        raw_directory = "/workspace/feat/GWS-001"
        mock_git_list_worktrees.return_value = [{"directory": raw_directory, "branch": BRANCH}]

        result = Worktree.list(workspace)

        assert len(result) == 1
        assert result[0].workspace is workspace
        assert result[0].dir == Path(raw_directory).resolve()
        assert result[0].branch == BRANCH
        assert result[0].is_new is False


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


class TestResolveOrCreate:
    def test_returns_existing_worktree_when_found(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=worktree)

        result = Worktree.resolve_or_create(workspace, BRANCH, BASE_BRANCH)

        assert result is worktree

    def test_creates_from_local_branch_when_not_existing(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=None)
        mocker.patch.object(Worktree, "_try_create_from_local_branch", return_value=worktree)

        result = Worktree.resolve_or_create(workspace, BRANCH, BASE_BRANCH)

        assert result is worktree

    def test_creates_from_remote_branch_when_not_local(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=None)
        mocker.patch.object(Worktree, "_try_create_from_local_branch", return_value=None)
        mocker.patch.object(Worktree, "_try_create_from_remote_branch", return_value=worktree)

        result = Worktree.resolve_or_create(workspace, BRANCH, BASE_BRANCH)

        assert result is worktree

    def test_creates_new_worktree_as_last_resort(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_try_resolve_existing", return_value=None)
        mocker.patch.object(Worktree, "_try_create_from_local_branch", return_value=None)
        mocker.patch.object(Worktree, "_try_create_from_remote_branch", return_value=None)
        mocker.patch.object(Worktree, "_create_new", return_value=worktree)

        result = Worktree.resolve_or_create(workspace, BRANCH, BASE_BRANCH)

        assert result is worktree

    def test_delegates_to_resolve_from_cwd_when_no_branch(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mock_resolve_from_cwd = mocker.patch.object(
            Worktree, "_resolve_from_cwd", return_value=worktree
        )

        Worktree.resolve_or_create(workspace, None, BASE_BRANCH)

        mock_resolve_from_cwd.assert_called_once_with(workspace)

    def test_returns_cwd_result_when_no_branch(
        self, mocker: MockerFixture, workspace: MagicMock, worktree: Worktree
    ) -> None:
        mocker.patch.object(Worktree, "_resolve_from_cwd", return_value=worktree)

        result = Worktree.resolve_or_create(workspace, None, BASE_BRANCH)

        assert result is worktree


class TestTryCreateFromRemoteBranch:
    @pytest.fixture(autouse=True)
    def mock_git(self, mocker: MockerFixture) -> None:
        mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=False)
        mocker.patch("git_workspace.worktree.git.local_branch_exists", return_value=False)
        mocker.patch("git_workspace.worktree.git.create_worktree_from_remote_branch")
        mocker.patch("git_workspace.worktree.git.create_worktree_from_local_branch")

    def test_creates_from_remote_when_remote_branch_exists(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=True)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_from_remote_branch")

        result = Worktree._try_create_from_remote_branch(workspace, BRANCH)

        assert result is not None
        mock_create.assert_called_once()

    def test_falls_back_to_local_when_only_local_branch_exists_after_fetch(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=False)
        mocker.patch("git_workspace.worktree.git.local_branch_exists", return_value=True)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_from_local_branch")

        result = Worktree._try_create_from_remote_branch(workspace, BRANCH)

        assert result is not None
        mock_create.assert_called_once()

    def test_returns_none_when_branch_not_found_after_fetch(self, workspace: MagicMock) -> None:
        result = Worktree._try_create_from_remote_branch(workspace, BRANCH)

        assert result is None


class TestCreateNew:
    @pytest.fixture(autouse=True)
    def mock_git(self, mocker: MockerFixture) -> None:
        mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=True)
        mocker.patch("git_workspace.worktree.git.create_worktree_new")

    def test_fetches_before_creating_worktree(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mock_fetch = mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=True)
        mocker.patch("git_workspace.worktree.git.create_worktree_new")

        Worktree._create_new(workspace, BRANCH, BASE_BRANCH)

        mock_fetch.assert_called_once_with(cwd=workspace.paths.root)

    def test_uses_origin_base_when_remote_branch_exists(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=True)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_new")

        Worktree._create_new(workspace, BRANCH, BASE_BRANCH)

        mock_create.assert_called_once_with(
            workspace.paths.worktree(BRANCH),
            BRANCH,
            f"origin/{BASE_BRANCH}",
            cwd=workspace.paths.root,
        )

    def test_falls_back_to_local_base_when_remote_branch_not_found(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=False)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_new")

        Worktree._create_new(workspace, BRANCH, BASE_BRANCH)

        mock_create.assert_called_once_with(
            workspace.paths.worktree(BRANCH),
            BRANCH,
            BASE_BRANCH,
            cwd=workspace.paths.root,
        )

    def test_uses_manifest_base_branch_when_none_provided(
        self, mocker: MockerFixture, workspace: MagicMock
    ) -> None:
        mocker.patch("git_workspace.worktree.git.fetch_origin")
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=True)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_new")
        workspace.manifest.base_branch = BASE_BRANCH

        Worktree._create_new(workspace, BRANCH, None)

        mock_create.assert_called_once_with(
            workspace.paths.worktree(BRANCH),
            BRANCH,
            f"origin/{BASE_BRANCH}",
            cwd=workspace.paths.root,
        )

    def test_proceeds_when_fetch_fails(self, mocker: MockerFixture, workspace: MagicMock) -> None:
        from git_workspace.errors import GitFetchError

        mocker.patch(
            "git_workspace.worktree.git.fetch_origin", side_effect=GitFetchError("offline")
        )
        mocker.patch("git_workspace.worktree.git.remote_branch_exists", return_value=False)
        mock_create = mocker.patch("git_workspace.worktree.git.create_worktree_new")

        Worktree._create_new(workspace, BRANCH, BASE_BRANCH)

        mock_create.assert_called_once()


class TestDelete:
    @pytest.fixture
    def mock_git_remove_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.worktree.git.remove_worktree")

    @pytest.mark.parametrize("force", [True, False])
    def test_calls_git_remove_worktree_with_correct_params(
        self,
        worktree: Worktree,
        mock_git_remove_worktree: MagicMock,
        force: bool,
    ) -> None:
        worktree.delete(force)

        mock_git_remove_worktree.assert_called_once_with(
            WORKTREE_DIR, force, cwd=Path("/workspace")
        )

    def test_cleans_intermediary_empty_paths(
        self,
        mocker: MockerFixture,
        worktree: Worktree,
        mock_git_remove_worktree: MagicMock,
    ) -> None:
        mock_clean = mocker.patch.object(worktree, "_clean_intermediary_empty_paths")

        worktree.delete(False)

        mock_clean.assert_called_once()
