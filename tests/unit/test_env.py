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
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKSPACE_DIR
    mock.paths.bin = BIN_DIR
    mock.paths.assets = ASSETS_DIR
    return mock


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKTREE_DIR
    mock.branch = BRANCH
    return mock


class TestBuildEnv:
    def test_sets_branch(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BRANCH"] == BRANCH

    def test_sets_branch_no_slash(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BRANCH_NO_SLASH"] == BRANCH.replace("/", "_")

    def test_sets_root(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_ROOT"] == str(WORKSPACE_DIR)

    def test_sets_name(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_NAME"] == WORKSPACE_NAME

    def test_sets_bin(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_BIN"] == str(BIN_DIR)

    def test_sets_assets(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_ASSETS"] == str(ASSETS_DIR)

    def test_sets_worktree(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_WORKTREE"] == str(WORKTREE_DIR)

    def test_sets_event(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, event="ON_TEST")
        assert env["GIT_WORKSPACE_EVENT"] == "ON_TEST"

    def test_omits_event_when_none(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree)
        assert "GIT_WORKSPACE_EVENT" not in env

    def test_includes_extra_vars(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, extra_vars={"FOO": "bar"})
        assert env["GIT_WORKSPACE_VAR_FOO"] == "bar"

    def test_normalizes_var_keys(self, workspace: MagicMock, worktree: MagicMock) -> None:
        env = build_env(workspace, worktree, extra_vars={"my-runtime-var": "value"})
        assert env["GIT_WORKSPACE_VAR_MY_RUNTIME_VAR"] == "value"
