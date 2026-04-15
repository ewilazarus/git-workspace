import pytest

from git_workspace.cli.commands.up import up
from git_workspace.cli.commands.reset import reset
from git_workspace.errors import WorkspaceLinkError
from git_workspace.workspace import Workspace


def test_non_override_link_creates_symlink(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    assert (workspace_with_links.dir / "main" / ".dotfile").is_symlink()


def test_non_override_symlink_points_to_asset(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / ".dotfile"
    expected_source = (workspace_with_links.paths.assets / "dotfile").resolve()
    assert link.resolve() == expected_source


def test_override_link_creates_symlink(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    assert (workspace_with_links.dir / "main" / "settings.json").is_symlink()


def test_override_symlink_points_to_asset(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / "settings.json"
    expected_source = (workspace_with_links.paths.assets / "settings.json").resolve()
    assert link.resolve() == expected_source


def test_non_override_link_is_added_to_exclude_file(
    workspace_with_links: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    exclude_content = workspace_with_links.paths.ignore_file.read_text()
    expected_path = str((workspace_with_links.dir / "main" / ".dotfile").absolute())
    assert expected_path in exclude_content


def test_override_link_is_not_added_to_exclude_file(
    workspace_with_links: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    exclude_content = workspace_with_links.paths.ignore_file.read_text()
    settings_path = str(
        (workspace_with_links.dir / "main" / "settings.json").absolute()
    )
    assert settings_path not in exclude_content


def test_links_applied_across_multiple_worktrees(
    workspace_with_links: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    up(
        branch="feature/other",
        base_branch="main",
        workspace_dir=str(workspace_with_links.dir),
    )
    assert (workspace_with_links.dir / "main" / ".dotfile").is_symlink()
    assert (workspace_with_links.dir / "feature" / "other" / ".dotfile").is_symlink()


def test_reset_reapplies_non_override_link(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / ".dotfile"
    link.unlink()
    assert not link.exists()
    reset(branch="main", workspace_dir=str(workspace_with_links.dir))
    assert link.is_symlink()


def test_reset_reapplies_override_link(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / "settings.json"
    link.unlink()
    assert not link.exists()
    reset(branch="main", workspace_dir=str(workspace_with_links.dir))
    assert link.is_symlink()


def test_cannot_link_to_existing_file(workspace_with_links: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / ".dotfile"
    link.unlink()
    link.write_text("i am a real file")
    with pytest.raises(WorkspaceLinkError):
        reset(branch="main", workspace_dir=str(workspace_with_links.dir))


def test_cannot_link_to_symlink_pointing_elsewhere(
    workspace_with_links: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_links.dir))
    link = workspace_with_links.dir / "main" / ".dotfile"
    link.unlink()
    other = workspace_with_links.dir / "other-target"
    other.write_text("other")
    link.symlink_to(other)
    with pytest.raises(WorkspaceLinkError):
        reset(branch="main", workspace_dir=str(workspace_with_links.dir))
