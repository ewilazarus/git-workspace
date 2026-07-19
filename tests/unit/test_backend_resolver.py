from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from git_workspace.backends.resolver import WorkspaceBackendResolver
from git_workspace.errors import InvalidInputError, ProviderUnavailableError
from git_workspace.manifest import WorkspaceSettings
from git_workspace.presenters.herdr import HerdrPresenter
from git_workspace.providers.herdr import HerdrWorktreeProvider
from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.workspace.models import PresenterKind, ProviderKind


@pytest.fixture
def herdr_installed(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value="/usr/bin/herdr")


@pytest.fixture
def herdr_missing(mocker: MockerFixture) -> None:
    mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value=None)


@pytest.fixture
def herdr_context(monkeypatch, tmp_path: Path, herdr_installed: None) -> None:
    socket = tmp_path / "herdr.sock"
    socket.touch()
    monkeypatch.setenv("HERDR_ENV", "1")
    monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))


class TestDefaults:
    def test_resolves_native_outside_herdr_context(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve()

        assert backend.name == "native"
        assert isinstance(backend.provider, NativeGitProvider)
        assert backend.presenter is None

    def test_auto_detects_herdr_inside_verified_context(self, herdr_context: None) -> None:
        backend = WorkspaceBackendResolver().resolve()

        assert backend.name == "herdr"
        assert isinstance(backend.provider, HerdrWorktreeProvider)
        assert isinstance(backend.presenter, HerdrPresenter)

    def test_executable_alone_is_not_enough_for_auto(self, herdr_installed: None) -> None:
        # herdr installed but no verified context markers → native.
        backend = WorkspaceBackendResolver().resolve()

        assert backend.name == "native"

    def test_env_marker_without_socket_is_not_verified(
        self, monkeypatch, tmp_path: Path, herdr_installed: None
    ) -> None:
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(tmp_path / "missing.sock"))

        assert WorkspaceBackendResolver().resolve().name == "native"


class TestExplicitSelection:
    def test_backend_name_native(self, herdr_context: None) -> None:
        backend = WorkspaceBackendResolver().resolve(backend_name="native")

        assert backend.name == "native"
        assert backend.presenter is None

    def test_backend_name_herdr(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(backend_name="herdr")

        assert isinstance(backend.provider, HerdrWorktreeProvider)
        assert isinstance(backend.presenter, HerdrPresenter)

    def test_explicit_herdr_without_executable_raises(self, herdr_missing: None) -> None:
        with pytest.raises(ProviderUnavailableError):
            WorkspaceBackendResolver().resolve(backend_name="herdr")

    def test_unknown_backend_name_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            WorkspaceBackendResolver().resolve(backend_name="vscode")

    def test_explicit_kinds_compose_across_preset(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(
            backend_name="herdr",
            presenter_kind=PresenterKind.NONE,
        )

        assert isinstance(backend.provider, HerdrWorktreeProvider)
        assert backend.presenter is None

    def test_explicit_provider_overrides_preset(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(
            backend_name="herdr",
            provider_kind=ProviderKind.NATIVE_GIT,
        )

        assert isinstance(backend.provider, NativeGitProvider)
        assert isinstance(backend.presenter, HerdrPresenter)


class TestManifestSettings:
    def test_config_backend_preset(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(settings=WorkspaceSettings(backend="herdr"))

        assert isinstance(backend.provider, HerdrWorktreeProvider)

    def test_config_native_disables_auto_detection(self, herdr_context: None) -> None:
        backend = WorkspaceBackendResolver().resolve(settings=WorkspaceSettings(backend="native"))

        assert backend.name == "native"

    def test_config_member_overrides_apply(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(
            settings=WorkspaceSettings(backend="herdr", presenter="none")
        )

        assert isinstance(backend.provider, HerdrWorktreeProvider)
        assert backend.presenter is None

    def test_cli_backend_suppresses_config_member_overrides(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(
            backend_name="herdr",
            settings=WorkspaceSettings(presenter="none"),
        )

        assert isinstance(backend.presenter, HerdrPresenter)

    def test_cli_kinds_beat_config_members(self, herdr_installed: None) -> None:
        backend = WorkspaceBackendResolver().resolve(
            presenter_kind=PresenterKind.HERDR,
            settings=WorkspaceSettings(backend="native", presenter="none"),
        )

        assert isinstance(backend.presenter, HerdrPresenter)

    def test_unknown_config_provider_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            WorkspaceBackendResolver().resolve(settings=WorkspaceSettings(provider="subversion"))

    def test_unknown_config_presenter_raises(self) -> None:
        with pytest.raises(InvalidInputError):
            WorkspaceBackendResolver().resolve(settings=WorkspaceSettings(presenter="vscode"))
