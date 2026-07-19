import json
from pathlib import Path

import pytest

import git_workspace.subprocesses.herdr as herdr
from git_workspace.errors import HerdrError
from tests.helpers import FakeCommandRunner

REPO = Path("/workspace")
TARGET = Path("/workspace/feature/x")
HERDR = "herdr"


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


def ok(result: dict) -> str:
    return json.dumps({"id": "cli:test", "result": result})


class TestResolveExecutable:
    def test_explicit_value_wins(self, monkeypatch) -> None:
        monkeypatch.setenv("HERDR_BIN_PATH", "/env/herdr")

        assert herdr.resolve_executable("/explicit/herdr") == "/explicit/herdr"

    def test_env_var_beats_path(self, monkeypatch, mocker) -> None:
        monkeypatch.setenv("HERDR_BIN_PATH", "/env/herdr")
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value="/path/herdr")

        assert herdr.resolve_executable() == "/env/herdr"

    def test_falls_back_to_path(self, mocker) -> None:
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value="/path/herdr")

        assert herdr.resolve_executable() == "/path/herdr"

    def test_none_when_unavailable(self, mocker) -> None:
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value=None)

        assert herdr.resolve_executable() is None


class TestInVerifiedContext:
    def test_true_with_env_marker_and_existing_socket(self, monkeypatch, tmp_path) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))

        assert herdr.in_verified_context() is True

    def test_false_without_env_marker(self, monkeypatch, tmp_path) -> None:
        socket = tmp_path / "herdr.sock"
        socket.touch()
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(socket))

        assert herdr.in_verified_context() is False

    def test_false_when_socket_missing(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("HERDR_ENV", "1")
        monkeypatch.setenv("HERDR_SOCKET_PATH", str(tmp_path / "gone.sock"))

        assert herdr.in_verified_context() is False


class TestCommands:
    def test_list_worktrees_argv(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"worktrees": []}))

        herdr.list_worktrees(REPO, executable=HERDR, runner=runner)

        assert runner.last_call.args == ("herdr", "worktree", "list", "--cwd", str(REPO), "--json")

    def test_create_worktree_argv_with_base(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"type": "worktree_created"}))

        herdr.create_worktree(REPO, "feature/x", TARGET, "main", executable=HERDR, runner=runner)

        assert runner.last_call.args == (
            "herdr",
            "worktree",
            "create",
            "--cwd",
            str(REPO),
            "--branch",
            "feature/x",
            "--path",
            str(TARGET),
            "--base",
            "main",
            "--no-focus",
            "--json",
        )

    def test_create_worktree_omits_base_when_none(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({}))

        herdr.create_worktree(REPO, "feature/x", TARGET, None, executable=HERDR, runner=runner)

        assert "--base" not in runner.last_call.args

    def test_open_worktree_argv(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"type": "worktree_opened"}))

        herdr.open_worktree(REPO, TARGET, executable=HERDR, runner=runner)

        assert runner.last_call.args == (
            "herdr",
            "worktree",
            "open",
            "--cwd",
            str(REPO),
            "--path",
            str(TARGET),
            "--no-focus",
            "--json",
        )

    def test_remove_worktree_argv_with_force(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"type": "worktree_removed"}))

        herdr.remove_worktree("w8", force=True, executable=HERDR, runner=runner)

        assert runner.last_call.args == (
            "herdr",
            "worktree",
            "remove",
            "--workspace",
            "w8",
            "--force",
            "--json",
        )

    def test_focus_and_close_argv(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"type": "ok"}))
        herdr.focus_workspace("w8", executable=HERDR, runner=runner)
        assert runner.last_call.args == ("herdr", "workspace", "focus", "w8")

        runner.queue(stdout=ok({"type": "ok"}))
        herdr.close_workspace("w8", executable=HERDR, runner=runner)
        assert runner.last_call.args == ("herdr", "workspace", "close", "w8")


class TestEnvelopeParsing:
    def test_returns_result_payload(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=ok({"type": "worktree_list", "worktrees": [{"path": "/x"}]}))

        result = herdr.list_worktrees(REPO, executable=HERDR, runner=runner)

        assert result["worktrees"] == [{"path": "/x"}]

    def test_error_envelope_raises_even_with_exit_zero(self, runner: FakeCommandRunner) -> None:
        runner.queue(
            exit_code=0,
            stdout=json.dumps(
                {"error": {"code": "not_git_worktree", "message": "not a work tree"}}
            ),
        )

        with pytest.raises(HerdrError) as excinfo:
            herdr.list_worktrees(REPO, executable=HERDR, runner=runner)

        assert excinfo.value.code == "not_git_worktree"

    def test_malformed_output_raises(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout="not json at all")

        with pytest.raises(HerdrError, match="malformed"):
            herdr.list_worktrees(REPO, executable=HERDR, runner=runner)

    def test_nonzero_exit_without_error_payload_raises(self, runner: FakeCommandRunner) -> None:
        runner.queue(exit_code=1, stdout="{}", stderr="server not running")

        with pytest.raises(HerdrError, match="server not running"):
            herdr.list_worktrees(REPO, executable=HERDR, runner=runner)
