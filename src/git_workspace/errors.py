from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from git_workspace.workspace.models import WorkspaceRecord


class GitWorkspaceError(Exception):
    """Base class for all git-workspace errors."""


class GitCloneError(GitWorkspaceError):
    """Raised when a `git clone` operation fails."""


class GitInitError(GitWorkspaceError):
    """Raised when a `git init` operation fails."""


class InvalidWorkspaceError(GitWorkspaceError):
    """Raised when a path does not point to a valid workspace root."""


class UnableToResolveWorkspaceError(GitWorkspaceError):
    """Raised when the workspace root cannot be inferred from the current working directory."""


class WorkspaceCreationError(GitWorkspaceError):
    """Raised when workspace creation fails during init or clone."""


class InvalidInputError(GitWorkspaceError):
    """Raised when user-provided input is invalid or cannot be parsed."""


class GitFetchError(GitWorkspaceError):
    """Raised when a `git fetch` operation fails."""


class WorkspaceBackendError(GitWorkspaceError):
    """Base class for provider and presenter failures."""


class ProviderError(WorkspaceBackendError):
    """Base class for worktree-provider failures."""


class ProviderUnavailableError(ProviderError):
    """Raised when a worktree provider cannot currently be used."""


class WorktreeCreationError(ProviderError):
    """Raised when a git worktree cannot be created."""


class WorktreeAlreadyExistsError(WorktreeCreationError):
    """Raised when worktree creation targets a path that is already occupied."""


class WorktreeRemovalError(ProviderError):
    """Raised when a git worktree cannot be removed."""


class UnsafeWorktreeRemovalError(WorktreeRemovalError):
    """Raised when removing a dirty worktree is refused without force."""


class WorktreeListingError(ProviderError):
    """Raised when `git worktree list` fails or produces unparseable output."""


class WorktreeResolutionError(GitWorkspaceError):
    """Raised when a worktree cannot be resolved from the given branch or working directory."""


class WorktreeNotFoundError(WorktreeResolutionError):
    """Raised when a path does not correspond to a registered git worktree."""


class PresenterError(WorkspaceBackendError):
    """Base class for workspace-presenter failures."""


class PresenterUnavailableError(PresenterError):
    """Raised when a workspace presenter cannot currently be used."""


class PresenterCapabilityError(PresenterError):
    """Raised when a presenter is asked to perform an operation it does not support."""


class PresentationNotFoundError(PresenterError):
    """Raised when no presentation exists for a worktree."""


class ExternalCommandError(WorkspaceBackendError):
    """Raised when an external command exits with a non-zero return code."""

    def __init__(self, *, command: list[str], exit_code: int, stdout: str, stderr: str) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Command {' '.join(command)!r} failed with exit code {exit_code}: {stderr.strip()}"
        )


class WorkspaceLinkError(GitWorkspaceError):
    """Raised when a symlink cannot be created due to a conflict at the target path."""


class WorkspaceCopyError(GitWorkspaceError):
    """Raised when a file copy cannot be applied due to a conflict at the target path."""


class HookExecutionError(GitWorkspaceError):
    """Raised when a hook script exits with a non-zero return code."""


class WorkspacePreparationError(GitWorkspaceError):
    """Raised when workspace preparation fails; carries the persisted failure record."""

    def __init__(self, record: WorkspaceRecord, *, cause: str) -> None:
        self.record = record
        worktree_path = record.worktree.worktree_path
        super().__init__(
            f"Failed to prepare workspace at {worktree_path}: {cause}\n"
            f"The worktree was preserved. Retry with: git workspace prepare {worktree_path}"
        )


class WorkspaceLockedError(GitWorkspaceError):
    """Raised when another workspace operation holds the lifecycle lock for a worktree."""


class WorkspaceStateError(GitWorkspaceError):
    """Raised when a persisted workspace state file cannot be used (e.g. newer schema)."""


class CacheError(GitWorkspaceError):
    """Base class for errors raised by the cache subsystem."""


class InvalidCacheKeyError(CacheError):
    """Raised when a cache namespace or key fails path-safety validation."""
