from __future__ import annotations

import builtins
from pathlib import Path
from typing import Protocol, runtime_checkable

from git_workspace.workspace.models import ManagedWorktree, ProviderKind, WorktreeRequest


@runtime_checkable
class WorktreeProvider(Protocol):
    """
    Owns the git worktree lifecycle: creation, discovery, and removal.

    A provider must never expose presentation behavior (focus, close, attach,
    open_window) and must never run workspace preparation.
    """

    @property
    def kind(self) -> ProviderKind:
        """Return the stable provider identifier."""
        ...

    def is_available(self) -> bool:
        """
        Return whether the provider can currently be used.

        Must not mutate state.
        """
        ...

    def create(self, request: WorktreeRequest) -> ManagedWorktree:
        """
        Create and register a git worktree.

        Must return only after the worktree exists. Must not run workspace
        preparation. Not inherently idempotent: when the target already exists
        it must either return the verified matching worktree or raise
        WorktreeAlreadyExistsError — never attach to an unrelated directory.
        """
        ...

    def import_existing(self, worktree_path: Path) -> ManagedWorktree:
        """
        Import or describe an existing registered git worktree.

        Must be idempotent. Must not prepare or present the worktree.
        Raises WorktreeNotFoundError when the path is not a registered worktree.
        """
        ...

    def find(self, worktree_path: Path) -> ManagedWorktree | None:
        """
        Find a managed worktree by canonical path.

        Must not mutate provider state.
        """
        ...

    def list(self, repository_path: Path | None = None) -> builtins.list[ManagedWorktree]:
        """
        List worktrees visible to this provider.

        When repository_path is supplied, filter to that repository.
        """
        ...

    def remove(self, worktree: ManagedWorktree, *, force: bool = False) -> None:
        """
        Remove the git worktree.

        Must not delete the branch. Must refuse dirty or unsafe removal unless
        force=True.
        """
        ...
