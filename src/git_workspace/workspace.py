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

_EXCLUDE_BEGIN = "# >>> git-workspace managed >>>"
_EXCLUDE_END = "# <<< git-workspace managed <<<"

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



def sync_exclude_block(worktree_path: Path, non_override_targets: list[str]) -> None:
    """
    Synchronizes the managed git-workspace section in the worktree's exclude file

    Rewrites only the managed block delimited by BEGIN/END markers, leaving
    all other entries untouched. The operation is idempotent.

    :param worktree_path: The root of the worktree
    :param non_override_targets: Link targets to include in the managed block
    """
    git_file = worktree_path / ".git"
    git_dir_ref = git_file.read_text().strip()
    git_dir = Path(git_dir_ref.removeprefix("gitdir: "))

    exclude_path = git_dir / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    existing = exclude_path.read_text() if exclude_path.exists() else ""

    kept: list[str] = []
    inside_managed = False
    for line in existing.splitlines():
        if line == _EXCLUDE_BEGIN:
            inside_managed = True
        elif line == _EXCLUDE_END:
            inside_managed = False
        elif not inside_managed:
            kept.append(line)

    while kept and kept[-1] == "":
        kept.pop()

    managed = [_EXCLUDE_BEGIN] + non_override_targets + [_EXCLUDE_END]
    parts = kept + ([""] if kept else []) + managed
    exclude_path.write_text("\n".join(parts) + "\n")


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
