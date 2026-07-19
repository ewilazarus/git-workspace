import builtins
import logging
from pathlib import Path

from git_workspace.errors import (
    HerdrError,
    ProviderError,
    ProviderUnavailableError,
    WorktreeAlreadyExistsError,
    WorktreeCreationError,
    WorktreeNotFoundError,
    WorktreeRemovalError,
)
from git_workspace.subprocesses import git, herdr
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.models import ManagedWorktree, ProviderKind, WorktreeRequest

logger = logging.getLogger(__name__)


class HerdrWorktreeProvider:
    """
    Worktree provider that delegates worktree ownership to herdr.

    Herdr opens a workspace presentation as a side effect of creating a
    worktree; the provider records the returned workspace id as metadata but
    never focuses or closes anything — that belongs to HerdrPresenter.

    Herdr removes worktrees by their open workspace id, so removal of a
    worktree that is not presented in herdr falls back to plain git removal.
    """

    def __init__(
        self,
        runner: CommandRunner = DEFAULT_RUNNER,
        executable: str | None = None,
    ) -> None:
        self._runner = runner
        self._explicit_executable = executable

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.HERDR

    def is_available(self) -> bool:
        return herdr.resolve_executable(self._explicit_executable) is not None

    def create(self, request: WorktreeRequest) -> ManagedWorktree:
        repository_path = request.repository_path
        target = request.target_path or (repository_path / request.branch).resolve()

        if any(wt.worktree_path == target for wt in self.list(repository_path)):
            raise WorktreeAlreadyExistsError(f"A worktree already exists at {target}")

        try:
            result = herdr.create_worktree(
                repository_path,
                request.branch,
                target,
                request.base_branch,
                executable=self._executable(),
                runner=self._runner,
            )
        except HerdrError as e:
            raise WorktreeCreationError(
                f"Herdr failed to create a worktree for branch {request.branch!r}: {e}"
            ) from e

        entry = result.get("worktree", {})
        return self._managed(
            repository_path,
            Path(entry.get("path", target)),
            entry.get("branch", request.branch),
            workspace_id=entry.get("open_workspace_id"),
        )

    def import_existing(self, worktree_path: Path) -> ManagedWorktree:
        worktree = self.find(worktree_path)
        if worktree is None:
            raise WorktreeNotFoundError(
                f"No registered git worktree found at {worktree_path.expanduser().resolve()}"
            )
        return worktree

    def find(self, worktree_path: Path) -> ManagedWorktree | None:
        canonical = worktree_path.expanduser().resolve()
        if not canonical.is_dir():
            return None

        try:
            result = herdr.list_worktrees(
                canonical, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            if e.code == "not_git_worktree":
                return None
            raise ProviderError(f"Herdr failed to inspect {canonical}: {e}") from e

        repository_path = Path(result.get("source", {}).get("repo_root", canonical))
        return next(
            (
                wt
                for wt in self._managed_entries(repository_path, result)
                if wt.worktree_path == canonical
            ),
            None,
        )

    def list(self, repository_path: Path | None = None) -> builtins.list[ManagedWorktree]:
        if repository_path is None:
            raise WorktreeNotFoundError(
                "The herdr provider lists worktrees per repository; a repository path is required"
            )

        try:
            result = herdr.list_worktrees(
                repository_path, executable=self._executable(), runner=self._runner
            )
        except HerdrError as e:
            raise ProviderError(f"Herdr failed to list worktrees in {repository_path}: {e}") from e

        return self._managed_entries(repository_path, result)

    def remove(self, worktree: ManagedWorktree, *, force: bool = False) -> None:
        current = self.find(worktree.worktree_path)
        if current is None:
            raise WorktreeNotFoundError(
                f"No registered git worktree found at {worktree.worktree_path}"
            )

        workspace_id = current.metadata.get("workspace_id")
        if workspace_id is None:
            # Not presented in herdr: herdr cannot address it, remove via git.
            logger.debug(
                "worktree %s has no herdr workspace; removing via git", worktree.worktree_path
            )
            git.remove_worktree(
                worktree.worktree_path,
                force,
                cwd=worktree.repository_path,
                runner=self._runner,
            )
            return

        try:
            herdr.remove_worktree(
                workspace_id,
                force=force,
                executable=self._executable(),
                runner=self._runner,
            )
        except HerdrError as e:
            if worktree.worktree_path.exists() and self.find(worktree.worktree_path) is None:
                raise WorktreeRemovalError(
                    "Herdr removed the workspace presentation, but the git worktree "
                    f"still exists: {worktree.worktree_path}"
                ) from e
            raise WorktreeRemovalError(
                f"Herdr failed to remove the worktree at {worktree.worktree_path}: {e}"
            ) from e

    def _executable(self) -> str:
        executable = herdr.resolve_executable(self._explicit_executable)
        if executable is None:
            raise ProviderUnavailableError(
                "herdr is not available: set HERDR_BIN_PATH or install herdr on PATH"
            )
        return executable

    def _managed_entries(
        self, repository_path: Path, result: dict
    ) -> builtins.list[ManagedWorktree]:
        return [
            self._managed(
                repository_path,
                Path(entry["path"]),
                entry["branch"],
                workspace_id=entry.get("open_workspace_id"),
            )
            for entry in result.get("worktrees", [])
            if entry.get("is_linked_worktree") and "branch" in entry
        ]

    def _managed(
        self,
        repository_path: Path,
        worktree_path: Path,
        branch: str,
        *,
        workspace_id: str | None,
    ) -> ManagedWorktree:
        metadata = {"workspace_id": workspace_id} if workspace_id else {}
        return ManagedWorktree(
            repository_path=repository_path,
            worktree_path=worktree_path,
            branch=branch,
            provider_kind=ProviderKind.HERDR,
            provider_id=workspace_id,
            metadata=metadata,
        )
