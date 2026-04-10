"""Integration tests for the init command."""
import subprocess
from pathlib import Path

from tests.integration.helpers import run, git_init, git_add, git_commit


def _make_config_repo(path: Path) -> Path:
    """Create a minimal local git repo to use as a --config-url."""
    path.mkdir(parents=True, exist_ok=True)
    git_init(path)
    (path / "manifest.toml").write_text('version = 1\nbase_branch = "main"\n')
    git_add(path, "manifest.toml")
    git_commit(path, "init config")
    return path


def test_init_creates_git_and_workspace_dirs(tmp_path: Path) -> None:
    config_repo = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    result = run("init", str(target), f"--config-url={config_repo}")

    assert result.ok, result.stderr
    assert (target / ".git").is_dir()
    assert (target / ".workspace").is_dir()


def test_init_git_dir_is_bare(tmp_path: Path) -> None:
    config_repo = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    run("init", str(target), f"--config-url={config_repo}")

    bare_result = subprocess.run(
        ["git", "rev-parse", "--is-bare-repository"],
        cwd=str(target / ".git"),
        capture_output=True,
        text=True,
    )
    assert bare_result.stdout.strip() == "true"


def test_init_workspace_contains_manifest(tmp_path: Path) -> None:
    config_repo = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    run("init", str(target), f"--config-url={config_repo}")

    assert (target / ".workspace" / "manifest.toml").is_file()


def test_init_defaults_to_cwd(tmp_path: Path) -> None:
    config_repo = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"
    target.mkdir()

    result = run("init", f"--config-url={config_repo}", cwd=target)

    assert result.ok, result.stderr
    assert (target / ".git").is_dir()
    assert (target / ".workspace").is_dir()


def test_init_fails_with_invalid_config_url(tmp_path: Path) -> None:
    target = tmp_path / "workspace"

    result = run("init", str(target), "--config-url=/nonexistent/path/to/config")

    assert not result.ok
    assert result.returncode != 0
