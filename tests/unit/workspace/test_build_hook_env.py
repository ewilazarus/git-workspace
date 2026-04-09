from pathlib import Path

from git_workspace import workspace

ROOT = Path("/workspace")
WORKTREE_PATH = ROOT / "feat" / "001"
BRANCH = "feat/001"
EVENT = "after_setup"


def test_standard_context_vars_are_set() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT)

    assert env["GIT_WORKSPACE_BRANCH"] == BRANCH
    assert env["GIT_WORKSPACE_BRANCH_NO_SLASH"] == "feat_001"
    assert env["GIT_WORKSPACE_ROOT"] == str(ROOT)
    assert env["GIT_WORKSPACE_WORKTREE"] == str(WORKTREE_PATH)
    assert env["GIT_WORKSPACE_EVENT"] == EVENT


def test_manifest_vars_are_prefixed() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT, manifest_vars={"db_url": "sqlite://"})

    assert env["GIT_WORKSPACE_VAR_DB_URL"] == "sqlite://"


def test_user_vars_override_manifest_vars() -> None:
    env = workspace.build_hook_env(
        BRANCH, ROOT, WORKTREE_PATH, EVENT,
        manifest_vars={"db_url": "sqlite://"},
        user_vars={"db_url": "postgres://"},
    )

    assert env["GIT_WORKSPACE_VAR_DB_URL"] == "postgres://"


def test_user_vars_are_prefixed() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT, user_vars={"my_var": "hello"})

    assert env["GIT_WORKSPACE_VAR_MY_VAR"] == "hello"


def test_var_keys_are_normalized_to_uppercase() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT, manifest_vars={"MixedCase": "val"})

    assert env["GIT_WORKSPACE_VAR_MIXEDCASE"] == "val"


def test_var_keys_non_alphanumeric_replaced_with_underscore() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT, manifest_vars={"my-var.name": "val"})

    assert env["GIT_WORKSPACE_VAR_MY_VAR_NAME"] == "val"


def test_inherits_process_environment() -> None:
    import os
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT)

    assert "PATH" in env
    assert env["PATH"] == os.environ["PATH"]


def test_no_vars_produces_only_standard_context() -> None:
    env = workspace.build_hook_env(BRANCH, ROOT, WORKTREE_PATH, EVENT)

    gw_keys = [k for k in env if k.startswith("GIT_WORKSPACE_")]
    assert set(gw_keys) == {
        "GIT_WORKSPACE_BRANCH",
        "GIT_WORKSPACE_BRANCH_NO_SLASH",
        "GIT_WORKSPACE_ROOT",
        "GIT_WORKSPACE_WORKTREE",
        "GIT_WORKSPACE_EVENT",
    }
