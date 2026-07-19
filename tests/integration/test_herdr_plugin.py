import fcntl
import json
import os
import stat
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from git_workspace.workspace import Workspace
from git_workspace.workspace.lock import (
    workspace_operation_lock,  # noqa: F401  (documents the lock under test)
)
from git_workspace.workspace.state import WorkspaceStateStore, state_file_stem
from tests.integration.conftest import _GIT_ENV

PLUGIN_ROOT = Path(__file__).parent.parent.parent / "integrations" / "herdr"
HOOK = PLUGIN_ROOT / "hooks" / "prepare"
FAKE_HERDR = Path(__file__).parent / "fixtures" / "fake_herdr.py"


@pytest.fixture
def gw_bin(tmp_path: Path) -> str:
    """A git-workspace wrapper bound to the project venv's interpreter."""
    wrapper = tmp_path / "git-workspace-wrapper"
    wrapper.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" -c "from git_workspace import main; main()" "$@"\n'
    )
    wrapper.chmod(0o755)
    return str(wrapper)


def event_json(worktree_path: Path, repo_root: Path, branch: str = "feature/hooked") -> str:
    return json.dumps(
        {
            "event": "worktree_created",
            "data": {
                "type": "worktree_created",
                "workspace": {
                    "workspace_id": "w1",
                    "worktree": {
                        "repo_root": str(repo_root),
                        "repo_key": str(repo_root / ".git"),
                        "checkout_path": str(worktree_path),
                        "is_linked_worktree": True,
                    },
                },
                "worktree": {
                    "path": str(worktree_path),
                    "branch": branch,
                    "is_linked_worktree": True,
                },
            },
        }
    )


def run_hook(
    *args: str,
    gw_bin: str,
    env_extra: dict[str, str],
    tmp_path: Path,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_WORKSPACE_BIN": gw_bin,
        "FAKE_HERDR_STATE": str(tmp_path / "fake-herdr-state.json"),
        "HERDR_BIN_PATH": str(FAKE_HERDR),
        **env_extra,
    }
    env.pop("HERDR_PLUGIN_EVENT_JSON", None) if "HERDR_PLUGIN_EVENT_JSON" not in env_extra else None
    return subprocess.run([str(HOOK), *args], env=env, capture_output=True, text=True)


def notifications(tmp_path: Path) -> list[dict]:
    state_file = tmp_path / "fake-herdr-state.json"
    if not state_file.exists():
        return []
    return json.loads(state_file.read_text()).get("notifications", [])


def add_raw_worktree(workspace: Workspace, branch: str = "feature/hooked") -> Path:
    worktree_path = workspace.dir / branch
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path)],
        cwd=workspace.dir,
        capture_output=True,
        env=_GIT_ENV,
        check=True,
    )
    return worktree_path.resolve()


class TestManifest:
    def test_is_valid_and_complete(self) -> None:
        manifest = tomllib.loads((PLUGIN_ROOT / "herdr-plugin.toml").read_text())

        assert manifest["id"] == "git-workspace"
        assert manifest["min_herdr_version"]
        assert set(manifest["platforms"]) == {"macos", "linux"}
        assert {event["on"] for event in manifest["events"]} == {
            "worktree.created",
            "worktree.opened",
        }

    def test_all_commands_point_at_executable_files(self) -> None:
        manifest = tomllib.loads((PLUGIN_ROOT / "herdr-plugin.toml").read_text())

        for entry in [*manifest["events"], *manifest["actions"]]:
            script = PLUGIN_ROOT / entry["command"][0]
            assert script.is_file(), f"missing hook script: {script}"
            assert script.stat().st_mode & stat.S_IXUSR, f"hook not executable: {script}"


