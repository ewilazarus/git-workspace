import logging
import shutil
from pathlib import Path

from git_workspace import git, utils
from git_workspace.errors import (
    GitCloneError,
    GitInitError,
    InvalidWorkspaceError,
    UnableToResolveWorkspaceError,
    WorkspaceCreationError,
)
from git_workspace.manifest import Manifest
from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)


class WorkspacePaths:
    """
    Resolves well-known paths within a workspace root directory.

    Acts as a single source of truth for all path conventions used by
    git-workspace, preventing hard-coded path strings from being scattered
    across the codebase.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    # <ROOT>/.workspace
    @property
    def config(self) -> Path:
        return self._root / ".workspace"

    # <ROOT>/.workspace/assets
    @property
    def assets(self) -> Path:
        return self.config / "assets"

    # <ROOT>/.workspace/bin
    @property
    def bin(self) -> Path:
        return self.config / "bin"

    # <ROOT>/.workspace/manifest.toml
    @property
    def manifest(self) -> Path:
        return self.config / "manifest.toml"

    # <ROOT>/.git
    @property
    def git(self) -> Path:
        return self._root / ".git"

    # <ROOT>/.git/info/exclude
    @property
    def ignore_file(self) -> Path:
        return self.git / "info" / "exclude"

    def worktree(self, branch: str) -> Path:
        """
        Returns the path where the worktree for ``branch`` should be created.

        :param branch: The branch name; may contain slashes for namespaced branches.
        :returns: ``<ROOT>/<branch>``
        """
        return self._root / branch


class WorkspaceValidator:
    """
    Validates that a directory path satisfies the workspace root structure contract.
    """

    @classmethod
    def validate(cls, path: Path) -> None:
        """
        Asserts that ``path`` is a valid workspace root.

        A valid workspace root must be an existing directory containing both a
        ``.git`` directory and a ``.workspace`` directory with a ``manifest.toml``
        file inside it.

        :param path: The path to validate.
        :raises InvalidWorkspaceError: If any structural requirement is not met.
        """
        paths = WorkspacePaths(path)

        # Workspace root must be a directory
        if not path.is_dir():
            raise InvalidWorkspaceError(f"The following path is not a valid directory: {path!r}")

        # Workspace root must have a child `.git` directory
        if not paths.git.is_dir():
            raise InvalidWorkspaceError(f"No {paths.git!r} folder found under the path: {path!r}")

        # Workspace root must have a child `.workspace` directory
        if not paths.config.is_dir():
            raise InvalidWorkspaceError(
                f"No {paths.config!r} folder found under the path: {path!r}"
            )

        # Workspace root's child `.workspace` directory must contain a `manifest.toml` file
        if not paths.manifest.is_file():
            raise InvalidWorkspaceError(
                f"No {paths.manifest!r} file found under the path: {path!r}"
            )


class WorkspaceResolver:
    """
    Resolves a workspace root path from a raw string or the current working directory.
    """

    @classmethod
    def _resolve(cls, path: Path) -> Path:
        for candidate in [path, *path.parents]:
            logger.debug("trying workspace candidate: %s", candidate)
            try:
                WorkspaceValidator.validate(candidate)
                logger.info("resolved workspace root: %s", candidate)
                return candidate
            except InvalidWorkspaceError:
                continue

        logger.warning("could not resolve workspace root from: %s", path)
        raise UnableToResolveWorkspaceError(f"Unable to resolve workspace root path from: {path!r}")

    @classmethod
    def resolve(cls, raw_workspace_dir: str | None) -> Workspace:
        """
        Resolves the workspace root path

        :param raw_path: The string representation of the path
        :raises InvalidWorkspaceError: If the `raw_path` is provided and points to
            an invalid workspace root
        :raises UnableToResolveWorkspaceError: If the `raw_path` isn't provided and
            the system is unable to resolve the workspace root (e.g. the current working
            directory isn't a child of a workspace root)
        :returns: The resolved ``Workspace`` for the root path
        """
        try:
            workspace_dir = (Path(raw_workspace_dir) if raw_workspace_dir else Path.cwd()).resolve(
                strict=True
            )
        except FileNotFoundError as e:
            raise InvalidWorkspaceError(
                f"The following path is invalid: {raw_workspace_dir!r}"
            ) from e

        resolved_workspace_dir = cls._resolve(workspace_dir)
        return Workspace(resolved_workspace_dir)


class WorkspaceFactory:
    """
    Creates new workspaces on disk for ``init`` and ``clone`` operations.

    Handles the two-part workspace structure: the bare git repository under
    ``.git`` and the configuration directory under ``.workspace``. Both parts
    can be seeded from a remote URL or created fresh from defaults.
    """

    DEFAULT_CONFIG_URL = "https://github.com/ewilazarus/git-workspace.git"
    DEFAULT_CONFIG_BRANCH = "config/v1"

    @classmethod
    def _create_from_remote(cls, url: str, git_path: Path) -> None:
        logger.info("cloning bare repository from %r to %s", url, git_path)
        try:
            git.clone(url, target=git_path, bare=True)
        except GitCloneError as e:
            raise WorkspaceCreationError(
                f"Failed to clone bare repository from {url!r} to {git_path}"
            ) from e
        git.configure_remote_fetch_refspec(cwd=git_path.parent)

    @classmethod
    def _create_new(cls, git_path: Path) -> None:
        logger.info("initializing new bare repository at %s", git_path)
        try:
            git.init(git_path, bare=True)
        except GitInitError as e:
            raise WorkspaceCreationError(
                f"Failed to initialize bare repository at {git_path}"
            ) from e

    @classmethod
    def _create_config_from_remote(cls, config_url: str, config_path: Path) -> None:
        logger.info("cloning config repository from %r to %s", config_url, config_path)
        try:
            git.clone(config_url, target=config_path)
        except GitCloneError as e:
            raise WorkspaceCreationError(
                f"Failed to clone config repository from {config_url!r} to {config_path}"
            ) from e

    @classmethod
    def _create_config_new(cls, config_path: Path) -> None:
        logger.info("seeding default config from %r", cls.DEFAULT_CONFIG_URL)
        try:
            git.clone(
                cls.DEFAULT_CONFIG_URL,
                target=config_path,
                branch=cls.DEFAULT_CONFIG_BRANCH,
            )
        except GitCloneError as e:
            raise WorkspaceCreationError(
                f"Failed to clone example config repository from {cls.DEFAULT_CONFIG_URL!r} to {config_path}"
            ) from e

        config_git_path = config_path / ".git"
        shutil.rmtree(config_git_path, ignore_errors=True)

        try:
            git.init(config_path, bare=False)
        except GitInitError as e:
            raise WorkspaceCreationError(
                f"Failed to re-initialize example config repository at {config_path}"
            ) from e

    @classmethod
    def create(
        cls,
        dir: Path,
        url: str | None = None,
        config_url: str | None = None,
    ) -> Workspace:
        """
        Creates a workspace at ``directory``, seeding it from remote URLs when provided.

        If ``url`` is given, the repository is cloned as a bare repo; otherwise a
        new bare repo is initialised. If ``config_url`` is given, the config
        directory is cloned from that URL; otherwise the default example config is
        used.

        :param directory: Root directory for the new workspace.
        :param url: Remote repository URL to clone. If ``None``, a new bare repo
            is initialised instead.
        :param config_url: URL of the ``.workspace`` config repository to clone.
            If ``None``, the default example config is cloned and re-initialised.
        :returns: A ``Workspace`` instance rooted at ``directory``.
        :raises WorkspaceCreationError: If any git operation during setup fails.
        """
        logger.info("creating workspace at %s (url=%r, config_url=%r)", dir, url, config_url)
        dir.mkdir(parents=True, exist_ok=True)
        paths = WorkspacePaths(dir)

        if url:
            cls._create_from_remote(url, paths.git)
        else:
            cls._create_new(paths.git)

        if config_url:
            cls._create_config_from_remote(config_url, paths.config)
        else:
            cls._create_config_new(paths.config)

        logger.info("workspace created at %s", dir)
        return Workspace(dir)


class Workspace:
    """
    Central object representing an open workspace.

    A workspace is a bare git repository paired with a ``.workspace``
    configuration directory. This class is the main entry point for all
    workspace operations, delegating to specialised helpers for resolution,
    creation, and worktree management.
    """

    def __init__(self, dir: Path) -> None:
        self.dir = dir
        self.paths = WorkspacePaths(dir)
        self.manifest = Manifest.load(self)

    @classmethod
    def resolve(cls, workspace_dir: str | None) -> Workspace:
        """
        Resolves and returns the workspace rooted at ``workspace_dir``, or inferred
        from the current working directory if ``workspace_dir`` is ``None``.

        :param workspace_dir: Path to the workspace root as a string, or ``None``
            to walk up from the cwd.
        :returns: The resolved ``Workspace`` instance.
        :raises InvalidWorkspaceError: If the provided path does not point to a
            valid workspace root.
        :raises UnableToResolveWorkspaceError: If no workspace root can be found
            by walking up from the cwd.
        """
        return WorkspaceResolver.resolve(workspace_dir)

    @classmethod
    def init(cls, workspace_dir: str | None, config_url: str | None) -> Workspace:
        """
        Initialises a new workspace for a repository that does not yet exist remotely.

        Creates a bare git repository and a ``.workspace`` configuration directory
        at ``workspace_dir`` (defaults to the cwd if ``None``).

        :param workspace_dir: Directory in which to create the workspace, or
            ``None`` to use the current working directory.
        :param config_url: URL of a config repository to clone as ``.workspace``.
            If ``None``, the default example config is used.
        :returns: The newly created ``Workspace`` instance.
        :raises WorkspaceCreationError: If any git operation during setup fails.
        """
        return WorkspaceFactory.create(
            Path(workspace_dir) if workspace_dir else Path.cwd().resolve(),
            config_url=config_url,
        )

    @classmethod
    def clone(cls, workspace_dir: str | None, url: str, config_url: str | None) -> Workspace:
        """
        Creates a new workspace by cloning an existing remote repository.

        The repository is cloned as a bare repo. If ``workspace_dir`` is ``None``,
        the directory name is derived from the humanish suffix of ``url``.

        :param workspace_dir: Target directory for the workspace, or ``None`` to
            derive a name from the repository URL.
        :param url: Remote repository URL to clone.
        :param config_url: URL of a config repository to clone as ``.workspace``.
            If ``None``, the default example config is used.
        :returns: The newly created ``Workspace`` instance.
        :raises WorkspaceCreationError: If any git operation during setup fails.
        """
        return WorkspaceFactory.create(
            dir=Path(workspace_dir or utils.extract_humanish_suffix(url)),
            url=url,
            config_url=config_url,
        )

    def list_worktrees(self) -> list[Worktree]:
        """
        Returns all worktrees currently registered in this workspace.

        :returns: List of ``Worktree`` instances.
        :raises WorktreeListingError: If ``git worktree list`` fails.
        """
        return Worktree.list(self)

    def resolve_worktree(self, branch: str | None) -> Worktree:
        """
        Resolves an existing worktree by branch name or from the current working directory.

        :param branch: Branch name to look up, or ``None`` to infer from cwd.
        :returns: The matching ``Worktree`` instance.
        :raises WorktreeResolutionError: If no worktree can be resolved.
        """
        return Worktree.resolve(self, branch)

    def resolve_or_create_worktree(self, branch: str | None, base_branch: str | None) -> Worktree:
        """
        Resolves an existing worktree or creates a new one for the given branch.

        :param branch: Branch name to resolve or create, or ``None`` to infer from cwd.
        :param base_branch: Branch to base a new branch on. Falls back to the
            manifest's ``base_branch`` when ``None``.
        :returns: The resolved or newly created ``Worktree`` instance.
        :raises WorktreeResolutionError: If ``branch`` is ``None`` and the cwd is
            not inside a known worktree.
        :raises WorktreeCreationError: If worktree creation fails at the git level.
        """
        return Worktree.resolve_or_create(self, branch, base_branch)
