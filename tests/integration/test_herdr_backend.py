import json
import subprocess
from pathlib import Path

import pytest

from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.remove import remove
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from git_workspace.workspace.state import WorkspaceStateStore
from tests.helpers import make_context

FAKE_HERDR = Path(__file__).parent / "fixtures" / "fake_herdr.py"


@pytest.fixture
def herdr_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Points HERDR_BIN_PATH at the fake herdr and returns its state file."""
    state = tmp_path / "fake-herdr-state.json"
    monkeypatch.setenv("FAKE_HERDR_STATE", str(state))
    monkeypatch.setenv("HERDR_BIN_PATH", str(FAKE_HERDR))
    return state


def herdr_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {"workspaces": {}, "focus_log": []}
    return json.loads(state_file.read_text())


def workspace_paths(state_file: Path) -> set[str]:
    return {info["path"] for info in herdr_state(state_file)["workspaces"].values()}


class TestUpWithHerdrBackend:
    def test_creates_prepares_and_presents(self, workspace: Workspace, herdr_env: Path) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="herdr")

        worktree_dir = (workspace.dir / "feat").resolve()
        assert worktree_dir.is_dir()

        state = herdr_state(herdr_env)
        assert str(worktree_dir) in workspace_paths(herdr_env)
        assert state["focus_log"], "presentation should have been focused"

        record = WorkspaceStateStore(workspace.paths.state).load(worktree_dir)
        assert record is not None
        assert record.lifecycle_state.value == "ready"
        assert record.presentation is not None
        assert record.presentation.presenter_kind.value == "herdr"
        assert record.presentation.presentation_id in state["focus_log"]

    def test_no_focus_still_opens_presentation(self, workspace: Workspace, herdr_env: Path) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="herdr", focus=False)

        assert str((workspace.dir / "feat").resolve()) in workspace_paths(herdr_env)
        assert herdr_state(herdr_env)["focus_log"] == []

    def test_detached_does_not_focus(self, workspace: Workspace, herdr_env: Path) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="herdr", detached=True)

        assert herdr_state(herdr_env)["focus_log"] == []

    def test_native_backend_never_touches_herdr(
        self, workspace: Workspace, herdr_env: Path
    ) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="native")

        assert not herdr_env.exists()

    def test_up_on_existing_worktree_presents_it(
        self, workspace: Workspace, herdr_env: Path
    ) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="native")
        assert not herdr_env.exists()

        up(ctx=make_context(str(workspace.dir)), branch="feat", backend="herdr")

        assert str((workspace.dir / "feat").resolve()) in workspace_paths(herdr_env)


class TestAutoDetection:
    def test_auto_selects_herdr_inside_verified_context(
        self,
        workspace: Workspace,
        herdr_env: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))

        up(ctx=make_context(str(workspace.dir)), branch="feat")

        assert str((workspace.dir / "feat").resolve()) in workspace_paths(herdr_env)

    def test_defaults_to_native_outside_context(
        self, workspace: Workspace, herdr_env: Path
    ) -> None:
        up(ctx=make_context(str(workspace.dir)), branch="feat")

        assert not herdr_env.exists()

    def test_manifest_native_backend_disables_detection(
        self,
        workspace: Workspace,
        herdr_env: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))
        manifest = workspace.paths.manifest
        manifest.write_text(manifest.read_text() + '\n[workspace]\nbackend = "native"\n')
        workspace.manifest = type(workspace.manifest).load(workspace)

        up(ctx=make_context(str(workspace.dir)), branch="feat")

        assert not herdr_env.exists()


class TestDownAndRemove:
    def test_down_closes_workspace_and_preserves_worktree(
        self,
        workspace: Workspace,
        herdr_env: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))
        up(ctx=make_context(str(workspace.dir)), branch="feat")
        assert workspace_paths(herdr_env)

        down(ctx=make_context(str(workspace.dir)), branch="feat")

        assert workspace_paths(herdr_env) == set()
        assert (workspace.dir / "feat").is_dir()

    def test_rm_removes_worktree_and_workspace_but_preserves_branch(
        self,
        workspace: Workspace,
        herdr_env: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))
        up(ctx=make_context(str(workspace.dir)), branch="feat")

        remove(ctx=make_context(str(workspace.dir)), branch="feat")

        assert workspace_paths(herdr_env) == set()
        assert not (workspace.dir / "feat").exists()
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", "refs/heads/feat"],
            cwd=workspace.dir,
            capture_output=True,
        )
        assert result.returncode == 0
