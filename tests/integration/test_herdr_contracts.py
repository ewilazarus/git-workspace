import subprocess
from pathlib import Path

import pytest

from git_workspace.presenters.herdr import HerdrPresenter
from git_workspace.providers.herdr import HerdrWorktreeProvider
from git_workspace.subprocesses.runner import SubprocessCommandRunner
from git_workspace.workspace.models import ManagedWorktree, ProviderKind
from tests.contracts.presenter import WorkspacePresenterContract
from tests.contracts.provider import WorktreeProviderContract
from tests.integration.conftest import _GIT_ENV

FAKE_HERDR = Path(__file__).parent / "fixtures" / "fake_herdr.py"


@pytest.fixture
def fake_herdr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("FAKE_HERDR_STATE", str(tmp_path / "fake-herdr-state.json"))
    return str(FAKE_HERDR)


@pytest.fixture
def herdr_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"], cwd=repo, capture_output=True, env=_GIT_ENV, check=True
    )
    (repo / "README.md").write_text("herdr contract fixture\n")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, env=_GIT_ENV, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=repo,
        capture_output=True,
        env=_GIT_ENV,
        check=True,
    )
    return repo


class TestHerdrProviderContract(WorktreeProviderContract):
    @pytest.fixture
    def provider(self, fake_herdr: str) -> HerdrWorktreeProvider:
        return HerdrWorktreeProvider(SubprocessCommandRunner(), executable=fake_herdr)

    @pytest.fixture
    def repo(self, herdr_repo: Path) -> Path:
        return herdr_repo


class TestHerdrPresenterContract(WorkspacePresenterContract):
    @pytest.fixture
    def presenter(self, fake_herdr: str) -> HerdrPresenter:
        return HerdrPresenter(SubprocessCommandRunner(), executable=fake_herdr)

    @pytest.fixture
    def worktree(self, herdr_repo: Path) -> ManagedWorktree:
        worktree_path = herdr_repo / "worktrees" / "presented"
        subprocess.run(
            ["git", "worktree", "add", "-b", "contract/presented", str(worktree_path)],
            cwd=herdr_repo,
            capture_output=True,
            env=_GIT_ENV,
            check=True,
        )
        return ManagedWorktree(
            repository_path=herdr_repo,
            worktree_path=worktree_path,
            branch="contract/presented",
            provider_kind=ProviderKind.HERDR,
        )
