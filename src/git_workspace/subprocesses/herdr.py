"""
Thin wrappers around the herdr CLI's socket-API subcommands.

All commands use herdr's JSON output. Herdr reports failures as an
``{"error": {"code", "message"}}`` envelope — sometimes with exit code 0 —
so parsing always inspects the payload rather than trusting the exit code.
"""

import json
import logging
import os
import shutil
from pathlib import Path

from git_workspace.errors import HerdrError
from git_workspace.subprocesses.runner import DEFAULT_RUNNER, CommandRunner

logger = logging.getLogger(__name__)

BIN_PATH_ENV = "HERDR_BIN_PATH"
CONTEXT_ENV = "HERDR_ENV"
SOCKET_PATH_ENV = "HERDR_SOCKET_PATH"


def resolve_executable(explicit: str | None = None) -> str | None:
    """
    Resolves the herdr executable: explicit value → HERDR_BIN_PATH → PATH.

    :returns: The executable to invoke, or None when herdr is not available.
    """
    if explicit:
        return explicit
    env_path = os.environ.get(BIN_PATH_ENV)
    if env_path:
        return env_path
    return shutil.which("herdr")


def in_verified_context() -> bool:
    """
    Returns whether the current process runs inside a reachable herdr session.

    True only when herdr's environment marker is set and the advertised
    session socket actually exists — the executable merely being installed is
    not enough to consider herdr active.
    """
    if os.environ.get(CONTEXT_ENV) != "1":
        return False
    socket_path = os.environ.get(SOCKET_PATH_ENV)
    return bool(socket_path) and Path(socket_path).exists()


def list_worktrees(
    cwd: Path,
    *,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """
    Lists the repository's worktrees as seen by herdr.

    :returns: The result payload: ``{"source": {...}, "worktrees": [...]}``.
        Worktree entries carry ``open_workspace_id`` when presented in herdr.
    """
    return _invoke(
        [executable, "worktree", "list", "--cwd", cwd, "--json"],
        runner=runner,
    )


def create_worktree(
    repository_path: Path,
    branch: str,
    target_path: Path,
    base_branch: str | None,
    *,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """
    Creates a git worktree through herdr.

    Herdr opens a workspace presentation as a side effect; ``--no-focus``
    keeps it in the background so focusing stays a presenter concern.

    :returns: The ``worktree_created`` result payload.
    """
    cmd: list[str | Path] = [
        executable,
        "worktree",
        "create",
        "--cwd",
        repository_path,
        "--branch",
        branch,
        "--path",
        target_path,
    ]
    if base_branch:
        cmd.extend(["--base", base_branch])
    cmd.extend(["--no-focus", "--json"])
    return _invoke(cmd, runner=runner)


def open_worktree(
    repository_path: Path,
    worktree_path: Path,
    *,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """
    Opens (or returns) the herdr workspace presenting an existing worktree.

    Natively idempotent: the payload carries ``already_open``.

    :returns: The ``worktree_opened`` result payload.
    """
    return _invoke(
        [
            executable,
            "worktree",
            "open",
            "--cwd",
            repository_path,
            "--path",
            worktree_path,
            "--no-focus",
            "--json",
        ],
        runner=runner,
    )


def remove_worktree(
    workspace_id: str,
    *,
    force: bool = False,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """
    Removes the git worktree presented by the given herdr workspace.

    Herdr identifies worktrees by their open workspace, closes the workspace,
    and removes the worktree. The branch is preserved.

    :returns: The ``worktree_removed`` result payload.
    """
    cmd: list[str | Path] = [executable, "worktree", "remove", "--workspace", workspace_id]
    if force:
        cmd.append("--force")
    cmd.append("--json")
    return _invoke(cmd, runner=runner)


def focus_workspace(
    workspace_id: str,
    *,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """Focuses a herdr workspace."""
    return _invoke([executable, "workspace", "focus", workspace_id], runner=runner)


def close_workspace(
    workspace_id: str,
    *,
    executable: str,
    runner: CommandRunner = DEFAULT_RUNNER,
) -> dict:
    """Closes a herdr workspace, preserving the underlying git worktree."""
    return _invoke([executable, "workspace", "close", workspace_id], runner=runner)


def _invoke(cmd: list[str | Path], *, runner: CommandRunner) -> dict:
    result = runner.run(cmd, check=False)

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.exit_code}"
        raise HerdrError(f"herdr returned malformed output: {detail}") from None

    error = payload.get("error")
    if error is not None:
        raise HerdrError(
            error.get("message", "herdr command failed"),
            code=error.get("code"),
        )

    if not result.ok:
        raise HerdrError(
            f"herdr command failed with exit code {result.exit_code}: {result.stderr.strip()}"
        )

    return payload.get("result", {})
