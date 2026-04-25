import os
import shutil
import subprocess
from pathlib import Path
from typing import Protocol

import pytest

from git_workspace.workspace import Workspace

FIXTURES_DIR = Path(__file__).parent / "fixtures"

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "fixture",
    "GIT_AUTHOR_EMAIL": "fixture@test.com",
    "GIT_COMMITTER_NAME": "fixture",
    "GIT_COMMITTER_EMAIL": "fixture@test.com",
}


class Setup(Protocol):
    def __call__(self, *, config: str = "minimal") -> None: ...


def _setup_fixture(tmp_path: Path, fixture_subpath: str) -> None:
    source = FIXTURES_DIR / fixture_subpath
    target = tmp_path / fixture_subpath

    # Copy fixture to tmp path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)

    # Rename dotgit to .git
    dotgit = target / "dotgit"
    dotgit.rename(target / ".git")

    # Commit any untracked fixture files so they are present when cloned
    subprocess.run(["git", "add", "."], cwd=target, capture_output=True, env=_GIT_ENV)
    subprocess.run(
        ["git", "commit", "--amend", "--no-edit", "--allow-empty"],
        cwd=target,
        capture_output=True,
        env=_GIT_ENV,
    )


@pytest.fixture
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Setup:
    monkeypatch.chdir(tmp_path)

    def _setup(*, config: str = "minimal") -> None:
        _setup_fixture(tmp_path, "repo")
        _setup_fixture(tmp_path, f"configs/{config}")

    return _setup


@pytest.fixture
def workspace(setup: Setup, tmp_path: Path) -> Workspace:
    setup()
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )


@pytest.fixture
def workspace_with_links(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-links")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-links"),
    )


@pytest.fixture
def workspace_with_copies(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-copies")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-copies"),
    )


@pytest.fixture
def workspace_with_hooks(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-hooks")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-hooks"),
    )


@pytest.fixture
def workspace_with_inline_hooks(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-inline-hooks")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-inline-hooks"),
    )


@pytest.fixture
def workspace_with_vars(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-vars")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-vars"),
    )


@pytest.fixture
def workspace_with_non_overwrite_copies(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-non-overwrite-copies")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-non-overwrite-copies"),
    )


@pytest.fixture
def workspace_with_placeholder_copies(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-placeholder-copies")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-placeholder-copies"),
    )


@pytest.fixture
def workspace_with_prune(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-prune")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-prune"),
    )


@pytest.fixture
def workspace_with_fingerprints(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-fingerprints")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-fingerprints"),
    )


@pytest.fixture
def workspace_with_adaptive_hooks(setup: Setup, tmp_path: Path) -> Workspace:
    setup(config="with-adaptive-hooks")
    return Workspace.clone(
        workspace_dir=str(tmp_path / "workspace"),
        url=str(tmp_path / "repo"),
        config_url=str(tmp_path / "configs" / "with-adaptive-hooks"),
    )
