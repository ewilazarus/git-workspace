"""
Reusable contract tests every WorkspacePresenter implementation must pass.

Subclasses provide the `presenter` fixture and a `worktree` fixture pointing
at a real, registered-but-not-presented worktree. Operations an
implementation does not support (see `capabilities`) are skipped here — the
implementation's own tests must assert they raise PresenterCapabilityError.
"""

from pathlib import Path

import pytest

from git_workspace.presenters.base import WorkspacePresenter
from git_workspace.workspace.models import ManagedWorktree


class WorkspacePresenterContract:
    @pytest.fixture
    def presenter(self) -> WorkspacePresenter:
        raise NotImplementedError("subclasses must provide a presenter fixture")

    @pytest.fixture
    def worktree(self, tmp_path: Path) -> ManagedWorktree:
        raise NotImplementedError("subclasses must provide a worktree fixture")

    def test_kind_is_stable(self, presenter: WorkspacePresenter) -> None:
        assert presenter.kind == presenter.kind
        assert isinstance(presenter.kind.value, str)

    def test_open_is_idempotent_when_supported(
        self, presenter: WorkspacePresenter, worktree: ManagedWorktree
    ) -> None:
        first = presenter.open(worktree)
        second = presenter.open(worktree)

        assert first.presentation_id == second.presentation_id

    def test_find_uses_canonical_path(
        self, presenter: WorkspacePresenter, worktree: ManagedWorktree, tmp_path: Path
    ) -> None:
        if not presenter.capabilities.can_find_existing:
            pytest.skip("presenter cannot find existing presentations")

        opened = presenter.open(worktree)
        alias = tmp_path / "presenter-alias"
        alias.symlink_to(worktree.worktree_path)

        found = presenter.find(alias)

        assert found is not None
        assert found.presentation_id == opened.presentation_id

    def test_find_returns_none_when_not_presented(
        self, presenter: WorkspacePresenter, worktree: ManagedWorktree
    ) -> None:
        if not presenter.capabilities.can_find_existing:
            pytest.skip("presenter cannot find existing presentations")

        assert presenter.find(worktree.worktree_path) is None

    def test_close_preserves_worktree(
        self, presenter: WorkspacePresenter, worktree: ManagedWorktree
    ) -> None:
        if not presenter.capabilities.can_close:
            pytest.skip("presenter cannot close presentations")

        presentation = presenter.open(worktree)

        presenter.close(worktree, presentation)

        assert worktree.worktree_path.is_dir()
        if presenter.capabilities.can_find_existing:
            assert presenter.find(worktree.worktree_path) is None

    def test_close_is_idempotent(
        self, presenter: WorkspacePresenter, worktree: ManagedWorktree
    ) -> None:
        if not presenter.capabilities.can_close:
            pytest.skip("presenter cannot close presentations")

        presentation = presenter.open(worktree)

        presenter.close(worktree, presentation)
        presenter.close(worktree, presentation)
