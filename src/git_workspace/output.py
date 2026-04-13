"""Styled terminal output helpers.

All functions write to stderr so they don't interfere with machine-readable
stdout (paths, JSON).  Rich strips ANSI codes automatically when stderr is not
a TTY (e.g. when captured by tests or scripts).

Public functions accept a template string with {key} placeholders plus keyword
arguments.  Parameter values are rendered in accent colour; the surrounding
text takes the function's base colour.
"""

from contextlib import contextmanager

from typing import Any, Iterator, Self
import collections

from rich.console import Console, Group
from rich.live import Live
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.spinner import Spinner
from rich.text import Text

_console = Console(stderr=True)


def info(msg: str) -> None:
    _console.print(msg)


def success(msg: str) -> None:
    _console.print(f"[green bold]✓ {msg}[/green bold]")


def error(msg: str) -> None:
    _console.print(f"[red bold]✗ Error: {msg}[/red bold]")


@contextmanager
def step(msg: str, ok_msg: str | None = None) -> Iterator:
    live = Live(
        Spinner(
            "dots",
            text=Text.from_markup(msg),
        ),
        console=_console,
        transient=ok_msg is None,
    )
    with live:
        yield
        if ok_msg:
            live.update(Text.from_markup(ok_msg))


class Progressbar:
    def __init__(self, event: str, total: int) -> None:
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn(f"[cyan]{event}[/cyan]"),
            BarColumn(bar_width=70),
            TaskProgressColumn(),
            TextColumn("[yellow]{task.description}[/yellow]"),
            console=_console,
        )
        self._task_id = self._progress.add_task("", total=total)
        self._live = Live(
            self._progress,
            console=_console,
            transient=True,
        )

    def __enter__(self) -> Self:
        self._live.__enter__()
        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self._live.__exit__(*args, **kwargs)

    def set_current(self, target: str) -> None:
        """Set the name of the link target currently being applied."""
        self._progress.update(self._task_id, description=target)

    def advance(self) -> None:
        """Call after each link is applied — advances the bar."""
        self._progress.advance(self._task_id)
        self._progress.update(self._task_id, description="")


class ProgressbarWithRollingOutput(Progressbar):
    _MAX_LINES = 20

    def __init__(self, event: str, total: int) -> None:
        super().__init__(event, total)
        self._buffer: collections.deque[str] = collections.deque(
            maxlen=self._MAX_LINES,
        )
        self._live = Live(
            self._group(),
            console=_console,
            transient=True,
        )

    def _group(self) -> Group:
        output = Text()
        for line in self._buffer:
            output.append(f"{line}\n", style="dim")
        return Group(self._progress, output)

    def write_line(self, line: str) -> None:
        """
        Append a streamed line from the current hook and refresh the display.
        """
        self._buffer.append(line)
        self._live.update(self._group())

    def advance(self) -> None:
        """
        Call after each hook completes — advances the bar and clears the output.
        """
        self._progress.advance(self._task_id)
        self._buffer.clear()
        self._progress.update(self._task_id, description="")
        self._live.update(self._group())
