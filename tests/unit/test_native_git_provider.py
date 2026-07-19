from pathlib import Path
from typing import Any

import pytest

from git_workspace.errors import (
    WorktreeAlreadyExistsError,
    WorktreeCreationError,
    WorktreeNotFoundError,
)
from git_workspace.providers.base import WorktreeProvider
from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.workspace.models import ManagedWorktree, ProviderKind, WorktreeRequest
from tests.helpers import FakeCommandRunner

BRANCH = "feat/GWS-001"
BASE_BRANCH = "main"
REPO = Path("/workspace")
TARGET = Path("/workspace/feat/GWS-001")
COMMIT_SHA = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture
def provider(runner: FakeCommandRunner) -> NativeGitProvider:
    return NativeGitProvider(runner)


def request(**overrides) -> WorktreeRequest:
    defaults: dict[str, Any] = {
        "repository_path": REPO,
        "branch": BRANCH,
        "base_branch": BASE_BRANCH,
        "target_path": TARGET,
    }
    defaults.update(overrides)
    return WorktreeRequest(**defaults)


def porcelain(directory: Path = TARGET, branch: str = BRANCH) -> str:
    return f"worktree {directory}\nHEAD {COMMIT_SHA}\nbranch refs/heads/{branch}"


class TestProtocol:
    def test_satisfies_worktree_provider_protocol(self, provider: NativeGitProvider) -> None:
        assert isinstance(provider, WorktreeProvider)

    def test_kind_is_native_git(self, provider: NativeGitProvider) -> None:
        assert provider.kind is ProviderKind.NATIVE_GIT

    def test_is_available_when_git_on_path(self, provider: NativeGitProvider, mocker) -> None:
        mocker.patch("git_workspace.providers.native_git.shutil.which", return_value="/usr/bin/git")

        assert provider.is_available() is True

    def test_is_unavailable_without_git(self, provider: NativeGitProvider, mocker) -> None:
        mocker.patch("git_workspace.providers.native_git.shutil.which", return_value=None)

        assert provider.is_available() is False


class TestCreate:
    def test_creates_from_local_branch_when_it_exists(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list: no conflict
        runner.queue(exit_code=0)  # local branch exists

        result = provider.create(request())

        assert runner.calls[1].args == (
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/heads/{BRANCH}",
        )
        assert runner.last_call.args == ("git", "worktree", "add", str(TARGET), BRANCH)
        assert runner.last_call.cwd == REPO
        assert result == ManagedWorktree(
            repository_path=REPO,
            worktree_path=TARGET,
            branch=BRANCH,
            provider_kind=ProviderKind.NATIVE_GIT,
        )

    def test_creates_tracking_worktree_from_remote_branch(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=0)  # fetch
        runner.queue(exit_code=0)  # remote branch exists

        provider.create(request())

        assert runner.calls[2].args == ("git", "fetch", "origin", "--prune")
        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "--track",
            "-b",
            BRANCH,
            str(TARGET),
            f"origin/{BRANCH}",
        )

    def test_creates_new_branch_preferring_remote_base(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=0)  # fetch
        runner.queue(exit_code=1)  # remote branch missing
        runner.queue(exit_code=0)  # remote base exists

        provider.create(request())

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "-b",
            BRANCH,
            str(TARGET),
            f"origin/{BASE_BRANCH}",
        )

    def test_creates_new_branch_from_local_base_when_remote_base_missing(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=0)  # fetch
        runner.queue(exit_code=1)  # remote branch missing
        runner.queue(exit_code=1)  # remote base missing

        provider.create(request())

        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "-b",
            BRANCH,
            str(TARGET),
            BASE_BRANCH,
        )

    def test_skips_remote_branch_lookup_when_fetch_fails(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=1)  # fetch fails
        runner.queue(exit_code=1)  # remote base missing

        provider.create(request())

        assert runner.calls[3].args == (
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/remotes/origin/{BASE_BRANCH}",
        )
        assert runner.last_call.args == (
            "git",
            "worktree",
            "add",
            "-b",
            BRANCH,
            str(TARGET),
            BASE_BRANCH,
        )

    def test_raises_when_target_already_registered(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout=porcelain())

        with pytest.raises(WorktreeAlreadyExistsError):
            provider.create(request())

    def test_raises_when_branch_missing_and_creation_not_requested(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=0)  # fetch
        runner.queue(exit_code=1)  # remote branch missing

        with pytest.raises(WorktreeCreationError):
            provider.create(request(create_branch=False))

    def test_raises_when_base_branch_missing_for_new_branch(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=1)  # local branch missing
        runner.queue(exit_code=0)  # fetch
        runner.queue(exit_code=1)  # remote branch missing

        with pytest.raises(WorktreeCreationError):
            provider.create(request(base_branch=None))

    def test_derives_target_from_repository_and_branch_when_omitted(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout="")  # worktree list
        runner.queue(exit_code=0)  # local branch exists

        result = provider.create(request(target_path=None))

        assert result.worktree_path == (REPO / BRANCH).resolve()


