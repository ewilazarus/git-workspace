from __future__ import annotations
from git_workspace.worktree import Worktree
from pathlib import Path
import shutil

import structlog

from git_workspace import git
from git_workspace.errors import (
    InvalidWorkspaceError,
    UnableToResolveWorkspaceError,
    GitCloneError,
    GitInitError,
    WorkspaceCreationError,
)
from git_workspace import utils
from git_workspace.manifest import Manifest

logger = structlog.get_logger(__name__)


class WorkspaceValidator:
    @classmethod
    def validate(cls, path: Path) -> None:
        # Workspace root must be a directory
        if not path.is_dir():
            raise InvalidWorkspaceError(
                f"The following path is not a valid directory: {path!r}"
            )

        # Workspace root must have a child `.git` directory
        git_path = path / ".git"
        if not git_path.is_dir():
            raise InvalidWorkspaceError(
                f"No {git_path!r} folder found under the path: {path!r}"
            )

        # Workspace root must have a child `.workspace` directory
        config_path = path / ".workspace"
        if not config_path.is_dir():
            raise InvalidWorkspaceError(
                f"No {config_path!r} folder found under the path: {path!r}"
            )

        # Workspace root's child `.workspace` directory must contain a `manifest.toml` file
        manifest_path = config_path / "manifest.toml"
        if not manifest_path.is_file():
            raise InvalidWorkspaceError(
                f"No {manifest_path!r} file found under the path: {path!r}"
            )


class WorkspaceResolver:
    @classmethod
    def _resolve(cls, path: Path) -> Path:
        for candidate in [path, *path.parents]:
            try:
                WorkspaceValidator.validate(candidate)
                return candidate
            except InvalidWorkspaceError:
                continue

        raise UnableToResolveWorkspaceError(
            f"Unable to resolve workspace root path from: {path!r}"
        )

    @classmethod
    def resolve(cls, workspace_directory: str | None) -> Workspace:
        """
        Resolves the workspace root path

        :param raw_path: The string representation of the path
        :raises InvalidWorkspaceError: If the `raw_path` is provided and points to
            an invalid workspace root
        :raises UnableToResolveWorkspaceError: If the `raw_path` isn't provided and
            the system is unable to resolve the workspace root (e.g. the current working
            directory isn't a child of a workspace root)
        :returns: The resolved `pathlib.Path` for the workspace root path
        """
        try:
            path = (
                Path(workspace_directory) if workspace_directory else Path.cwd()
            ).resolve(strict=True)
        except FileNotFoundError as e:
            raise InvalidWorkspaceError(
                f"The following path is invalid: {workspace_directory!r}"
            ) from e

        resolved_path = cls._resolve(path)
        return Workspace(resolved_path)


class WorkspaceCreator:
    DEFAULT_CONFIG_URL = "https://github.com/ewilazarus/git-workspace.git"
    DEFAULT_CONFIG_BRANCH = "config/v1"

    @classmethod
    def _create_from_remote(cls, url: str, git_path: Path) -> None:
        try:
            git.clone(url, target=git_path, bare=True)
        except GitCloneError as e:
            raise WorkspaceCreationError("Failed to clone bare repository") from e

    @classmethod
    def _create_new(cls, git_path: Path) -> None:
        try:
            git.init(git_path, bare=True)
        except GitInitError as e:
            raise WorkspaceCreationError("Failed to initialize bare repository") from e

    @classmethod
    def _create_config_from_remote(cls, config_url: str, config_path: Path) -> None:
        try:
            git.clone(config_url, target=config_path)
        except GitCloneError as e:
            raise WorkspaceCreationError("Failed to clone config repository") from e

    @classmethod
    def _create_config_new(cls, config_path: Path) -> None:
        try:
            git.clone(
                cls.DEFAULT_CONFIG_URL,
                target=config_path,
                branch=cls.DEFAULT_CONFIG_BRANCH,
            )
        except GitCloneError as e:
            raise WorkspaceCreationError(
                "Failed to clone example config repository"
            ) from e

        config_git_path = config_path / ".git"
        shutil.rmtree(config_git_path, ignore_errors=True)

        try:
            git.init(config_path, bare=False)
        except GitInitError as e:
            raise WorkspaceCreationError(
                "Failed to re-initialize example config repository"
            ) from e

    @classmethod
    def create(
        cls,
        directory: Path,
        url: str | None = None,
        config_url: str | None = None,
    ) -> Workspace:
        directory.mkdir(parents=True, exist_ok=True)

        git_directory = directory / ".git"
        if url:
            cls._create_from_remote(url, git_directory)
        else:
            cls._create_new(git_directory)

        config_directory = directory / ".workspace"
        if config_url:
            cls._create_config_from_remote(config_url, config_directory)
        else:
            cls._create_config_new(config_directory)

        return Workspace(directory)


class Workspace:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.manifest = Manifest.load(self)

    @classmethod
    def resolve(cls, workspace_directory: str | None) -> Workspace:
        return WorkspaceResolver.resolve(workspace_directory)

    @classmethod
    def init(cls, workspace_directory: str | None, config_url: str | None) -> Workspace:
        return WorkspaceCreator.create(
            Path(workspace_directory) if workspace_directory else Path.cwd().resolve(),
            config_url=config_url,
        )

    @classmethod
    def clone(
        cls, workspace_directory: str | None, url: str, config_url: str | None
    ) -> Workspace:
        return WorkspaceCreator.create(
            directory=Path(workspace_directory or utils.extract_humanish_suffix(url)),
            url=url,
            config_url=config_url,
        )

    def list_worktrees(self) -> list[Worktree]:
        return Worktree.list(self)

    def resolve_worktree(self, branch: str | None) -> Worktree:
        return Worktree.resolve(self, branch)

    def resolve_or_create_worktree(
        self, branch: str | None, base_branch: str | None
    ) -> Worktree:
        return Worktree.resolve_or_create(self, branch, base_branch)
