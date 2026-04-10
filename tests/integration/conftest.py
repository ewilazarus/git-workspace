"""Integration test fixtures (auto-discovered by pytest)."""
from pathlib import Path

import pytest

from tests.integration.helpers import git_add, git_commit, git_config, git_init


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """
    Provide an isolated temporary Git repository that is also a valid workspace.

    Each test gets its own fresh repository under tmp_path with:
    - A valid Git config (user name/email)
    - One initial commit on main
    - A .workspace/ directory (making it a valid workspace root)
    """
    git_init(tmp_path)
    (tmp_path / "README").write_text("workspace\n")
    git_add(tmp_path, "README")
    git_commit(tmp_path, "initial commit")
    workspace_dir = tmp_path / ".workspace"
    workspace_dir.mkdir()
    (workspace_dir / "manifest.toml").write_text('version = 1\nbase_branch = "main"\n')
    return tmp_path
