from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.doctor import (
    _check_asset_sources_exist,
    _check_asset_target_clashes,
    _check_asset_target_escapes,
    _check_base_branch,
    _check_copy_placeholders,
    _check_fingerprint_algorithm,
    _check_fingerprint_empty_name,
    _check_fingerprint_files,
    _check_fingerprint_length,
    _check_fingerprint_name_clashes,
    _check_fingerprint_name_var_clashes,
    _check_hook_bin_references,
    _check_hook_duplicates,
    _check_hook_empty_entries,
    _check_manifest_parseable,
    _check_manifest_version,
    _check_orphaned_assets,
    _check_orphaned_bin_scripts,
    _check_stale_worktrees,
    _check_var_normalization_clashes,
)
from git_workspace.manifest import Copy, Fingerprint, Hooks, Link, Manifest


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    ws = mocker.MagicMock()
    ws.manifest.hooks = Hooks()
    ws.manifest.links = []
    ws.manifest.copies = []
    ws.manifest.vars = {}
    ws.manifest.fingerprints = []
    ws.manifest.version = Manifest.DEFAULT_VERSION
    ws.manifest.base_branch = Manifest.DEFAULT_BRANCH
    return ws


class TestCheckManifestParseable:
    def test_returns_no_findings_for_valid_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = 'version = 1\nbase_branch = "main"'

        findings = []
        _check_manifest_parseable(workspace, findings)
        assert findings == []

    def test_returns_error_on_os_error(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.side_effect = OSError("file not found")

        findings = []
        _check_manifest_parseable(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "Cannot read manifest" in findings[0].message

    def test_returns_error_on_invalid_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = "!!! not valid toml"

        findings = []
        _check_manifest_parseable(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "not valid TOML" in findings[0].message


class TestCheckManifestVersion:
    def test_returns_no_findings_for_current_version(self, workspace: MagicMock) -> None:
        workspace.manifest.version = Manifest.DEFAULT_VERSION

        findings = []
        _check_manifest_version(workspace.manifest, findings)
        assert findings == []

    def test_returns_error_for_future_version(self, workspace: MagicMock) -> None:
        workspace.manifest.version = Manifest.DEFAULT_VERSION + 1

        findings = []
        _check_manifest_version(workspace.manifest, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert str(Manifest.DEFAULT_VERSION + 1) in findings[0].message


class TestCheckAssetSourcesExist:
    def test_returns_no_findings_when_all_sources_exist(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="dotfile", target=".dotfile")]
        (workspace.paths.assets / "dotfile").exists.return_value = True

        findings = []
        _check_asset_sources_exist(workspace, findings)
        assert findings == []

    def test_returns_error_for_missing_link_source(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"
        workspace.paths.assets.mkdir()
        workspace.manifest.links = [Link(source="missing", target=".missing")]
        workspace.manifest.copies = []

        findings = []
        _check_asset_sources_exist(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "missing" in findings[0].message

    def test_returns_error_for_missing_copy_source(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"
        workspace.paths.assets.mkdir()
        workspace.manifest.links = []
        workspace.manifest.copies = [Copy(source="config", target="config.yaml")]

        findings = []
        _check_asset_sources_exist(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "config" in findings[0].message


class TestCheckAssetTargetClashes:
    def test_returns_no_findings_for_unique_targets(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target=".a")]
        workspace.manifest.copies = [Copy(source="b", target=".b")]

        findings = []
        _check_asset_target_clashes(workspace, findings)
        assert findings == []

    def test_returns_error_for_duplicate_link_targets(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [
            Link(source="a", target=".config"),
            Link(source="b", target=".config"),
        ]
        workspace.manifest.copies = []

        findings = []
        _check_asset_target_clashes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert ".config" in findings[0].message

    def test_returns_error_for_link_copy_target_clash(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target=".config")]
        workspace.manifest.copies = [Copy(source="b", target=".config")]

        findings = []
        _check_asset_target_clashes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert ".config" in findings[0].message


class TestCheckAssetTargetEscapes:
    def test_returns_no_findings_for_safe_target(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="subdir/config.json")]
        workspace.manifest.copies = []

        findings = []
        _check_asset_target_escapes(workspace, findings)
        assert findings == []

    def test_returns_error_for_dotdot_escape(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="../../etc/passwd")]
        workspace.manifest.copies = []

        findings = []
        _check_asset_target_escapes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_returns_error_for_absolute_target(self, workspace: MagicMock) -> None:
        workspace.manifest.links = []
        workspace.manifest.copies = [Copy(source="a", target="/etc/passwd")]

        findings = []
        _check_asset_target_escapes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_single_dotdot_is_an_escape(self, workspace: MagicMock) -> None:
        workspace.manifest.links = [Link(source="a", target="..")]
        workspace.manifest.copies = []

        findings = []
        _check_asset_target_escapes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"


class TestCheckVarNormalizationClashes:
    def test_returns_no_findings_for_unique_keys(self, workspace: MagicMock) -> None:
        workspace.manifest.vars = {"foo": "1", "bar": "2"}

        findings = []
        _check_var_normalization_clashes(workspace, findings)
        assert findings == []

    def test_returns_error_for_clashing_keys(self, workspace: MagicMock) -> None:
        workspace.manifest.vars = {"my-key": "1", "my_key": "2"}

        findings = []
        _check_var_normalization_clashes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "my-key" in findings[0].message
        assert "my_key" in findings[0].message


class TestCheckHookBinReferences:
    def test_inline_command_with_spaces_is_not_flagged(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=["docker build . -t myapp"])

        findings = []
        _check_hook_bin_references(workspace, findings)
        assert findings == []

    def test_warns_for_missing_bin_script(self, workspace: MagicMock, tmp_path: Path) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=["install_deps"])

        findings = []
        _check_hook_bin_references(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "install_deps" in findings[0].message

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

        findings = []
        _check_hook_bin_references(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "not executable" in findings[0].message

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

        findings = []
        _check_hook_bin_references(workspace, findings)
        assert findings == []

    def test_empty_entry_is_skipped(self, workspace: MagicMock, tmp_path: Path) -> None:
        workspace.paths.bin = tmp_path / "bin"
        workspace.paths.bin.mkdir()
        workspace.manifest.hooks = Hooks(on_setup=[""])

        findings = []
        _check_hook_bin_references(workspace, findings)
        assert findings == []


class TestCheckHookEmptyEntries:
    def test_returns_no_findings_for_non_empty_hooks(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install"])

        findings = []
        _check_hook_empty_entries(workspace, findings)
        assert findings == []

    def test_returns_warning_for_empty_entry(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=[""])

        findings = []
        _check_hook_empty_entries(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "on_setup" in findings[0].message

    def test_returns_warning_for_whitespace_only_entry(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_detach=["   "])

        findings = []
        _check_hook_empty_entries(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "on_detach" in findings[0].message


class TestCheckHookDuplicates:
    def test_returns_no_findings_for_unique_entries(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["a", "b"])

        findings = []
        _check_hook_duplicates(workspace, findings)
        assert findings == []

    def test_returns_warning_for_duplicate_in_same_event(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install", "install"])

        findings = []
        _check_hook_duplicates(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "on_setup" in findings[0].message
        assert "install" in findings[0].message

    def test_same_entry_in_different_events_is_fine(self, workspace: MagicMock) -> None:
        workspace.manifest.hooks = Hooks(on_setup=["install"], on_attach=["install"])

        findings = []
        _check_hook_duplicates(workspace, findings)
        assert findings == []


class TestCheckOrphanedBinScripts:
    def test_returns_no_findings_when_bin_dir_absent(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.bin = tmp_path / "bin"

        findings = []
        _check_orphaned_bin_scripts(workspace, findings)
        assert findings == []

    def test_returns_no_findings_when_all_scripts_referenced(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "setup.sh").write_text("#!/bin/sh")
        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks(on_setup=["setup.sh"])

        findings = []
        _check_orphaned_bin_scripts(workspace, findings)
        assert findings == []

    def test_returns_warning_for_unreferenced_script(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "unused.sh").write_text("#!/bin/sh")
        workspace.paths.bin = bin_dir
        workspace.manifest.hooks = Hooks()

        findings = []
        _check_orphaned_bin_scripts(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "unused.sh" in findings[0].message


class TestCheckOrphanedAssets:
    def test_returns_no_findings_when_assets_dir_absent(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        workspace.paths.assets = tmp_path / "assets"

        findings = []
        _check_orphaned_assets(workspace, findings)
        assert findings == []

    def test_returns_no_findings_when_all_assets_referenced(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "dotfile").write_text("content")
        workspace.paths.assets = assets_dir
        workspace.manifest.links = [Link(source="dotfile", target=".dotfile")]
        workspace.manifest.copies = []

        findings = []
        _check_orphaned_assets(workspace, findings)
        assert findings == []

    def test_returns_warning_for_unreferenced_asset(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets_dir = tmp_path / "assets"
        assets_dir.mkdir()
        (assets_dir / "orphan.txt").write_text("content")
        workspace.paths.assets = assets_dir
        workspace.manifest.links = []
        workspace.manifest.copies = []

        findings = []
        _check_orphaned_assets(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "orphan.txt" in findings[0].message


class TestCheckBaseBranch:
    def test_returns_no_findings_when_local_branch_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=True)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=False)
        workspace.manifest.base_branch = "main"

        findings = []
        _check_base_branch(workspace, findings)
        assert findings == []

    def test_returns_no_findings_when_remote_branch_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=False)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=True)
        workspace.manifest.base_branch = "main"

        findings = []
        _check_base_branch(workspace, findings)
        assert findings == []

    def test_returns_warning_when_neither_exists(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        mocker.patch("git_workspace.doctor.git.local_branch_exists", return_value=False)
        mocker.patch("git_workspace.doctor.git.remote_branch_exists", return_value=False)
        workspace.manifest.base_branch = "develop"

        findings = []
        _check_base_branch(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "develop" in findings[0].message


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

        findings = []
        _check_stale_worktrees(workspace, findings)
        assert findings == []

    def test_returns_warning_for_missing_dir(
        self, workspace: MagicMock, mocker: MockerFixture, tmp_path: Path
    ) -> None:
        wt_dir = tmp_path / "gone"
        mocker.patch(
            "git_workspace.doctor.git.list_worktrees",
            return_value=[{"directory": str(wt_dir), "branch": "feature/gone", "head": "abc123"}],
        )

        findings = []
        _check_stale_worktrees(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "feature/gone" in findings[0].message

    def test_returns_no_findings_on_listing_error(
        self, workspace: MagicMock, mocker: MockerFixture
    ) -> None:
        from git_workspace.errors import WorktreeListingError

        mocker.patch(
            "git_workspace.doctor.git.list_worktrees",
            side_effect=WorktreeListingError("git error"),
        )

        findings = []
        _check_stale_worktrees(workspace, findings)
        assert findings == []


class TestCheckCopyPlaceholders:
    def test_returns_no_findings_for_known_base_var(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text("branch={{ GIT_WORKSPACE_BRANCH }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)
        assert findings == []

    def test_returns_no_findings_for_known_manifest_var(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text("env={{ GIT_WORKSPACE_VAR_ENV }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {"env": "staging"}

        findings = []
        _check_copy_placeholders(workspace, findings)
        assert findings == []

    def test_returns_warning_for_unknown_placeholder(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text("x={{ GIT_WORKSPACE_TYPO }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "GIT_WORKSPACE_TYPO" in findings[0].message

    def test_deduplicates_repeated_unknown_placeholder_in_same_file(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text(
            "{{ GIT_WORKSPACE_TYPO }} and {{ GIT_WORKSPACE_TYPO }}"
        )
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)

        assert len(findings) == 1

    def test_skips_missing_source(self, workspace: MagicMock, tmp_path: Path) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="missing.txt", target="missing.txt")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)
        assert findings == []

    def test_skips_binary_files(self, workspace: MagicMock, tmp_path: Path) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "binary.bin").write_bytes(b"\xff\xfe")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="binary.bin", target="binary.bin")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)
        assert findings == []

    def test_checks_files_inside_directory_source(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        subdir = assets / "config"
        subdir.mkdir()
        (subdir / "app.yaml").write_text("key={{ GIT_WORKSPACE_UNKNOWN }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="config", target="config")]
        workspace.manifest.vars = {}

        findings = []
        _check_copy_placeholders(workspace, findings)

        assert len(findings) == 1
        assert "GIT_WORKSPACE_UNKNOWN" in findings[0].message

    def test_returns_no_findings_for_fingerprint_placeholder(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text("hash={{ GIT_WORKSPACE_FINGERPRINT_DEPS }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {}
        workspace.manifest.fingerprints = [Fingerprint(name="deps", files=["package.json"])]

        findings = []
        _check_copy_placeholders(workspace, findings)
        assert findings == []

    def test_warns_for_fingerprint_placeholder_when_fingerprint_not_declared(
        self, workspace: MagicMock, tmp_path: Path
    ) -> None:
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "template.txt").write_text("hash={{ GIT_WORKSPACE_FINGERPRINT_DEPS }}")
        workspace.paths.assets = assets
        workspace.manifest.copies = [Copy(source="template.txt", target="template.txt")]
        workspace.manifest.vars = {}
        workspace.manifest.fingerprints = []

        findings = []
        _check_copy_placeholders(workspace, findings)

        assert len(findings) == 1
        assert "GIT_WORKSPACE_FINGERPRINT_DEPS" in findings[0].message


class TestCheckFingerprintNameClashes:
    def test_returns_no_findings_for_unique_names(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="alpha", files=[]),
            Fingerprint(name="beta", files=[]),
        ]

        findings = []
        _check_fingerprint_name_clashes(workspace, findings)
        assert findings == []

    def test_returns_error_for_clashing_normalized_names(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="docker-deps", files=[]),
            Fingerprint(name="docker_deps", files=[]),
        ]

        findings = []
        _check_fingerprint_name_clashes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "docker-deps" in findings[0].message
        assert "docker_deps" in findings[0].message


class TestCheckFingerprintNameVarClashes:
    def test_returns_no_findings_when_no_overlap(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="deps", files=[])]
        workspace.manifest.vars = {"other": "value"}

        findings = []
        _check_fingerprint_name_var_clashes(workspace, findings)
        assert findings == []

    def test_returns_warning_when_normalized_names_match(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="my-key", files=[])]
        workspace.manifest.vars = {"my_key": "value"}

        findings = []
        _check_fingerprint_name_var_clashes(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "my-key" in findings[0].message


class TestCheckFingerprintEmptyName:
    def test_returns_no_findings_for_non_empty_name(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="deps", files=[])]

        findings = []
        _check_fingerprint_empty_name(workspace, findings)
        assert findings == []

    def test_returns_error_for_empty_name(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="", files=[])]

        findings = []
        _check_fingerprint_empty_name(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_returns_error_for_whitespace_only_name(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="   ", files=[])]

        findings = []
        _check_fingerprint_empty_name(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"


class TestCheckFingerprintFiles:
    def test_returns_no_findings_for_valid_files(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="deps", files=["package.json", "uv.lock"])
        ]

        findings = []
        _check_fingerprint_files(workspace, findings)
        assert findings == []

    def test_returns_warning_for_empty_files_list(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="deps", files=[])]

        findings = []
        _check_fingerprint_files(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"

    def test_returns_warning_for_duplicate_file(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="deps", files=["package.json", "package.json"])
        ]

        findings = []
        _check_fingerprint_files(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "package.json" in findings[0].message

    def test_returns_error_for_dotdot_escape(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="deps", files=["../../etc/passwd"])
        ]

        findings = []
        _check_fingerprint_files(workspace, findings)

        assert any(f.level == "error" for f in findings)

    def test_returns_error_for_absolute_path(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="deps", files=["/etc/passwd"])
        ]

        findings = []
        _check_fingerprint_files(workspace, findings)

        assert any(f.level == "error" for f in findings)


class TestCheckFingerprintAlgorithm:
    def test_returns_no_findings_for_sha256(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], algorithm="sha256")]

        findings = []
        _check_fingerprint_algorithm(workspace, findings)
        assert findings == []

    def test_returns_no_findings_for_md5(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], algorithm="md5")]

        findings = []
        _check_fingerprint_algorithm(workspace, findings)
        assert findings == []

    def test_returns_error_for_unsupported_algorithm(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], algorithm="blake2b")]

        findings = []
        _check_fingerprint_algorithm(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"
        assert "blake2b" in findings[0].message


class TestCheckFingerprintLength:
    def test_returns_no_findings_for_valid_length(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], length=12)]

        findings = []
        _check_fingerprint_length(workspace, findings)
        assert findings == []

    def test_returns_error_for_zero_length(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], length=0)]

        findings = []
        _check_fingerprint_length(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_returns_error_for_negative_length(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [Fingerprint(name="x", files=[], length=-1)]

        findings = []
        _check_fingerprint_length(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "error"

    def test_returns_warning_when_length_exceeds_digest_size(self, workspace: MagicMock) -> None:
        workspace.manifest.fingerprints = [
            Fingerprint(name="x", files=[], algorithm="md5", length=100)
        ]

        findings = []
        _check_fingerprint_length(workspace, findings)

        assert len(findings) == 1
        assert findings[0].level == "warning"
        assert "32" in findings[0].message
