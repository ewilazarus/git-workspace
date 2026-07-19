import builtins
import logging
from pathlib import Path

from git_workspace.errors import (
    HerdrError,
    PresentationNotFoundError,
    PresenterError,
    PresenterUnavailableError,
)
from git_workspace.subprocesses import herdr
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterCapabilities,
    PresenterKind,
)

logger = logging.getLogger(__name__)

_CAPABILITIES = PresenterCapabilities(
    can_find_existing=True,
    can_focus_existing=True,
    can_close=True,
    can_list=True,
    supports_runtime_identity=True,
)


class HerdrPresenter:
    """
    Presents worktrees as herdr workspaces.

    Never creates branches, invokes `git worktree add`, removes worktrees, or
    runs preparation — it only opens, focuses, closes, and lists workspaces.
    """

    def __init__(
        self,
        runner: CommandRunner = DEFAULT_RUNNER,
        executable: str | None = None,
    ) -> None:
        self._runner = runner
        self._explicit_executable = executable

    @property
    def kind(self) -> PresenterKind:
        return PresenterKind.HERDR

    @property
    def capabilities(self) -> PresenterCapabilities:
        return _CAPABILITIES

    def is_available(self) -> bool:
        return herdr.resolve_executable(self._explicit_executable) is not None

    def open(self, worktree: ManagedWorktree) -> Presentation:
        try:
            result = herdr.open_worktree(
                worktree.repository_path,
                worktree.worktree_path,
                executable=self._executable(),
                runner=self._runner,
            )
        except HerdrError as e:
            raise PresenterError(
                f"Herdr failed to open a workspace for {worktree.worktree_path}: {e}"
            ) from e

        workspace_id = result.get("workspace", {}).get("workspace_id")
        if workspace_id is None:
            raise PresenterError(
                f"Herdr did not return a workspace id for {worktree.worktree_path}"
            )
        return self._presentation(workspace_id)

    def find(self, worktree_path: Path) -> Presentation | None:
        canonical = worktree_path.expanduser().resolve()

        try:
            result = herdr.list_worktrees(
                canonical, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            if e.code == "not_git_worktree":
                return None
            raise PresenterError(f"Herdr failed to inspect {canonical}: {e}") from e

        workspace_id = next(
            (
                entry.get("open_workspace_id")
                for entry in result.get("worktrees", [])
                if Path(entry.get("path", "")) == canonical and entry.get("open_workspace_id")
            ),
            None,
        )
        return self._presentation(workspace_id) if workspace_id else None

    def focus(
        self,
        worktree: ManagedWorktree,
        presentation: Presentation | None = None,
    ) -> Presentation:
        """
        Focuses the workspace presenting the worktree, opening one when none
        exists yet.
        """
        target = presentation or self.find(worktree.worktree_path) or self.open(worktree)
        assert target.presentation_id is not None

        try:
            herdr.focus_workspace(
                target.presentation_id, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            if e.code == "workspace_not_found":
                raise PresentationNotFoundError(
                    f"Herdr workspace {target.presentation_id} no longer exists"
                ) from e
            raise PresenterError(
                f"Herdr failed to focus workspace {target.presentation_id}: {e}"
            ) from e
        return target

    def close(
        self,
        worktree: ManagedWorktree,
        presentation: Presentation | None = None,
    ) -> None:
        target = presentation or self.find(worktree.worktree_path)
        if target is None or target.presentation_id is None:
            return

        try:
            herdr.close_workspace(
                target.presentation_id, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            if e.code == "workspace_not_found":
                return
            raise PresenterError(
                f"Herdr failed to close workspace {target.presentation_id}: {e}"
            ) from e

    def list(self, repository_path: Path | None = None) -> builtins.list[tuple[Path, Presentation]]:
        if repository_path is None:
            raise PresenterError(
                "The herdr presenter lists presentations per repository; "
                "a repository path is required"
            )

        try:
            result = herdr.list_worktrees(
                repository_path, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            raise PresenterError(
                f"Herdr failed to list workspaces for {repository_path}: {e}"
            ) from e

        return [
            (Path(entry["path"]), self._presentation(entry["open_workspace_id"]))
            for entry in result.get("worktrees", [])
            if entry.get("open_workspace_id") and entry.get("is_linked_worktree")
        ]

    def _executable(self) -> str:
        executable = herdr.resolve_executable(self._explicit_executable)
        if executable is None:
            raise PresenterUnavailableError(
                "herdr is not available: set HERDR_BIN_PATH or install herdr on PATH"
            )
        return executable

    @staticmethod
    def _presentation(workspace_id: str) -> Presentation:
        return Presentation(
            presenter_kind=PresenterKind.HERDR,
            presentation_id=workspace_id,
        )
