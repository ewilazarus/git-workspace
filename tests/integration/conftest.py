"""Integration test fixtures (auto-discovered by pytest)."""
from pathlib import Path

import pytest

from tests.integration.helpers import git_add, git_commit, git_config, git_init


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """
    Provide an isolated temporary Git repository with an initial commit.

    Each test gets its own fresh repository under tmp_path. The repository
    has Git user config set and one initial commit on main.
    """
    git_init(tmp_path)
    (tmp_path / "README").write_text("workspace\n")
    git_add(tmp_path, "README")
    git_commit(tmp_path, "initial commit")
    return tmp_path
