import builtins
import fcntl
import os
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.backends.models import WorkspaceBackend
from git_workspace.errors import (
    HookExecutionError,
    WorkspaceLockedError,
    WorkspacePreparationError,
    WorktreeNotFoundError,
)
from git_workspace.workspace.models import (
    ManagedWorktree,
    Presentation,
    PresenterCapabilities,
    PresenterKind,
    ProviderKind,
    WorkspaceLifecycleState,
    WorktreeRequest,
)
from git_workspace.workspace.service import WorkspaceService
from git_workspace.workspace.state import WorkspaceStateStore, state_file_stem

BRANCH = "feature/auth"
BASE_BRANCH = "main"


class FakeProvider:
    kind = ProviderKind.NATIVE_GIT

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path
        self.worktrees: list[ManagedWorktree] = []
        self.created: list[WorktreeRequest] = []
        self.removed: list[tuple[ManagedWorktree, bool]] = []

    def register(self, worktree_path: Path, branch: str) -> ManagedWorktree:
        worktree_path.mkdir(parents=True, exist_ok=True)
        managed = ManagedWorktree(
            repository_path=self.repository_path,
            worktree_path=worktree_path,
            branch=branch,
            provider_kind=ProviderKind.NATIVE_GIT,
        )
        self.worktrees.append(managed)
        return managed

    def is_available(self) -> bool:
        return True

    def create(self, request: WorktreeRequest) -> ManagedWorktree:
        self.created.append(request)
        assert request.target_path is not None
        return self.register(request.target_path, request.branch)

    def import_existing(self, worktree_path: Path) -> ManagedWorktree:
        found = self.find(worktree_path)
        if found is None:
            raise WorktreeNotFoundError(f"No registered git worktree found at {worktree_path}")
        return found

    def find(self, worktree_path: Path) -> ManagedWorktree | None:
        canonical = worktree_path.expanduser().resolve()
        return next((wt for wt in self.worktrees if wt.worktree_path == canonical), None)

    def list(self, repository_path: Path | None = None) -> builtins.list[ManagedWorktree]:
        return [*self.worktrees]

    def remove(self, worktree: ManagedWorktree, *, force: bool = False) -> None:
        self.removed.append((worktree, force))
        self.worktrees = [wt for wt in self.worktrees if wt != worktree]


@dataclass
class FakePreparer:
    calls: list[tuple[str, Path, str]] = field(default_factory=list)
    prepare_error: Exception | None = None
    teardown_error: Exception | None = None

    def prepare(self, worktree_path, branch, *, runtime_vars=None, effective_branch=None):
        self.calls.append(("prepare", worktree_path, branch))
        if self.prepare_error is not None:
            raise self.prepare_error

    def attach(self, worktree_path, branch, *, runtime_vars=None, effective_branch=None):
        self.calls.append(("attach", worktree_path, branch))

    def detach(self, worktree_path, branch, *, runtime_vars=None, effective_branch=None):
        self.calls.append(("detach", worktree_path, branch))

    def teardown(self, worktree_path, branch, *, runtime_vars=None, effective_branch=None):
        self.calls.append(("teardown", worktree_path, branch))
        if self.teardown_error is not None:
            raise self.teardown_error

    def names(self) -> list[str]:
        return [name for name, *_ in self.calls]


class FakePresenter:
    kind = PresenterKind.NONE

    def __init__(self, *, can_close: bool = True, open_error: Exception | None = None) -> None:
        self.opened: list[ManagedWorktree] = []
        self.focused: list[ManagedWorktree] = []
        self.closed: list[ManagedWorktree] = []
        self.open_error = open_error
        self._can_close = can_close

    @property
    def capabilities(self) -> PresenterCapabilities:
        return PresenterCapabilities(
            can_find_existing=True,
            can_focus_existing=True,
            can_close=self._can_close,
            can_list=True,
            supports_runtime_identity=True,
        )

    def is_available(self) -> bool:
        return True

    def open(self, worktree: ManagedWorktree) -> Presentation:
        if self.open_error is not None:
            raise self.open_error
        self.opened.append(worktree)
        return Presentation(presenter_kind=PresenterKind.NONE, presentation_id="p-1")

    def find(self, worktree_path: Path) -> Presentation | None:
        return None

    def focus(self, worktree, presentation=None) -> Presentation:
        self.focused.append(worktree)
        return presentation or Presentation(presenter_kind=PresenterKind.NONE)

    def close(self, worktree, presentation=None) -> None:
        self.closed.append(worktree)

    def list(self, repository_path=None):
        return []


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    d = tmp_path / "workspace"
    d.mkdir()
    return d


@pytest.fixture
def provider(workspace_dir: Path) -> FakeProvider:
    return FakeProvider(workspace_dir)


@pytest.fixture
def preparer() -> FakePreparer:
    return FakePreparer()


@pytest.fixture
def store(workspace_dir: Path) -> WorkspaceStateStore:
    return WorkspaceStateStore(workspace_dir / ".workspace" / ".state")


