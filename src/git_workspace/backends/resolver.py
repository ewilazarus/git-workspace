import logging

from git_workspace.backends.models import WorkspaceBackend
from git_workspace.errors import InvalidInputError, ProviderUnavailableError
from git_workspace.manifest import WorkspaceSettings
from git_workspace.presenters.base import WorkspacePresenter
from git_workspace.presenters.herdr import HerdrPresenter
from git_workspace.providers.base import WorktreeProvider
from git_workspace.providers.herdr import HerdrWorktreeProvider
from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.subprocesses import herdr
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.models import PresenterKind, ProviderKind

logger = logging.getLogger(__name__)

BACKEND_NATIVE = "native"
BACKEND_HERDR = "herdr"
BACKEND_AUTO = "auto"

_KNOWN_BACKENDS = (BACKEND_NATIVE, BACKEND_HERDR, BACKEND_AUTO)


class WorkspaceBackendResolver:
    """
    Resolves the workspace backend for an operation.

    Precedence: explicit CLI provider/presenter kinds → explicit CLI backend
    name → manifest ``[workspace]`` provider/presenter → manifest backend →
    verified environment detection → native.

    A CLI backend name suppresses the manifest's member overrides (the flag
    expresses full intent); CLI provider/presenter kinds always win over any
    preset. ``auto`` selects herdr only inside a verified herdr context —
    the executable merely existing is never enough.
    """

    def __init__(self, runner: CommandRunner = DEFAULT_RUNNER) -> None:
        self._runner = runner

    def resolve(
        self,
        *,
        backend_name: str | None = None,
        provider_kind: ProviderKind | None = None,
        presenter_kind: PresenterKind | None = None,
        settings: WorkspaceSettings | None = None,
    ) -> WorkspaceBackend:
        settings = settings or WorkspaceSettings()

        preset_name = backend_name or settings.backend or BACKEND_AUTO
        if preset_name not in _KNOWN_BACKENDS:
            raise InvalidInputError(
                f"Unknown backend {preset_name!r}; available backends: {', '.join(_KNOWN_BACKENDS)}"
            )

        resolved_provider_kind = provider_kind or (
            self._parse_provider(settings.provider) if backend_name is None else None
        )
        resolved_presenter_kind = presenter_kind or (
            self._parse_presenter(settings.presenter) if backend_name is None else None
        )

        name, preset_provider, preset_presenter = self._preset(preset_name)

        provider = (
            self._provider(resolved_provider_kind)
            if resolved_provider_kind is not None
            else preset_provider
        )
        presenter = (
            self._presenter(resolved_presenter_kind)
            if resolved_presenter_kind is not None
            else preset_presenter
        )

        logger.debug(
            "resolved backend %r (provider=%s, presenter=%s)",
            name,
            provider.kind,
            presenter.kind if presenter else None,
        )
        return WorkspaceBackend(name=name, provider=provider, presenter=presenter)

    def _preset(self, preset_name: str) -> tuple[str, WorktreeProvider, WorkspacePresenter | None]:
        if preset_name == BACKEND_AUTO:
            if self._herdr_context_verified():
                logger.debug("auto-detected verified herdr context")
                preset_name = BACKEND_HERDR
            else:
                preset_name = BACKEND_NATIVE

        if preset_name == BACKEND_HERDR:
            self._require_herdr()
            return (
                BACKEND_HERDR,
                HerdrWorktreeProvider(self._runner),
                HerdrPresenter(self._runner),
            )
        return (BACKEND_NATIVE, NativeGitProvider(self._runner), None)

    def _provider(self, kind: ProviderKind) -> WorktreeProvider:
        if kind is ProviderKind.HERDR:
            self._require_herdr()
            return HerdrWorktreeProvider(self._runner)
        return NativeGitProvider(self._runner)

    def _presenter(self, kind: PresenterKind) -> WorkspacePresenter | None:
        if kind is PresenterKind.HERDR:
            self._require_herdr()
            return HerdrPresenter(self._runner)
        return None

    @staticmethod
    def _parse_provider(raw: str | None) -> ProviderKind | None:
        if raw is None:
            return None
        try:
            return ProviderKind(raw)
        except ValueError:
            raise InvalidInputError(
                f"Unknown provider {raw!r}; available providers: "
                f"{', '.join(kind.value for kind in ProviderKind)}"
            ) from None

    @staticmethod
    def _parse_presenter(raw: str | None) -> PresenterKind | None:
        if raw is None:
            return None
        try:
            return PresenterKind(raw)
        except ValueError:
            raise InvalidInputError(
                f"Unknown presenter {raw!r}; available presenters: "
                f"{', '.join(kind.value for kind in PresenterKind)}"
            ) from None

    @staticmethod
    def _herdr_context_verified() -> bool:
        return herdr.in_verified_context() and herdr.resolve_executable() is not None

    @staticmethod
    def _require_herdr() -> None:
        if herdr.resolve_executable() is None:
            raise ProviderUnavailableError(
                "herdr is not available: set HERDR_BIN_PATH or install herdr on PATH"
            )
