from git_workspace.worktree import Worktree
from git_workspace.workspace import Workspace
import os
import re
import subprocess


from git_workspace.errors import HookExecutionError


class HookRunner:
    def __init__(
        self, workspace: Workspace, worktree: Worktree, runtime_vars: dict[str, str]
    ) -> None:
        self._workspace = workspace
        self._worktree = worktree
        self._bin_path = workspace.directory / ".workspace" / "bin"
        self._worktree_directory = str(worktree.directory)
        self._runtime_vars = runtime_vars

    def _normalize_variable_key(self, value: str) -> str:
        return re.sub(r"[^A-Z0-9]", "_", value.upper())

    def _build_env(self, event: str) -> dict[str, str]:
        env = {
            **os.environ,
            "GIT_WORKSPACE_BRANCH": self._worktree.branch,
            "GIT_WORKSPACE_BRANCH_NO_SLASH": self._worktree.branch.replace("/", "_"),
            "GIT_WORKSPACE_ROOT": str(self._workspace.directory),
            "GIT_WORKSPACE_WORKTREE": self._worktree_directory,
            "GIT_WORKSPACE_EVENT": event,
        }

        for key, value in (self._workspace.manifest.vars or {}).items():
            normalized = self._normalize_variable_key(key)
            env[f"GIT_WORKSPACE_VAR_{normalized}"] = value

        for key, value in (self._runtime_vars or {}).items():
            normalized = self._normalize_variable_key(key)
            env[f"GIT_WORKSPACE_VAR_{normalized}"] = value

        return env

    def _run_hook(self, event: str, hook_name: str, env: dict[str, str]) -> None:
        hook_path = str(self._bin_path / hook_name)
        worktree_directory = self._worktree_directory

        with subprocess.Popen(
            [hook_path],
            cwd=worktree_directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            # bufsize=1,
        ) as proc:
            # TODO: include rich goodies
            pass

        if proc.returncode != 0:
            raise HookExecutionError()

    def _run_hooks(self, event: str, hook_names: list[str]) -> None:
        env = self._build_env(event)
        for hook_name in hook_names:
            self._run_hook(event, hook_name, env)

    def run_on_setup_hooks(self) -> None:
        self._run_hooks("ON_SETUP", self._workspace.manifest.hooks.on_setup)

    def run_on_activate_hooks(self) -> None:
        self._run_hooks("ON_ACTIVATE", self._workspace.manifest.hooks.on_activate)

    def run_on_attach_hooks(self) -> None:
        self._run_hooks("ON_ATTACH", self._workspace.manifest.hooks.on_attach)

    def run_on_deactivate_hooks(self) -> None:
        self._run_hooks("ON_DEACTIVATE", self._workspace.manifest.hooks.on_deactivate)

    def run_on_remove_hooks(self) -> None:
        self._run_hooks("ON_REMOVE", self._workspace.manifest.hooks.on_remove)
