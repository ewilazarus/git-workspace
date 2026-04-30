from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace.cli.commands.compose import (
    _find_compose_file,
    _slugify_project_name,
    compose,
)
from tests.helpers import make_context

WORKSPACE_DIR = "/workspace"
COMPOSE_FILE = Path("/workspace/.workspace/compose.yml")
CONFIG_DIR = Path("/workspace/.workspace")


@pytest.fixture(autouse=True)
def mock_workspace_resolve(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.compose.Workspace.resolve")
    mock.return_value.paths.config = CONFIG_DIR
    mock.return_value.dir.name = "workspace"
    return mock


@pytest.fixture(autouse=True)
def mock_find_compose_file(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "git_workspace.cli.commands.compose._find_compose_file",
        return_value=COMPOSE_FILE,
    )


@pytest.fixture(autouse=True)
def mock_subprocess_run(mocker: MockerFixture) -> MagicMock:
    mock = mocker.patch("git_workspace.cli.commands.compose.subprocess.run")
    mock.return_value.returncode = 0
    return mock


class TestResolveWorkspace:
    def test_resolves_workspace_with_root(self, mock_workspace_resolve: MagicMock) -> None:
        ctx = make_context(WORKSPACE_DIR)
        compose(ctx=ctx)
        mock_workspace_resolve.assert_called_once_with(WORKSPACE_DIR)

    def test_resolves_workspace_without_root(self, mock_workspace_resolve: MagicMock) -> None:
        ctx = make_context()
        compose(ctx=ctx)
        mock_workspace_resolve.assert_called_once_with(None)


class TestDockerInvocation:
    def test_invokes_docker_compose_with_project_name_and_file(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        ctx = make_context()
        compose(ctx=ctx)
        cmd = mock_subprocess_run.call_args[0][0]
        assert cmd[:6] == ["docker", "compose", "-p", "workspace", "-f", str(COMPOSE_FILE)]

    def test_forwards_extra_args_verbatim(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        ctx = make_context()
        ctx.args = ["up", "-d", "--build"]
        compose(ctx=ctx)
        cmd = mock_subprocess_run.call_args[0][0]
        assert cmd[-3:] == ["up", "-d", "--build"]

    def test_runs_in_workspace_config_dir(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        ctx = make_context()
        compose(ctx=ctx)
        assert mock_subprocess_run.call_args[1]["cwd"] == CONFIG_DIR

    def test_passes_slugified_name_to_docker(
        self,
        mock_workspace_resolve: MagicMock,
        mock_subprocess_run: MagicMock,
    ) -> None:
        mock_workspace_resolve.return_value.dir.name = "My Workspace"
        ctx = make_context()
        compose(ctx=ctx)
        cmd = mock_subprocess_run.call_args[0][0]
        assert cmd[3] == "my-workspace"


class TestExitCodes:
    def test_propagates_nonzero_exit_code(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        mock_subprocess_run.return_value.returncode = 2
        ctx = make_context()
        with pytest.raises(typer.Exit) as exc:
            compose(ctx=ctx)
        assert exc.value.exit_code == 2

    def test_errors_when_docker_missing(
        self,
        mock_subprocess_run: MagicMock,
    ) -> None:
        mock_subprocess_run.side_effect = FileNotFoundError
        ctx = make_context()
        with pytest.raises(typer.Exit) as exc:
            compose(ctx=ctx)
        assert exc.value.exit_code == 1


class TestNoComposeFile:
    def test_errors_when_no_compose_file(
        self,
        mock_find_compose_file: MagicMock,
    ) -> None:
        mock_find_compose_file.return_value = None
        ctx = make_context()
        with pytest.raises(typer.Exit) as exc:
            compose(ctx=ctx)
        assert exc.value.exit_code == 1


class TestFindComposeFile:
    def test_returns_none_when_no_file_exists(self, tmp_path: Path) -> None:
        assert _find_compose_file(tmp_path) is None

    @pytest.mark.parametrize(
        "present,expected_name",
        [
            (["compose.yaml"], "compose.yaml"),
            (["compose.yml"], "compose.yml"),
            (["docker-compose.yaml"], "docker-compose.yaml"),
            (["docker-compose.yml"], "docker-compose.yml"),
            # precedence: compose.yaml beats everything
            (
                ["compose.yaml", "compose.yml", "docker-compose.yaml", "docker-compose.yml"],
                "compose.yaml",
            ),
            # compose.yml beats docker-compose.*
            (["compose.yml", "docker-compose.yaml", "docker-compose.yml"], "compose.yml"),
            # docker-compose.yaml beats docker-compose.yml
            (["docker-compose.yaml", "docker-compose.yml"], "docker-compose.yaml"),
        ],
    )
    def test_finds_file_by_precedence(
        self,
        tmp_path: Path,
        present: list[str],
        expected_name: str,
    ) -> None:
        for name in present:
            (tmp_path / name).write_text("")
        result = _find_compose_file(tmp_path)
        assert result == tmp_path / expected_name


class TestSlugifyProjectName:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("my-project", "my-project"),
            ("My Project", "my-project"),
            ("repo.git", "repo-git"),
            ("feat.compose-support", "feat-compose-support"),
            ("_weird_", "weird_"),
            ("___", "workspace"),
            ("Foo_Bar", "foo_bar"),
            ("UPPER", "upper"),
            ("hello world!", "hello-world-"),
        ],
    )
    def test_slugify(self, name: str, expected: str) -> None:
        assert _slugify_project_name(name) == expected
