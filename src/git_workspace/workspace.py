from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
import shutil

import structlog

from git_workspace import git
from git_workspace.errors import (
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    GitCloneError,
    GitInitError,
    WorkspaceCreationError,
)

DEFAULT_CONFIG_URL = "https://github.com/ewilazarus/git-workspace.git"
DEFAULT_CONFIG_BRANCH = "config/v1"

logger = structlog.get_logger(__name__)


def _validate_root_path(path: Path) -> None:
    # Workspace root must be a directory
    if not path.is_dir():
        raise InvalidWorkspaceRootError(
            f"The following path is not a valid directory: {path!r}"
        )

    # Workspace root must have a child `.git` directory
    git_path = path / ".git"
    if not git_path.is_dir():
        raise InvalidWorkspaceRootError(
            f"No {git_path!r} folder found under the provided path: {path!r}"
        )

    # Workspace root must have a child `.workspace` directory
    config_path = path / ".workspace"
    if not config_path.is_dir():
        raise InvalidWorkspaceRootError(
            f"No {config_path!r} folder found under the provided path: {path!r}"
        )

    # Workspace root's child `.workspace` directory must contain a `manifest.toml` file
    manifest_path = config_path / "manifest.toml"
    if not manifest_path.is_file():
        raise InvalidWorkspaceRootError(
            f"No {manifest_path!r} file found under the provided path: {path!r}"
        )


def _resolve_root_path() -> Path:
    cwd = Path.cwd().resolve()

    for candidate in [cwd, *cwd.parents]:
        try:
            _validate_root_path(candidate)
            return candidate
        except InvalidWorkspaceRootError:
            continue

    raise UnableToResolveWorkspaceRootError(
        f"Unable to resolve workspace root path from current working directory: {cwd!r}"
    )


def _resolve_user_provided_root_path(raw_path: str) -> Path:
    try:
        path = Path(raw_path).resolve(strict=True)
    except FileNotFoundError as e:
        raise InvalidWorkspaceRootError(
            f"The following path is invalid: {raw_path!r}"
        ) from e

    _validate_root_path(path)

    return path


def resolve_root_path(raw_path: str | None = None) -> Path:
    """
    Resolves the workspace root path

    :param raw_path: The string representation of the path
    :raises InvalidWorkspaceRootError: If the `raw_path` is provided and points to
        an invalid workspace root
    :raises UnableToResolveWorkspaceRootError: If the `raw_path` isn't provided and
        the system is unable to resolve the workspace root (e.g. the current working
        directory isn't a child of a workspace root)
    :returns: The resolved `pathlib.Path` for the workspace root path
    """
    log = logger.bind(raw_path=raw_path)

    log.debug("Attempting to resolve workspace root path")

    result = (
        _resolve_user_provided_root_path(raw_path) if raw_path else _resolve_root_path()
    )

    log.debug("Successfully resolved workspace root path", result=result)

    return result


def _create_from_remote(url: str, git_path: Path) -> None:
    try:
        git.clone(url, target=git_path, bare=True)
    except GitCloneError as e:
        raise WorkspaceCreationError("Failed to clone bare repository") from e


def _create_new(git_path: Path) -> None:
    try:
        git.init(git_path, bare=True)
    except GitInitError as e:
        raise WorkspaceCreationError("Failed to initialize bare repository") from e


def _create_config_from_remote(config_url: str, config_path: Path) -> None:
    try:
        git.clone(config_url, target=config_path)
    except GitCloneError as e:
        raise WorkspaceCreationError("Failed to clone config repository") from e


def _create_config_new(config_path: Path) -> None:
    try:
        git.clone(DEFAULT_CONFIG_URL, target=config_path, branch=DEFAULT_CONFIG_BRANCH)
    except GitCloneError as e:
        raise WorkspaceCreationError("Failed to clone example config repository") from e

    config_git_path = config_path / ".git"
    shutil.rmtree(config_git_path, ignore_errors=True)

    try:
        git.init(config_path, bare=False)
    except GitInitError as e:
        raise WorkspaceCreationError(
            "Failed to re-initialize example config repository"
        ) from e


class UpAction(Enum):
    RESUME = auto()
    CREATE_FROM_LOCAL = auto()
    CREATE_FROM_REMOTE = auto()
    CREATE_FROM_BASE = auto()


