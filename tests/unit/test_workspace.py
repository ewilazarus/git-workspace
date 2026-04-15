from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.workspace import Workspace

DIRECTORY = Path("/workspace")
WORKSPACE_DIR = str(DIRECTORY)
URL = "https://github.com/user/repo.git"
CONFIG_URL = "https://github.com/user/config.git"


@pytest.fixture(autouse=True)
def mock_manifest_load(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.Manifest.load")


@pytest.fixture
def workspace() -> Workspace:
    return Workspace(DIRECTORY)


class TestConstructor:
    def test_loads_manifest(self, mock_manifest_load: MagicMock) -> None:
        workspace = Workspace(DIRECTORY)
        mock_manifest_load.assert_called_once_with(workspace)


class TestResolve:
    @pytest.fixture
    def mock_resolver_resolve(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.WorkspaceResolver.resolve")

    def test_delegates_to_workspace_resolver(self, mock_resolver_resolve: MagicMock) -> None:
        Workspace.resolve(WORKSPACE_DIR)
        mock_resolver_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_returns_resolver_result(self, mock_resolver_resolve: MagicMock) -> None:
        result = Workspace.resolve(WORKSPACE_DIR)
        assert result is mock_resolver_resolve.return_value


class TestInit:
    @pytest.fixture
    def mock_factory_create(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.WorkspaceFactory.create")

    def test_calls_factory_with_provided_directory(self, mock_factory_create: MagicMock) -> None:
        Workspace.init(WORKSPACE_DIR, CONFIG_URL)
        mock_factory_create.assert_called_once_with(
            Path(WORKSPACE_DIR),
            config_url=CONFIG_URL,
        )

    def test_calls_factory_with_cwd_when_no_directory(
        self, mocker: MockerFixture, mock_factory_create: MagicMock
    ) -> None:
        mock_cwd = mocker.patch("git_workspace.workspace.Path.cwd")
        mock_cwd.return_value.resolve.return_value = DIRECTORY

        Workspace.init(None, CONFIG_URL)

        mock_factory_create.assert_called_once_with(DIRECTORY, config_url=CONFIG_URL)

    def test_returns_factory_result(self, mock_factory_create: MagicMock) -> None:
        result = Workspace.init(WORKSPACE_DIR, CONFIG_URL)
        assert result is mock_factory_create.return_value


class TestClone:
    @pytest.fixture
    def mock_factory_create(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.WorkspaceFactory.create")

    def test_calls_factory_with_provided_directory(self, mock_factory_create: MagicMock) -> None:
        Workspace.clone(WORKSPACE_DIR, URL, CONFIG_URL)
        mock_factory_create.assert_called_once_with(
            dir=Path(WORKSPACE_DIR),
            url=URL,
            config_url=CONFIG_URL,
        )

    def test_calls_factory_with_humanish_suffix_when_no_directory(
        self, mocker: MockerFixture, mock_factory_create: MagicMock
    ) -> None:
        mock_extract = mocker.patch("git_workspace.workspace.utils.extract_humanish_suffix")
        mock_extract.return_value = "repo"

        Workspace.clone(None, URL, CONFIG_URL)

        mock_extract.assert_called_once_with(URL)
        mock_factory_create.assert_called_once_with(
            dir=Path("repo"),
            url=URL,
            config_url=CONFIG_URL,
        )

    def test_returns_factory_result(self, mock_factory_create: MagicMock) -> None:
        result = Workspace.clone(WORKSPACE_DIR, URL, CONFIG_URL)
        assert result is mock_factory_create.return_value


class TestListWorktrees:
    @pytest.fixture
    def mock_worktree_list(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.Worktree.list")

    def test_delegates_to_worktree_list(
        self, workspace: Workspace, mock_worktree_list: MagicMock
    ) -> None:
        workspace.list_worktrees()
        mock_worktree_list.assert_called_once_with(workspace)

    def test_returns_worktree_list_result(
        self, workspace: Workspace, mock_worktree_list: MagicMock
    ) -> None:
        result = workspace.list_worktrees()
        assert result is mock_worktree_list.return_value


class TestResolveWorktree:
    @pytest.fixture
    def mock_worktree_resolve(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.Worktree.resolve")

    def test_delegates_to_worktree_resolve(
        self, workspace: Workspace, mock_worktree_resolve: MagicMock
    ) -> None:
        branch = "feat/GWS-001"
        workspace.resolve_worktree(branch)
        mock_worktree_resolve.assert_called_once_with(workspace, branch)

    def test_returns_worktree_resolve_result(
        self, workspace: Workspace, mock_worktree_resolve: MagicMock
    ) -> None:
        result = workspace.resolve_worktree("feat/GWS-001")
        assert result is mock_worktree_resolve.return_value


class TestResolveOrCreateWorktree:
    @pytest.fixture
    def mock_worktree_resolve_or_create(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.workspace.Worktree.resolve_or_create")

    def test_delegates_to_worktree_resolve_or_create(
        self, workspace: Workspace, mock_worktree_resolve_or_create: MagicMock
    ) -> None:
        branch = "feat/GWS-001"
        base_branch = "main"
        workspace.resolve_or_create_worktree(branch, base_branch)
        mock_worktree_resolve_or_create.assert_called_once_with(workspace, branch, base_branch)

    def test_returns_worktree_resolve_or_create_result(
        self, workspace: Workspace, mock_worktree_resolve_or_create: MagicMock
    ) -> None:
        result = workspace.resolve_or_create_worktree("feat/GWS-001", "main")
        assert result is mock_worktree_resolve_or_create.return_value
