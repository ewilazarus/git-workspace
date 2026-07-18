import subprocess
from pathlib import Path

import pytest

from git_workspace.providers.native_git import NativeGitProvider
from git_workspace.subprocesses.runner import SubprocessCommandRunner
from tests.contracts.provider import WorktreeProviderContract
from tests.integration.conftest import _GIT_ENV


class TestNativeGitProviderContract(WorktreeProviderContract):
    @pytest.fixture
    def provider(self) -> NativeGitProvider:
        return NativeGitProvider(SubprocessCommandRunner())

    @pytest.fixture
    def repo(self, tmp_path: Path) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=repo, capture_output=True, env=_GIT_ENV, check=True
        )
        (repo / "README.md").write_text("contract fixture\n")
        subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, env=_GIT_ENV, check=True)
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=repo,
            capture_output=True,
            env=_GIT_ENV,
            check=True,
        )
        return repo
