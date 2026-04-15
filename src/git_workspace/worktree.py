from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, TYPE_CHECKING

from git_workspace import git
from git_workspace.errors import GitFetchError, WorktreeResolutionError

if TYPE_CHECKING:
    from git_workspace.workspace import Workspace


def _directory_birthtime(directory: Path) -> datetime:
    stat = directory.stat()
    ts = getattr(stat, "st_birthtime", None) or stat.st_ctime
    return datetime.fromtimestamp(ts)


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
    directory: Path
    branch: str
    is_new: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def age_days(self) -> int:
        """Returns the number of full days since the worktree directory was created."""
        return (datetime.now() - self.timestamp).days

    @classmethod
    def list(cls, workspace: Workspace) -> List[Worktree]:
        """
        Returns all worktrees currently registered in the workspace.

        :param workspace: The workspace whose worktrees should be listed.
        :returns: List of ``Worktree`` instances, one per registered git worktree.
        :raises WorktreeListingError: If ``git worktree list`` fails.
        """
        raw_worktrees = git.list_worktrees(cwd=workspace.directory)
        return [
            Worktree(
                workspace=workspace,
                directory=(d := Path(raw_worktree["directory"]).resolve()),
                branch=raw_worktree["branch"],
                is_new=False,
                timestamp=_directory_birthtime(d),
            )
            for raw_worktree in raw_worktrees
        ]

    @classmethod
    def _try_resolve_existing(
        cls, workspace: Workspace, branch: str
    ) -> Worktree | None:
        existing_worktrees = cls.list(workspace)
        return next(
            (worktree for worktree in existing_worktrees if worktree.branch == branch),
            None,
        )

    @classmethod
    def _try_create_from_local_branch(
        cls,
        workspace: Workspace,
        branch: str,
    ) -> Worktree | None:
        if not git.local_branch_exists(branch, cwd=workspace.paths.root):
            return None

        directory = workspace.paths.worktree(branch)
        git.create_worktree_from_local_branch(
            directory, branch, cwd=workspace.paths.root
        )

        return Worktree(
            workspace=workspace,
            directory=directory,
            branch=branch,
            is_new=True,
        )

    @classmethod
    def _try_create_from_remote_branch(
        cls,
        workspace: Workspace,
        branch: str,
    ) -> Worktree | None:
        try:
            git.fetch_origin(cwd=workspace.paths.root)
        except GitFetchError:
            return None

        if not git.remote_branch_exists(branch, cwd=workspace.directory):
            return None

        directory = workspace.paths.worktree(branch)
        git.create_worktree_from_remote_branch(
            directory,
            branch,
            cwd=workspace.directory,
        )

        return Worktree(
            workspace=workspace,
            directory=directory,
            branch=branch,
            is_new=True,
        )

    @classmethod
    def _create_new(
        cls,
        workspace: Workspace,
        branch: str,
        base_branch: str | None,
    ) -> Worktree:
        resolved_base_branch = base_branch or workspace.manifest.base_branch

        directory = workspace.paths.worktree(branch)
        git.create_worktree_new(
            directory,
            branch,
            resolved_base_branch,
            cwd=workspace.paths.root,
        )

        return Worktree(
            workspace=workspace,
            directory=directory,
            branch=branch,
            is_new=True,
        )

    @classmethod
    def _resolve_from_cwd(
        cls,
        workspace: Workspace,
    ) -> Worktree:
        worktree_dir = git.try_get_worktree_dir()
        if worktree_dir is None:
            # TODO: Improve exception msg
            raise WorktreeResolutionError("can't resolve worktree from cwd")
        branch = git.get_worktree_branch(cwd=worktree_dir)

        return Worktree(
            workspace=workspace,
            directory=Path(worktree_dir).resolve(),
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
                # TODO: Improve exception msg
                raise WorktreeResolutionError("can't resolve worktree from cwd")
            return worktree
        else:
            return cls._resolve_from_cwd(workspace)

    @classmethod
    def resolve_or_create(
        cls,
        workspace: Workspace,
        branch: str | None,
        base_branch: str | None,
    ) -> Worktree:
        """
        Resolves an existing worktree or creates a new one for the given branch.

        Resolution is attempted in order: existing worktree → local branch →
        remote branch → brand new branch from ``base_branch``. If ``branch`` is
        ``None``, the worktree is resolved from the current working directory
        without creation.

        :param workspace: The workspace to operate on.
        :param branch: The branch name to resolve or create, or ``None`` to
            resolve from cwd.
        :param base_branch: The branch to base a new branch on. Falls back to
            the manifest's ``base_branch`` if ``None``.
        :returns: The resolved or newly created ``Worktree`` instance.
        :raises WorktreeResolutionError: If ``branch`` is ``None`` and the cwd
            is not inside a known worktree.
        :raises WorktreeCreationError: If worktree creation fails at the git level.
        """
        if branch:
            return (
                cls._try_resolve_existing(workspace, branch)
                or cls._try_create_from_local_branch(workspace, branch)
                or cls._try_create_from_remote_branch(workspace, branch)
                or cls._create_new(workspace, branch, base_branch)
            )
        else:
            return cls._resolve_from_cwd(workspace)

    def _clean_intermediary_empty_paths(self) -> None:
        parent = self.directory.parent
        while parent != self.workspace.directory:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def delete(self, force: bool) -> None:
        """
        Removes this worktree and cleans up any empty intermediary directories.

        Delegates to ``git worktree remove`` and then walks up the directory
        tree removing empty parents until the workspace root is reached.

        :param force: If ``True``, removes the worktree even if it has
            uncommitted changes.
        :raises WorktreeRemovalError: If ``git worktree remove`` fails.
        """
        git.remove_worktree(self.directory, force, cwd=self.workspace.directory)
        self._clean_intermediary_empty_paths()
