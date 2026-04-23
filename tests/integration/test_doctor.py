import shutil

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace import ui
from git_workspace.cli.commands.doctor import doctor
from git_workspace.cli.commands.up import up
from git_workspace.errors import InvalidWorkspaceError, UnableToResolveWorkspaceError
from git_workspace.manifest import Manifest
from git_workspace.workspace import Workspace


def _remove_keep_files(workspace: Workspace) -> None:
    for d in [workspace.paths.assets, workspace.paths.bin]:
        keep = d / ".keep"
        if keep.exists():
            keep.unlink()


def _errors(mocker: MockerFixture):
    return mocker.patch.object(ui.console, "error")


def _warnings(mocker: MockerFixture):
    return mocker.patch.object(ui.console, "warning")


def _messages(mock) -> list[str]:
    return [call[0][0] for call in mock.call_args_list]


class TestDoctorNotInWorkspace:
    def test_errors_outside_workspace(self, tmp_path: Workspace) -> None:
        with pytest.raises((InvalidWorkspaceError, UnableToResolveWorkspaceError)):
            doctor(workspace_dir=str(tmp_path))


class TestDoctorManifestParseable:
    def test_errors_on_unparseable_manifest(
        self, workspace: Workspace, mocker: MockerFixture
    ) -> None:
        workspace.paths.manifest.write_text("!!! not valid toml !!!")

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace.dir))

        assert exc.value.exit_code == 1
        assert any("TOML" in msg for msg in _messages(mock_error))


class TestDoctorManifestVersion:
    def test_errors_on_unsupported_version(
        self, workspace: Workspace, mocker: MockerFixture
    ) -> None:
        workspace.paths.manifest.write_text(
            f'version = {Manifest.DEFAULT_VERSION + 1}\nbase_branch = "main"'
        )

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace.dir))

        assert exc.value.exit_code == 1
        assert any(str(Manifest.DEFAULT_VERSION + 1) in msg for msg in _messages(mock_error))


class TestDoctorAssetSourcesExist:
    def test_errors_on_missing_link_source(
        self, workspace_with_links: Workspace, mocker: MockerFixture
    ) -> None:
        for f in workspace_with_links.paths.assets.iterdir():
            f.unlink()

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace_with_links.dir))

        assert exc.value.exit_code == 1
        mock_error.assert_called()

    def test_errors_on_missing_copy_source(
        self, workspace_with_copies: Workspace, mocker: MockerFixture
    ) -> None:
        for f in workspace_with_copies.paths.assets.iterdir():
            f.unlink()

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace_with_copies.dir))

        assert exc.value.exit_code == 1
        mock_error.assert_called()


class TestDoctorAssetTargetClashes:
    def test_errors_on_clashing_link_targets(
        self, workspace_with_links: Workspace, mocker: MockerFixture
    ) -> None:
        workspace_with_links.paths.manifest.write_text("""
version = 1
base_branch = "main"

[[link]]
source = "dotfile"
target = ".shared"

[[link]]
source = "settings.json"
target = ".shared"
""")

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace_with_links.dir))

        assert exc.value.exit_code == 1
        assert any(".shared" in msg for msg in _messages(mock_error))

    def test_errors_on_link_copy_target_clash(
        self, workspace_with_links: Workspace, mocker: MockerFixture
    ) -> None:
        workspace_with_links.paths.manifest.write_text("""
version = 1
base_branch = "main"

[[link]]
source = "dotfile"
target = ".shared"

[[copy]]
source = "settings.json"
target = ".shared"
""")

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace_with_links.dir))

        assert exc.value.exit_code == 1
        assert any(".shared" in msg for msg in _messages(mock_error))


class TestDoctorAssetTargetEscapes:
    def test_errors_on_target_escaping_worktree(
        self, workspace_with_links: Workspace, mocker: MockerFixture
    ) -> None:
        workspace_with_links.paths.manifest.write_text("""
version = 1
base_branch = "main"

[[link]]
source = "dotfile"
target = "../../escape"
""")

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace_with_links.dir))

        assert exc.value.exit_code == 1
        assert any("escape" in msg for msg in _messages(mock_error))


