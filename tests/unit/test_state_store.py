import json
from pathlib import Path

import pytest

from git_workspace.errors import WorkspaceStateError
from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterKind,
    ProviderKind,
    WorkspaceLifecycleState,
    WorkspaceRecord,
)
from git_workspace.workspace.state import SCHEMA_VERSION, WorkspaceStateStore, state_file_stem


@pytest.fixture
def store(tmp_path: Path) -> WorkspaceStateStore:
    return WorkspaceStateStore(tmp_path / ".state")


@pytest.fixture
def worktree(tmp_path: Path) -> ManagedWorktree:
    return ManagedWorktree(
        repository_path=tmp_path / "workspace",
        worktree_path=tmp_path / "workspace" / "feature" / "auth",
        branch="feature/auth",
        provider_kind=ProviderKind.NATIVE_GIT,
    )


class TestStateFileStem:
    def test_is_deterministic(self, tmp_path: Path) -> None:
        path = tmp_path / "feature" / "auth"

        assert state_file_stem(path) == state_file_stem(path)

    def test_distinguishes_paths_with_same_name(self, tmp_path: Path) -> None:
        assert state_file_stem(tmp_path / "a" / "wt") != state_file_stem(tmp_path / "b" / "wt")

    def test_canonicalizes_before_hashing(self, tmp_path: Path) -> None:
        assert state_file_stem(tmp_path / "wt") == state_file_stem(tmp_path / "x" / ".." / "wt")

    def test_slug_is_filesystem_safe(self, tmp_path: Path) -> None:
        stem = state_file_stem(tmp_path / "we ird@name!")

        assert "/" not in stem
        assert " " not in stem
        assert "@" not in stem


class TestSaveAndLoad:
    def test_round_trips_a_record(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        record = WorkspaceRecord(
            worktree=worktree,
            presentation=None,
            lifecycle_state=WorkspaceLifecycleState.READY,
        )

        store.save(record)
        loaded = store.load(worktree.worktree_path)

        assert loaded == record

    def test_round_trips_presentation(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        record = WorkspaceRecord(
            worktree=worktree,
            presentation=Presentation(
                presenter_kind=PresenterKind.NONE,
                presentation_id="p-1",
                metadata={"session": "s-1"},
            ),
            lifecycle_state=WorkspaceLifecycleState.READY,
        )

        store.save(record)
        loaded = store.load(worktree.worktree_path)

        assert loaded == record

    def test_writes_schema_version(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)

        state_file = next(store.state_dir.glob("*.json"))
        assert json.loads(state_file.read_text())["schema_version"] == SCHEMA_VERSION

    def test_seeds_gitignore_in_state_dir(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)

        assert (store.state_dir / ".gitignore").read_text() == "*\n!.gitignore\n"

    def test_missing_state_is_none_not_an_error(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        assert store.load(worktree.worktree_path) is None

    def test_corrupt_state_is_treated_as_missing(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)
        state_file = next(store.state_dir.glob("*.json"))
        state_file.write_text("{ not json")

        assert store.load(worktree.worktree_path) is None

    def test_newer_schema_is_a_hard_error(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        record = store.save_created(worktree)
        state_file = next(store.state_dir.glob("*.json"))
        raw = json.loads(state_file.read_text())
        raw["schema_version"] = SCHEMA_VERSION + 1
        state_file.write_text(json.dumps(raw))

        with pytest.raises(WorkspaceStateError):
            store.load(record.worktree.worktree_path)


class TestTransitions:
    def test_save_created_persists_created_state(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        record = store.save_created(worktree)

        assert record.lifecycle_state is WorkspaceLifecycleState.CREATED
        assert store.load(worktree.worktree_path) == record

    def test_set_state_transitions_and_clears_error(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)
        store.mark_preparation_failed(worktree.worktree_path, error="boom")

        record = store.set_state(worktree.worktree_path, WorkspaceLifecycleState.READY)

        assert record.lifecycle_state is WorkspaceLifecycleState.READY
        assert record.preparation_error is None

    def test_mark_preparation_failed_records_error(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)

        record = store.mark_preparation_failed(worktree.worktree_path, error="hook exploded")

        assert record.lifecycle_state is WorkspaceLifecycleState.PREPARATION_FAILED
        assert record.preparation_error == "hook exploded"

    def test_set_state_requires_an_existing_record(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        with pytest.raises(WorkspaceStateError):
            store.set_state(worktree.worktree_path, WorkspaceLifecycleState.READY)


class TestDeleteAndList:
    def test_delete_removes_the_state_file(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.save_created(worktree)

        store.delete(worktree.worktree_path)

        assert store.load(worktree.worktree_path) is None

    def test_delete_is_idempotent(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree
    ) -> None:
        store.delete(worktree.worktree_path)

    def test_list_returns_all_records(
        self, store: WorkspaceStateStore, worktree: ManagedWorktree, tmp_path: Path
    ) -> None:
        other = ManagedWorktree(
            repository_path=tmp_path / "workspace",
            worktree_path=tmp_path / "workspace" / "other",
            branch="other",
            provider_kind=ProviderKind.NATIVE_GIT,
        )
        store.save_created(worktree)
        store.save_created(other)

        records = store.list()

        assert {r.worktree.branch for r in records} == {"feature/auth", "other"}

    def test_list_is_empty_without_state_dir(self, store: WorkspaceStateStore) -> None:
        assert store.list() == []
