import builtins
import logging
from dataclasses import dataclass
from pathlib import Path

from git_workspace.backends.models import WorkspaceBackend
from git_workspace.backends.resolver import WorkspaceBackendResolver
from git_workspace.errors import (
    GitWorkspaceError,
    InvalidInputError,
    WorkspacePreparationError,
)
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner
from git_workspace.workspace.core import Workspace
from git_workspace.workspace.lock import workspace_operation_lock
from git_workspace.workspace.models import (
    ManagedWorktree,
    PresenterKind,
    ProviderKind,
    WorkspaceLifecycleState,
    WorkspaceRecord,
    WorktreeRequest,
)
from git_workspace.workspace.preparer import WorkspacePreparer
from git_workspace.workspace.state import WorkspaceStateStore
from git_workspace.workspace.worktree import Worktree

logger = logging.getLogger(__name__)

# Lifecycle states that mean the worktree exists but its preparation never
# completed: retry preparation instead of assuming it is usable.
_UNPREPARED_STATES = frozenset(
    {
        WorkspaceLifecycleState.CREATED,
        WorkspaceLifecycleState.PREPARING,
        WorkspaceLifecycleState.PREPARATION_FAILED,
    }
)


@dataclass(frozen=True)
class PrepareOutcome:
    record: WorkspaceRecord
    skipped: bool


@dataclass(frozen=True)
class PruneFailure:
    worktree: Worktree
    error: GitWorkspaceError


