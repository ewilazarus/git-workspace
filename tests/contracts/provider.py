"""
Reusable contract tests every WorktreeProvider implementation must pass.

Subclasses provide the `provider` fixture and a `repo` fixture pointing at a
real repository the provider can operate on. Command-construction specifics
belong in per-provider unit tests; this contract asserts observable behavior
only, so future providers can subclass it unchanged.

A matching WorkspacePresenterContract will be added once the first presenter
implementation exists.
"""

import subprocess
from pathlib import Path

import pytest

from git_workspace.errors import (
    ProviderError,
    WorktreeAlreadyExistsError,
    WorktreeNotFoundError,
)
from git_workspace.providers.base import WorktreeProvider
from git_workspace.workspace.models import ManagedWorktree, WorktreeRequest


class WorktreeProviderContract:
    @pytest.fixture
    def provider(self) -> WorktreeProvider:
        raise NotImplementedError("subclasses must provide a provider fixture")

    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        raise NotImplementedError("subclasses must provide a repository fixture")

    @pytest.fixture
    def registered_worktree(self, provider: WorktreeProvider, repo: Path) -> ManagedWorktree:
        return provider.create(
            WorktreeRequest(
                repository_path=repo,
                branch="contract/existing",
                base_branch="main",
                target_path=repo / "worktrees" / "existing",
            )
        )

    def _branch_exists(self, repo: Path, branch: str) -> bool:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
            cwd=repo,
            capture_output=True,
        )
        return result.returncode == 0

    def test_kind_is_stable(self, provider: WorktreeProvider) -> None:
        assert provider.kind == provider.kind
        assert isinstance(provider.kind.value, str)

    def test_is_available_does_not_mutate(self, provider: WorktreeProvider, repo: Path) -> None:
        before = provider.list(repo)

        provider.is_available()

        assert provider.list(repo) == before

    def test_create_registers_worktree(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, repo: Path
    ) -> None:
        assert registered_worktree.worktree_path.is_dir()
        assert registered_worktree in provider.list(repo)

    def test_create_conflicting_target_raises(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, repo: Path
    ) -> None:
        with pytest.raises(WorktreeAlreadyExistsError):
            provider.create(
                WorktreeRequest(
                    repository_path=repo,
                    branch="contract/other",
                    base_branch="main",
                    target_path=registered_worktree.worktree_path,
                )
            )

    def test_import_existing_is_idempotent(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree
    ) -> None:
        first = provider.import_existing(registered_worktree.worktree_path)
        second = provider.import_existing(registered_worktree.worktree_path)

        assert first == second
        assert first.worktree_path == registered_worktree.worktree_path

    def test_import_existing_rejects_unregistered_path(
        self, provider: WorktreeProvider, tmp_path: Path
    ) -> None:
        unregistered = tmp_path / "not-a-worktree"
        unregistered.mkdir()

        with pytest.raises(WorktreeNotFoundError):
            provider.import_existing(unregistered)

    def test_find_uses_canonical_path(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, tmp_path: Path
    ) -> None:
        alias = tmp_path / "alias"
        alias.symlink_to(registered_worktree.worktree_path)

        found = provider.find(alias)

        assert found is not None
        assert found.worktree_path == registered_worktree.worktree_path

    def test_find_returns_none_for_unknown_path(
        self, provider: WorktreeProvider, tmp_path: Path
    ) -> None:
        unknown = tmp_path / "unknown"
        unknown.mkdir()

        assert provider.find(unknown) is None

    def test_list_filters_by_repository(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, repo: Path
    ) -> None:
        worktrees = provider.list(repo)

        assert all(wt.repository_path == repo.expanduser().resolve() for wt in worktrees)
        assert registered_worktree in worktrees

    def test_remove_preserves_branch(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, repo: Path
    ) -> None:
        provider.remove(registered_worktree)

        assert not registered_worktree.worktree_path.exists()
        assert self._branch_exists(repo, registered_worktree.branch)

    def test_remove_rejects_dirty_worktree(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree
    ) -> None:
        (registered_worktree.worktree_path / "untracked.txt").write_text("dirty")

        with pytest.raises(ProviderError):
            provider.remove(registered_worktree)

        assert registered_worktree.worktree_path.is_dir()

    def test_remove_force_removes_dirty_worktree(
        self, provider: WorktreeProvider, registered_worktree: ManagedWorktree, repo: Path
    ) -> None:
        (registered_worktree.worktree_path / "untracked.txt").write_text("dirty")

        provider.remove(registered_worktree, force=True)

        assert not registered_worktree.worktree_path.exists()
        assert self._branch_exists(repo, registered_worktree.branch)
