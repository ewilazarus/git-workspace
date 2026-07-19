from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ProviderKind(StrEnum):
    NATIVE_GIT = "native-git"
    HERDR = "herdr"


class PresenterKind(StrEnum):
    NONE = "none"
    HERDR = "herdr"


class WorkspaceLifecycleState(StrEnum):
    CREATED = "created"
    PREPARING = "preparing"
    READY = "ready"
    PREPARATION_FAILED = "preparation-failed"
    DETACHED = "detached"
    TEARING_DOWN = "tearing-down"
    REMOVED = "removed"


def _canonical(path: Path) -> Path:
    return path.expanduser().resolve()


@dataclass(frozen=True)
class WorktreeRequest:
    repository_path: Path
    branch: str
    base_branch: str | None = None
    target_path: Path | None = None
    create_branch: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository_path", _canonical(self.repository_path))
        if self.target_path is not None:
            object.__setattr__(self, "target_path", _canonical(self.target_path))


@dataclass(frozen=True)
class ManagedWorktree:
    repository_path: Path
    worktree_path: Path
    branch: str
    provider_kind: ProviderKind
    provider_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "repository_path", _canonical(self.repository_path))
        object.__setattr__(self, "worktree_path", _canonical(self.worktree_path))


@dataclass(frozen=True)
class Presentation:
    presenter_kind: PresenterKind
    presentation_id: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PresenterCapabilities:
    can_find_existing: bool
    can_focus_existing: bool
    can_close: bool
    can_list: bool
    supports_runtime_identity: bool


@dataclass(frozen=True)
class WorkspaceRecord:
    worktree: ManagedWorktree
    presentation: Presentation | None
    lifecycle_state: WorkspaceLifecycleState
    preparation_error: str | None = None
