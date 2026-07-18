from __future__ import annotations

from dataclasses import dataclass

from git_workspace.presenters.base import WorkspacePresenter
from git_workspace.providers.base import WorktreeProvider


@dataclass(frozen=True)
class WorkspaceBackend:
    """
    A configured combination of one worktree provider and zero or one
    workspace presenter. A backend is configuration, not a lifecycle owner.
    """

    name: str
    provider: WorktreeProvider
    presenter: WorkspacePresenter | None
