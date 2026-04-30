from pathlib import Path
from typing import cast
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
COPY_NO_OVERWRITE = Copy(source="config", target=".config", overwrite=False)
COPY_NO_OVERWRITE_WITH_OVERRIDE = Copy(source="env", target=".env", override=True, overwrite=False)


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.workspace.paths.assets = ASSETS_DIR
    mock.workspace.paths.ignore_file = mocker.MagicMock()
    mock.workspace.manifest.copies = [COPY_WITH_OVERRIDE, COPY_WITHOUT_OVERRIDE]
    return mock


@pytest.fixture
def ignore(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock(spec=IgnoreManager)


@pytest.fixture
def copier(worktree: MagicMock, ignore: MagicMock) -> Copier:
    return Copier(worktree, ignore, env={})


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
    def mock_copy_with_substitution(self, mocker: MockerFixture, copier: Copier) -> MagicMock:
        return mocker.patch.object(copier, "_copy_with_substitution")

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
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        copier._apply_with_override(source, target)

        mock_copy_with_substitution.assert_called_once_with(source, target)


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
    def mock_copy_with_substitution(self, mocker: MockerFixture, copier: Copier) -> MagicMock:
        return mocker.patch.object(copier, "_copy_with_substitution")

    def test_copies_file_when_target_absent(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        copier._apply_without_override(source, target)

        mock_copy_with_substitution.assert_called_once_with(source, target)

    def test_overwrites_when_target_exists(
        self,
        copier: Copier,
        source: MagicMock,
        target: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        target.exists.return_value = True

        copier._apply_without_override(source, target)

        mock_copy_with_substitution.assert_called_once_with(source, target)

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
        worktree = mocker.MagicMock()
        worktree.dir = self.WORKTREE_DIR
        worktree.workspace.paths.assets = self.ASSETS_DIR
        worktree.workspace.manifest.copies = []
        ignore = mocker.MagicMock(spec=IgnoreManager)
        return Copier(worktree, ignore, env={})

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


class TestSkipExisting:
    @pytest.fixture(autouse=True)
    def mock_git_skip_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.git.skip_worktree")

    @pytest.fixture
    def target_mock(self, copier: Copier) -> MagicMock:
        return cast(MagicMock, copier._worktree.dir).__truediv__.return_value.absolute.return_value

    def test_returns_false_when_overwrite_true(
        self,
        copier: Copier,
        target_mock: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        assert copier._skip_existing(COPY_WITH_OVERRIDE) is False

    def test_returns_false_when_target_absent(
        self,
        copier: Copier,
        target_mock: MagicMock,
    ) -> None:
        target_mock.exists.return_value = False

        assert copier._skip_existing(COPY_NO_OVERWRITE) is False

    def test_returns_true_when_overwrite_false_and_target_exists(
        self,
        copier: Copier,
        target_mock: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        assert copier._skip_existing(COPY_NO_OVERWRITE) is True

    def test_calls_skip_worktree_for_override_copy_with_existing_target(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._skip_existing(COPY_NO_OVERWRITE_WITH_OVERRIDE)

        mock_git_skip_worktree.assert_called_once()

    def test_does_not_call_skip_worktree_for_non_override_copy(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._skip_existing(COPY_NO_OVERWRITE)

        mock_git_skip_worktree.assert_not_called()

    def test_collects_ignore_for_non_override_copy_with_existing_target(
        self,
        copier: Copier,
        target_mock: MagicMock,
        ignore: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._skip_existing(COPY_NO_OVERWRITE)

        ignore.collect.assert_called_once()

    def test_does_not_collect_ignore_for_override_copy(
        self,
        copier: Copier,
        target_mock: MagicMock,
        ignore: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._skip_existing(COPY_NO_OVERWRITE_WITH_OVERRIDE)

        ignore.collect.assert_not_called()


class TestApplyWithOverwriteFalse:
    @pytest.fixture(autouse=True)
    def mock_copy_with_substitution(self, mocker: MockerFixture, copier: Copier) -> MagicMock:
        return mocker.patch.object(copier, "_copy_with_substitution")

    @pytest.fixture(autouse=True)
    def mock_git_skip_worktree(self, mocker: MockerFixture) -> MagicMock:
        return mocker.patch("git_workspace.assets.git.skip_worktree")

    @pytest.fixture
    def target_mock(self, copier: Copier) -> MagicMock:
        # Resolve the same MagicMock chain that Copier._apply will compute for target
        return cast(MagicMock, copier._worktree.dir).__truediv__.return_value.absolute.return_value

    def test_skips_non_override_copy_when_target_exists(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._apply(COPY_NO_OVERWRITE)

        mock_copy_with_substitution.assert_not_called()

    def test_copies_non_override_when_target_absent(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        target_mock.exists.return_value = False
        target_mock.is_symlink.return_value = False

        copier._apply(COPY_NO_OVERWRITE)

        mock_copy_with_substitution.assert_called_once()

    def test_still_collects_ignore_when_target_exists(
        self,
        copier: Copier,
        target_mock: MagicMock,
        ignore: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._apply(COPY_NO_OVERWRITE)

        ignore.collect.assert_called_once()

    def test_skips_override_copy_when_target_exists(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._apply(COPY_NO_OVERWRITE_WITH_OVERRIDE)

        mock_copy_with_substitution.assert_not_called()

    def test_calls_skip_worktree_even_when_skipping_override(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_git_skip_worktree: MagicMock,
    ) -> None:
        target_mock.exists.return_value = True

        copier._apply(COPY_NO_OVERWRITE_WITH_OVERRIDE)

        mock_git_skip_worktree.assert_called_once()

    def test_copies_override_when_target_absent(
        self,
        copier: Copier,
        target_mock: MagicMock,
        mock_copy_with_substitution: MagicMock,
    ) -> None:
        target_mock.exists.return_value = False
        target_mock.is_symlink.return_value = False

        copier._apply(COPY_NO_OVERWRITE_WITH_OVERRIDE)

        mock_copy_with_substitution.assert_called_once()


class TestCopyWithSubstitution:
    ASSETS_DIR = Path("/workspace/.workspace/assets")
    WORKTREE_DIR = Path("/workspace/feat/GWS-001")
    ENV = {
        "GIT_WORKSPACE_BRANCH": "feat/GWS-001",
        "GIT_WORKSPACE_ROOT": "/workspace",
        "GIT_WORKSPACE_VAR_MY_VAR": "my_value",
    }

    @pytest.fixture
    def copier(self, mocker: MockerFixture) -> Copier:
        worktree = mocker.MagicMock()
        worktree.dir = self.WORKTREE_DIR
        worktree.workspace.paths.assets = self.ASSETS_DIR
        worktree.workspace.manifest.copies = []
        ignore = mocker.MagicMock(spec=IgnoreManager)
        return Copier(worktree, ignore, env=self.ENV)

    def test_resolves_known_placeholder(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="branch={{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "branch=feat/GWS-001"

    def test_leaves_unknown_placeholder_verbatim(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_TYPO }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "{{ GIT_WORKSPACE_TYPO }}"

    def test_resolves_custom_var_placeholder(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_VAR_MY_VAR }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "my_value"

    def test_copies_binary_file_as_is(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "binary.bin"
        target = self.WORKTREE_DIR / "binary.bin"
        binary_content = b"\xff\xfe\x00\x01"
        fs.create_dir(str(self.ASSETS_DIR))
        fs.create_dir(str(self.WORKTREE_DIR))
        source.write_bytes(binary_content)

        copier._copy_with_substitution(source, target)

        assert target.read_bytes() == binary_content

    def test_count_is_one_for_single_resolved_placeholder(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        assert copier._copy_with_substitution(source, target) == 1

    def test_count_reflects_number_of_resolved_placeholders(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH }} {{ GIT_WORKSPACE_ROOT }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        assert copier._copy_with_substitution(source, target) == 2

    def test_count_is_zero_for_unknown_placeholder(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_UNKNOWN }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        assert copier._copy_with_substitution(source, target) == 0

    def test_count_is_zero_for_non_j2_file(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "binary.bin"
        target = self.WORKTREE_DIR / "binary.bin"
        fs.create_dir(str(self.ASSETS_DIR))
        fs.create_dir(str(self.WORKTREE_DIR))
        source.write_bytes(b"\xff\xfe")

        assert copier._copy_with_substitution(source, target) == 0

    def test_each_call_returns_its_own_count(self, copier: Copier, fs: FakeFilesystem) -> None:
        s1 = self.ASSETS_DIR / "f1.txt.j2"
        s2 = self.ASSETS_DIR / "f2.txt.j2"
        fs.create_file(str(s1), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_file(str(s2), contents="{{ GIT_WORKSPACE_ROOT }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        assert copier._copy_with_substitution(s1, self.WORKTREE_DIR / "f1.txt") == 1
        assert copier._copy_with_substitution(s2, self.WORKTREE_DIR / "f2.txt") == 1

    def test_apply_returns_substitution_count(
        self, copier: Copier, fs: FakeFilesystem, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.assets.git.skip_worktree")
        fs.create_file(
            str(self.ASSETS_DIR / "template.txt.j2"), contents="{{ GIT_WORKSPACE_BRANCH }}"
        )
        fs.create_dir(str(self.WORKTREE_DIR))
        copy = Copy(source="template.txt.j2", target="template.txt")

        assert copier._apply(copy) == 1

    def test_apply_returns_zero_when_skipped(self, copier: Copier, fs: FakeFilesystem) -> None:
        fs.create_file(str(self.ASSETS_DIR / "template.txt"), contents="x")
        fs.create_file(str(self.WORKTREE_DIR / "template.txt"), contents="existing")
        copy = Copy(source="template.txt", target="template.txt", overwrite=False)

        assert copier._apply(copy) == 0


class TestJinjaTemplating:
    ASSETS_DIR = Path("/workspace/.workspace/assets")
    WORKTREE_DIR = Path("/workspace/feat/GWS-001")
    ENV = {
        "GIT_WORKSPACE_BRANCH": "main",
        "GIT_WORKSPACE_VAR_ENV": "staging",
        "PATH": "/usr/bin",  # non-prefixed env should not be exposed to templates
    }

    @pytest.fixture
    def copier(self, mocker: MockerFixture) -> Copier:
        worktree = mocker.MagicMock()
        worktree.dir = self.WORKTREE_DIR
        worktree.workspace.paths.assets = self.ASSETS_DIR
        worktree.workspace.manifest.copies = []
        ignore = mocker.MagicMock(spec=IgnoreManager)
        return Copier(worktree, ignore, env=self.ENV)

    def test_renders_if_block_when_condition_true(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(
            str(source),
            contents='{% if GIT_WORKSPACE_BRANCH == "main" %}prod{% else %}dev{% endif %}',
        )
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "prod"

    def test_renders_if_block_when_condition_false(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(
            str(source),
            contents='{% if GIT_WORKSPACE_BRANCH == "release" %}prod{% else %}dev{% endif %}',
        )
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "dev"

    def test_supports_filters(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH | upper }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "MAIN"

    def test_supports_for_loop(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(
            str(source),
            contents="{% for c in GIT_WORKSPACE_BRANCH %}{{ c }}-{% endfor %}",
        )
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "m-a-i-n-"

    def test_unknown_variable_renders_verbatim(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_TYPO }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "{{ GIT_WORKSPACE_TYPO }}"

    def test_does_not_expose_non_prefixed_env_to_templates(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{{ PATH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "{{ PATH }}"

    def test_preserves_trailing_newline(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="branch={{ GIT_WORKSPACE_BRANCH }}\n")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "branch=main\n"

    def test_template_syntax_error_is_wrapped(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "template.txt.j2"
        target = self.WORKTREE_DIR / "template.txt"
        fs.create_file(str(source), contents="{% if GIT_WORKSPACE_BRANCH %}oops")
        fs.create_dir(str(self.WORKTREE_DIR))

        with pytest.raises(WorkspaceCopyError) as exc:
            copier._copy_with_substitution(source, target)

        assert "template.txt.j2" in str(exc.value)


class TestJ2Suffix:
    ASSETS_DIR = Path("/workspace/.workspace/assets")
    WORKTREE_DIR = Path("/workspace/feat/GWS-001")
    ENV = {
        "GIT_WORKSPACE_BRANCH": "main",
    }

    @pytest.fixture
    def copier(self, mocker: MockerFixture) -> Copier:
        worktree = mocker.MagicMock()
        worktree.dir = self.WORKTREE_DIR
        worktree.workspace.paths.assets = self.ASSETS_DIR
        worktree.workspace.manifest.copies = []
        ignore = mocker.MagicMock(spec=IgnoreManager)
        return Copier(worktree, ignore, env=self.ENV)

    def test_j2_source_is_rendered(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "config.yaml.j2"
        target = self.WORKTREE_DIR / "config.yaml"
        fs.create_file(str(source), contents="branch={{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "branch=main"

    def test_non_j2_text_file_is_copied_verbatim(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "config.yaml"
        target = self.WORKTREE_DIR / "config.yaml"
        fs.create_file(str(source), contents="branch={{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "branch={{ GIT_WORKSPACE_BRANCH }}"

    def test_non_j2_binary_file_is_copied_verbatim(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "image.png"
        target = self.WORKTREE_DIR / "image.png"
        binary_content = b"\x89PNG\r\n\x1a\n"
        fs.create_dir(str(self.ASSETS_DIR))
        fs.create_dir(str(self.WORKTREE_DIR))
        source.write_bytes(binary_content)

        copier._copy_with_substitution(source, target)

        assert target.read_bytes() == binary_content

    def test_j2_bak_file_is_copied_verbatim(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "config.j2.bak"
        target = self.WORKTREE_DIR / "config.j2.bak"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.read_text() == "{{ GIT_WORKSPACE_BRANCH }}"

    def test_target_path_is_honoured_verbatim_when_it_has_j2(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        source = self.ASSETS_DIR / "config.yaml.j2"
        target = self.WORKTREE_DIR / "config.yaml.j2"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_with_substitution(source, target)

        assert target.exists()
        assert target.read_text() == "main"

    def test_count_is_zero_for_non_j2_source(self, copier: Copier, fs: FakeFilesystem) -> None:
        source = self.ASSETS_DIR / "plain.txt"
        target = self.WORKTREE_DIR / "plain.txt"
        fs.create_file(str(source), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        assert copier._copy_with_substitution(source, target) == 0

    def test_directory_renders_j2_and_copies_plain(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        src_dir = self.ASSETS_DIR / "config"
        dst_dir = self.WORKTREE_DIR / "config"
        fs.create_file(str(src_dir / "app.yaml.j2"), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_file(str(src_dir / "static.txt"), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_dir_with_substitution(src_dir, dst_dir)

        assert (dst_dir / "app.yaml").read_text() == "main"
        assert not (dst_dir / "app.yaml.j2").exists()
        assert (dst_dir / "static.txt").read_text() == "{{ GIT_WORKSPACE_BRANCH }}"

    def test_directory_strips_j2_suffix_from_nested_files(
        self, copier: Copier, fs: FakeFilesystem
    ) -> None:
        src_dir = self.ASSETS_DIR / "vscode"
        dst_dir = self.WORKTREE_DIR / ".vscode"
        fs.create_file(
            str(src_dir / "settings.json.j2"),
            contents='{"branch": "{{ GIT_WORKSPACE_BRANCH }}"}',
        )
        fs.create_file(
            str(src_dir / "nested" / "launch.json.j2"),
            contents='{"branch": "{{ GIT_WORKSPACE_BRANCH }}"}',
        )
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_dir_with_substitution(src_dir, dst_dir)

        assert (dst_dir / "settings.json").read_text() == '{"branch": "main"}'
        assert not (dst_dir / "settings.json.j2").exists()
        assert (dst_dir / "nested" / "launch.json").read_text() == '{"branch": "main"}'
        assert not (dst_dir / "nested" / "launch.json.j2").exists()

    def test_directory_only_strips_trailing_j2(self, copier: Copier, fs: FakeFilesystem) -> None:
        src_dir = self.ASSETS_DIR / "config"
        dst_dir = self.WORKTREE_DIR / "config"
        fs.create_file(str(src_dir / "config.j2.bak"), contents="{{ GIT_WORKSPACE_BRANCH }}")
        fs.create_dir(str(self.WORKTREE_DIR))

        copier._copy_dir_with_substitution(src_dir, dst_dir)

        assert (dst_dir / "config.j2.bak").read_text() == "{{ GIT_WORKSPACE_BRANCH }}"
