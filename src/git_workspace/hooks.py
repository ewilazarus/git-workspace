import logging
import os
import re
import subprocess
from types import TracebackType

from rich.console import Group
from rich.live import Live
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.spinner import Spinner
from rich.text import Text

from git_workspace.errors import HookExecutionError
from git_workspace.ui import console
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

    Use as a context manager so the "Running hooks" display is finalized
    correctly after all hook types complete.
    """

    def __init__(
        self, workspace: Workspace, worktree: Worktree, runtime_vars: dict[str, str]
    ) -> None:
        self._workspace = workspace
        self._worktree = worktree
        self._worktree_dir = str(worktree.dir)
        self._runtime_vars = runtime_vars

        self._live: Live | None = None
        self._section_spinner = Spinner("dots", text=" Running hooks")
        self._completed_types: list[tuple[str, list[str]]] = []
        self._current_type_label: str | None = None
        self._current_type_progress: Progress | None = None
        self._output_lines: list[Text] = []

    def __enter__(self) -> HookRunner:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None
            if exc_type is None:
                self._print_success()
            else:
                self._print_error()

    def _make_renderable(self) -> Group:
        rows: list = []
        rows.append(self._section_spinner)

        for type_label, hook_names in self._completed_types:
            row = Text.assemble(("✓", "bold green"), f"    {type_label}: ")
            for i, name in enumerate(hook_names):
                if i > 0:
                    row.append(", ")
                row.append(name, style="name")
            rows.append(row)

        if self._current_type_progress is not None:
            rows.append(self._current_type_progress)
            rows.extend(self._output_lines[-6:])

        return Group(*rows)

    def _print_type_rows(self) -> None:
        for type_label, hook_names in self._completed_types:
            row = Text.assemble(("✓", "bold green"), f"    {type_label}: ")
            for i, name in enumerate(hook_names):
                if i > 0:
                    row.append(", ")
                row.append(name, style="name")
            console.print(row)

    def _print_success(self) -> None:
        console.print(Text.assemble(("✓", "bold green"), "  Running hooks"))
        self._print_type_rows()

    def _print_error(self) -> None:
        console.print(Text.assemble(("✗", "bold red"), "  Running hooks"))
        self._print_type_rows()
        if self._current_type_label is not None:
            console.print(Text.assemble(("✗", "bold red"), f"    {self._current_type_label}"))

    def _ensure_live_started(self) -> None:
        if self._live is None:
            self._live = Live(
                self._make_renderable(),
                console=console,
                refresh_per_second=15,
                transient=True,
            )
            self._live.start()

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

    def _run_hooks(self, event: str, hook_names: list[str]) -> None:
        if not hook_names:
            return

        type_label = event.removeprefix("ON_").capitalize()
        env = self._build_env(event)
        self._ensure_live_started()

        self._current_type_progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[name]{task.fields[hook]}[/name]"),
            console=console,
        )
        task_id = self._current_type_progress.add_task(
            f"   {type_label}", total=len(hook_names), hook=""
        )
        self._current_type_label = type_label
        self._output_lines = []
        assert self._live is not None
        self._live.update(self._make_renderable())

        for hook_name in hook_names:
            self._output_lines = []
            self._current_type_progress.update(task_id, hook=hook_name)
            cmd = self._resolve_command(hook_name)
            logger.debug("running hook %r as %s in %s", hook_name, cmd, self._worktree_dir)

            with subprocess.Popen(
                cmd,
                cwd=self._worktree_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            ) as proc:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    self._output_lines.append(Text(raw.rstrip(), style="hook"))
                    self._live.update(self._make_renderable())

            if proc.returncode != 0:
                logger.error("hook %r exited with code %d", hook_name, proc.returncode)
                raise HookExecutionError(f"hook {hook_name!r} exited with code {proc.returncode}")

            logger.debug("hook %r completed successfully", hook_name)
            self._current_type_progress.advance(task_id)
            self._output_lines = []
            self._live.update(self._make_renderable())

        self._completed_types.append((type_label, hook_names))
        self._current_type_label = None
        self._current_type_progress = None
        self._live.update(self._make_renderable())

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
