from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_unconditional_group_always_runs(workspace_with_adaptive_hooks: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert (workspace_with_adaptive_hooks.dir / ".hook-unconditional").exists()


def test_unconditional_group_runs_on_gabriel_branch(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="gabriel/foo", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert (workspace_with_adaptive_hooks.dir / ".hook-unconditional").exists()


def test_gabriel_group_runs_when_branch_matches(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="gabriel/foo", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert (workspace_with_adaptive_hooks.dir / ".hook-gabriel").exists()


def test_gabriel_group_skipped_when_branch_does_not_match(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert not (workspace_with_adaptive_hooks.dir / ".hook-gabriel").exists()


def test_not_gabriel_group_runs_when_branch_does_not_match(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert (workspace_with_adaptive_hooks.dir / ".hook-not-gabriel").exists()


def test_not_gabriel_group_skipped_when_branch_matches(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="gabriel/foo", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert not (workspace_with_adaptive_hooks.dir / ".hook-not-gabriel").exists()


def test_both_conditions_and_semantics_runs_when_all_hold(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="gabriel/my-feature", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert (workspace_with_adaptive_hooks.dir / ".hook-gabriel-not-wip").exists()


def test_both_conditions_and_semantics_skipped_when_one_fails(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(branch="gabriel/wip-something", workspace_dir=str(workspace_with_adaptive_hooks.dir))
    assert not (workspace_with_adaptive_hooks.dir / ".hook-gabriel-not-wip").exists()


def test_as_flag_overrides_effective_branch_for_condition(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(
        branch="main",
        workspace_dir=str(workspace_with_adaptive_hooks.dir),
        effective_branch="gabriel/impersonated",
    )
    assert (workspace_with_adaptive_hooks.dir / ".hook-gabriel").exists()
    assert not (workspace_with_adaptive_hooks.dir / ".hook-not-gabriel").exists()


def test_as_flag_does_not_change_git_workspace_branch_env(
    workspace_with_adaptive_hooks: Workspace,
) -> None:
    up(
        branch="main",
        workspace_dir=str(workspace_with_adaptive_hooks.dir),
        effective_branch="gabriel/impersonated",
        detached=False,
    )
    branch_file = workspace_with_adaptive_hooks.dir / ".hook-attach-branch"
    assert branch_file.exists()
    assert branch_file.read_text().strip() == "main"
