from pathlib import Path

import pytest

import git_workspace.subprocesses.git as git
from git_workspace.errors import (
    GitCloneError,
    GitFetchError,
    GitInitError,
    WorktreeCreationError,
    WorktreeListingError,
    WorktreeRemovalError,
)
from tests.helpers import FakeCommandRunner

URL = "https://github.com/user/repo.git"
BRANCH = "feat/GWS-001"
BASE_BRANCH = "main"
TARGET = Path("/target")
WORKTREE_DIR = Path("/workspace/feat/GWS-001")
CWD = Path("/workspace")
COMMIT_SHA = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


class TestClone:
    def test_builds_basic_clone_command(self, runner: FakeCommandRunner) -> None:
        git.clone(URL, runner=runner)

        assert runner.last_call.args == ("git", "clone", URL)

    def test_appends_target_when_provided(self, runner: FakeCommandRunner) -> None:
        git.clone(URL, target=TARGET, runner=runner)

        assert runner.last_call.args == ("git", "clone", URL, str(TARGET))

    def test_appends_bare_flag_when_bare(self, runner: FakeCommandRunner) -> None:
        git.clone(URL, bare=True, runner=runner)

        assert runner.last_call.args == ("git", "clone", "--bare", URL)

    def test_appends_branch_flags_when_provided(self, runner: FakeCommandRunner) -> None:
        git.clone(URL, branch=BASE_BRANCH, runner=runner)

        assert runner.last_call.args == (
            "git",
            "clone",
            "-b",
            BASE_BRANCH,
            "--single-branch",
            URL,
        )

    def test_raises_git_clone_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(GitCloneError):
            git.clone(URL, runner=runner)


class TestInit:
    def test_builds_init_command_with_target(self, runner: FakeCommandRunner) -> None:
        git.init(TARGET, bare=False, runner=runner)

        assert runner.last_call.args == ("git", "init", str(TARGET))

    def test_appends_bare_flag_when_bare(self, runner: FakeCommandRunner) -> None:
        git.init(TARGET, bare=True, runner=runner)

        assert runner.last_call.args == ("git", "init", "--bare", str(TARGET))

    def test_raises_git_init_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(GitInitError):
            git.init(TARGET, bare=False, runner=runner)


class TestListWorktrees:
    def test_builds_list_command_with_cwd(self, runner: FakeCommandRunner) -> None:
        git.list_worktrees(CWD, runner=runner)

        assert runner.last_call.args == ("git", "worktree", "list", "--porcelain")
        assert runner.last_call.cwd == CWD

    def test_returns_parsed_worktrees(self, runner: FakeCommandRunner) -> None:
        runner.queue(
            stdout=f"worktree {WORKTREE_DIR}\nHEAD {COMMIT_SHA}\nbranch refs/heads/{BRANCH}"
        )

        result = git.list_worktrees(CWD, runner=runner)

        assert result == [{"directory": str(WORKTREE_DIR), "head": COMMIT_SHA, "branch": BRANCH}]

    def test_skips_detached_head_worktrees(self, runner: FakeCommandRunner) -> None:
        runner.queue(
            stdout=(
                f"worktree {WORKTREE_DIR}\nHEAD {COMMIT_SHA}\nbranch refs/heads/{BRANCH}\n"
                "\n"
                f"worktree /workspace/detached\nHEAD {COMMIT_SHA}\ndetached"
            )
        )

        result = git.list_worktrees(CWD, runner=runner)

        assert result == [{"directory": str(WORKTREE_DIR), "head": COMMIT_SHA, "branch": BRANCH}]

    def test_returns_empty_list_when_no_matches(self, runner: FakeCommandRunner) -> None:
        result = git.list_worktrees(CWD, runner=runner)

        assert result == []

    def test_raises_worktree_listing_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(WorktreeListingError):
            git.list_worktrees(CWD, runner=runner)


class TestConfigureRemoteFetchRefspec:
    def test_sets_correct_refspec(self, runner: FakeCommandRunner) -> None:
        git.configure_remote_fetch_refspec(CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "config",
            "remote.origin.fetch",
            "+refs/heads/*:refs/remotes/origin/*",
        )
        assert runner.last_call.cwd == CWD


class TestFetchOrigin:
    def test_builds_fetch_command_with_cwd(self, runner: FakeCommandRunner) -> None:
        git.fetch_origin(CWD, runner=runner)

        assert runner.last_call.args == ("git", "fetch", "origin", "--prune")
        assert runner.last_call.cwd == CWD

    def test_raises_git_fetch_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(GitFetchError):
            git.fetch_origin(CWD, runner=runner)


