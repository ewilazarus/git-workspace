import logging
import os
import re
import subprocess

from rich.console import Group
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from git_workspace.errors import HookExecutionError
from git_workspace.ui import console, print_error, print_success
from git_workspace.workspace import Workspace
from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)


class HookRunner:
    """
    Executes lifecycle hook scripts defined in the workspace manifest.

    Each hook script is run as a subprocess from the worktree directory, with a
    standardised set of ``GIT_WORKSPACE_*`` environment variables injected
    alongside the current process environment.  Manifest-level vars and
    caller-supplied runtime vars are both normalised and forwarded as
    ``GIT_WORKSPACE_VAR_*`` variables.
    """

    def __init__(
        self, workspace: Workspace, worktree: Worktree, runtime_vars: dict[str, str]
    ) -> None:
        self._workspace = workspace
        self._worktree = worktree
        self._worktree_dir = str(worktree.dir)
        self._runtime_vars = runtime_vars

    def _normalize_variable_key(self, value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "_", value.upper())

    def _build_env(self, event: str) -> dict[str, str]:
        env = {
            **os.environ,
            "GIT_WORKSPACE_BRANCH": self._worktree.branch,
            "GIT_WORKSPACE_BRANCH_NO_SLASH": self._worktree.branch.replace("/", "_"),
            "GIT_WORKSPACE_ROOT": str(self._workspace.dir),
            "GIT_WORKSPACE_NAME": self._workspace.dir.name,
            "GIT_WORKSPACE_WORKTREE": self._worktree_dir,
            "GIT_WORKSPACE_EVENT": event,
        }

        for key, value in (self._workspace.manifest.vars or {}).items():
            normalized = self._normalize_variable_key(key)
            env[f"GIT_WORKSPACE_VAR_{normalized}"] = value

        for key, value in (self._runtime_vars or {}).items():
            normalized = self._normalize_variable_key(key)
            env[f"GIT_WORKSPACE_VAR_{normalized}"] = value

        return env

    def _resolve_command(self, hook_name: str) -> list[str]:
        bin_path = self._workspace.paths.bin / hook_name
        if bin_path.is_file():
            logger.debug("resolved hook %r to bin script: %s", hook_name, bin_path)
            return [str(bin_path)]
        logger.debug("no bin script for %r, falling back to shell: sh -c %r", hook_name, hook_name)
        return ["sh", "-c", hook_name]

    def _run_hook(self, hook_name: str, env: dict[str, str]) -> None:
        cmd = self._resolve_command(hook_name)
        worktree_dir = self._worktree_dir
        logger.debug("running hook %r as %s in %s", hook_name, cmd, worktree_dir)

        spinner = Spinner("dots", text=f"   {hook_name}")
        output_lines: list[Text] = []

        with subprocess.Popen(
            cmd,
            cwd=worktree_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        ) as proc:
            assert proc.stdout is not None
            with Live(spinner, console=console, refresh_per_second=15, transient=True) as live:
                for raw in proc.stdout:
                    output_lines.append(Text(raw.rstrip(), style="hook"))
                    live.update(Group(spinner, *output_lines[-6:]))

        if proc.returncode != 0:
            logger.error("hook %r exited with code %d", hook_name, proc.returncode)
            print_error(f"Hook [bold]{hook_name}[/] failed")
            raise HookExecutionError()

        logger.debug("hook %r completed successfully", hook_name)
        print_success(f"  {hook_name}")

    def _run_hooks(self, event: str, hook_names: list[str]) -> None:
        env = self._build_env(event)
        for hook_name in hook_names:
            self._run_hook(hook_name, env)

    def run_on_setup_hooks(self) -> None:
        """
        Runs all ``on_setup`` hooks.

        Called after a worktree is first created or explicitly reset. Suitable
        for one-time setup tasks such as installing dependencies or generating
        configuration files.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_SETUP", self._workspace.manifest.hooks.on_setup)

    def run_on_activate_hooks(self) -> None:
        """
        Runs all ``on_activate`` hooks.

        Called on every ``up`` invocation, regardless of whether the session is
        attached or detached. Suitable for lightweight per-session tasks such as
        loading environment variables.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_ACTIVATE", self._workspace.manifest.hooks.on_activate)

    def run_on_attach_hooks(self) -> None:
        """
        Runs all ``on_attach`` hooks.

        Called during ``up`` when running in attached (interactive) mode. Skipped
        when ``--detached`` is passed. Suitable for tasks that require a terminal
        or a user session, such as launching editors or shells.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_ATTACH", self._workspace.manifest.hooks.on_attach)

    def run_on_deactivate_hooks(self) -> None:
        """
        Runs all ``on_deactivate`` hooks.

        Called during ``down`` and ``remove``. Counterpart to ``on_activate``;
        intended for tearing down any state set up during activation.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_DEACTIVATE", self._workspace.manifest.hooks.on_deactivate)

    def run_on_remove_hooks(self) -> None:
        """
        Runs all ``on_remove`` hooks.

        Called during ``remove``, after deactivation and before the worktree is
        deleted. Suitable for cleanup tasks that must happen before the worktree
        directory is removed.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_REMOVE", self._workspace.manifest.hooks.on_remove)
