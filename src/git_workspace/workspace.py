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
    WorktreeDirtyError,  # noqa: F401 — re-exported for callers
    WorktreeNotFoundError,  # noqa: F401 — re-exported for callers
    WorktreeRemovalError,  # noqa: F401 — re-exported for callers
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

    log = logger.bind(root=str(root), cwd=str(cwd))
    log.debug("Attempting to resolve branch")

    for excluded in [root / ".workspace", root / ".git"]:
        try:
            cwd.relative_to(excluded)
            log.debug("cwd is inside excluded directory, branch unresolvable", excluded=str(excluded))
            return None
        except ValueError:
            pass

    try:
        relative = cwd.relative_to(root)
    except ValueError:
        log.debug("cwd is outside workspace root, branch unresolvable")
        return None

    if relative == Path("."):
        log.debug("cwd is the workspace root itself, branch unresolvable")
        return None

    worktree_root = git.get_worktree_root(cwd)
    if worktree_root is None:
        log.debug("cwd is not inside a worktree, branch unresolvable")
        return None

    branch = git.get_current_branch(worktree_root)
    if branch is None:
        log.debug("Worktree HEAD is detached, branch unresolvable")
        return None
    log.debug("Successfully resolved branch", branch=branch)
    return branch


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
    log = logger.bind(bin_path=bin_path, cwd=cwd)

    if not hook_names:
        log.debug("No hooks to run")
        return

    for hook_name in hook_names:
        log.debug("Running hook", hook=hook_name)
        result = subprocess.run([str(bin_path / hook_name)], cwd=str(cwd), env=env)
        if result.returncode != 0:
            log.debug("Hook failed", hook=hook_name, exit_code=result.returncode)
            raise HookExecutionError(
                f"Hook {hook_name!r} failed with exit code {result.returncode}"
            )
        log.debug("Hook succeeded", hook=hook_name)


def run_on_setup_hooks(
    root: Path,
    worktree_result: WorktreeResult,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_setup hooks for newly created worktrees.

    Skipped when resuming an existing worktree or when skip_hooks is True.

    :param root: The workspace root path
    :param worktree_result: The result of the worktree creation/resume step
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=worktree_result.path)

    if not worktree_result.is_new:
        log.debug("Skipping on_setup hooks: worktree already exists")
        return
    if skip_hooks:
        log.debug("Skipping on_setup hooks: skip_hooks=True")
        return

    log.debug("Running on_setup hooks")
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.on_setup,
        cwd=worktree_result.path,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=worktree_result.path,
            event="on_setup",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    log.debug("on_setup hooks completed")


def run_on_activate_hooks(
    root: Path,
    worktree_result: WorktreeResult,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_activate hooks on every up invocation (new and resumed).

    Suppressed only when skip_hooks is True.

    :param root: The workspace root path
    :param worktree_result: The result of the worktree creation/resume step
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=worktree_result.path)

    if skip_hooks:
        log.debug("Skipping on_activate hooks: skip_hooks=True")
        return

    log.debug("Running on_activate hooks")
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.on_activate,
        cwd=worktree_result.path,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=worktree_result.path,
            event="on_activate",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    log.debug("on_activate hooks completed")


def run_on_attach_hooks(
    root: Path,
    worktree_result: WorktreeResult,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_attach hooks when up is invoked in attached mode.

    Not called in detached mode. Suppressed by skip_hooks.

    :param root: The workspace root path
    :param worktree_result: The result of the worktree creation/resume step
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=worktree_result.path)

    if skip_hooks:
        log.debug("Skipping on_attach hooks: skip_hooks=True")
        return

    log.debug("Running on_attach hooks")
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.on_attach,
        cwd=worktree_result.path,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=worktree_result.path,
            event="on_attach",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    log.debug("on_attach hooks completed")


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
    log = logger.bind(worktree=worktree_path, num_links=len(links))
    log.debug("Applying links")

    assets_root = root / ".workspace" / "assets"

    for link in links:
        source = assets_root / link.source
        target = worktree_path / link.target
        link_log = log.bind(source=str(source), target=str(target), override=link.override)

        target.parent.mkdir(parents=True, exist_ok=True)

        if link.override:
            link_log.debug("Applying override link")
            git.skip_worktree(link.target, cwd=worktree_path)
            if target.exists() or target.is_symlink():
                target.unlink()
            target.symlink_to(source)
            link_log.debug("Override link applied")
        else:
            if target.is_symlink():
                if target.readlink() == source:
                    link_log.debug("Link already up to date, skipping")
                    continue
                raise WorkspaceLinkError(
                    f"Cannot create link: {target!r} already points elsewhere"
                )
            if target.exists():
                raise WorkspaceLinkError(
                    f"Cannot create link: {target!r} already exists"
                )
            link_log.debug("Applying link")
            target.symlink_to(source)
            link_log.debug("Link applied")

    log.debug("Links applied")


