from tkinter import W
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
    current = Path.cwd().resolve()

    for candidate in [current, *current.parents]:
        try:
            _validate_root_path(candidate)
            return candidate
        except InvalidWorkspaceRootError:
            continue

    raise UnableToResolveWorkspaceRootError(
        f"Unable to resolve workspace root path from current working directory: {current!r}"
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

    path.mkdir(parents=True)

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
