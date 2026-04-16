from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockerFixture

from git_workspace.assets import Copier, IgnoreManager
from git_workspace.errors import WorkspaceCopyError
from git_workspace.manifest import Copy

ASSETS_DIR = Path("/workspace/.workspace/assets")
WORKTREE_DIR = Path("/workspace/feat/GWS-001")

COPY_WITH_OVERRIDE = Copy(source="env", target=".env", override=True)
COPY_WITHOUT_OVERRIDE = Copy(source="config", target=".config", override=False)


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.paths.assets = ASSETS_DIR
    mock.paths.ignore_file = mocker.MagicMock()
    mock.manifest.copies = [COPY_WITH_OVERRIDE, COPY_WITHOUT_OVERRIDE]
    return mock


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.directory = WORKTREE_DIR
    return mock


@pytest.fixture
def ignore(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock(spec=IgnoreManager)


@pytest.fixture
def copier(workspace: MagicMock, worktree: MagicMock, ignore: MagicMock) -> Copier:
    return Copier(workspace, worktree, ignore)


class TestApplyWithOverride:
    @pytest.fixture
    def source(self) -> MagicMock:
        mock = MagicMock()
        mock.is_dir.return_value = False
        return mock

    @pytest.fixture
    def target(self) -> MagicMock:
        mock = MagicMock()
        mock.exists.return_value = False
        mock.is_symlink.return_value = False
        mock.is_dir.return_value = False
        return mock

    @pytest.fixture(autouse=True)
    def mock_git_skip_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.git.skip_worktree")

    @pytest.fixture(autouse=True)
    def mock_shutil_copy2(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.shutil.copy2")

    def test_apply_calls_skip_worktree_for_override(
        self,
        copier: Copier,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        copier._apply(COPY_WITH_OVERRIDE)

        mock_git_skip_worktree.assert_called_once()

    def test_removes_when_target_exists(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
    ) -> None:
        target.exists.return_value = True

        copier._apply_with_override(source, target)

        target.unlink.assert_called_once()

    def test_removes_when_target_is_symlink(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
    ) -> None:
        target.is_symlink.return_value = True

        copier._apply_with_override(source, target)

        target.unlink.assert_called_once()

    def test_does_not_remove_when_target_absent(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
    ) -> None:
        copier._apply_with_override(source, target)

        target.unlink.assert_not_called()

    def test_copies_file(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
        mock_shutil_copy2: MagicMock,
    ) -> None:
        copier._apply_with_override(source, target)

        mock_shutil_copy2.assert_called_once_with(source, target)


class TestApplyWithoutOverride:
    @pytest.fixture
    def source(self) -> MagicMock:
        mock = MagicMock()
        mock.is_dir.return_value = False
        return mock

    @pytest.fixture
    def target(self) -> MagicMock:
        mock = MagicMock()
        mock.is_symlink.return_value = False
        mock.exists.return_value = False
        return mock

    @pytest.fixture(autouse=True)
    def mock_shutil_copy2(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.shutil.copy2")

    def test_copies_file_when_target_absent(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
        mock_shutil_copy2: MagicMock,
    ) -> None:
        copier._apply_without_override(source, target)

        mock_shutil_copy2.assert_called_once_with(source, target)

    def test_overwrites_when_target_exists(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
        mock_shutil_copy2: MagicMock,
    ) -> None:
        target.exists.return_value = True

        copier._apply_without_override(source, target)

        mock_shutil_copy2.assert_called_once_with(source, target)

    def test_raises_when_target_is_symlink(
        self, copier: Copier, source: MagicMock, target: MagicMock
    ) -> None:
        target.is_symlink.return_value = True

        with pytest.raises(WorkspaceCopyError):
            copier._apply_without_override(source, target)


class TestApply:
    @pytest.fixture
    def mock_apply(self, mocker: MockerFixture, copier: Copier) -> MagicMock:
        return mocker.patch.object(copier, "_apply")

    def test_applies_each_copy(self, copier: Copier, mock_apply: MagicMock) -> None:
        copier.apply()

        assert mock_apply.call_count == len(copier._assets)

    def test_calls_apply_with_each_copy(self, copier: Copier, mock_apply: MagicMock) -> None:
        copier.apply()

        applied_copies = [call.args[0] for call in mock_apply.call_args_list]
        assert applied_copies == copier._assets


class TestApplyCreatesParentDirs:
    ASSETS_DIR = Path("/workspace/.workspace/assets")
    WORKTREE_DIR = Path("/workspace/feat/GWS-001")

    @pytest.fixture(autouse=True)
    def filesystem(self, fs: FakeFilesystem) -> None:
        fs.create_file(str(self.ASSETS_DIR / "config.yaml"))

    @pytest.fixture(autouse=True)
    def mock_git_skip_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.git.skip_worktree")

    @pytest.fixture
    def copier(self, mocker: MockerFixture) -> Copier:
        workspace = mocker.MagicMock()
        workspace.paths.assets = self.ASSETS_DIR
        workspace.paths.ignore_file = mocker.MagicMock()
        workspace.manifest.copies = []
        worktree = mocker.MagicMock()
        worktree.dir = self.WORKTREE_DIR
        ignore = mocker.MagicMock(spec=IgnoreManager)
        return Copier(workspace, worktree, ignore)

    def test_creates_parent_dir_before_copying(self, copier: Copier) -> None:
        nested = Copy(source="config.yaml", target="config/local/config.yaml")
        parent = self.WORKTREE_DIR / "config" / "local"

        assert not parent.exists()
        copier._apply(nested)
        assert parent.exists()

    def test_creates_deeply_nested_parent_dirs(self, copier: Copier) -> None:
        nested = Copy(source="config.yaml", target="a/b/c/config.yaml")
        parent = self.WORKTREE_DIR / "a" / "b" / "c"

        assert not parent.exists()
        copier._apply(nested)
        assert parent.exists()
