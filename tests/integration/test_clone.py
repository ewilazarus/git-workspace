"""Integration tests for the clone command."""
import subprocess
from pathlib import Path

from tests.integration.helpers import run, git_init, git_add, git_commit


def _make_source_repo(path: Path) -> Path:
    """Create a local git repo with a commit to serve as a clone source."""
    path.mkdir(parents=True, exist_ok=True)
    git_init(path)
    (path / "README").write_text("source repo\n")
    git_add(path, "README")
    git_commit(path, "initial commit")
    return path


def _make_config_repo(path: Path) -> Path:
    """Create a minimal local git repo to use as a --config-url."""
    path.mkdir(parents=True, exist_ok=True)
    git_init(path)
    (path / "manifest.toml").write_text('version = 1\nbase_branch = "main"\n')
    git_add(path, "manifest.toml")
    git_commit(path, "init config")
    return path


def test_clone_creates_git_and_workspace_dirs(tmp_path: Path) -> None:
    source = _make_source_repo(tmp_path / "source")
    config = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    result = run("clone", str(source), str(target), f"--config-url={config}")

    assert result.ok, result.stderr
    assert (target / ".git").is_dir()
    assert (target / ".workspace").is_dir()


def test_clone_git_dir_is_bare(tmp_path: Path) -> None:
    source = _make_source_repo(tmp_path / "source")
    config = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    run("clone", str(source), str(target), f"--config-url={config}")

    bare_result = subprocess.run(
        ["git", "rev-parse", "--is-bare-repository"],
        cwd=str(target / ".git"),
        capture_output=True,
        text=True,
    )
    assert bare_result.stdout.strip() == "true"


def test_clone_workspace_contains_manifest(tmp_path: Path) -> None:
    source = _make_source_repo(tmp_path / "source")
    config = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    run("clone", str(source), str(target), f"--config-url={config}")

    assert (target / ".workspace" / "manifest.toml").is_file()


def test_clone_infers_directory_from_url(tmp_path: Path) -> None:
    # Source repo lives outside tmp_path so the inferred name doesn't collide
    import tempfile
    with tempfile.TemporaryDirectory() as remote_dir:
        source = _make_source_repo(Path(remote_dir) / "myproject")
        config = _make_config_repo(tmp_path / "config")

        result = run("clone", str(source), f"--config-url={config}", cwd=tmp_path)

    assert result.ok, result.stderr
    assert (tmp_path / "myproject" / ".git").is_dir()


def test_clone_uses_explicit_directory(tmp_path: Path) -> None:
    source = _make_source_repo(tmp_path / "source")
    config = _make_config_repo(tmp_path / "config")
    explicit_target = tmp_path / "custom-name"

    result = run("clone", str(source), str(explicit_target), f"--config-url={config}")

    assert result.ok, result.stderr
    assert (explicit_target / ".git").is_dir()


def test_clone_fails_with_invalid_url(tmp_path: Path) -> None:
    config = _make_config_repo(tmp_path / "config")

    result = run("clone", "/nonexistent/repo", str(tmp_path / "workspace"), f"--config-url={config}")

    assert not result.ok
    assert result.returncode != 0


def test_cloned_workspace_is_valid_for_up(tmp_path: Path) -> None:
    source = _make_source_repo(tmp_path / "source")
    config = _make_config_repo(tmp_path / "config")
    target = tmp_path / "workspace"

    run("clone", str(source), str(target), f"--config-url={config}")

    # Write a proper manifest so up can work
    (target / ".workspace" / "manifest.toml").write_text(
        'version = 1\nbase_branch = "main"\n'
    )

    result = run("up", "feat/test", "-r", str(target))

    assert result.ok, result.stderr
    assert (target / "feat" / "test").is_dir()