class TestDoctorVarNormalizationClashes:
    def test_errors_on_clashing_var_keys(self, workspace: Workspace, mocker: MockerFixture) -> None:
        workspace.paths.manifest.write_text("""
version = 1
base_branch = "main"

[vars]
my-key = "a"
my_key = "b"
""")

        mock_error = _errors(mocker)

        with pytest.raises(typer.Exit) as exc:
            doctor(workspace_dir=str(workspace.dir))

        assert exc.value.exit_code == 1
        assert any("my-key" in msg and "my_key" in msg for msg in _messages(mock_error))


class TestDoctorHookBinReferences:
    def test_warns_on_missing_bin_script(
        self, workspace_with_hooks: Workspace, mocker: MockerFixture
    ) -> None:
        (workspace_with_hooks.paths.bin / "on_setup").unlink()

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace_with_hooks.dir))

        assert any("on_setup" in msg for msg in _messages(mock_warning))

    def test_warns_on_non_executable_bin_script(
        self, workspace_with_hooks: Workspace, mocker: MockerFixture
    ) -> None:
        (workspace_with_hooks.paths.bin / "on_setup").chmod(0o644)

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace_with_hooks.dir))

        assert any("on_setup" in msg and "executable" in msg for msg in _messages(mock_warning))


class TestDoctorHookEmptyEntries:
    def test_warns_on_empty_hook_entry(self, workspace: Workspace, mocker: MockerFixture) -> None:
        workspace.paths.manifest.write_text("""
version = 1
base_branch = "main"

[hooks]
on_setup = [""]
""")

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace.dir))

        assert any("on_setup" in msg for msg in _messages(mock_warning))


class TestDoctorHookDuplicates:
    def test_warns_on_duplicate_hook_entry(
        self, workspace: Workspace, mocker: MockerFixture
    ) -> None:
        workspace.paths.manifest.write_text("""
version = 1
base_branch = "main"

[hooks]
on_setup = ["echo hello", "echo hello"]
""")

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace.dir))

        assert any("on_setup" in msg and "echo hello" in msg for msg in _messages(mock_warning))


class TestDoctorOrphanedBinScripts:
    def test_warns_on_unreferenced_bin_script(
        self, workspace_with_hooks: Workspace, mocker: MockerFixture
    ) -> None:
        (workspace_with_hooks.paths.bin / "orphan.sh").write_text("#!/bin/sh\necho orphan")

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace_with_hooks.dir))

        assert any("orphan.sh" in msg for msg in _messages(mock_warning))


class TestDoctorOrphanedAssets:
    def test_warns_about_unreferenced_asset(
        self, workspace_with_links: Workspace, mocker: MockerFixture
    ) -> None:
        (workspace_with_links.paths.assets / "orphan.txt").write_text("unused")

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace_with_links.dir))

        assert any("orphan.txt" in msg for msg in _messages(mock_warning))


class TestDoctorBaseBranch:
    def test_warns_on_nonexistent_base_branch(
        self, workspace: Workspace, mocker: MockerFixture
    ) -> None:
        workspace.paths.manifest.write_text("""
version = 1
base_branch = "this-branch-does-not-exist"
""")

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace.dir))

        assert any("this-branch-does-not-exist" in msg for msg in _messages(mock_warning))


class TestDoctorStaleWorktrees:
    def test_warns_about_stale_worktree(self, workspace: Workspace, mocker: MockerFixture) -> None:
        up(branch="main", workspace_dir=str(workspace.dir))
        shutil.rmtree(workspace.paths.worktree("main"))

        mock_warning = _warnings(mocker)

        doctor(workspace_dir=str(workspace.dir))

        assert any("main" in msg and "no longer exists" in msg for msg in _messages(mock_warning))


class TestDoctorClean:
    def test_healthy_workspace_prints_success(
        self, workspace: Workspace, mocker: MockerFixture
    ) -> None:
        _remove_keep_files(workspace)
        mock_success = mocker.patch.object(ui.console, "success")

        doctor(workspace_dir=str(workspace.dir))

        mock_success.assert_called_once()
        assert "healthy" in mock_success.call_args[0][0].lower()

    def test_healthy_workspace_exits_0(self, workspace: Workspace) -> None:
        _remove_keep_files(workspace)

        doctor(workspace_dir=str(workspace.dir))
