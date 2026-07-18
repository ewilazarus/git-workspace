import pytest

from git_workspace.backends.resolver import WorkspaceBackendResolver
from git_workspace.errors import InvalidInputError
from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.workspace.models import PresenterKind, ProviderKind


class TestWorkspaceBackendResolver:
    def test_resolves_native_backend_by_default(self) -> None:
        backend = WorkspaceBackendResolver().resolve()

        assert backend.name == "native"
        assert isinstance(backend.provider, NativeGitProvider)
        assert backend.presenter is None

    def test_resolves_native_backend_by_name(self) -> None:
        backend = WorkspaceBackendResolver().resolve(backend_name="native")

        assert backend.name == "native"

    def test_accepts_explicit_native_composition(self) -> None:
        backend = WorkspaceBackendResolver().resolve(
            provider_kind=ProviderKind.NATIVE_GIT,
            presenter_kind=PresenterKind.NONE,
        )

        assert isinstance(backend.provider, NativeGitProvider)
        assert backend.presenter is None

    def test_rejects_unknown_backend_name(self) -> None:
        with pytest.raises(InvalidInputError):
            WorkspaceBackendResolver().resolve(backend_name="herdr")
