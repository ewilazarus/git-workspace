import dataclasses
from pathlib import Path

import pytest

from git_workspace.workspace.models import (
    ManagedWorktree,
    ProviderKind,
    WorkspaceLifecycleState,
    WorkspaceRecord,
    WorktreeRequest,
)


class TestWorktreeRequest:
    def test_normalizes_repository_and_target_paths(self, tmp_path: Path) -> None:
        request = WorktreeRequest(
            repository_path=tmp_path / ".." / tmp_path.name,
            branch="feature/x",
            target_path=tmp_path / "sub" / ".." / "wt",
        )

        assert request.repository_path == tmp_path.resolve()
        assert request.target_path == (tmp_path / "wt").resolve()

    def test_expands_user_home(self) -> None:
        request = WorktreeRequest(repository_path=Path("~/repo"), branch="main")

        assert not str(request.repository_path).startswith("~")

    def test_is_frozen(self, tmp_path: Path) -> None:
        request = WorktreeRequest(repository_path=tmp_path, branch="main")

        with pytest.raises(dataclasses.FrozenInstanceError):
            request.branch = "other"  # ty: ignore[invalid-assignment]


class TestManagedWorktree:
    def test_normalizes_paths(self, tmp_path: Path) -> None:
        worktree = ManagedWorktree(
            repository_path=tmp_path / ".",
            worktree_path=tmp_path / "a" / ".." / "wt",
            branch="main",
            provider_kind=ProviderKind.NATIVE_GIT,
        )

        assert worktree.repository_path == tmp_path.resolve()
        assert worktree.worktree_path == (tmp_path / "wt").resolve()

    def test_is_frozen(self, tmp_path: Path) -> None:
        worktree = ManagedWorktree(
            repository_path=tmp_path,
            worktree_path=tmp_path / "wt",
            branch="main",
            provider_kind=ProviderKind.NATIVE_GIT,
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            worktree.branch = "other"  # ty: ignore[invalid-assignment]


class TestWorkspaceRecord:
    def test_holds_lifecycle_state_and_optional_error(self, tmp_path: Path) -> None:
        worktree = ManagedWorktree(
            repository_path=tmp_path,
            worktree_path=tmp_path / "wt",
            branch="main",
            provider_kind=ProviderKind.NATIVE_GIT,
        )

        record = WorkspaceRecord(
            worktree=worktree,
            presentation=None,
            lifecycle_state=WorkspaceLifecycleState.PREPARATION_FAILED,
            preparation_error="hook failed",
        )

        assert record.lifecycle_state is WorkspaceLifecycleState.PREPARATION_FAILED
        assert record.preparation_error == "hook failed"


class TestEnums:
    def test_provider_kind_values(self) -> None:
        assert ProviderKind.NATIVE_GIT.value == "native-git"

    def test_lifecycle_states_are_stable_identifiers(self) -> None:
        assert [state.value for state in WorkspaceLifecycleState] == [
            "created",
            "preparing",
            "ready",
            "preparation-failed",
            "detached",
            "tearing-down",
            "removed",
        ]
