from __future__ import annotations

import builtins
from pathlib import Path
from typing import Protocol, runtime_checkable

from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterCapabilities,
    PresenterKind,
)


@runtime_checkable
class WorkspacePresenter(Protocol):
    """
    Owns the presentation of a worktree: an external runtime or UI such as an
    editor window or terminal session.

    A presenter must never create git branches, invoke `git worktree add`,
    remove worktrees, or run workspace preparation/teardown. Operations not
    supported by an implementation (see `capabilities`) must raise
    PresenterCapabilityError instead of silently claiming success.
    """

    @property
    def kind(self) -> PresenterKind:
        """Return the stable presenter identifier."""
        ...

    @property
    def capabilities(self) -> PresenterCapabilities:
        """Return what this presenter reliably supports."""
        ...

    def is_available(self) -> bool:
        """
        Return whether the presenter can currently be used.

        Must not mutate state.
        """
        ...

    def open(self, worktree: ManagedWorktree) -> Presentation:
        """
        Open or register a presentation for the worktree.

        Must be idempotent where the underlying platform allows it. If a
        presentation already exists, return it instead of creating a duplicate.
        """
        ...

    def find(self, worktree_path: Path) -> Presentation | None:
        """
        Find the presentation associated with a canonical worktree path.

        Must not mutate state.
        """
        ...

    def focus(
        self,
        worktree: ManagedWorktree,
        presentation: Presentation | None = None,
    ) -> Presentation:
        """
        Focus an existing presentation.

        May call open() when no presentation exists, if documented by the
        implementation.
        """
        ...

    def close(
        self,
        worktree: ManagedWorktree,
        presentation: Presentation | None = None,
    ) -> None:
        """
        Close or detach the presentation while preserving the git worktree.

        Must be idempotent.
        """
        ...

    def list(self, repository_path: Path | None = None) -> builtins.list[tuple[Path, Presentation]]:
        """
        List worktree-path-to-presentation mappings visible to this presenter.
        """
        ...
