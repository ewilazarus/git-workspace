from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.assets import Linker
from git_workspace.errors import WorkspaceLinkError
from git_workspace.manifest import Link

ASSETS_DIR = Path("/workspace/.workspace/assets")
WORKTREE_DIR = Path("/workspace/feat/GWS-001")

LINK_WITH_OVERRIDE = Link(source="env", target=".env", override=True)
LINK_WITHOUT_OVERRIDE = Link(source="config", target=".config", override=False)


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.paths.assets = ASSETS_DIR
    mock.paths.ignore_file = mocker.MagicMock()
    mock.manifest.links = [LINK_WITH_OVERRIDE, LINK_WITHOUT_OVERRIDE]
    return mock


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.directory = WORKTREE_DIR
    return mock


@pytest.fixture
def linker(workspace: MagicMock, worktree: MagicMock) -> Linker:
    return Linker(workspace, worktree)


class TestApplyWithOverride:
    @pytest.fixture
    def source(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def target(self) -> MagicMock:
        mock = MagicMock()
        mock.exists.return_value = False
        mock.is_symlink.return_value = False
        return mock

    @pytest.fixture
    def mock_git_skip_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.git.skip_worktree")

    def test_calls_git_skip_worktree_with_target(
        self,
        linker: Linker,
        source: MagicMock,
        target: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        linker._apply_with_override(source, target)

        mock_git_skip_worktree.assert_called_once_with(target)

    def test_unlinks_when_target_exists(
        self,
        linker: Linker,
        source: MagicMock,
        target: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        target.exists.return_value = True

        linker._apply_with_override(source, target)

        target.unlink.assert_called_once()

    def test_unlinks_when_target_is_symlink(
        self,
        linker: Linker,
        source: MagicMock,
        target: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        target.is_symlink.return_value = True

        linker._apply_with_override(source, target)

        target.unlink.assert_called_once()

    def test_does_not_unlink_when_target_absent(
        self,
        linker: Linker,
        source: MagicMock,
        target: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        linker._apply_with_override(source, target)

        target.unlink.assert_not_called()

    def test_creates_symlink_to_source(
        self,
        linker: Linker,
        source: MagicMock,
        target: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        linker._apply_with_override(source, target)

        target.symlink_to.assert_called_once_with(source)


class TestApplyWithoutOverride:
    @pytest.fixture
    def source(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def target(self) -> MagicMock:
        mock = MagicMock()
        mock.is_symlink.return_value = False
        mock.exists.return_value = False
        return mock

    def test_creates_symlink_when_target_absent(
        self, linker: Linker, source: MagicMock, target: MagicMock
    ) -> None:
        linker._apply_without_override(source, target)

        target.symlink_to.assert_called_once_with(source)

    def test_skips_when_symlink_already_points_to_source(
        self, linker: Linker, source: MagicMock, target: MagicMock
    ) -> None:
        target.is_symlink.return_value = True
        target.readlink.return_value = source

        linker._apply_without_override(source, target)

        target.symlink_to.assert_not_called()

    def test_raises_when_symlink_points_to_different_source(
        self, linker: Linker, source: MagicMock, target: MagicMock
    ) -> None:
        target.is_symlink.return_value = True
        target.readlink.return_value = MagicMock()

        with pytest.raises(WorkspaceLinkError):
            linker._apply_without_override(source, target)

    def test_raises_when_target_exists(
        self, linker: Linker, source: MagicMock, target: MagicMock
    ) -> None:
        target.exists.return_value = True

        with pytest.raises(WorkspaceLinkError):
            linker._apply_without_override(source, target)


class TestApply:
    @pytest.fixture
    def mock_apply(self, mocker: MockerFixture, linker: Linker) -> MagicMock:
        return mocker.patch.object(linker, "_apply")

    @pytest.fixture
    def mock_sync(self, mocker: MockerFixture, linker: Linker) -> MagicMock:
        return mocker.patch.object(linker._ignore_manager, "sync")

    def test_applies_each_link(
        self, linker: Linker, mock_apply: MagicMock, mock_sync: MagicMock
    ) -> None:
        linker.apply()

        assert mock_apply.call_count == len(linker._links)

    def test_calls_apply_with_each_link(
        self, linker: Linker, mock_apply: MagicMock, mock_sync: MagicMock
    ) -> None:
        linker.apply()

        applied_links = [call.args[0] for call in mock_apply.call_args_list]
        assert applied_links == linker._links

    def test_syncs_ignore_manager_after_applying_links(
        self, linker: Linker, mock_apply: MagicMock, mock_sync: MagicMock
    ) -> None:
        linker.apply()

        mock_sync.assert_called_once()
