import os
import stat
from pathlib import Path

import pytest
from click.testing import Result
from typer.testing import CliRunner

from git_workspace.cli import app
from git_workspace.workspace import Workspace

MINIMAL_COMPOSE = """\
services:
  db:
    image: postgres:16
"""

runner = CliRunner()


@pytest.fixture
def fake_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a stub docker binary that logs its argv and respects DOCKER_STUB_EXIT."""
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(
        '#!/usr/bin/env sh\necho "$@" >> "$DOCKER_STUB_LOG"\nexit "${DOCKER_STUB_EXIT:-0}"\n'
    )
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")
    return bin_dir


@pytest.fixture
def stub_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Path to the file the docker stub writes its argv into."""
    log = tmp_path / "docker-stub.log"
    monkeypatch.setenv("DOCKER_STUB_LOG", str(log))
    return log


@pytest.fixture
def workspace_with_compose(workspace: Workspace) -> Workspace:
    (workspace.paths.config / "compose.yml").write_text(MINIMAL_COMPOSE)
    return workspace


def _invoke(args: list[str]) -> Result:
    return runner.invoke(app, args)


class TestDockerInvocation:
    def test_invokes_docker_compose_with_workspace_name(
        self,
        workspace_with_compose: Workspace,
        fake_docker: Path,
        stub_log: Path,
    ) -> None:
        result = _invoke(["compose", "-r", str(workspace_with_compose.dir)])
        assert result.exit_code == 0, result.output
        logged = stub_log.read_text()
        assert f"-p {workspace_with_compose.dir.name}" in logged
        assert "-f" in logged
        assert "compose.yml" in logged

    def test_passes_through_subcommand_args(
        self,
        workspace_with_compose: Workspace,
        fake_docker: Path,
        stub_log: Path,
    ) -> None:
        result = _invoke(["compose", "-r", str(workspace_with_compose.dir), "up", "-d", "--build"])
        assert result.exit_code == 0, result.output
        logged = stub_log.read_text()
        assert "up -d --build" in logged

    def test_compose_yaml_takes_precedence_over_docker_compose_yml(
        self,
        workspace: Workspace,
        fake_docker: Path,
        stub_log: Path,
    ) -> None:
        (workspace.paths.config / "docker-compose.yml").write_text(MINIMAL_COMPOSE)
        (workspace.paths.config / "compose.yaml").write_text(MINIMAL_COMPOSE)
        result = _invoke(["compose", "-r", str(workspace.dir)])
        assert result.exit_code == 0, result.output
        logged = stub_log.read_text()
        assert "compose.yaml" in logged
        assert "docker-compose.yml" not in logged


class TestWorkspaceResolution:
    def test_resolves_from_subdirectory(
        self,
        workspace_with_compose: Workspace,
        fake_docker: Path,
        stub_log: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        subdir = workspace_with_compose.dir / "some-subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)
        result = _invoke(["compose"])
        assert result.exit_code == 0, result.output
        assert stub_log.exists()

    def test_works_with_root_flag_from_outside_workspace(
        self,
        workspace_with_compose: Workspace,
        fake_docker: Path,
        stub_log: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = _invoke(["compose", "-r", str(workspace_with_compose.dir)])
        assert result.exit_code == 0, result.output
        assert stub_log.exists()


class TestProjectNameSlug:
    def test_uppercase_dir_name_is_slugified(
        self,
        setup,
        tmp_path: Path,
        fake_docker: Path,
        stub_log: Path,
    ) -> None:
        setup()
        ws = Workspace.clone(
            workspace_dir=str(tmp_path / "My Workspace"),
            url=str(tmp_path / "repo"),
            config_url=str(tmp_path / "configs" / "minimal"),
        )
        (ws.paths.config / "compose.yml").write_text(MINIMAL_COMPOSE)
        result = _invoke(["compose", "-r", str(ws.dir)])
        assert result.exit_code == 0, result.output
        logged = stub_log.read_text()
        assert "-p my-workspace" in logged


class TestErrorCases:
    def test_errors_when_no_compose_file(
        self,
        workspace: Workspace,
        fake_docker: Path,
        stub_log: Path,
    ) -> None:
        result = _invoke(["compose", "-r", str(workspace.dir)])
        assert result.exit_code == 1
        assert not stub_log.exists()

    def test_errors_when_docker_not_on_path(
        self,
        workspace_with_compose: Workspace,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("PATH", "")
        result = _invoke(["compose", "-r", str(workspace_with_compose.dir)])
        assert result.exit_code == 1

    def test_propagates_docker_exit_code(
        self,
        workspace_with_compose: Workspace,
        fake_docker: Path,
        stub_log: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("DOCKER_STUB_EXIT", "2")
        result = _invoke(["compose", "-r", str(workspace_with_compose.dir)])
        assert result.exit_code == 2
