from git_workspace.cli.commands.up import up
from git_workspace.workspace import Workspace


def test_manifest_var_is_passed_to_hooks(workspace_with_vars: Workspace) -> None:
    up(branch="main", workspace_dir=str(workspace_with_vars.directory))
    value = (
        (workspace_with_vars.directory / ".hook-var-manifest-var").read_text().strip()
    )
    assert value == "from-manifest"


def test_runtime_var_is_passed_to_hooks(workspace_with_vars: Workspace) -> None:
    up(
        branch="main",
        workspace_dir=str(workspace_with_vars.directory),
        runtime_vars={"shared-var": "runtime-value"},  # ty:ignore[invalid-argument-type]
    )
    value = (workspace_with_vars.directory / ".hook-var-shared-var").read_text().strip()
    assert value == "runtime-value"


def test_runtime_var_overrides_manifest_var(workspace_with_vars: Workspace) -> None:
    up(
        branch="main",
        workspace_dir=str(workspace_with_vars.directory),
        runtime_vars={"shared-var": "overridden"},  # ty:ignore[invalid-argument-type]
    )
    value = (workspace_with_vars.directory / ".hook-var-shared-var").read_text().strip()
    assert value == "overridden"


def test_manifest_var_used_when_no_runtime_override(
    workspace_with_vars: Workspace,
) -> None:
    up(branch="main", workspace_dir=str(workspace_with_vars.directory))
    value = (workspace_with_vars.directory / ".hook-var-shared-var").read_text().strip()
    assert value == "manifest-value"
