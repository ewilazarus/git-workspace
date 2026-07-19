import logging
from pathlib import Path

from git_workspace.workspace.assets import Copier, IgnoreManager, Linker
from git_workspace.workspace.core import Workspace
from git_workspace.workspace.env import build_env
from git_workspace.workspace.fingerprint import compute_fingerprints
from git_workspace.workspace.hooks import HookRunner
from git_workspace.workspace.worktree import Worktree

logger = logging.getLogger(__name__)


class WorkspacePreparer:
    """
    Owns the project-specific setup lifecycle of a worktree: assets (links,
    copies, templates), environment construction, fingerprints, and hooks.

    Backend-agnostic by design: it receives plain data (a worktree path and
    branch) and must never import providers, presenters, or backends. Hook
    execution intentionally runs user-authored shell command strings (see
    HookRunner) and is exempt from the CommandRunner argv-only rule.
    """

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    def prepare(
        self,
        worktree_path: Path,
        branch: str,
        *,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> None:
        """
        Applies assets and runs ``on_setup`` hooks for the worktree.

        Safe to retry: asset application honors overwrite/override flags and
        hooks are expected to self-skip via fingerprints and the cache.
        """
        logger.debug("preparing worktree %r at %s", branch, worktree_path)
        worktree, env = self._context(worktree_path, branch, runtime_vars)

        with IgnoreManager(worktree) as ignore:
            Copier(worktree, ignore, env).apply()
            Linker(worktree, ignore).apply()

        with HookRunner(worktree, env=env, effective_branch=effective_branch or branch) as runner:
            runner.run_on_setup_hooks()

    def attach(
        self,
        worktree_path: Path,
        branch: str,
        *,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> None:
        """Runs ``on_attach`` hooks when entering a worktree session."""
        logger.debug("attaching to worktree %r at %s", branch, worktree_path)
        worktree, env = self._context(worktree_path, branch, runtime_vars)
        with HookRunner(worktree, env=env, effective_branch=effective_branch or branch) as runner:
            runner.run_on_attach_hooks()

    def detach(
        self,
        worktree_path: Path,
        branch: str,
        *,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> None:
        """Runs ``on_detach`` hooks when leaving a worktree session."""
        logger.debug("detaching from worktree %r at %s", branch, worktree_path)
        worktree, env = self._context(worktree_path, branch, runtime_vars)
        with HookRunner(worktree, env=env, effective_branch=effective_branch or branch) as runner:
            runner.run_on_detach_hooks()

    def teardown(
        self,
        worktree_path: Path,
        branch: str,
        *,
        runtime_vars: dict[str, str] | None = None,
        effective_branch: str | None = None,
    ) -> None:
        """Runs ``on_teardown`` hooks before a worktree is removed."""
        logger.debug("tearing down worktree %r at %s", branch, worktree_path)
        worktree, env = self._context(worktree_path, branch, runtime_vars)
        with HookRunner(worktree, env=env, effective_branch=effective_branch or branch) as runner:
            runner.run_on_teardown_hooks()

    def _context(
        self,
        worktree_path: Path,
        branch: str,
        runtime_vars: dict[str, str] | None,
    ) -> tuple[Worktree, dict[str, str]]:
        worktree = Worktree(workspace=self._workspace, dir=worktree_path, branch=branch)
        fingerprint_vars = compute_fingerprints(worktree, self._workspace.manifest.fingerprints)
        env = build_env(worktree, runtime_vars or {}, fingerprint_vars)
        return worktree, env
