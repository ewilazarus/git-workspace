from git_workspace.cli.commands.up import up
from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.remove import remove
from git_workspace.workspace import Workspace


def test_on_setup_hook_runs_on_first_up(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert (workspace_with_hooks.directory / ".hook-on-setup").exists()


def test_on_setup_hook_does_not_run_on_subsequent_up(
    workspace_with_hooks: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    marker = workspace_with_hooks.directory / ".hook-on-setup"
    marker.unlink()
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert not marker.exists()


def test_on_activate_hook_runs_on_every_up(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    runs = (workspace_with_hooks.directory / ".hook-on-activate-runs").read_text()
    assert runs.count("ran") == 2


def test_on_attach_hook_runs_when_not_detached(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory), detached=False)
    assert (workspace_with_hooks.directory / ".hook-on-attach").exists()


def test_on_attach_hook_skipped_when_detached(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory), detached=True)
    assert not (workspace_with_hooks.directory / ".hook-on-attach").exists()


def test_on_deactivate_hook_runs_on_down(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    down(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert (workspace_with_hooks.directory / ".hook-on-deactivate").exists()


def test_on_setup_hook_runs_on_reset(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    marker = workspace_with_hooks.directory / ".hook-on-setup"
    marker.unlink()
    reset(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert marker.exists()


def test_on_deactivate_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    remove(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert (workspace_with_hooks.directory / ".hook-on-deactivate").exists()


def test_on_remove_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    remove(branch="main", workspace_dir=str(workspace_with_hooks.directory))
    assert (workspace_with_hooks.directory / ".hook-on-remove").exists()
