import fnmatch
import logging
import os
import subprocess
from contextlib import AbstractContextManager
from types import TracebackType

from git_workspace.errors import HookExecutionError
from git_workspace.manifest import HookGroup
from git_workspace.ui import HookProgress, console
from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)


def _matches(group: HookGroup, effective_branch: str) -> bool:
    if group.conditions is None:
        return True
    c = group.conditions
    if c.if_branch_matches and not fnmatch.fnmatchcase(effective_branch, c.if_branch_matches):
        return False
    if c.if_branch_not_matches and fnmatch.fnmatchcase(effective_branch, c.if_branch_not_matches):
        return False
    return True


class HookRunner:
    """
    Executes lifecycle hook scripts defined in the workspace manifest.

    Each hook script is run as a subprocess from the worktree directory, with a
    standardised set of ``GIT_WORKSPACE_*`` environment variables injected
    alongside the current process environment.  Manifest-level vars and
    caller-supplied runtime vars are both normalised and forwarded as
    ``GIT_WORKSPACE_VAR_*`` variables.

    ``effective_branch`` is used only to evaluate hook group conditions; it does
    not affect the ``GIT_WORKSPACE_BRANCH`` environment variable exposed to hook
    scripts (which always reflects the real worktree branch).

    Use as a context manager so the "Running hooks" display is finalized
    correctly after all hook types complete.
    """

    def __init__(
        self,
        worktree: Worktree,
        env: dict[str, str],
        effective_branch: str,
    ) -> None:
        self._worktree = worktree
        self._worktree_dir = str(worktree.dir)
        self._env = env
        self._effective_branch = effective_branch
        self._hook_display_cm: AbstractContextManager[HookProgress] | None = None
        self._hook_progress: HookProgress | None = None

    def _ensure_display(self) -> HookProgress:
        if self._hook_progress is None:
            self._hook_display_cm = console.hook_display()
            self._hook_progress = self._hook_display_cm.__enter__()
        return self._hook_progress

    def __enter__(self) -> HookRunner:
        self._ensure_display()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._hook_display_cm is not None:
            self._hook_display_cm.__exit__(exc_type, exc_val, exc_tb)

    def _resolve_command(self, hook_name: str) -> str:
        bin_path = self._worktree.workspace.paths.bin / hook_name
        if bin_path.is_file():
            logger.debug("resolved hook %r to bin script: %s", hook_name, bin_path)
            return str(bin_path)
        logger.debug("no bin script for %r, running as inline shell command", hook_name)
        return hook_name

    def _run_hooks(self, event: str, groups: list[HookGroup]) -> None:
        hook_names = [
            cmd
            for g in groups
            if _matches(g, self._effective_branch)
            for cmd in g.commands
            if cmd.strip()
        ]
        if not hook_names:
            return

        type_label = event.removeprefix("ON_").capitalize()
        env = {**self._env, "GIT_WORKSPACE_EVENT": event}
        progress = self._ensure_display()
        shell = os.environ.get("SHELL", "sh")

        progress.begin_section(type_label, len(hook_names))

        for hook_name in hook_names:
            progress.on_hook_start(hook_name)
            cmd = self._resolve_command(hook_name)
            logger.debug("running hook %r as %r in %s", hook_name, cmd, self._worktree_dir)

            with subprocess.Popen(
                cmd,
                cwd=self._worktree_dir,
                env=env,
                shell=True,
                executable=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as proc:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    progress.on_output_line(raw.rstrip())

            if proc.returncode != 0:
                logger.error("hook %r exited with code %d", hook_name, proc.returncode)
                raise HookExecutionError(f"Hook {hook_name!r} exited with code {proc.returncode}")

            logger.debug("hook %r completed successfully", hook_name)
            progress.on_hook_done()

        progress.on_section_done(type_label, hook_names)

    def run_on_setup_hooks(self) -> None:
        """
        Runs all matching ``on_setup`` hook groups.

        Called after a worktree is first created or explicitly reset. Suitable
        for one-time setup tasks such as installing dependencies or generating
        configuration files.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_SETUP", self._worktree.workspace.manifest.hooks.on_setup)

    def run_on_attach_hooks(self) -> None:
        """
        Runs all matching ``on_attach`` hook groups.

        Called during ``up`` when running in attached (interactive) mode. Skipped
        when ``--detached`` is passed. Suitable for tasks that require a terminal
        or a user session, such as launching editors or shells.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_ATTACH", self._worktree.workspace.manifest.hooks.on_attach)

    def run_on_detach_hooks(self) -> None:
        """
        Runs all matching ``on_detach`` hook groups.

        Called during ``down`` and at the start of ``rm``. Counterpart to
        ``on_attach``; intended for tearing down any interactive session state.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_DETACH", self._worktree.workspace.manifest.hooks.on_detach)

    def run_on_teardown_hooks(self) -> None:
        """
        Runs all matching ``on_teardown`` hook groups.

        Called during ``rm``, after ``on_detach`` and before the worktree is
        deleted. Suitable for final cleanup tasks that must happen before the
        worktree directory is removed.

        :raises HookExecutionError: If any hook script exits with a non-zero code.
        """
        self._run_hooks("ON_TEARDOWN", self._worktree.workspace.manifest.hooks.on_teardown)
