from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.env import build_env

BRANCH = "feat/GWS-001"
WORKSPACE_DIR = Path("/workspace")
WORKSPACE_NAME = "workspace"
WORKTREE_DIR = Path("/workspace/feat/GWS-001")
BIN_DIR = Path("/workspace/.workspace/bin")
ASSETS_DIR = Path("/workspace/.workspace/assets")


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKTREE_DIR
    mock.branch = BRANCH
    mock.workspace.dir = WORKSPACE_DIR
    mock.workspace.paths.bin = BIN_DIR
    mock.workspace.paths.assets = ASSETS_DIR
    return mock


class TestBuildEnv:
    def test_sets_branch(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BRANCH"] == BRANCH

    def test_sets_branch_no_slash(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BRANCH_NO_SLASH"] == BRANCH.replace("/", "_")

    def test_sets_root(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_ROOT"] == str(WORKSPACE_DIR)

    def test_sets_name(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_NAME"] == WORKSPACE_NAME

    def test_sets_bin(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BIN"] == str(BIN_DIR)

    def test_sets_assets(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_ASSETS"] == str(ASSETS_DIR)

    def test_sets_worktree(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_WORKTREE"] == str(WORKTREE_DIR)

    def test_sets_event(self, worktree: MagicMock) -> None:
        env = build_env(worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_EVENT"] == "ON_TEST"

    def test_omits_event_when_none(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert "GIT_WORKSPACE_EVENT" not in env

    def test_includes_extra_vars(self, worktree: MagicMock) -> None:
        env = build_env(worktree, extra_vars={"FOO": "bar"})
        assert env["GIT_WORKSPACE_VAR_FOO"] == "bar"

    def test_normalizes_var_keys(self, worktree: MagicMock) -> None:
        env = build_env(worktree, extra_vars={"my-runtime-var": "value"})
        assert env["GIT_WORKSPACE_VAR_MY_RUNTIME_VAR"] == "value"