def sync_exclude_block(worktree_path: Path, non_override_targets: list[str]) -> None:
    """
    Synchronizes the managed git-workspace section in the worktree's exclude file

    Rewrites only the managed block delimited by BEGIN/END markers, leaving
    all other entries untouched. The operation is idempotent.

    :param worktree_path: The root of the worktree
    :param non_override_targets: Link targets to include in the managed block
    """
    log = logger.bind(worktree=str(worktree_path), targets=non_override_targets)
    log.debug("Syncing exclude block")

    git_file = worktree_path / ".git"
    git_dir_ref = git_file.read_text().strip()
    git_dir = Path(git_dir_ref.removeprefix("gitdir: "))
    log.debug("Resolved worktree git dir", git_dir=str(git_dir))

    commondir_file = git_dir / "commondir"
    if commondir_file.exists():
        commondir = commondir_file.read_text().strip()
        git_dir = (git_dir / commondir).resolve()
        log.debug("Resolved common git dir via commondir", git_dir=str(git_dir))

    exclude_path = git_dir / "info" / "exclude"
    log.debug("Resolved exclude file", exclude_path=str(exclude_path))

    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    existing = exclude_path.read_text() if exclude_path.exists() else ""
    log.debug("Read existing exclude file", num_lines=len(existing.splitlines()))

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

    log.debug("Exclude block synced", managed_entries=non_override_targets)


def find_worktree_path(branch: str, cwd: Path | None = None) -> Path:
    """
    Returns the path of an existing worktree for the given branch.

    :param branch: The branch name to look up
    :param cwd: The git repository directory. If None, uses the current directory.
    :raises WorktreeNotFoundError: If no worktree exists for the branch
    :returns: The worktree path
    """
    log = logger.bind(branch=branch, cwd=str(cwd) if cwd else None)
    log.debug("Looking for existing worktree")

    worktrees = git.list_worktrees_metadata(cwd=cwd)
    matching = next((wt for wt in worktrees if wt.branch == branch), None)

    if matching is None:
        raise WorktreeNotFoundError(
            f"No worktree found for branch {branch!r}; run 'git workspace up {branch}' first"
        )

    log.debug("Found worktree", path=str(matching.path))
    return matching.path


def run_on_setup_hooks_for_reset(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_setup hooks unconditionally for the reset command.

    Unlike run_on_setup_hooks, this always executes regardless of whether
    the worktree is new or existing, since reset re-applies workspace state.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_setup hooks (reset): skip_hooks=True")
        return

    log.debug("Running on_setup hooks (reset)")
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.on_setup,
        cwd=worktree_path,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=worktree_path,
            event="on_setup",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    log.debug("on_setup hooks (reset) completed")


def cleanup_empty_parent_dirs(path: Path, stop_at: Path) -> None:
    """
    Removes empty parent directories between path and stop_at (exclusive).

    Walks upward from path.parent, removing each directory if empty,
    stopping as soon as a non-empty directory or stop_at is reached.

    :param path: The removed path whose parents should be cleaned up
    :param stop_at: The boundary directory — never removed
    """
    log = logger.bind(path=str(path), stop_at=str(stop_at))
    parent = path.parent
    while parent != stop_at:
        try:
            parent.rmdir()
            log.debug("Removed empty parent directory", directory=str(parent))
        except OSError:
            break
        parent = parent.parent


def run_on_remove_hooks(
    root: Path,
    worktree_path: Path,
    hooks: Hooks,
    branch: str,
    manifest_vars: dict[str, str] | None = None,
    user_vars: dict[str, str] | None = None,
    skip_hooks: bool = False,
) -> None:
    """
    Runs on_remove hooks when a worktree is removed.

    Runs before the worktree is deleted so the hook can inspect its state.
    Hook failures abort removal — the worktree is not touched.

    :param root: The workspace root path
    :param worktree_path: The worktree root path
    :param hooks: The hooks configuration from the manifest
    :param branch: The target branch name, injected into hook environment
    :param manifest_vars: Variables from the manifest, exposed to hooks
    :param user_vars: CLI variables, override manifest vars
    :param skip_hooks: If True, suppresses hook execution
    :raises HookExecutionError: If any hook exits with a non-zero status
    """
    log = logger.bind(branch=branch, worktree=str(worktree_path))

    if skip_hooks:
        log.debug("Skipping on_remove hooks: skip_hooks=True")
        return

    log.debug("Running on_remove hooks")
    _run_hooks(
        bin_path=root / ".workspace" / "bin",
        hook_names=hooks.on_remove,
        cwd=worktree_path,
        env=build_hook_env(
            branch=branch,
            root=root,
            worktree_path=worktree_path,
            event="on_remove",
            manifest_vars=manifest_vars,
            user_vars=user_vars,
        ),
    )
    log.debug("on_remove hooks completed")


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
