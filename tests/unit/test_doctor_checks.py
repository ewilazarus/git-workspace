from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.doctor import (
    check_asset_sources_exist,
    check_asset_target_clashes,
    check_asset_target_escapes,
    check_base_branch,
    check_hook_bin_references,
    check_hook_duplicates,
    check_hook_empty_entries,
    check_manifest_parseable,
    check_manifest_version,
    check_orphaned_assets,
    check_orphaned_bin_scripts,
    check_stale_worktrees,
    check_var_normalization_clashes,
)
from git_workspace.manifest import Copy, Hooks, Link, Manifest


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    ws = mocker.MagicMock()
    ws.manifest.hooks = Hooks()
    ws.manifest.links = []
    ws.manifest.copies = []
    ws.manifest.vars = {}
    ws.manifest.version = Manifest.DEFAULT_VERSION
    ws.manifest.base_branch = Manifest.DEFAULT_BRANCH
    return ws


class TestCheckManifestParseable:
    def test_returns_no_findings_for_valid_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = 'version = 1\nbase_branch = "main"'

        assert check_manifest_parseable(workspace) == []

    def test_returns_error_on_os_error(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.side_effect = OSError("file not found")

        result = check_manifest_parseable(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert "Cannot read manifest" in result[0].message

    def test_returns_error_on_invalid_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = "!!! not valid toml"

        result = check_manifest_parseable(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert "not valid TOML" in result[0].message


class TestCheckManifestVersion:
    def test_returns_no_findings_for_current_version(self, workspace: MagicMock) -> None:
        workspace.manifest.version = Manifest.DEFAULT_VERSION

        assert check_manifest_version(workspace.manifest) == []

    def test_returns_error_for_future_version(self, workspace: MagicMock) -> None:
        workspace.manifest.version = Manifest.DEFAULT_VERSION + 1

        result = check_manifest_version(workspace.manifest)

        assert len(result) == 1
        assert result[0].level == "error"
        assert str(Manifest.DEFAULT_VERSION + 1) in result[0].message


class TestCheckAssetSourcesExist:
    def test_returns_no_findings_when_all_sources_exist(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="dotfile", target=".dotfile")]
        (workspace.paths.assets / "dotfile").exists.return_value = True

        assert check_asset_sources_exist(workspace) == []

    def test_returns_error_for_missing_link_source(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"
        workspace.paths.assets.mkdir()
        workspace.manifest.links = [Link(source="missing", target=".missing")]
        workspace.manifest.copies = []

        result = check_asset_sources_exist(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert "missing" in result[0].message

    def test_returns_error_for_missing_copy_source(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"
        workspace.paths.assets.mkdir()
        workspace.manifest.links = []
        workspace.manifest.copies = [Copy(source="config", target="config.yaml")]

        result = check_asset_sources_exist(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert "config" in result[0].message


class TestCheckAssetTargetClashes:
    def test_returns_no_findings_for_unique_targets(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target=".a")]
        workspace.manifest.copies = [Copy(source="b", target=".b")]

        assert check_asset_target_clashes(workspace) == []

    def test_returns_error_for_duplicate_link_targets(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [
            Link(source="a", target=".config"),
            Link(source="b", target=".config"),
        ]
        workspace.manifest.copies = []

        result = check_asset_target_clashes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert ".config" in result[0].message

    def test_returns_error_for_link_copy_target_clash(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target=".config")]
        workspace.manifest.copies = [Copy(source="b", target=".config")]

        result = check_asset_target_clashes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert ".config" in result[0].message


class TestCheckAssetTargetEscapes:
    def test_returns_no_findings_for_safe_target(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="subdir/config.json")]
        workspace.manifest.copies = []

        assert check_asset_target_escapes(workspace) == []

    def test_returns_error_for_dotdot_escape(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="../../etc/passwd")]
        workspace.manifest.copies = []

        result = check_asset_target_escapes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"

    def test_returns_error_for_absolute_target(self, workspace: MagicMock) -> None:
        workspace.manifest.links = []
        workspace.manifest.copies = [Copy(source="a", target="/etc/passwd")]

        result = check_asset_target_escapes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"

    def test_single_dotdot_is_an_escape(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="..")]
        workspace.manifest.copies = []

        result = check_asset_target_escapes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"


class TestCheckVarNormalizationClashes:
    def test_returns_no_findings_for_unique_keys(self, workspace: MagicMock) -> None:
        workspace.manifest.vars = {"foo": "1", "bar": "2"}

        assert check_var_normalization_clashes(workspace) == []

    def test_returns_error_for_clashing_keys(self, workspace: MagicMock) -> None:
        workspace.manifest.vars = {"my-key": "1", "my_key": "2"}

        result = check_var_normalization_clashes(workspace)

        assert len(result) == 1
        assert result[0].level == "error"
        assert "my-key" in result[0].message
        assert "my_key" in result[0].message


class TestCheckHookBinReferences:
    def test_inline_command_with_spaces_is_not_flagged(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=["docker build . -t myapp"])

        assert check_hook_bin_references(workspace) == []

    def test_warns_for_missing_bin_script(self, workspace: MagicMock, tmp_path: Path) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=["install_deps"])

        result = check_hook_bin_references(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "install_deps" in result[0].message

    def test_warns_for_non_executable_bin_script(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        script = bin_dir / "setup.sh"
        script.write_text("#!/bin/sh\necho hello")
        script.chmod(0o644)

        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks(on_setup=["setup.sh"])

        result = check_hook_bin_references(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "not executable" in result[0].message

    def test_no_finding_for_executable_bin_script(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        script = bin_dir / "setup.sh"
        script.write_text("#!/bin/sh\necho hello")
        script.chmod(0o755)

        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks(on_setup=["setup.sh"])

        assert check_hook_bin_references(workspace) == []

    def test_empty_entry_is_skipped(self, workspace: MagicMock, tmp_path: Path) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=[""])

        assert check_hook_bin_references(workspace) == []


class TestCheckHookEmptyEntries:
    def test_returns_no_findings_for_non_empty_hooks(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install"])

        assert check_hook_empty_entries(workspace) == []

    def test_returns_warning_for_empty_entry(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=[""])

        result = check_hook_empty_entries(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "on_setup" in result[0].message

    def test_returns_warning_for_whitespace_only_entry(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_activate=["   "])

        result = check_hook_empty_entries(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "on_activate" in result[0].message


class TestCheckHookDuplicates:
    def test_returns_no_findings_for_unique_entries(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["a", "b"])

        assert check_hook_duplicates(workspace) == []

    def test_returns_warning_for_duplicate_in_same_event(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install", "install"])

        result = check_hook_duplicates(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "on_setup" in result[0].message
        assert "install" in result[0].message

    def test_same_entry_in_different_events_is_fine(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install"], on_activate=["install"])

        assert check_hook_duplicates(workspace) == []


class TestCheckOrphanedBinScripts:
    def test_returns_no_findings_when_bin_dir_absent(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.bin = tmp_path / "bin"

        assert check_orphaned_bin_scripts(workspace) == []

    def test_returns_no_findings_when_all_scripts_referenced(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "setup.sh").write_text("#!/bin/sh")
        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks(on_setup=["setup.sh"])

        assert check_orphaned_bin_scripts(workspace) == []

    def test_returns_warning_for_unreferenced_script(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "unused.sh").write_text("#!/bin/sh")
        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks()

        result = check_orphaned_bin_scripts(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "unused.sh" in result[0].message


class TestCheckOrphanedAssets:
    def test_returns_no_findings_when_assets_dir_absent(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"

        assert check_orphaned_assets(workspace) == []

    def test_returns_no_findings_when_all_assets_referenced(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "dotfile").write_text("content")
        workspace.paths.assets = assets_dir
        workspace.manifest.links = [Link(source="dotfile", target=".dotfile")]
        workspace.manifest.copies = []

        assert check_orphaned_assets(workspace) == []

    def test_returns_warning_for_unreferenced_asset(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "orphan.txt").write_text("content")
        workspace.paths.assets = assets_dir
        workspace.manifest.links = []
        workspace.manifest.copies = []

        result = check_orphaned_assets(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "orphan.txt" in result[0].message


class TestCheckBaseBranch:
    def test_returns_no_findings_when_local_branch_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=True)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=False)
        workspace.manifest.base_branch = "main"

        assert check_base_branch(workspace) == []

    def test_returns_no_findings_when_remote_branch_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=False)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=True)
        workspace.manifest.base_branch = "main"

        assert check_base_branch(workspace) == []

    def test_returns_warning_when_neither_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=False)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=False)
        workspace.manifest.base_branch = "develop"

        result = check_base_branch(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "develop" in result[0].message


class TestCheckStaleWorktrees:
    def test_returns_no_findings_when_all_dirs_exist(
        self, workspace: MagicMock, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        wt_dir = tmp_path / "main"
        wt_dir.mkdir()
        mocker.patch(
            "git_workspace.doctor.git.list_worktrees",
            return_value=[{"directory": str(wt_dir), "branch": "main", "head": "abc123"}],
        )

        assert check_stale_worktrees(workspace) == []

    def test_returns_warning_for_missing_dir(
        self, workspace: MagicMock, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        wt_dir = tmp_path / "gone"
        mocker.patch(
            "git_workspace.doctor.git.list_worktrees",
            return_value=[{"directory": str(wt_dir), "branch": "feature/gone", "head": "abc123"}],
        )

        result = check_stale_worktrees(workspace)

        assert len(result) == 1
        assert result[0].level == "warning"
        assert "feature/gone" in result[0].message

    def test_returns_no_findings_on_listing_error(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        from git_workspace.errors import WorktreeListingError

        mocker.patch(
            "git_workspace.doctor.git.list_worktrees",
            side_effect=WorktreeListingError("git error"),
        )

        assert check_stale_worktrees(workspace) == []
