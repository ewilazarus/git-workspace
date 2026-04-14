from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

import git_workspace.git as git
from git_workspace.errors import (
    GitCloneError,
    GitFetchError,
    GitInitError,
    WorktreeCreationError,
    WorktreeListingError,
    WorktreeRemovalError,
)

URL = "https://github.com/user/repo.git"
BRANCH = "feat/GWS-001"
BASE_BRANCH = "main"
TARGET = Path("/target")
WORKTREE_DIR = Path("/workspace/feat/GWS-001")
CWD = Path("/workspace")
COMMIT_SHA = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


@pytest.fixture(autouse=True)
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.git.subprocess.run")
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    mock.return_value.stderr = ""
    return mock


class TestClone:
    def test_builds_basic_clone_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.clone(URL)

        assert mock_subprocess_run.call_args.args[0] == ["git", "clone", URL]

    def test_appends_target_when_provided(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.clone(URL, target=TARGET)

        assert mock_subprocess_run.call_args.args[0] == ["git", "clone", URL, TARGET]

    def test_appends_bare_flag_when_bare(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.clone(URL, bare=True)

        assert mock_subprocess_run.call_args.args[0] == ["git", "clone", "--bare", URL]

    def test_appends_branch_flags_when_provided(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.clone(URL, branch=BASE_BRANCH)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "clone", "-b", BASE_BRANCH, "--single-branch", URL,
        ]

    def test_raises_git_clone_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(GitCloneError):
            git.clone(URL)


class TestInit:
    def test_builds_init_command_with_target(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.init(TARGET, bare=False)

        assert mock_subprocess_run.call_args.args[0] == ["git", "init", TARGET]

    def test_appends_bare_flag_when_bare(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.init(TARGET, bare=True)

        assert mock_subprocess_run.call_args.args[0] == ["git", "init", "--bare", TARGET]

    def test_raises_git_init_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(GitInitError):
            git.init(TARGET, bare=False)


class TestListWorktrees:
    def test_builds_list_command_with_cwd(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.list_worktrees(CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "list", "--porcelain"
        ]
        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_returns_parsed_worktrees(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.stdout = (
            f"worktree {WORKTREE_DIR}\n"
            f"HEAD {COMMIT_SHA}\n"
            f"branch refs/heads/{BRANCH}"
        )

        result = git.list_worktrees(CWD)

        assert result == [
            {"directory": str(WORKTREE_DIR), "head": COMMIT_SHA, "branch": BRANCH}
        ]

    def test_returns_empty_list_when_no_matches(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.stdout = ""

        result = git.list_worktrees(CWD)

        assert result == []

    def test_raises_worktree_listing_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(WorktreeListingError):
            git.list_worktrees(CWD)


class TestFetchOrigin:
    def test_builds_fetch_command_with_cwd(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.fetch_origin(CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "fetch", "origin", "--prune"
        ]
        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_raises_git_fetch_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(GitFetchError):
            git.fetch_origin(CWD)


class TestLocalBranchExists:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.local_branch_exists(BRANCH, CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "rev-parse", "--verify", "--quiet", f"refs/heads/{BRANCH}"
        ]

    def test_returns_true_when_branch_exists(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 0

        assert git.local_branch_exists(BRANCH, CWD) is True

    def test_returns_false_when_branch_not_found(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        assert git.local_branch_exists(BRANCH, CWD) is False


class TestRemoteBranchExists:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.remote_branch_exists(BRANCH, CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{BRANCH}"
        ]

    def test_returns_true_when_branch_exists(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 0

        assert git.remote_branch_exists(BRANCH, CWD) is True

    def test_returns_false_when_branch_not_found(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        assert git.remote_branch_exists(BRANCH, CWD) is False


class TestSkipWorktree:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.skip_worktree(TARGET)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "update-index", "--skip-worktree", TARGET
        ]

    def test_does_not_raise_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        git.skip_worktree(TARGET)


class TestCreateWorktreeFromLocalBranch:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.create_worktree_from_local_branch(WORKTREE_DIR, BRANCH, CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "add", WORKTREE_DIR, BRANCH
        ]
        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_raises_worktree_creation_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_from_local_branch(WORKTREE_DIR, BRANCH, CWD)


class TestCreateWorktreeFromRemoteBranch:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.create_worktree_from_remote_branch(WORKTREE_DIR, BRANCH, CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "add", "--track", "-b", BRANCH, WORKTREE_DIR, f"origin/{BRANCH}",
        ]
        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_raises_worktree_creation_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_from_remote_branch(WORKTREE_DIR, BRANCH, CWD)


class TestCreateWorktreeNew:
    def test_builds_correct_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.create_worktree_new(WORKTREE_DIR, BRANCH, BASE_BRANCH, CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "add", "-b", BRANCH, WORKTREE_DIR, BASE_BRANCH,
        ]
        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_raises_worktree_creation_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(WorktreeCreationError):
            git.create_worktree_new(WORKTREE_DIR, BRANCH, BASE_BRANCH, CWD)


class TestTryGetWorktreeDir:
    def test_returns_stripped_stdout_when_in_worktree(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.stdout = f"{WORKTREE_DIR}\n"

        result = git.try_get_worktree_dir()

        assert result == str(WORKTREE_DIR)

    def test_returns_none_when_not_in_worktree(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        result = git.try_get_worktree_dir()

        assert result is None


class TestGetWorktreeBranch:
    def test_returns_stripped_stdout(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.stdout = f"{BRANCH}\n"

        result = git.get_worktree_branch(str(CWD))

        assert result == BRANCH


class TestRemoveWorktree:
    def test_builds_basic_remove_command(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.remove_worktree(WORKTREE_DIR, cwd=CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "remove", WORKTREE_DIR
        ]

    def test_passes_cwd(self, mock_subprocess_run: MagicMock) -> None:
        git.remove_worktree(WORKTREE_DIR, cwd=CWD)

        assert mock_subprocess_run.call_args.kwargs["cwd"] == CWD

    def test_appends_force_flag_when_force(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        git.remove_worktree(WORKTREE_DIR, force=True, cwd=CWD)

        assert mock_subprocess_run.call_args.args[0] == [
            "git", "worktree", "remove", "--force", WORKTREE_DIR
        ]

    def test_raises_worktree_removal_error_on_failure(
        self, mock_subprocess_run: MagicMock
    ) -> None:
        mock_subprocess_run.return_value.returncode = 1

        with pytest.raises(WorktreeRemovalError):
            git.remove_worktree(WORKTREE_DIR, cwd=CWD)
