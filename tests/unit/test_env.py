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
CACHE_DIR = Path("/workspace/.workspace/.cache")


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKTREE_DIR
    mock.branch = BRANCH
    mock.workspace.dir = WORKSPACE_DIR
    mock.workspace.paths.bin = BIN_DIR
    mock.workspace.paths.assets = ASSETS_DIR
    mock.workspace.paths.cache = CACHE_DIR
    return mock


class TestBuildEnv:
    def test_sets_branch(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_BRANCH"] == BRANCH

    def test_sets_branch_no_slash(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_BRANCH_NO_SLASH"] == BRANCH.replace("/", "_")

    def test_sets_root(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_ROOT"] == str(WORKSPACE_DIR)

    def test_sets_name(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_NAME"] == WORKSPACE_NAME

    def test_sets_bin(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_BIN"] == str(BIN_DIR)

    def test_sets_assets(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_ASSETS"] == str(ASSETS_DIR)

    def test_sets_worktree(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_WORKTREE"] == str(WORKTREE_DIR)

    def test_sets_cache_dir(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert env["GIT_WORKSPACE_CACHE_DIR"] == str(CACHE_DIR)

    def test_includes_extra_vars(self, worktree: MagicMock) -> None:
        env = build_env(worktree, runtime_vars={"FOO": "bar"})
        assert env["GIT_WORKSPACE_VAR_FOO"] == "bar"

    def test_normalizes_var_keys(self, worktree: MagicMock) -> None:
        env = build_env(worktree, runtime_vars={"my-runtime-var": "value"})
        assert env["GIT_WORKSPACE_VAR_MY_RUNTIME_VAR"] == "value"

    def test_includes_fingerprint_vars(self, worktree: MagicMock) -> None:
        env = build_env(worktree, fingerprint_vars={"docker-deps": "abc123"})
        assert env["GIT_WORKSPACE_FINGERPRINT_DOCKER_DEPS"] == "abc123"

    def test_normalizes_fingerprint_keys(self, worktree: MagicMock) -> None:
        env = build_env(worktree, fingerprint_vars={"my-fingerprint": "deadbeef"})
        assert env["GIT_WORKSPACE_FINGERPRINT_MY_FINGERPRINT"] == "deadbeef"

    def test_fingerprint_and_var_same_normalized_name_produce_separate_keys(
        self, worktree: MagicMock
    ) -> None:
        env = build_env(
            worktree,
            runtime_vars={"deps": "from-var"},
            fingerprint_vars={"deps": "from-fp"},
        )
        assert env["GIT_WORKSPACE_VAR_DEPS"] == "from-var"
        assert env["GIT_WORKSPACE_FINGERPRINT_DEPS"] == "from-fp"

    def test_no_fingerprint_vars_does_not_set_fingerprint_keys(self, worktree: MagicMock) -> None:
        env = build_env(worktree)
        assert not any(k.startswith("GIT_WORKSPACE_FINGERPRINT_") for k in env)
