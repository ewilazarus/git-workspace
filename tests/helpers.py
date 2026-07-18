from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock

from git_workspace.cli.callbacks import Context
from git_workspace.errors import ExternalCommandError
from git_workspace.subprocesses.runner import CommandResult


def make_context(workspace_dir: str | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.obj = Context(workspace_dir)
    ctx.args = []
    return ctx


@dataclass(frozen=True)
class FakeCall:
    args: tuple[str, ...]
    cwd: Path | None
    env: Mapping[str, str] | None
    check: bool


@dataclass
class FakeCommandRunner:
    """
    CommandRunner test double: records every call and replays queued results.

    Queued results are consumed in FIFO order; once the queue is empty, every
    call returns ``default_exit_code``/``default_stdout``/``default_stderr``.
    """

    default_exit_code: int = 0
    default_stdout: str = ""
    default_stderr: str = ""
    calls: list[FakeCall] = field(default_factory=list)
    _queue: list[CommandResult] = field(default_factory=list)

    def queue(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        self._queue.append(
            CommandResult(args=(), exit_code=exit_code, stdout=stdout, stderr=stderr)
        )

    @property
    def last_call(self) -> FakeCall:
        return self.calls[-1]

    def run(
        self,
        args: Sequence[str | Path],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = True,
    ) -> CommandResult:
        str_args = tuple(str(arg) for arg in args)
        self.calls.append(FakeCall(args=str_args, cwd=cwd, env=env, check=check))

        if self._queue:
            queued = self._queue.pop(0)
            result = CommandResult(
                args=str_args,
                exit_code=queued.exit_code,
                stdout=queued.stdout,
                stderr=queued.stderr,
            )
        else:
            result = CommandResult(
                args=str_args,
                exit_code=self.default_exit_code,
                stdout=self.default_stdout,
                stderr=self.default_stderr,
            )

        if check and not result.ok:
            raise ExternalCommandError(
                command=list(str_args),
                exit_code=result.exit_code,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        return result
