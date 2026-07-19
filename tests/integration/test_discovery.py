import subprocess
from pathlib import Path

from git_workspace.workspace import Workspace
from git_workspace.workspace.core import WorkspaceResolver
from tests.integration.conftest import _GIT_ENV


def _up(workspace: Workspace, branch: str) -> Path:
    from git_workspace.workspace.service import WorkspaceService

    worktree = WorkspaceService.create(workspace).up(branch, detached=True)
    return worktree.dir


class TestResolveFromWorktree:
    def test_resolves_from_worktree_root(self, workspace: Workspace) -> None:
        worktree_dir = _up(workspace, "feature/discovery")

        resolved = WorkspaceResolver.resolve_from_worktree(worktree_dir)

        assert resolved.dir == workspace.dir

    def test_resolves_from_deep_subdirectory(self, workspace: Workspace) -> None:
        worktree_dir = _up(workspace, "feature/discovery")
        deep = worktree_dir / "a" / "b"
        deep.mkdir(parents=True)

        resolved = WorkspaceResolver.resolve_from_worktree(deep)

        assert resolved.dir == workspace.dir

    def test_resolves_worktree_created_outside_workspace_root(
        self, workspace: Workspace, tmp_path: Path
    ) -> None:
        outside = tmp_path / "elsewhere" / "wt"
        subprocess.run(
            ["git", "worktree", "add", "-b", "feature/outside", str(outside)],
            cwd=workspace.dir,
            capture_output=True,
            env=_GIT_ENV,
            check=True,
        )

        resolved = WorkspaceResolver.resolve_from_worktree(outside)

        assert resolved.dir == workspace.dir

    def test_falls_back_to_walk_up_from_inside_config_repo(self, workspace: Workspace) -> None:
        # .workspace is itself a git repo; rev-parse there points at the config
        # repo's git dir, so discovery must fall back to walking up.
        resolved = WorkspaceResolver.resolve_from_worktree(workspace.paths.config)

        assert resolved.dir == workspace.dir