class TestEventHook:
    def test_prepares_worktree_from_created_event(
        self, workspace_with_hooks: Workspace, gw_bin: str, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)

        result = run_hook(
            gw_bin=gw_bin,
            env_extra={
                "HERDR_PLUGIN_EVENT_JSON": event_json(worktree_path, workspace_with_hooks.dir)
            },
            tmp_path=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        assert (workspace_with_hooks.dir / ".hook-on-setup").exists()
        record = WorkspaceStateStore(workspace_with_hooks.paths.state).load(worktree_path)
        assert record is not None
        assert record.lifecycle_state.value == "ready"

    def test_skips_repositories_without_git_workspace_config(
        self, gw_bin: str, tmp_path: Path
    ) -> None:
        plain_repo = tmp_path / "plain"
        plain_repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=plain_repo, capture_output=True, check=True
        )

        result = run_hook(
            gw_bin=gw_bin,
            env_extra={"HERDR_PLUGIN_EVENT_JSON": event_json(plain_repo / "wt", plain_repo)},
            tmp_path=tmp_path,
        )

        assert result.returncode == 0
        assert "skipping" in result.stdout
        assert notifications(tmp_path) == []

    def test_missing_worktree_path_is_a_noop(self, gw_bin: str, tmp_path: Path) -> None:
        result = run_hook(
            gw_bin=gw_bin,
            env_extra={"HERDR_PLUGIN_EVENT_JSON": json.dumps({"event": "x", "data": {}})},
            tmp_path=tmp_path,
        )

        assert result.returncode == 0
        assert "nothing to prepare" in result.stdout

    def test_failure_sends_notification_with_retry_hint(
        self, workspace_with_hooks: Workspace, gw_bin: str, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)
        hook = workspace_with_hooks.paths.bin / "on_setup"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)

        result = run_hook(
            gw_bin=gw_bin,
            env_extra={
                "HERDR_PLUGIN_EVENT_JSON": event_json(worktree_path, workspace_with_hooks.dir)
            },
            tmp_path=tmp_path,
        )

        assert result.returncode != 0
        sent = notifications(tmp_path)
        assert len(sent) == 1
        assert "prepare --force" in sent[0]["body"]

    def test_lock_contention_is_benign(
        self, workspace_with_hooks: Workspace, gw_bin: str, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)
        locks_dir = workspace_with_hooks.paths.state / "locks"
        locks_dir.mkdir(parents=True, exist_ok=True)
        lock_file = locks_dir / f"{state_file_stem(worktree_path)}.lock"

        fd = os.open(lock_file, os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            result = run_hook(
                gw_bin=gw_bin,
                env_extra={
                    "HERDR_PLUGIN_EVENT_JSON": event_json(worktree_path, workspace_with_hooks.dir)
                },
                tmp_path=tmp_path,
            )
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

        assert result.returncode == 0
        assert "skipping" in result.stdout
        assert notifications(tmp_path) == []

    def test_missing_git_workspace_binary_notifies_and_fails(
        self, workspace_with_hooks: Workspace, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)
        # A PATH with python3 (for the hook's own shebang) but no git-workspace.
        bare_bin = tmp_path / "bare-bin"
        bare_bin.mkdir()
        (bare_bin / "python3").symlink_to(sys.executable)

        result = run_hook(
            gw_bin="",
            env_extra={
                "GIT_WORKSPACE_BIN": "",
                "PATH": str(bare_bin),
                "HERDR_PLUGIN_EVENT_JSON": event_json(worktree_path, workspace_with_hooks.dir),
            },
            tmp_path=tmp_path,
        )

        assert result.returncode == 1
        assert notifications(tmp_path)


class TestActionMode:
    def test_prepares_worktree_from_invocation_context(
        self, workspace_with_hooks: Workspace, gw_bin: str, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)
        context = json.dumps(
            {
                "workspace_id": "w1",
                "workspace_cwd": str(worktree_path),
                "worktree": {
                    "repo_root": str(workspace_with_hooks.dir),
                    "checkout_path": str(worktree_path),
                },
            }
        )

        result = run_hook(
            gw_bin=gw_bin,
            env_extra={"HERDR_PLUGIN_CONTEXT_JSON": context},
            tmp_path=tmp_path,
        )

        assert result.returncode == 0, result.stderr
        record = WorkspaceStateStore(workspace_with_hooks.paths.state).load(worktree_path)
        assert record is not None
        assert record.lifecycle_state.value == "ready"

    def test_force_flag_reruns_preparation(
        self, workspace_with_hooks: Workspace, gw_bin: str, tmp_path: Path
    ) -> None:
        worktree_path = add_raw_worktree(workspace_with_hooks)
        context = json.dumps(
            {
                "worktree": {
                    "repo_root": str(workspace_with_hooks.dir),
                    "checkout_path": str(worktree_path),
                }
            }
        )
        env = {"HERDR_PLUGIN_CONTEXT_JSON": context}

        run_hook(gw_bin=gw_bin, env_extra=env, tmp_path=tmp_path)
        marker = workspace_with_hooks.dir / ".hook-on-setup"
        marker.unlink()

        run_hook(gw_bin=gw_bin, env_extra=env, tmp_path=tmp_path)
        assert not marker.exists(), "plain prepare should no-op when READY"

        result = run_hook(gw_bin=gw_bin, env_extra=env, tmp_path=tmp_path, *("--force",))
        assert result.returncode == 0
        assert marker.exists(), "--force should re-run setup hooks"
