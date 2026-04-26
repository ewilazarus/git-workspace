from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.hooks import HookCommandResolver, HookNamesResolver, HookRunner
from git_workspace.manifest import HookConditions, HookGroup

BRANCH = "feat/GWS-001"
WORKSPACE_DIR = Path("/workspace")
WORKSPACE_NAME = "workspace"
WORKTREE_DIR = Path("/workspace/feat/GWS-001")
BIN_DIR = Path("/workspace/.workspace/bin")
ASSETS_DIR = Path("/workspace/.workspace/assets")


def _group(commands: list[str], conditions: HookConditions | None = None) -> HookGroup:
    return HookGroup(commands=commands, conditions=conditions)


HOOKS_ON_SETUP = [_group(["setup.sh"])]
HOOKS_ON_ATTACH = [_group(["attach.sh"])]
HOOKS_ON_DETACH = [_group(["detach.sh"])]
HOOKS_ON_TEARDOWN = [_group(["teardown.sh"])]


@pytest.fixture
def worktree(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.dir = WORKTREE_DIR
    mock.branch = BRANCH
    mock.workspace.dir = WORKSPACE_DIR
    mock.workspace.paths.bin = BIN_DIR
    mock.workspace.paths.assets = ASSETS_DIR
    mock.workspace.manifest.vars = {}
    mock.workspace.manifest.hooks.on_setup = HOOKS_ON_SETUP
    mock.workspace.manifest.hooks.on_attach = HOOKS_ON_ATTACH
    mock.workspace.manifest.hooks.on_detach = HOOKS_ON_DETACH
    mock.workspace.manifest.hooks.on_teardown = HOOKS_ON_TEARDOWN
    return mock


@pytest.fixture
def hook_runner(worktree: MagicMock) -> HookRunner:
    return HookRunner(worktree, {}, effective_branch=BRANCH)


@pytest.fixture(autouse=True)
def mock_bin_is_file(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("pathlib.Path.is_file", return_value=True)


@pytest.fixture(autouse=True)
def mock_popen(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.hooks.subprocess.Popen")
    mock.return_value.__enter__.return_value.returncode = 0
    return mock


class TestHookNamesResolver:
    def test_returns_commands_from_unconditional_group(self) -> None:
        resolver = HookNamesResolver("any/branch")
        groups = [_group(["setup.sh", "build.sh"])]
        assert resolver.resolve_hook_names(groups) == ["setup.sh", "build.sh"]

    def test_returns_empty_list_for_no_groups(self) -> None:
        resolver = HookNamesResolver("any/branch")
        assert resolver.resolve_hook_names([]) == []

    def test_skips_empty_and_whitespace_only_commands(self) -> None:
        resolver = HookNamesResolver("any/branch")
        groups = [_group(["real.sh", "", "   "])]
        assert resolver.resolve_hook_names(groups) == ["real.sh"]

    def test_flattens_commands_across_multiple_groups(self) -> None:
        resolver = HookNamesResolver("any/branch")
        groups = [_group(["first.sh"]), _group(["second.sh"])]
        assert resolver.resolve_hook_names(groups) == ["first.sh", "second.sh"]

    def test_includes_group_when_if_branch_matches_matches(self) -> None:
        resolver = HookNamesResolver("gabriel/foo")
        cond = HookConditions(if_branch_matches="gabriel/*")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == ["cmd.sh"]

    def test_excludes_group_when_if_branch_matches_does_not_match(self) -> None:
        resolver = HookNamesResolver("feat/bar")
        cond = HookConditions(if_branch_matches="gabriel/*")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == []

    def test_includes_group_when_if_branch_not_matches_does_not_match(self) -> None:
        resolver = HookNamesResolver("feat/bar")
        cond = HookConditions(if_branch_not_matches="gabriel/*")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == ["cmd.sh"]

    def test_excludes_group_when_if_branch_not_matches_matches(self) -> None:
        resolver = HookNamesResolver("gabriel/foo")
        cond = HookConditions(if_branch_not_matches="gabriel/*")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == []

    def test_and_condition_passes_when_both_hold(self) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*", if_branch_not_matches="gabriel/wip-*")
        resolver = HookNamesResolver("gabriel/feature")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == ["cmd.sh"]

    def test_and_condition_fails_when_not_matches_blocks(self) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*", if_branch_not_matches="gabriel/wip-*")
        resolver = HookNamesResolver("gabriel/wip-thing")
        assert resolver.resolve_hook_names([_group(["cmd.sh"], cond)]) == []

    def test_mixed_groups_only_matching_commands_returned(self) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*")
        groups = [_group(["unconditional.sh"]), _group(["conditional.sh"], cond)]
        assert HookNamesResolver("feat/bar").resolve_hook_names(groups) == ["unconditional.sh"]
        assert HookNamesResolver("gabriel/foo").resolve_hook_names(groups) == [
            "unconditional.sh",
            "conditional.sh",
        ]


class TestHookCommandResolver:
    def test_returns_bin_path_when_script_exists(self, mocker: MockerFixture) -> None:
        mocker.patch("pathlib.Path.is_file", return_value=True)
        worktree = mocker.MagicMock()
        worktree.workspace.paths.bin = BIN_DIR
        resolver = HookCommandResolver(worktree)
        assert resolver.resolve_command("setup.sh") == str(BIN_DIR / "setup.sh")

    def test_returns_hook_name_as_inline_when_no_bin_script(self, mocker: MockerFixture) -> None:
        mocker.patch("pathlib.Path.is_file", return_value=False)
        worktree = mocker.MagicMock()
        worktree.workspace.paths.bin = BIN_DIR
        resolver = HookCommandResolver(worktree)
        assert resolver.resolve_command("docker build . -t myapp") == "docker build . -t myapp"


class TestResolveCommand:
    def test_runs_bin_script_when_file_exists(
        self,
        hook_runner: HookRunner,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"})

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "setup.sh")
        assert mock_popen.call_args.kwargs["shell"] is True
        assert mock_popen.call_args.kwargs["executable"] == "/usr/bin/zsh"

    def test_runs_inline_command_when_no_bin_script(
        self,
        hook_runner: HookRunner,
        mock_bin_is_file: MagicMock,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_bin_is_file.return_value = False
        mocker.patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"})

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == "setup.sh"
        assert mock_popen.call_args.kwargs["shell"] is True
        assert mock_popen.call_args.kwargs["executable"] == "/usr/bin/zsh"

    def test_falls_back_to_sh_when_shell_not_set(
        self,
        hook_runner: HookRunner,
        mock_bin_is_file: MagicMock,
        mock_popen: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_bin_is_file.return_value = False
        mocker.patch.dict("os.environ", {}, clear=True)

        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.kwargs["executable"] == "sh"


class TestRunOnSetupHooks:
    def test_runs_hooks_from_on_setup_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "setup.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_setup_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_SETUP"


class TestRunOnAttachHooks:
    def test_runs_hooks_from_on_attach_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_attach_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "attach.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_attach_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_ATTACH"


class TestRunOnDetachHooks:
    def test_runs_hooks_from_on_detach_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_detach_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "detach.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_detach_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_DETACH"


class TestRunOnTeardownHooks:
    def test_runs_hooks_from_on_teardown_list(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_teardown_hooks()

        assert mock_popen.call_args.args[0] == str(BIN_DIR / "teardown.sh")

    def test_sets_correct_event_in_env(
        self, hook_runner: HookRunner, mock_popen: MagicMock
    ) -> None:
        hook_runner.run_on_teardown_hooks()

        assert mock_popen.call_args.kwargs["env"]["GIT_WORKSPACE_EVENT"] == "ON_TEARDOWN"


class TestConditionMatching:
    def _runner(self, worktree: MagicMock, groups: list[HookGroup], branch: str) -> HookRunner:
        worktree.workspace.manifest.hooks.on_setup = groups
        return HookRunner(worktree, {}, effective_branch=branch)

    def test_no_conditions_always_runs(self, worktree: MagicMock, mock_popen: MagicMock) -> None:
        runner = self._runner(worktree, [_group(["cmd.sh"])], "any/branch")
        runner.run_on_setup_hooks()
        assert mock_popen.called

    def test_if_branch_matches_runs_when_pattern_matches(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "gabriel/foo")
        runner.run_on_setup_hooks()
        assert mock_popen.called

    def test_if_branch_matches_skipped_when_pattern_does_not_match(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "feat/bar")
        runner.run_on_setup_hooks()
        assert not mock_popen.called

    def test_if_branch_not_matches_runs_when_branch_does_not_match(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_not_matches="gabriel/*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "feat/bar")
        runner.run_on_setup_hooks()
        assert mock_popen.called

    def test_if_branch_not_matches_skipped_when_branch_matches(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_not_matches="gabriel/*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "gabriel/foo")
        runner.run_on_setup_hooks()
        assert not mock_popen.called

    def test_both_conditions_runs_when_all_hold(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*", if_branch_not_matches="gabriel/wip-*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "gabriel/feature")
        runner.run_on_setup_hooks()
        assert mock_popen.called

    def test_both_conditions_skipped_when_not_matches_fails(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*", if_branch_not_matches="gabriel/wip-*")
        runner = self._runner(worktree, [_group(["cmd.sh"], cond)], "gabriel/wip-thing")
        runner.run_on_setup_hooks()
        assert not mock_popen.called

    def test_two_matching_groups_both_run(self, worktree: MagicMock, mock_popen: MagicMock) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*")
        groups = [_group(["first.sh"]), _group(["second.sh"], cond)]
        runner = self._runner(worktree, groups, "gabriel/foo")
        runner.run_on_setup_hooks()
        assert mock_popen.call_count == 2

    def test_only_matching_group_runs_when_one_skipped(
        self, worktree: MagicMock, mock_popen: MagicMock
    ) -> None:
        cond = HookConditions(if_branch_matches="gabriel/*")
        groups = [_group(["unconditional.sh"]), _group(["conditional.sh"], cond)]
        runner = self._runner(worktree, groups, "feat/bar")
        runner.run_on_setup_hooks()
        assert mock_popen.call_count == 1
        assert mock_popen.call_args.args[0] == str(BIN_DIR / "unconditional.sh")
