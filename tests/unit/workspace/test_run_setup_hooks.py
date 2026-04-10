from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace import workspace
from git_workspace.errors import HookExecutionError, WorkspaceLinkError
from git_workspace.manifest import Hooks, Link

ROOT = Path("/workspace")
WORKTREE_PATH = ROOT / "feat" / "001"
BRANCH = "feat/001"
NO_LINKS: list[Link] = []


@pytest.fixture(autouse=True)
def mock_apply_links(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.apply_links")


@pytest.fixture(autouse=True)
def mock_sync_exclude(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.sync_exclude_block")


@pytest.fixture(autouse=True)
def mock_run_on_setup_hooks(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.workspace.run_on_setup_hooks")


def test_applies_links(mock_apply_links: MagicMock) -> None:
    links = [Link(source="env", target=".env")]

    workspace.setup_worktree(ROOT, WORKTREE_PATH, links, Hooks(), branch=BRANCH)

    mock_apply_links.assert_called_once_with(ROOT, WORKTREE_PATH, links)


def test_syncs_exclude_block(mock_sync_exclude: MagicMock) -> None:
    links = [
        Link(source="env", target=".env", override=False),
        Link(source="secrets", target=".secrets", override=True),
    ]

    workspace.setup_worktree(ROOT, WORKTREE_PATH, links, Hooks(), branch=BRANCH)

    mock_sync_exclude.assert_called_once_with(WORKTREE_PATH, [".env"])


def test_calls_run_on_setup_hooks(mock_run_on_setup_hooks: MagicMock) -> None:
    hook_config = Hooks(on_setup=["install.sh"])

    workspace.setup_worktree(ROOT, WORKTREE_PATH, NO_LINKS, hook_config, branch=BRANCH)

    mock_run_on_setup_hooks.assert_called_once_with(
        root=ROOT,
        worktree_path=WORKTREE_PATH,
        hooks=hook_config,
        branch=BRANCH,
        manifest_vars=None,
        user_vars=None,
        skip_hooks=False,
    )


def test_forwards_skip_hooks_to_run_on_setup_hooks(mock_run_on_setup_hooks: MagicMock) -> None:
    workspace.setup_worktree(ROOT, WORKTREE_PATH, NO_LINKS, Hooks(), branch=BRANCH, skip_hooks=True)

    mock_run_on_setup_hooks.assert_called_once()
    _, kwargs = mock_run_on_setup_hooks.call_args
    assert kwargs["skip_hooks"] is True


def test_link_error_propagates(mock_apply_links: MagicMock) -> None:
    mock_apply_links.side_effect = WorkspaceLinkError("link already exists")

    with pytest.raises(WorkspaceLinkError):
        workspace.setup_worktree(ROOT, WORKTREE_PATH, NO_LINKS, Hooks(), branch=BRANCH)


def test_hook_error_propagates(mock_run_on_setup_hooks: MagicMock) -> None:
    mock_run_on_setup_hooks.side_effect = HookExecutionError("hook failed")

    with pytest.raises(HookExecutionError):
        workspace.setup_worktree(ROOT, WORKTREE_PATH, NO_LINKS, Hooks(), branch=BRANCH)