class TestList:
    def test_parses_porcelain_into_managed_worktrees(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        runner.queue(exit_code=0, stdout=porcelain())

        result = provider.list(REPO)

        assert runner.last_call.args == ("git", "worktree", "list", "--porcelain")
        assert runner.last_call.cwd == REPO
        assert result == [
            ManagedWorktree(
                repository_path=REPO,
                worktree_path=TARGET,
                branch=BRANCH,
                provider_kind=ProviderKind.NATIVE_GIT,
            )
        ]

    def test_requires_a_repository_path(self, provider: NativeGitProvider) -> None:
        with pytest.raises(WorktreeNotFoundError):
            provider.list(None)


class TestFind:
    def test_returns_none_for_missing_directory(self, provider: NativeGitProvider) -> None:
        assert provider.find(Path("/nonexistent/worktree")) is None

    def test_returns_none_outside_a_repository(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        runner.queue(exit_code=128)

        assert provider.find(tmp_path) is None

    def test_finds_worktree_by_canonical_path(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        repo = tmp_path
        worktree_dir = tmp_path / "wt"
        worktree_dir.mkdir()
        runner.queue(exit_code=0, stdout=str(repo / ".git"))
        runner.queue(exit_code=0, stdout=porcelain(directory=worktree_dir))

        result = provider.find(worktree_dir)

        assert result is not None
        assert result.worktree_path == worktree_dir.resolve()
        assert result.repository_path == repo.resolve()

    def test_returns_none_when_path_not_registered(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        unregistered = tmp_path / "other"
        unregistered.mkdir()
        runner.queue(exit_code=0, stdout=str(tmp_path / ".git"))
        runner.queue(exit_code=0, stdout=porcelain(directory=tmp_path / "wt"))

        assert provider.find(unregistered) is None


class TestImportExisting:
    def test_returns_managed_worktree_when_registered(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        worktree_dir = tmp_path / "wt"
        worktree_dir.mkdir()
        runner.queue(exit_code=0, stdout=str(tmp_path / ".git"))
        runner.queue(exit_code=0, stdout=porcelain(directory=worktree_dir))

        result = provider.import_existing(worktree_dir)

        assert result.worktree_path == worktree_dir.resolve()

    def test_is_idempotent(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        worktree_dir = tmp_path / "wt"
        worktree_dir.mkdir()
        for _ in range(2):
            runner.queue(exit_code=0, stdout=str(tmp_path / ".git"))
            runner.queue(exit_code=0, stdout=porcelain(directory=worktree_dir))

        first = provider.import_existing(worktree_dir)
        second = provider.import_existing(worktree_dir)

        assert first == second

    def test_raises_for_unregistered_path(
        self, provider: NativeGitProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        runner.queue(exit_code=128)

        with pytest.raises(WorktreeNotFoundError):
            provider.import_existing(tmp_path)


class TestRemove:
    def worktree(self) -> ManagedWorktree:
        return ManagedWorktree(
            repository_path=REPO,
            worktree_path=TARGET,
            branch=BRANCH,
            provider_kind=ProviderKind.NATIVE_GIT,
        )

    def test_removes_without_force(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        provider.remove(self.worktree())

        assert runner.last_call.args == ("git", "worktree", "remove", str(TARGET))
        assert runner.last_call.cwd == REPO

    def test_removes_with_force(
        self, provider: NativeGitProvider, runner: FakeCommandRunner
    ) -> None:
        provider.remove(self.worktree(), force=True)

        assert runner.last_call.args == ("git", "worktree", "remove", "--force", str(TARGET))
