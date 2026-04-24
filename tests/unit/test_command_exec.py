from unittest.mock import MagicMock

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace.cli.commands.exec import exec_cmd
from git_workspace.errors import WorktreeResolutionError

BRANCH = "feature/my-branch"
WORKSPACE_DIR = "/workspace"
COMMAND = ["echo", "hello"]


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.exec.Workspace.resolve")


@pytest.fixture(autouse=True)
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.exec.subprocess.run")
    mock.return_value.returncode = 0
    return mock


@pytest.fixture(autouse=True)
def mock_activate_worktree(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.exec.operations.activate_worktree")


@pytest.fixture
def mock_ctx() -> MagicMock:
    ctx = MagicMock(spec=typer.Context)
    ctx.args = COMMAND
    return ctx


@pytest.fixture
def empty_ctx() -> MagicMock:
    ctx = MagicMock(spec=typer.Context)
    ctx.args = []
    return ctx


class TestExec:
    def test_raises_when_no_command(
        self,
        mock_workspace_resolve: MagicMock,
        empty_ctx: MagicMock,
    ) -> None:
        from git_workspace.errors import InvalidInputError

        with pytest.raises(InvalidInputError):
            exec_cmd(branch=BRANCH, ctx=empty_ctx)

    def test_resolves_workspace(
        self,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        exec_cmd(branch=BRANCH, ctx=mock_ctx, workspace_dir=WORKSPACE_DIR)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_worktree(
        self,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        exec_cmd(branch=BRANCH, ctx=mock_ctx)
        mock_workspace_resolve.return_value.resolve_worktree.assert_called_once_with(BRANCH)

    def test_runs_command_in_worktree_dir(
        self,
        mock_workspace_resolve: MagicMock,
        mock_subprocess_run: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        exec_cmd(branch=BRANCH, ctx=mock_ctx)
        worktree = mock_workspace_resolve.return_value.resolve_worktree.return_value
        assert mock_subprocess_run.call_args.kwargs["cwd"] == worktree.dir

    def test_propagates_exit_code(
        self,
        mock_subprocess_run: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_subprocess_run.return_value.returncode = 42
        with pytest.raises(typer.Exit) as exc_info:
            exec_cmd(branch=BRANCH, ctx=mock_ctx)
        assert exc_info.value.exit_code == 42

    def test_prompts_when_worktree_missing(
        self,
        mocker: MockerFixture,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.resolve_worktree.side_effect = WorktreeResolutionError(
            "not found"
        )
        mock_confirm = mocker.patch(
            "git_workspace.cli.commands.exec.typer.confirm", return_value=True
        )

        exec_cmd(branch=BRANCH, ctx=mock_ctx)

        mock_confirm.assert_called_once()

    def test_reraises_when_user_declines(
        self,
        mocker: MockerFixture,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.resolve_worktree.side_effect = WorktreeResolutionError(
            "not found"
        )
        mocker.patch("git_workspace.cli.commands.exec.typer.confirm", return_value=False)

        with pytest.raises(WorktreeResolutionError):
            exec_cmd(branch=BRANCH, ctx=mock_ctx)

    def test_creates_worktree_when_user_confirms(
        self,
        mocker: MockerFixture,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.resolve_worktree.side_effect = WorktreeResolutionError(
            "not found"
        )
        mocker.patch("git_workspace.cli.commands.exec.typer.confirm", return_value=True)

        exec_cmd(branch=BRANCH, ctx=mock_ctx)

        mock_workspace_resolve.return_value.resolve_or_create_worktree.assert_called_once_with(
            BRANCH, None
        )

    def test_activates_worktree_detached_when_created(
        self,
        mocker: MockerFixture,
        mock_workspace_resolve: MagicMock,
        mock_activate_worktree: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.resolve_worktree.side_effect = WorktreeResolutionError(
            "not found"
        )
        mocker.patch("git_workspace.cli.commands.exec.typer.confirm", return_value=True)
        worktree = mock_workspace_resolve.return_value.resolve_or_create_worktree.return_value

        exec_cmd(branch=BRANCH, ctx=mock_ctx)

        mock_activate_worktree.assert_called_once_with(worktree, runtime_vars={}, detached=True)

    def test_skips_prompt_when_force(
        self,
        mocker: MockerFixture,
        mock_workspace_resolve: MagicMock,
        mock_ctx: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.resolve_worktree.side_effect = WorktreeResolutionError(
            "not found"
        )
        mock_confirm = mocker.patch("git_workspace.cli.commands.exec.typer.confirm")

        exec_cmd(branch=BRANCH, ctx=mock_ctx, force=True)

        mock_confirm.assert_not_called()
        mock_workspace_resolve.return_value.resolve_or_create_worktree.assert_called_once_with(
            BRANCH, None
        )
