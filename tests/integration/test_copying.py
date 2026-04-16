from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_non_override_copy_creates_file(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / ".dotfile"
    assert target.exists()
    assert not target.is_symlink()


def test_non_override_copy_has_correct_content(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / ".dotfile"
    source = workspace_with_copies.paths.assets / "dotfile"
    assert target.read_text() == source.read_text()


def test_override_copy_creates_file(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / "settings.json"
    assert target.exists()
    assert not target.is_symlink()


def test_override_copy_has_correct_content(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / "settings.json"
    source = workspace_with_copies.paths.assets / "settings.json"
    assert target.read_text() == source.read_text()


def test_non_override_copy_is_added_to_exclude_file(
    workspace_with_copies: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    exclude_content = workspace_with_copies.paths.ignore_file.read_text()
    assert ".dotfile" in exclude_content


def test_override_copy_is_not_added_to_exclude_file(
    workspace_with_copies: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    exclude_content = workspace_with_copies.paths.ignore_file.read_text()
    settings_path = str((workspace_with_copies.dir / "main" / "settings.json").absolute())
    assert settings_path not in exclude_content


def test_copies_applied_across_multiple_worktrees(
    workspace_with_copies: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    up(
        branch="feature/other",
        base_branch="main",
        workspace_dir=str(workspace_with_copies.dir),
    )
    assert (workspace_with_copies.dir / "main" / ".dotfile").exists()
    assert (workspace_with_copies.dir / "feature" / "other" / ".dotfile").exists()


def test_reset_reapplies_non_override_copy(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / ".dotfile"
    target.unlink()
    assert not target.exists()
    reset(branch="main", workspace_dir=str(workspace_with_copies.dir))
    assert target.exists()


def test_reset_reapplies_override_copy(workspace_with_copies: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / "settings.json"
    target.unlink()
    assert not target.exists()
    reset(branch="main", workspace_dir=str(workspace_with_copies.dir))
    assert target.exists()


def test_reset_overwrites_modified_copy(
    workspace_with_copies: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / ".dotfile"
    source = workspace_with_copies.paths.assets / "dotfile"
    target.write_text("modified by user")
    reset(branch="main", workspace_dir=str(workspace_with_copies.dir))
    assert target.read_text() == source.read_text()


def test_copy_is_independent_of_source(workspace_with_copies: Workspace) -> None:
    """Modifying the copied file does not affect the source asset."""
    up(branch="main", workspace_dir=str(workspace_with_copies.dir))
    target = workspace_with_copies.dir / "main" / ".dotfile"
    source = workspace_with_copies.paths.assets / "dotfile"
    original_content = source.read_text()
    target.write_text("modified")
    assert source.read_text() == original_content
