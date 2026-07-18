import builtins
import logging
import shutil
from pathlib import Path

from git_workspace.errors import (
    GitFetchError,
    WorktreeAlreadyExistsError,
    WorktreeCreationError,
    WorktreeNotFoundError,
)
from git_workspace.subprocesses import git
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.models import ManagedWorktree, ProviderKind, WorktreeRequest

logger = logging.getLogger(__name__)


class NativeGitProvider:
    """
    Worktree provider backed by the git CLI.

    Owns the full worktree-creation resolution chain: local branch → remote
    branch (with tracking) → new branch from base (preferring origin/<base>)
    → orphan fallback for empty repositories.
    """

    def __init__(self, runner: CommandRunner = DEFAULT_RUNNER) -> None:
        self._runner = runner

    @property
    def kind(self) -> ProviderKind:
        return ProviderKind.NATIVE_GIT

    def is_available(self) -> bool:
        return shutil.which("git") is not None

    def create(self, request: WorktreeRequest) -> ManagedWorktree:
        repository_path = request.repository_path
        branch = request.branch
        target = request.target_path or (repository_path / branch).resolve()

        if any(wt.worktree_path == target for wt in self.list(repository_path)):
            raise WorktreeAlreadyExistsError(f"A worktree already exists at {target}")

        if git.local_branch_exists(branch, cwd=repository_path, runner=self._runner):
            logger.info("creating worktree from local branch %r", branch)
            git.create_worktree_from_local_branch(
                target, branch, cwd=repository_path, runner=self._runner
            )
            return self._managed(repository_path, target, branch)

        fetched = True
        try:
            git.fetch_origin(cwd=repository_path, runner=self._runner)
        except GitFetchError:
            logger.debug("fetch failed, proceeding with local refs only")
            fetched = False

        if fetched and git.remote_branch_exists(branch, cwd=repository_path, runner=self._runner):
            logger.info("creating worktree from remote branch %r", branch)
            git.create_worktree_from_remote_branch(
                target, branch, cwd=repository_path, runner=self._runner
            )
            return self._managed(repository_path, target, branch)

        if not request.create_branch:
            raise WorktreeCreationError(
                f"Branch {branch!r} does not exist and branch creation was not requested"
            )

        base_branch = request.base_branch
        if base_branch is None:
            raise WorktreeCreationError(f"A base branch is required to create branch {branch!r}")

        # Prefer origin/<base> so we always fork from the latest remote commit,
        # not a local ref that may be stale or locked by an active worktree.
        base_ref = (
            f"origin/{base_branch}"
            if git.remote_branch_exists(base_branch, cwd=repository_path, runner=self._runner)
            else base_branch
        )

        logger.info("creating new worktree for branch %r from base %r", branch, base_ref)
        git.create_worktree_new(target, branch, base_ref, cwd=repository_path, runner=self._runner)
        return self._managed(repository_path, target, branch)

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

        common_dir = git.git_common_dir(canonical, runner=self._runner)
        if common_dir is None:
            return None

        repository_path = common_dir.parent
        return next(
            (wt for wt in self.list(repository_path) if wt.worktree_path == canonical),
            None,
        )

    def list(self, repository_path: Path | None = None) -> builtins.list[ManagedWorktree]:
        if repository_path is None:
            raise WorktreeNotFoundError(
                "The native git provider has no global worktree registry; "
                "a repository path is required to list worktrees"
            )

        raw_worktrees = git.list_worktrees(cwd=repository_path, runner=self._runner)
        return [
            self._managed(repository_path, Path(raw["directory"]), raw["branch"])
            for raw in raw_worktrees
        ]

    def remove(self, worktree: ManagedWorktree, *, force: bool = False) -> None:
        git.remove_worktree(
            worktree.worktree_path,
            force,
            cwd=worktree.repository_path,
            runner=self._runner,
        )

    def _managed(self, repository_path: Path, worktree_path: Path, branch: str) -> ManagedWorktree:
        return ManagedWorktree(
            repository_path=repository_path,
            worktree_path=worktree_path,
            branch=branch,
            provider_kind=ProviderKind.NATIVE_GIT,
        )
