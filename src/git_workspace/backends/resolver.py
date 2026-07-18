import logging

from git_workspace.backends.models import WorkspaceBackend
from git_workspace.errors import InvalidInputError
from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.models import PresenterKind, ProviderKind

logger = logging.getLogger(__name__)

NATIVE_BACKEND_NAME = "native"

_KNOWN_BACKENDS = (NATIVE_BACKEND_NAME,)


class WorkspaceBackendResolver:
    """
    Resolves the workspace backend to use for an operation.

    Only the native backend (native-git provider, no presenter) exists today;
    the resolver still validates its inputs so unknown names fail loudly once
    selection surfaces (CLI flags, configuration) are added.
    """

    def __init__(self, runner: CommandRunner = DEFAULT_RUNNER) -> None:
        self._runner = runner

    def resolve(
        self,
        *,
        backend_name: str | None = None,
        provider_kind: ProviderKind | None = None,
        presenter_kind: PresenterKind | None = None,
    ) -> WorkspaceBackend:
        if backend_name is not None and backend_name not in _KNOWN_BACKENDS:
            raise InvalidInputError(
                f"Unknown backend {backend_name!r}; available backends: "
                f"{', '.join(_KNOWN_BACKENDS)}"
            )
        if provider_kind is not None and provider_kind is not ProviderKind.NATIVE_GIT:
            raise InvalidInputError(f"Unknown provider {provider_kind!r}")
        if presenter_kind is not None and presenter_kind is not PresenterKind.NONE:
            raise InvalidInputError(f"Unknown presenter {presenter_kind!r}")

        logger.debug("resolved backend: native")
        return WorkspaceBackend(
            name=NATIVE_BACKEND_NAME,
            provider=NativeGitProvider(self._runner),
            presenter=None,
        )
