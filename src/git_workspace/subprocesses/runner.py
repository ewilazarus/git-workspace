import logging
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from git_workspace.errors import ExternalCommandError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CommandResult:
    """The captured outcome of an external command invocation."""

    args: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@runtime_checkable
class CommandRunner(Protocol):
    """
    Executes external commands and captures their output.

    All structured tool invocations (git, and future provider/presenter
    executables) must go through a runner so tests can inject fakes. The one
    sanctioned exception is hook execution, which runs user-authored shell
    command strings and therefore cannot use argv lists.
    """

    def run(
        self,
        args: Sequence[str | Path],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> CommandResult: ...


class SubprocessCommandRunner:
    """Runs commands via subprocess with captured output. Never uses shell=True."""

    def run(
        self,
        args: Sequence[str | Path],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> CommandResult:
        str_args = tuple(str(arg) for arg in args)
        logger.debug("running command: %s (cwd=%s)", " ".join(str_args), cwd or "(inherited)")
        completed = subprocess.run(
            str_args,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            capture_output=True,
            text=True,
        )
        result = CommandResult(
            args=str_args,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        if check and not result.ok:
            raise ExternalCommandError(
                command=list(str_args),
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result


DEFAULT_RUNNER: CommandRunner = SubprocessCommandRunner()