@dataclass
class UpPlan:
    action: UpAction
    branch: str
    base_branch: str | None = None


def resolve_up_plan(
    branch: str,
    explicit_base_branch: str | None = None,
    manifest_base_branch: str | None = None,
) -> UpPlan:
    """
    Determines what the up command should do for a given branch

    Resolution order:
    1. If an existing worktree already tracks the branch → RESUME
    2. If a local branch exists → CREATE_FROM_LOCAL
    3. If a remote branch exists (known refs) → CREATE_FROM_REMOTE
    4. Fetch origin, then retry remote check → CREATE_FROM_REMOTE
    5. Otherwise → CREATE_FROM_BASE

    :param branch: The target branch name
    :param explicit_base_branch: Base branch explicitly provided by the caller
    :param manifest_base_branch: Base branch from the workspace manifest
    :returns: An UpPlan describing the action to take
    """
    worktrees = git.list_worktrees_metadata()
    if any(wt.branch == branch for wt in worktrees):
        return UpPlan(action=UpAction.RESUME, branch=branch)

    if git.local_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_LOCAL, branch=branch)

    if git.remote_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=branch)

    git.fetch_origin()

    if git.remote_branch_exists(branch):
        return UpPlan(action=UpAction.CREATE_FROM_REMOTE, branch=branch)

    base = resolve_base_branch(
        explicit=explicit_base_branch,
        manifest_base_branch=manifest_base_branch,
    )
    return UpPlan(action=UpAction.CREATE_FROM_BASE, branch=branch, base_branch=base)


def resolve_base_branch(
    explicit: str | None = None,
    manifest_base_branch: str | None = None,
) -> str:
    """
    Resolves the base branch to use when creating a new local branch

    Resolution order:
    1. Explicit value provided by the caller (e.g. CLI --base option)
    2. base_branch from the workspace manifest
    3. Default branch inferred from origin/HEAD
    4. Hardcoded fallback: "main"

    :param explicit: Branch name explicitly requested by the user
    :param manifest_base_branch: base_branch value from the workspace manifest
    :returns: The resolved base branch name
    """
    if explicit is not None:
        return explicit
    if manifest_base_branch is not None:
        return manifest_base_branch
    origin_head = git.get_origin_head()
    if origin_head is not None:
        return origin_head
    return "main"


def resolve_branch(root: Path, cwd: Path | None = None) -> str | None:
    """
    Resolves the target branch from the current working directory

    Infers which workspace worktree the user is in by examining the current working
    directory relative to the workspace root. The `.workspace` and `.git` directories
    are excluded. Intermediate directories that are not worktree roots (e.g.
    `feat/` when branches like `feat/001` and `feat/002` exist) return None.

    :param root: The workspace root path
    :param cwd: The current working directory. If None, uses Path.cwd().
    :returns: The branch name if the cwd is inside a workspace worktree, None otherwise
    """
    if cwd is None:
        cwd = Path.cwd().resolve()

    for excluded in [root / ".workspace", root / ".git"]:
        try:
            cwd.relative_to(excluded)
            return None
        except ValueError:
            pass

    try:
        relative = cwd.relative_to(root)
    except ValueError:
        return None

    if relative == Path("."):
        return None

    worktree_root = git.get_worktree_root(cwd)
    if worktree_root is None:
        return None

    return git.get_current_branch(worktree_root)


def create(
    path: Path,
    url: str | None = None,
    config_url: str | None = None,
) -> None:
    """
    Creates a workspace root

    :param path: The path in which the workspace root should be created
    :param url: The url that should be cloned into the bare repository. If omitted
        a new bare repository is going to be created.
    :param config_url: The url of the configuration that should be cloned. If omitted
        the example configuration repository is going to be cloned.
    :raises WorkspaceCreationError: If the workspace failed to be created
    """
    log = logger.bind(path=path, url=url, config_url=config_url)

    log.debug("Attempting to create workspace")

    path.mkdir(parents=True, exist_ok=True)

    git_path = path / ".git"
    if url:
        _create_from_remote(url, git_path)
    else:
        _create_new(git_path)

    config_path = path / ".workspace"
    if config_url:
        _create_config_from_remote(config_url, config_path)
    else:
        _create_config_new(config_path)

    log.debug("Successfully created workspace")
