import json
from pathlib import Path

import pytest

from git_workspace.errors import (
    ProviderError,
    ProviderUnavailableError,
    WorktreeAlreadyExistsError,
    WorktreeCreationError,
    WorktreeNotFoundError,
    WorktreeRemovalError,
)
from git_workspace.providers.base import WorktreeProvider
from git_workspace.providers.herdr import HerdrWorktreeProvider
from git_workspace.workspace.models import ProviderKind, WorktreeRequest
from tests.helpers import FakeCommandRunner

HERDR = "/fake/herdr"
BRANCH = "feature/x"
BASE_BRANCH = "main"


@pytest.fixture
def runner() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture
def provider(runner: FakeCommandRunner) -> HerdrWorktreeProvider:
    return HerdrWorktreeProvider(runner, executable=HERDR)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    d = tmp_path / "repo"
    d.mkdir()
    return d


def entry(path: Path, branch: str = BRANCH, workspace_id: str | None = None) -> dict:
    data = {
        "branch": branch,
        "is_bare": False,
        "is_detached": False,
        "is_linked_worktree": True,
        "is_prunable": False,
        "label": "repo",
        "path": str(path),
    }
    if workspace_id:
        data["open_workspace_id"] = workspace_id
    return data


def list_payload(repo: Path, *entries: dict) -> str:
    return json.dumps(
        {
            "id": "cli:worktree:list",
            "result": {
                "source": {"repo_root": str(repo), "repo_key": str(repo / ".git")},
                "type": "worktree_list",
                "worktrees": [
                    {"is_bare": True, "is_linked_worktree": False, "path": str(repo)},
                    *entries,
                ],
            },
        }
    )


def created_payload(path: Path, branch: str, workspace_id: str) -> str:
    return json.dumps(
        {
            "id": "cli:worktree:create",
            "result": {
                "type": "worktree_created",
                "workspace": {"workspace_id": workspace_id, "label": path.name},
                "worktree": entry(path, branch, workspace_id),
            },
        }
    )


def error_payload(code: str, message: str = "boom") -> str:
    return json.dumps({"error": {"code": code, "message": message}, "id": "cli:x"})


class TestProtocol:
    def test_satisfies_worktree_provider_protocol(self, provider: HerdrWorktreeProvider) -> None:
        assert isinstance(provider, WorktreeProvider)

    def test_kind_is_herdr(self, provider: HerdrWorktreeProvider) -> None:
        assert provider.kind is ProviderKind.HERDR

    def test_is_available_with_executable(self, provider: HerdrWorktreeProvider) -> None:
        assert provider.is_available() is True

    def test_is_unavailable_without_executable(
        self, runner: FakeCommandRunner, mocker, monkeypatch
    ) -> None:
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value=None)

        assert HerdrWorktreeProvider(runner).is_available() is False

    def test_operations_raise_when_unavailable(
        self, runner: FakeCommandRunner, mocker, repo: Path
    ) -> None:
        mocker.patch("git_workspace.subprocesses.herdr.shutil.which", return_value=None)

        with pytest.raises(ProviderUnavailableError):
            HerdrWorktreeProvider(runner).list(repo)


