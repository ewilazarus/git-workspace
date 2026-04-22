from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.prune import prune
from git_workspace.cli.commands.remove import remove
from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_inline_command_runs_as_shell(workspace_with_inline_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_inline_hooks.dir))
    assert (workspace_with_inline_hooks.dir / ".inline-hook-ran").exists()


def test_on_setup_hook_runs_on_first_up(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert (workspace_with_hooks.dir / ".hook-on-setup").exists()


def test_on_setup_hook_does_not_run_on_subsequent_up(
    workspace_with_hooks: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    marker = workspace_with_hooks.dir / ".hook-on-setup"
    marker.unlink()
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert not marker.exists()


def test_on_activate_hook_runs_on_every_up(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    runs = (workspace_with_hooks.dir / ".hook-on-activate-runs").read_text()
    assert runs.count("ran") == 2


def test_on_attach_hook_runs_when_not_detached(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir), detached=False)
    assert (workspace_with_hooks.dir / ".hook-on-attach").exists()


def test_on_attach_hook_skipped_when_detached(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir), detached=True)
    assert not (workspace_with_hooks.dir / ".hook-on-attach").exists()


def test_on_deactivate_hook_runs_on_down(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    down(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert (workspace_with_hooks.dir / ".hook-on-deactivate").exists()


def test_on_setup_hook_runs_on_reset(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    marker = workspace_with_hooks.dir / ".hook-on-setup"
    marker.unlink()
    reset(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert marker.exists()


def test_on_deactivate_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    remove(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert (workspace_with_hooks.dir / ".hook-on-deactivate").exists()


def test_on_remove_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    remove(branch="main", workspace_dir=str(workspace_with_hooks.dir))
    assert (workspace_with_hooks.dir / ".hook-on-remove").exists()


def test_hooks_do_not_run_on_prune(workspace_with_hooks: Workspace) -> None:
    up(branch="feat", workspace_dir=str(workspace_with_hooks.dir))
    prune(root=str(workspace_with_hooks.dir), older_than_days=-1, dry_run=False)
    assert not (workspace_with_hooks.dir / ".hook-on-deactivate").exists()
    assert not (workspace_with_hooks.dir / ".hook-on-remove").exists()
