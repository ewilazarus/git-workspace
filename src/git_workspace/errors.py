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


class WorktreeCreationError(GitWorkspaceError):
    """Raised when a git worktree cannot be created."""


class WorktreeRemovalError(GitWorkspaceError):
    """Raised when a git worktree cannot be removed."""


class WorkspaceLinkError(GitWorkspaceError):
    """Raised when a symlink cannot be created due to a conflict at the target path."""


class WorkspaceCopyError(GitWorkspaceError):
    """Raised when a file copy cannot be applied due to a conflict at the target path."""


class HookExecutionError(GitWorkspaceError):
    """Raised when a hook script exits with a non-zero return code."""


class WorktreeListingError(GitWorkspaceError):
    """Raised when `git worktree list` fails or produces unparseable output."""


class WorktreeResolutionError(GitWorkspaceError):
    """Raised when a worktree cannot be resolved from the given branch or working directory."""