class TestCreate:
    def test_creates_and_records_workspace_id(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        target = repo / BRANCH
        runner.queue(stdout=list_payload(repo))
        runner.queue(stdout=created_payload(target, BRANCH, "w8"))

        result = provider.create(
            WorktreeRequest(
                repository_path=repo, branch=BRANCH, base_branch=BASE_BRANCH, target_path=target
            )
        )

        assert runner.last_call.args == (
            HERDR,
            "worktree",
            "create",
            "--cwd",
            str(repo.resolve()),
            "--branch",
            BRANCH,
            "--path",
            str(target.resolve()),
            "--base",
            BASE_BRANCH,
            "--no-focus",
            "--json",
        )
        assert result.provider_kind is ProviderKind.HERDR
        assert result.provider_id == "w8"
        assert result.metadata == {"workspace_id": "w8"}
        assert result.branch == BRANCH

    def test_never_focuses(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        target = repo / BRANCH
        runner.queue(stdout=list_payload(repo))
        runner.queue(stdout=created_payload(target, BRANCH, "w8"))

        provider.create(WorktreeRequest(repository_path=repo, branch=BRANCH, target_path=target))

        assert "--no-focus" in runner.last_call.args
        assert not any("focus" == arg for call in runner.calls for arg in call.args)

    def test_raises_when_target_already_registered(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        target = repo / BRANCH
        runner.queue(stdout=list_payload(repo, entry(target)))

        with pytest.raises(WorktreeAlreadyExistsError):
            provider.create(
                WorktreeRequest(repository_path=repo, branch="other", target_path=target)
            )

    def test_wraps_herdr_failure(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        runner.queue(stdout=list_payload(repo))
        runner.queue(stdout=error_payload("worktree_create_failed"))

        with pytest.raises(WorktreeCreationError):
            provider.create(
                WorktreeRequest(repository_path=repo, branch=BRANCH, target_path=repo / BRANCH)
            )


class TestList:
    def test_skips_bare_and_unbranched_entries(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        runner.queue(stdout=list_payload(repo, entry(wt, workspace_id="w3")))

        result = provider.list(repo)

        assert len(result) == 1
        assert result[0].worktree_path == wt.resolve()
        assert result[0].metadata == {"workspace_id": "w3"}

    def test_requires_repository_path(self, provider: HerdrWorktreeProvider) -> None:
        with pytest.raises(WorktreeNotFoundError):
            provider.list(None)

    def test_wraps_herdr_failure(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        runner.queue(stdout="garbage output")

        with pytest.raises(ProviderError):
            provider.list(repo)


class TestFindAndImport:
    def test_finds_by_canonical_path(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo, entry(wt)))

        result = provider.find(wt / "sub" / "..")

        assert result is not None
        assert result.worktree_path == wt.resolve()

    def test_find_returns_none_for_missing_directory(
        self, provider: HerdrWorktreeProvider, tmp_path: Path
    ) -> None:
        assert provider.find(tmp_path / "missing") is None

    def test_find_returns_none_outside_git(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, tmp_path: Path
    ) -> None:
        runner.queue(exit_code=0, stdout=error_payload("not_git_worktree"))

        assert provider.find(tmp_path) is None

    def test_import_existing_is_idempotent(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo, entry(wt)))
        runner.queue(stdout=list_payload(repo, entry(wt)))

        assert provider.import_existing(wt) == provider.import_existing(wt)

    def test_import_existing_raises_for_unregistered(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        stranger = repo / "stranger"
        stranger.mkdir()
        runner.queue(stdout=list_payload(repo))

        with pytest.raises(WorktreeNotFoundError):
            provider.import_existing(stranger)


class TestRemove:
    def test_removes_through_herdr_when_workspace_open(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo, entry(wt, workspace_id="w8")))  # find
        runner.queue(stdout=json.dumps({"result": {"type": "worktree_removed"}}))

        provider.remove(provider_worktree(repo, wt), force=True)

        assert runner.last_call.args == (
            HERDR,
            "worktree",
            "remove",
            "--workspace",
            "w8",
            "--force",
            "--json",
        )

    def test_falls_back_to_git_when_not_presented(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo, entry(wt)))  # find: no workspace id

        provider.remove(provider_worktree(repo, wt))

        assert runner.last_call.args == ("git", "worktree", "remove", str(wt.resolve()))

    def test_reports_partial_failure_when_worktree_survives(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo, entry(wt, workspace_id="w8")))  # find
        runner.queue(stdout=error_payload("remove_failed"))  # herdr remove fails
        runner.queue(stdout=list_payload(repo))  # re-find: no longer registered

        with pytest.raises(WorktreeRemovalError, match="still exists"):
            provider.remove(provider_worktree(repo, wt))

    def test_raises_for_unregistered_worktree(
        self, provider: HerdrWorktreeProvider, runner: FakeCommandRunner, repo: Path
    ) -> None:
        wt = repo / BRANCH
        wt.mkdir(parents=True)
        runner.queue(stdout=list_payload(repo))

        with pytest.raises(WorktreeNotFoundError):
            provider.remove(provider_worktree(repo, wt))


def provider_worktree(repo: Path, wt: Path):
    from git_workspace.workspace.models import ManagedWorktree

    return ManagedWorktree(
        repository_path=repo,
        worktree_path=wt,
        branch=BRANCH,
        provider_kind=ProviderKind.HERDR,
    )
