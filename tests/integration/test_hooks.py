from git_workspace.cli.commands.down import down
from git_workspace.cli.commands.prune import prune
from git_workspace.cli.commands.remove import remove
from git_workspace.cli.commands.reset import reset
from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace
from tests.helpers import make_context


def test_inline_command_runs_as_shell(workspace_with_inline_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_inline_hooks.dir)), branch="main")
    assert (workspace_with_inline_hooks.dir / ".inline-hook-ran").exists()


def test_on_setup_hook_runs_on_first_up(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert (workspace_with_hooks.dir / ".hook-on-setup").exists()


def test_on_setup_hook_does_not_run_on_subsequent_up(
    workspace_with_hooks: Workspace,
) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    marker = workspace_with_hooks.dir / ".hook-on-setup"
    marker.unlink()
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert not marker.exists()


def test_on_attach_hook_runs_when_not_detached(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main", detached=False)
    assert (workspace_with_hooks.dir / ".hook-on-attach").exists()


def test_on_attach_hook_skipped_when_detached(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main", detached=True)
    assert not (workspace_with_hooks.dir / ".hook-on-attach").exists()


def test_on_attach_hook_skipped_on_existing_worktree_when_detached(
    workspace_with_hooks: Workspace,
) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main", detached=True)
    marker = workspace_with_hooks.dir / ".hook-on-attach"
    assert not marker.exists()
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main", detached=True)
    assert not marker.exists()


def test_on_detach_hook_runs_on_down(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    down(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert (workspace_with_hooks.dir / ".hook-on-detach").exists()


def test_on_setup_hook_runs_on_reset(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    marker = workspace_with_hooks.dir / ".hook-on-setup"
    marker.unlink()
    reset(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert marker.exists()


def test_on_detach_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    remove(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert (workspace_with_hooks.dir / ".hook-on-detach").exists()


def test_on_teardown_hook_runs_on_remove(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    remove(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert (workspace_with_hooks.dir / ".hook-on-teardown").exists()


def test_on_detach_runs_before_on_teardown_on_remove(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    remove(ctx=make_context(str(workspace_with_hooks.dir)), branch="main")
    assert (workspace_with_hooks.dir / ".hook-on-detach").exists()
    assert (workspace_with_hooks.dir / ".hook-on-teardown").exists()


def test_hooks_do_not_run_on_prune(workspace_with_hooks: Workspace) -> None:
    up(ctx=make_context(str(workspace_with_hooks.dir)), branch="feat")
    prune(ctx=make_context(str(workspace_with_hooks.dir)), older_than_days=-1, dry_run=False)
    assert not (workspace_with_hooks.dir / ".hook-on-detach").exists()
    assert not (workspace_with_hooks.dir / ".hook-on-teardown").exists()
