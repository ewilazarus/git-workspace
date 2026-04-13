from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from git_workspace import git
from git_workspace.errors import WorktreeCreationError, WorktreeResolutionError  # noqa: F401 — re-exported for callers
from git_workspace.workspace import Workspace

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Worktree:
    workspace: Workspace
    directory: Path
    branch: str
    is_new: bool = False

    @classmethod
    def list(cls, workspace: Workspace) -> List[Worktree]:
        raw_worktrees = git.list_worktrees(str(workspace.directory))
        return [
            Worktree(
                workspace=workspace,
                directory=Path(raw_worktree["directory"]).resolve(),
                branch=raw_worktree["branch"],
                is_new=False,
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
        if not git.local_branch_exists(str(workspace.directory), branch):
            return None

        directory = workspace.directory / branch
        git.add_worktree(str(workspace.directory), str(directory), branch)

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
        git.fetch_origin()

        if not git.remote_branch_exists(str(workspace.directory), branch):
            return None

        directory = workspace.directory / branch
        git.add_worktree_tracking_remote(
            str(workspace.directory), str(directory), branch
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

        directory = workspace.directory / branch
        git.add_worktree_new_branch(
            str(workspace.directory),
            str(directory),
            branch,
            resolved_base_branch,
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
        raw_directory = git.try_get_worktree_dir()
        if raw_directory is None:
            # TODO: Improve exception msg
            raise WorktreeResolutionError("can't resolve worktree from cwd")
        branch = git.get_worktree_branch(raw_directory)

        return Worktree(
            workspace=workspace,
            directory=Path(raw_directory).resolve(),
            branch=branch,
            is_new=False,
        )

    @classmethod
    def resolve(cls, workspace: Workspace, branch: str | None) -> Worktree:
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
        git.remove_worktree(str(self.directory), force)
        self._clean_intermediary_empty_paths()