class WorkspaceService:
    """
    Orchestrates the workspace lifecycle across the worktree provider, the
    preparer, the presenter (when configured), and the state store.

    Every mutating operation holds a per-worktree lifecycle lock and follows
    the state machine: CREATED → PREPARING → READY/PREPARATION_FAILED, with
    DETACHED and TEARING_DOWN for session exit and removal.
    """

    def __init__(
        self,
        *,
        workspace: Workspace,
        backend: WorkspaceBackend,
        preparer: WorkspacePreparer,
        state_store: WorkspaceStateStore,
    ) -> None:
        self._workspace = workspace
        self._backend = backend
        self._preparer = preparer
        self._state = state_store

    @classmethod
    def create(
        cls,
        workspace: Workspace,
        *,
        backend_name: str | None = None,
        provider_kind: ProviderKind | None = None,
        presenter_kind: PresenterKind | None = None,
        runner: CommandRunner = DEFAULT_RUNNER,
        resolver: WorkspaceBackendResolver | None = None,
    ) -> WorkspaceService:
        backend = (resolver or WorkspaceBackendResolver(runner)).resolve(
            backend_name=backend_name,
            provider_kind=provider_kind,
            presenter_kind=presenter_kind,
            settings=workspace.manifest.workspace,
        )
        return cls(
            workspace=workspace,
            backend=backend,
            preparer=WorkspacePreparer(workspace),
            state_store=WorkspaceStateStore(workspace.paths.state),
        )

    def up(
        self,
        branch: str | None,
        *,
        base_branch: str | None = None,
        runtime_vars: dict[str, str] | None = None,
        detached: bool = False,
        effective_branch: str | None = None,
        focus: bool = True,
    ) -> Worktree:
        """
        Ensures a prepared worktree exists for the branch and attaches to it.

        New worktrees go through the full lifecycle (create → prepare →
        attach). Existing worktrees are re-prepared only when their recorded
        state says preparation never completed; worktrees without state are
        grandfathered as READY.
        """
        runtime_vars = runtime_vars or {}

        if branch:
            existing = next(
                (wt for wt in Worktree.list(self._workspace) if wt.branch == branch), None
            )
        else:
            existing = Worktree.resolve(self._workspace, None)

        if existing is not None:
            return self._up_existing(
                existing,
                runtime_vars=runtime_vars,
                detached=detached,
                effective_branch=effective_branch,
                focus=focus,
            )

        assert branch is not None
        return self._up_new(
            branch,
            base_branch=base_branch,
            runtime_vars=runtime_vars,
            detached=detached,
            effective_branch=effective_branch,
            focus=focus,
        )

    def prepare_path(
        self,
        worktree_path: Path,
        *,
        force: bool = False,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> PrepareOutcome:
        """
        Prepares an existing worktree, regardless of which tool created it.

        No-ops when the worktree is already READY unless ``force`` is set.
        Never creates a worktree and never touches presentation.
        """
        managed = self._backend.provider.import_existing(worktree_path)

        with self._lock(managed.worktree_path):
            record = self._state.load(managed.worktree_path)
            if (
                record is not None
                and record.lifecycle_state is WorkspaceLifecycleState.READY
                and not force
            ):
                logger.debug("worktree %s already prepared; skipping", managed.worktree_path)
                return PrepareOutcome(record=record, skipped=True)

            if record is None:
                self._state.save_created(managed)

            worktree = self._worktree_for(managed)
            record = self._run_prepare(
                worktree, runtime_vars=runtime_vars or {}, effective_branch=effective_branch
            )
            return PrepareOutcome(record=record, skipped=False)

    def down(
        self,
        branch: str | None,
        *,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> Worktree:
        """
        Runs the detach lifecycle and closes the presentation when supported.

        Never removes the worktree.
        """
        worktree = Worktree.resolve(self._workspace, branch)

        with self._lock(worktree.dir):
            self._preparer.detach(
                worktree.dir,
                worktree.branch,
                runtime_vars=runtime_vars,
                effective_branch=effective_branch,
            )

            record = self._state.load(worktree.dir)
            managed = record.worktree if record else self._managed_for(worktree)
            self._close_presentation(managed, record)

            if record is None:
                self._state.save(
                    WorkspaceRecord(
                        worktree=managed,
                        presentation=None,
                        lifecycle_state=WorkspaceLifecycleState.DETACHED,
                    )
                )
            elif record.lifecycle_state not in _UNPREPARED_STATES:
                # Preserve unfinished-preparation states so the next `up`
                # still retries preparation after a detach.
                self._state.set_state(worktree.dir, WorkspaceLifecycleState.DETACHED)

        return worktree

    def remove(
        self,
        branch: str | None,
        *,
        force: bool = False,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> Worktree:
        """
        Removes a worktree: detach + teardown hooks, then provider removal.

        A teardown failure aborts before anything is deleted. The branch is
        never deleted.
        """
        worktree = Worktree.resolve(self._workspace, branch)

        with self._lock(worktree.dir):
            record = self._state.load(worktree.dir)
            managed = record.worktree if record else self._managed_for(worktree)

            if record is None:
                self._state.save(
                    WorkspaceRecord(
                        worktree=managed,
                        presentation=None,
                        lifecycle_state=WorkspaceLifecycleState.TEARING_DOWN,
                    )
                )
            else:
                self._state.set_state(worktree.dir, WorkspaceLifecycleState.TEARING_DOWN)

            # Close the presentation before teardown so background UI
            # processes cannot hold files or services open during cleanup.
            self._close_presentation(managed, record)

            self._preparer.detach(
                worktree.dir,
                worktree.branch,
                runtime_vars=runtime_vars,
                effective_branch=effective_branch,
            )
            self._preparer.teardown(
                worktree.dir,
                worktree.branch,
                runtime_vars=runtime_vars,
                effective_branch=effective_branch,
            )

            self._backend.provider.remove(managed, force=force)
            self._clean_intermediary_empty_paths(worktree.dir)
            self._state.delete(worktree.dir)

        return worktree

    def list_worktrees(self) -> builtins.list[Worktree]:
        return Worktree.list(self._workspace)

    def prune_candidates(self, *, older_than_days: int | None = None) -> builtins.list[Worktree]:
        """
        Returns worktrees older than the threshold, excluding protected branches.

        The threshold falls back to the manifest's ``[prune]`` configuration.
        """
        manifest = self._workspace.manifest

        threshold = older_than_days
        if threshold is None:
            if manifest.prune is None:
                raise InvalidInputError("Must pass --older-than-days or define [prune] in manifest")
            threshold = manifest.prune.older_than_days

        protected: set[str] = set(manifest.prune.exclude_branches) if manifest.prune else set()

        return [
            worktree
            for worktree in Worktree.list(self._workspace)
            if worktree.age_days > threshold and worktree.branch not in protected
        ]

    def prune(
        self,
        candidates: builtins.list[Worktree],
        *,
        runtime_vars: dict[str, str] | None = None,
    ) -> builtins.list[PruneFailure]:
        """
        Removes each candidate through the full remove lifecycle.

        A failure (teardown hook, held lock) skips that worktree and pruning
        continues; failures are returned for the caller to report.
        """
        failures = []
        for worktree in candidates:
            try:
                self.remove(worktree.branch, force=True, runtime_vars=runtime_vars)
            except GitWorkspaceError as e:
                logger.warning("failed to prune worktree %r: %s", worktree.branch, e)
                failures.append(PruneFailure(worktree=worktree, error=e))
        return failures

    def _up_new(
        self,
        branch: str,
        *,
        base_branch: str | None,
        runtime_vars: dict[str, str],
        detached: bool,
        effective_branch: str | None,
        focus: bool,
    ) -> Worktree:
        target = self._workspace.paths.worktree(branch)

        with self._lock(target):
            managed = self._backend.provider.create(
                WorktreeRequest(
                    repository_path=self._workspace.dir,
                    branch=branch,
                    base_branch=base_branch or self._workspace.manifest.base_branch,
                    target_path=target,
                )
            )
            self._state.save_created(managed)

            worktree = self._worktree_for(managed, is_new=True)
            self._run_prepare(
                worktree, runtime_vars=runtime_vars, effective_branch=effective_branch
            )

            if not detached:
                self._preparer.attach(
                    worktree.dir,
                    worktree.branch,
                    runtime_vars=runtime_vars,
                    effective_branch=effective_branch,
                )

            self._present(managed, focus=focus and not detached)

        return worktree

    def _up_existing(
        self,
        worktree: Worktree,
        *,
        runtime_vars: dict[str, str],
        detached: bool,
        effective_branch: str | None,
        focus: bool,
    ) -> Worktree:
        with self._lock(worktree.dir):
            record = self._state.load(worktree.dir)
            managed = record.worktree if record else self._managed_for(worktree)

            if record is None:
                # Legacy worktree predating the state store: assume it was
                # prepared by the tool that created it.
                self._state.save(
                    WorkspaceRecord(
                        worktree=managed,
                        presentation=None,
                        lifecycle_state=WorkspaceLifecycleState.READY,
                    )
                )
            elif record.lifecycle_state in _UNPREPARED_STATES:
                self._run_prepare(
                    worktree, runtime_vars=runtime_vars, effective_branch=effective_branch
                )
            else:
                self._state.set_state(worktree.dir, WorkspaceLifecycleState.READY)

            if not detached:
                self._preparer.attach(
                    worktree.dir,
                    worktree.branch,
                    runtime_vars=runtime_vars,
                    effective_branch=effective_branch,
                )

            self._present(managed, focus=focus and not detached)

        return worktree

    def _run_prepare(
        self,
        worktree: Worktree,
        *,
        runtime_vars: dict[str, str],
        effective_branch: str | None,
    ) -> WorkspaceRecord:
        self._state.set_state(worktree.dir, WorkspaceLifecycleState.PREPARING)
        try:
            self._preparer.prepare(
                worktree.dir,
                worktree.branch,
                runtime_vars=runtime_vars,
                effective_branch=effective_branch,
            )
        except Exception as e:
            record = self._state.mark_preparation_failed(worktree.dir, error=str(e))
            raise WorkspacePreparationError(record, cause=str(e)) from e
        return self._state.set_state(worktree.dir, WorkspaceLifecycleState.READY)

    def _present(self, managed: ManagedWorktree, *, focus: bool) -> None:
        presenter = self._backend.presenter
        if presenter is None:
            return

        presentation = presenter.open(managed)
        if focus:
            presentation = presenter.focus(managed, presentation)

        record = self._state.load(managed.worktree_path)
        if record is not None:
            self._state.save(
                WorkspaceRecord(
                    worktree=record.worktree,
                    presentation=presentation,
                    lifecycle_state=record.lifecycle_state,
                    preparation_error=record.preparation_error,
                )
            )

    def _close_presentation(self, managed: ManagedWorktree, record: WorkspaceRecord | None) -> None:
        presenter = self._backend.presenter
        if presenter is None or not presenter.capabilities.can_close:
            return
        presenter.close(managed, record.presentation if record else None)

    def _worktree_for(self, managed: ManagedWorktree, *, is_new: bool = False) -> Worktree:
        return Worktree(
            workspace=self._workspace,
            dir=managed.worktree_path,
            branch=managed.branch,
            is_new=is_new,
        )

    def _managed_for(self, worktree: Worktree) -> ManagedWorktree:
        return ManagedWorktree(
            repository_path=self._workspace.dir,
            worktree_path=worktree.dir,
            branch=worktree.branch,
            provider_kind=self._backend.provider.kind,
        )

    def _lock(self, worktree_path: Path):
        return workspace_operation_lock(self._state.locks_dir, worktree_path)

    def _clean_intermediary_empty_paths(self, worktree_dir: Path) -> None:
        parent = worktree_dir.parent
        while parent != self._workspace.dir:
            try:
                parent.rmdir()
                logger.debug("removed empty intermediary directory: %s", parent)
            except OSError:
                break
            parent = parent.parent