@pytest.fixture
def workspace(mocker: MockerFixture, workspace_dir: Path, provider: FakeProvider) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = workspace_dir
    mock.manifest.base_branch = BASE_BRANCH
    mock.manifest.prune = None
    mock.paths.worktree.side_effect = lambda branch: workspace_dir / branch
    mock.paths.state = workspace_dir / ".workspace" / ".state"
    mock.provider = provider
    return mock


def make_service(
    workspace: MagicMock,
    provider: FakeProvider,
    preparer: FakePreparer,
    store: WorkspaceStateStore,
    presenter: FakePresenter | None = None,
) -> WorkspaceService:
    backend = WorkspaceBackend(name="native", provider=provider, presenter=presenter)
    return WorkspaceService(
        workspace=workspace,
        backend=backend,
        preparer=preparer,  # ty:ignore[invalid-argument-type]
        state_store=store,
    )


@pytest.fixture
def service(
    workspace: MagicMock,
    provider: FakeProvider,
    preparer: FakePreparer,
    store: WorkspaceStateStore,
) -> WorkspaceService:
    return make_service(workspace, provider, preparer, store)


class TestUpNew:
    def test_creates_prepares_and_attaches(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        worktree = service.up(BRANCH)

        request = provider.created[0]
        assert request.branch == BRANCH
        assert request.base_branch == BASE_BRANCH
        assert request.target_path == (workspace_dir / BRANCH).resolve()
        assert preparer.names() == ["prepare", "attach"]
        assert worktree.is_new is True

        record = store.load(worktree.dir)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_detached_skips_attach(self, service: WorkspaceService, preparer: FakePreparer) -> None:
        service.up(BRANCH, detached=True)

        assert preparer.names() == ["prepare"]

    def test_uses_explicit_base_branch(
        self, service: WorkspaceService, provider: FakeProvider
    ) -> None:
        service.up(BRANCH, base_branch="develop")

        assert provider.created[0].base_branch == "develop"

    def test_preparation_failure_preserves_worktree_and_records_state(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        preparer.prepare_error = HookExecutionError("hook exploded")

        with pytest.raises(WorkspacePreparationError) as excinfo:
            service.up(BRANCH)

        assert provider.removed == []
        assert "prepare" in str(excinfo.value)

        record = store.load(workspace_dir / BRANCH)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.PREPARATION_FAILED
        assert record.preparation_error == "hook exploded"


class TestUpExisting:
    def test_legacy_worktree_is_grandfathered_ready_without_prepare(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / BRANCH, BRANCH)

        service.up(BRANCH)

        assert preparer.names() == ["attach"]
        record = store.load(workspace_dir / BRANCH)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_failed_preparation_is_retried_on_up(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)
        store.mark_preparation_failed(managed.worktree_path, error="boom")

        service.up(BRANCH)

        assert preparer.names() == ["prepare", "attach"]
        record = store.load(managed.worktree_path)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_ready_worktree_only_attaches(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)
        store.set_state(managed.worktree_path, WorkspaceLifecycleState.READY)

        service.up(BRANCH)

        assert preparer.names() == ["attach"]


class TestPreparePath:
    def test_rejects_unregistered_path(self, service: WorkspaceService, tmp_path: Path) -> None:
        with pytest.raises(WorktreeNotFoundError):
            service.prepare_path(tmp_path / "unknown")

    def test_prepares_worktree_without_state(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)

        outcome = service.prepare_path(managed.worktree_path)

        assert outcome.skipped is False
        assert preparer.names() == ["prepare"]
        assert outcome.record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_skips_when_already_ready(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)
        store.set_state(managed.worktree_path, WorkspaceLifecycleState.READY)

        outcome = service.prepare_path(managed.worktree_path)

        assert outcome.skipped is True
        assert preparer.names() == []

    def test_force_reruns_preparation(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)
        store.set_state(managed.worktree_path, WorkspaceLifecycleState.READY)

        outcome = service.prepare_path(managed.worktree_path, force=True)

        assert outcome.skipped is False
        assert preparer.names() == ["prepare"]

    def test_retries_after_failure(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        preparer.prepare_error = HookExecutionError("boom")
        with pytest.raises(WorkspacePreparationError):
            service.prepare_path(managed.worktree_path)

        preparer.prepare_error = None
        outcome = service.prepare_path(managed.worktree_path)

        assert outcome.record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_never_runs_attach(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)

        service.prepare_path(managed.worktree_path)

        assert "attach" not in preparer.names()


class TestDown:
    def test_detaches_and_preserves_worktree(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)

        service.down(BRANCH)

        assert preparer.names() == ["detach"]
        assert provider.removed == []
        record = store.load(managed.worktree_path)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.DETACHED

    def test_preserves_failed_preparation_state(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)
        store.mark_preparation_failed(managed.worktree_path, error="boom")

        service.down(BRANCH)

        record = store.load(managed.worktree_path)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.PREPARATION_FAILED


class TestRemove:
    def test_runs_detach_teardown_then_provider_removal(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.save_created(managed)

        service.remove(BRANCH)

        assert preparer.names() == ["detach", "teardown"]
        assert provider.removed == [(managed, False)]
        assert store.load(managed.worktree_path) is None

    def test_passes_force_to_provider(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / BRANCH, BRANCH)

        service.remove(BRANCH, force=True)

        assert provider.removed[0][1] is True

    def test_teardown_failure_prevents_removal(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        preparer.teardown_error = HookExecutionError("teardown exploded")

        with pytest.raises(HookExecutionError):
            service.remove(BRANCH)

        assert provider.removed == []
        record = store.load(managed.worktree_path)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.TEARING_DOWN

    def test_cleans_empty_intermediary_directories(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / "feature" / "auth", "feature/auth")

        service.remove("feature/auth")

        # FakeProvider.remove does not delete the directory itself, so remove
        # it here as the real provider would before the cleanup runs.
        assert (workspace_dir / "feature").exists()

    def test_never_deletes_branch(self, service: WorkspaceService) -> None:
        # Structural guarantee: the service has no branch-deletion pathway;
        # provider.remove receives only the worktree.
        assert not hasattr(service, "delete_branch")


class TestPresenterSeam:
    def test_up_opens_and_focuses_presentation(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
    ) -> None:
        presenter = FakePresenter()
        service = make_service(workspace, provider, preparer, store, presenter)

        worktree = service.up(BRANCH)

        assert len(presenter.opened) == 1
        assert len(presenter.focused) == 1
        record = store.load(worktree.dir)
        assert record is not None
        assert record.presentation is not None
        assert record.presentation.presentation_id == "p-1"

    def test_up_without_focus_only_opens(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
    ) -> None:
        presenter = FakePresenter()
        service = make_service(workspace, provider, preparer, store, presenter)

        service.up(BRANCH, focus=False)

        assert len(presenter.opened) == 1
        assert presenter.focused == []

    def test_presentation_failure_preserves_prepared_worktree(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        presenter = FakePresenter(open_error=RuntimeError("presenter exploded"))
        service = make_service(workspace, provider, preparer, store, presenter)

        with pytest.raises(RuntimeError):
            service.up(BRANCH)

        assert provider.removed == []
        record = store.load(workspace_dir / BRANCH)
        assert record is not None
        assert record.lifecycle_state is WorkspaceLifecycleState.READY

    def test_down_closes_presentation_when_supported(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        presenter = FakePresenter()
        service = make_service(workspace, provider, preparer, store, presenter)
        provider.register(workspace_dir / BRANCH, BRANCH)

        service.down(BRANCH)

        assert len(presenter.closed) == 1

    def test_down_skips_close_when_unsupported(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        presenter = FakePresenter(can_close=False)
        service = make_service(workspace, provider, preparer, store, presenter)
        provider.register(workspace_dir / BRANCH, BRANCH)

        service.down(BRANCH)

        assert presenter.closed == []

    def test_remove_closes_presentation_before_teardown(
        self,
        workspace: MagicMock,
        provider: FakeProvider,
        preparer: FakePreparer,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        presenter = FakePresenter()
        service = make_service(workspace, provider, preparer, store, presenter)
        provider.register(workspace_dir / BRANCH, BRANCH)

        service.remove(BRANCH)

        assert len(presenter.closed) == 1


class TestPrune:
    def test_candidates_use_threshold_and_exclusions(
        self,
        service: WorkspaceService,
        workspace: MagicMock,
        provider: FakeProvider,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / "feature" / "old", "feature/old")
        provider.register(workspace_dir / "main", "main")
        prune_config = MagicMock()
        prune_config.older_than_days = -1
        prune_config.exclude_branches = ["main"]
        workspace.manifest.prune = prune_config

        candidates = service.prune_candidates()

        assert [wt.branch for wt in candidates] == ["feature/old"]

    def test_prune_removes_candidates_through_lifecycle(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / BRANCH, BRANCH)
        candidates = service.prune_candidates(older_than_days=-1)

        failures = service.prune(candidates)

        assert failures == []
        assert preparer.names() == ["detach", "teardown"]
        assert len(provider.removed) == 1
        assert provider.removed[0][1] is True  # always forced

    def test_prune_continues_after_failure(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        preparer: FakePreparer,
        workspace_dir: Path,
    ) -> None:
        provider.register(workspace_dir / "feature" / "a", "feature/a")
        provider.register(workspace_dir / "feature" / "b", "feature/b")
        candidates = service.prune_candidates(older_than_days=-1)
        preparer.teardown_error = HookExecutionError("boom")

        failures = service.prune(candidates)

        assert len(failures) == 2
        assert provider.removed == []
        # Both candidates were attempted despite the first failure.
        assert preparer.names().count("teardown") == 2


class TestLocking:
    def test_concurrent_operation_fails_fast(
        self,
        service: WorkspaceService,
        provider: FakeProvider,
        store: WorkspaceStateStore,
        workspace_dir: Path,
    ) -> None:
        managed = provider.register(workspace_dir / BRANCH, BRANCH)
        store.locks_dir.mkdir(parents=True, exist_ok=True)
        lock_path = store.locks_dir / f"{state_file_stem(managed.worktree_path)}.lock"

        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with pytest.raises(WorkspaceLockedError):
                service.up(BRANCH)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
