import os
from pathlib import Path
import re
import shutil
import subprocess

import structlog

from git_workspace import git
from git_workspace.errors import (
    InvalidWorkspaceRootError,
    UnableToResolveWorkspaceRootError,
    GitCloneError,
    GitInitError,
    HookExecutionError,
    WorkspaceCreationError,
    WorkspaceLinkError,
)
from git_workspace.manifest import Hooks, Link
from git_workspace.worktree import WorktreeResult

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


def build_hook_env(
    branch: str,
    root: Path,
    worktree_path: Path,
    event: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Builds the environment dict for hook execution

    Standard context vars (GW_BRANCH, GW_ROOT, GW_WORKTREE, GW_EVENT) are always
    set. Manifest vars are applied next, then CLI user vars override them.
    All user-defined variable names are normalized to uppercase.

    :param branch: The target branch name
    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param event: The lifecycle event name (e.g. "after_setup", "after_activate")
    :param manifest_vars: Variables defined in the workspace manifest
    :param user_vars: Variables provided by the CLI, overriding manifest vars
    :returns: A merged environment dict suitable for passing to subprocess
    """
    env = {
        **os.environ,
        "GIT_WORKSPACE_BRANCH": branch,
        "GIT_WORKSPACE_BRANCH_NO_SLASH": branch.replace("/", "_"),
        "GIT_WORKSPACE_ROOT": str(root),
        "GIT_WORKSPACE_WORKTREE": str(worktree_path),
        "GIT_WORKSPACE_EVENT": event,
    }
    for key, value in (manifest_vars or {}).items():
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = value
    for key, value in (user_vars or {}).items():
        normalized = re.sub(r"[^A-Z0-9]", "_", key.upper())
        env[f"GIT_WORKSPACE_VAR_{normalized}"] = value
    return env


def _run_hooks(
    bin_path: Path, hook_names: list[str], cwd: Path, env: dict[str, str]
) -> None:
    for hook_name in hook_names:
        result = subprocess.run([str(bin_path / hook_name)], cwd=str(cwd), env=env)
        if result.returncode != 0:
            raise HookExecutionError(
                f"Hook {hook_name!r} failed with exit code {result.returncode}"
            )


def run_setup_hooks(
    root: Path,
    worktree_result: WorktreeResult,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs after_setup hooks for newly created worktrees

    Setup hooks are skipped when resuming an existing worktree or when
    skip_hooks is True. Core setup logic is not affected by skip_hooks.

    :param root: The workspace root path
    :param worktree_result: The result of the worktree creation/resume step
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    if not worktree_result.is_new or skip_hooks:
        return
    env = build_hook_env(
        branch=branch,
        root=root,
        worktree_path=worktree_result.path,
        event="after_setup",
        manifest_vars=manifest_vars,
        user_vars=user_vars,
    )
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.after_setup,
        cwd=worktree_result.path,
        env=env,
    )


def run_activation_hooks(
    root: Path,
    worktree_result: WorktreeResult,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs before_activate and after_activate hooks for all up flows

    Activation hooks run regardless of whether the worktree is new or resumed.
    They are suppressed only when skip_hooks is True. before_activate runs
    before the worktree is entered; after_activate runs after.

    :param root: The workspace root path
    :param worktree_result: The result of the worktree creation/resume step
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    if skip_hooks:
        return
    bin_path = root / ".workspace" / "bin"
    cwd = worktree_result.path
    _run_hooks(
        bin_path=bin_path,
        hook_names=hooks.before_activate,
        cwd=cwd,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=cwd,
            event="before_activate",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    _run_hooks(
        bin_path=bin_path,
        hook_names=hooks.after_activate,
        cwd=cwd,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=cwd,
            event="after_activate",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )


def apply_links(root: Path, worktree_path: Path, links: list[Link]) -> None:
    """
    Applies symbolic links from the workspace configuration into a worktree

    Normal links fail if the target already exists and is not already the desired
    symlink. Override links replace any existing target, first marking the file
    with git update-index --skip-worktree. Parent directories are created as needed.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param links: The list of links to apply
    :raises WorkspaceLinkError: If a normal link target already exists and is not the correct symlink
    """
    assets_root = root / ".workspace" / "assets"

    for link in links:
        source = assets_root / link.source
        target = worktree_path / link.target

        target.parent.mkdir(parents=True, exist_ok=True)

        if link.override:
            git.skip_worktree(link.target, cwd=worktree_path)
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(source)
        else:
            if target.is_symlink():
                if target.readlink() == source:
                    continue
                raise WorkspaceLinkError(
                    f"Cannot create link: {target!r} already points elsewhere"
                )
            if target.exists():
                raise WorkspaceLinkError(
                    f"Cannot create link: {target!r} already exists"
                )
            target.symlink_to(source)


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
