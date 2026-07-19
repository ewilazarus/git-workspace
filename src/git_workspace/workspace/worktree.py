import builtins
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from git_workspace.errors import WorktreeResolutionError
from git_workspace.subprocesses import git
from git_workspace.utils import directory_birthtime

if TYPE_CHECKING:
    from git_workspace.workspace.core import Workspace

logger = logging.getLogger(__name__)


@dataclass
class Worktree:
    """
    Represents a git worktree within a workspace.

    Each worktree corresponds to a single branch checked out under the workspace
    root directory. The ``is_new`` flag indicates that the worktree was just
    created in the current operation rather than resolved from an existing one,
    which triggers setup hooks and asset linking.

    ``timestamp`` records when the worktree directory was created, used to
    compute the worktree's age in days.
    """

    workspace: Workspace
    dir: Path
    branch: str
    is_new: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def age_days(self) -> int:
        """Returns the number of full days since the worktree directory was created."""
        return (datetime.now() - self.timestamp).days

    @classmethod
    def list(cls, workspace: Workspace) -> builtins.list[Worktree]:
        """
        Returns all worktrees currently registered in the workspace.

        :param workspace: The workspace whose worktrees should be listed.
        :returns: List of ``Worktree`` instances, one per registered git worktree.
        :raises WorktreeListingError: If ``git worktree list`` fails.
        """
        return [
            Worktree(
                workspace=workspace,
                dir=managed.worktree_path,
                branch=managed.branch,
                is_new=False,
                timestamp=directory_birthtime(managed.worktree_path),
            )
            for managed in workspace.provider.list(workspace.dir)
        ]

    @classmethod
    def _try_resolve_existing(cls, workspace: Workspace, branch: str) -> Worktree | None:
        existing_worktrees = cls.list(workspace)
        worktree = next((wt for wt in existing_worktrees if wt.branch == branch), None)
        if worktree:
            logger.debug("found existing worktree for branch %r at %s", branch, worktree.dir)
        else:
            logger.debug("no existing worktree for branch %r", branch)
        return worktree

    @classmethod
    def _resolve_from_cwd(
        cls,
        workspace: Workspace,
    ) -> Worktree:
        logger.debug("resolving worktree from cwd")
        worktree_dir = git.try_get_worktree_dir()
        if worktree_dir is None:
            cwd = Path.cwd()
            logger.warning("cwd is not inside a git worktree")
            raise WorktreeResolutionError(
                f"Cannot resolve worktree from cwd: {cwd!r} is not inside a git worktree"
            )
        branch = git.get_worktree_branch(cwd=worktree_dir)
        logger.debug("resolved worktree from cwd: branch=%r dir=%s", branch, worktree_dir)

        return Worktree(
            workspace=workspace,
            dir=Path(worktree_dir).resolve(),
            branch=branch,
            is_new=False,
        )

    @classmethod
    def resolve(cls, workspace: Workspace, branch: str | None) -> Worktree:
        """
        Resolves an existing worktree by branch name or from the current working directory.

        If ``branch`` is provided, searches the registered worktrees for an exact
        match and raises if none is found. If ``branch`` is ``None``, the worktree
        is inferred from the current working directory.

        :param workspace: The workspace to search within.
        :param branch: The branch name to look up, or ``None`` to resolve from cwd.
        :returns: The matching ``Worktree`` instance.
        :raises WorktreeResolutionError: If no worktree can be resolved.
        """
        if branch:
            worktree = cls._try_resolve_existing(workspace, branch)
            if not worktree:
                logger.warning("no worktree found for branch %r", branch)
                raise WorktreeResolutionError(f"No worktree found for branch {branch!r}")
            return worktree
        else:
            return cls._resolve_from_cwd(workspace)