class TestLocalBranchExists:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.local_branch_exists(BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/heads/{BRANCH}",
        )

    def test_returns_true_when_branch_exists(self, runner: FakeCommandRunner) -> None:
        assert git.local_branch_exists(BRANCH, CWD, runner=runner) is True

    def test_returns_false_when_branch_not_found(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        assert git.local_branch_exists(BRANCH, CWD, runner=runner) is False


class TestRemoteBranchExists:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.remote_branch_exists(BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{BRANCH}",
        )

    def test_returns_true_when_branch_exists(self, runner: FakeCommandRunner) -> None:
        assert git.remote_branch_exists(BRANCH, CWD, runner=runner) is True

    def test_returns_false_when_branch_not_found(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        assert git.remote_branch_exists(BRANCH, CWD, runner=runner) is False


class TestSkipWorktree:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.skip_worktree(TARGET, runner=runner)

        assert runner.last_call.args == (
            "git",
            "update-index",
            "--skip-worktree",
            str(TARGET),
        )

    def test_does_not_raise_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        git.skip_worktree(TARGET, runner=runner)


class TestCreateWorktreeFromLocalBranch:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.create_worktree_from_local_branch(WORKTREE_DIR, BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            str(WORKTREE_DIR),
            BRANCH,
        )
        assert runner.last_call.cwd == CWD

    def test_raises_worktree_creation_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_from_local_branch(WORKTREE_DIR, BRANCH, CWD, runner=runner)


class TestCreateWorktreeFromRemoteBranch:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.create_worktree_from_remote_branch(WORKTREE_DIR, BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "--track",
            "-b",
            BRANCH,
            str(WORKTREE_DIR),
            f"origin/{BRANCH}",
        )
        assert runner.last_call.cwd == CWD

    def test_raises_worktree_creation_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_from_remote_branch(WORKTREE_DIR, BRANCH, CWD, runner=runner)


class TestCreateWorktreeNew:
    def test_builds_correct_command(self, runner: FakeCommandRunner) -> None:
        git.create_worktree_new(WORKTREE_DIR, BRANCH, BASE_BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "-b",
            BRANCH,
            str(WORKTREE_DIR),
            BASE_BRANCH,
        )
        assert runner.last_call.cwd == CWD

    def test_falls_back_to_orphan_worktree_when_base_missing(
        self, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=1)
        runner.queue(exit_code=0)

        git.create_worktree_new(WORKTREE_DIR, BRANCH, BASE_BRANCH, CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "--orphan",
            "-b",
            BRANCH,
            str(WORKTREE_DIR),
        )

    def test_raises_worktree_creation_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_new(WORKTREE_DIR, BRANCH, BASE_BRANCH, CWD, runner=runner)


class TestGitCommonDir:
    def test_resolves_relative_output_against_path(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=".git\n")

        result = git.git_common_dir(CWD, runner=runner)

        assert runner.last_call.args == ("git", "rev-parse", "--git-common-dir")
        assert runner.last_call.cwd == CWD
        assert result == (CWD / ".git").resolve()

    def test_returns_absolute_output_as_is(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout="/workspace/.git\n")

        result = git.git_common_dir(WORKTREE_DIR, runner=runner)

        assert result == Path("/workspace/.git").resolve()

    def test_returns_none_outside_a_repository(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 128

        assert git.git_common_dir(CWD, runner=runner) is None


class TestTryGetWorktreeDir:
    def test_returns_stripped_stdout_when_in_worktree(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=f"{WORKTREE_DIR}\n")

        result = git.try_get_worktree_dir(runner=runner)

        assert result == str(WORKTREE_DIR)

    def test_returns_none_when_not_in_worktree(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        result = git.try_get_worktree_dir(runner=runner)

        assert result is None


class TestGetWorktreeBranch:
    def test_returns_stripped_stdout(self, runner: FakeCommandRunner) -> None:
        runner.queue(stdout=f"{BRANCH}\n")

        result = git.get_worktree_branch(str(CWD), runner=runner)

        assert result == BRANCH


class TestRemoveWorktree:
    def test_builds_basic_remove_command(self, runner: FakeCommandRunner) -> None:
        git.remove_worktree(WORKTREE_DIR, cwd=CWD, runner=runner)

        assert runner.last_call.args == ("git", "worktree", "remove", str(WORKTREE_DIR))

    def test_passes_cwd(self, runner: FakeCommandRunner) -> None:
        git.remove_worktree(WORKTREE_DIR, cwd=CWD, runner=runner)

        assert runner.last_call.cwd == CWD

    def test_appends_force_flag_when_force(self, runner: FakeCommandRunner) -> None:
        git.remove_worktree(WORKTREE_DIR, force=True, cwd=CWD, runner=runner)

        assert runner.last_call.args == (
            "git",
            "worktree",
            "remove",
            "--force",
            str(WORKTREE_DIR),
        )

    def test_raises_worktree_removal_error_on_failure(self, runner: FakeCommandRunner) -> None:
        runner.default_exit_code = 1

        with pytest.raises(WorktreeRemovalError):
            git.remove_worktree(WORKTREE_DIR, cwd=CWD, runner=runner)
