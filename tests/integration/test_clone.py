import subprocess
from pathlib import Path

from conftest import Setup

from git_workspace.cli.commands.clone import clone


def test_creates_git_directory(setup: Setup, tmp_path: Path) -> None:
    setup()
    clone(
        url=str(tmp_path / "repo"),
        workspace_dir=str(tmp_path / "workspace"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )
    assert (tmp_path / "workspace" / ".git").is_dir()


def test_creates_config_directory(setup: Setup, tmp_path: Path) -> None:
    setup()
    clone(
        url=str(tmp_path / "repo"),
        workspace_dir=str(tmp_path / "workspace"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )
    assert (tmp_path / "workspace" / ".workspace").is_dir()


def test_creates_manifest_file(setup: Setup, tmp_path: Path) -> None:
    setup()
    clone(
        url=str(tmp_path / "repo"),
        workspace_dir=str(tmp_path / "workspace"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )
    assert (tmp_path / "workspace" / ".workspace" / "manifest.toml").is_file()


def test_git_repository_is_bare(setup: Setup, tmp_path: Path) -> None:
    setup()
    clone(
        url=str(tmp_path / "repo"),
        workspace_dir=str(tmp_path / "workspace"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )
    git_config = (tmp_path / "workspace" / ".git" / "config").read_text()
    assert "bare = true" in git_config


def test_clones_repository_history(setup: Setup, tmp_path: Path) -> None:
    setup()
    clone(
        url=str(tmp_path / "repo"),
        workspace_dir=str(tmp_path / "workspace"),
        config_url=str(tmp_path / "configs" / "minimal"),
    )
    result = subprocess.run(
        ["git", "branch", "--list", "main"],
        cwd=str(tmp_path / "workspace"),
        capture_output=True,
        text=True,
    )
    assert "main" in result.stdout
