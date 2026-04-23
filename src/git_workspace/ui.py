import sys
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any, Protocol

from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn
from rich.spinner import Spinner
from rich.text import Text
from rich.theme import Theme

_theme = Theme(
    {
        "branch": "bold cyan",
        "path": "bold yellow",
        "name": "bold magenta",
        "success": "bold green",
        "error": "bold red",
        "hook": "dim",
    }
)

_console = Console(stderr=True, theme=_theme, highlight=False)


class HookProgress(Protocol):
    def begin_section(self, type_label: str, hook_count: int) -> None: ...
    def on_hook_start(self, hook_name: str) -> None: ...
    def on_output_line(self, line: str) -> None: ...
    def on_hook_done(self) -> None: ...
    def on_section_done(self, type_label: str, hook_names: list[str]) -> None: ...


class AssetProgress(Protocol):
    def on_asset_applied(self, src: str, dst: str) -> None: ...


class UI(Protocol):
    def step(self, msg: str) -> None: ...
    def success(self, msg: str) -> None: ...
    def error(self, msg: str) -> None: ...
    def spinner(self, label: str) -> AbstractContextManager[None]: ...
    def hook_display(self) -> AbstractContextManager[HookProgress]: ...
    def asset_display(self, label: str) -> AbstractContextManager[AssetProgress]: ...


class _RichHookProgress:
    def __init__(self) -> None:
        self._live: Live | None = None
        self._section_spinner = Spinner("dots", text=" Running hooks")
        self._completed_types: list[tuple[str, list[str]]] = []
        self._current_type_label: str | None = None
        self._current_type_progress: Progress | None = None
        self._current_task_id: int = 0
        self._output_lines: list[Text] = []

    def _make_renderable(self) -> Group:
        rows: list = [self._section_spinner]
        for type_label, hook_names in self._completed_types:
            row = Text.assemble(("✓", "bold green"), f"    {type_label}: ")
            for i, name in enumerate(hook_names):
                if i > 0:
                    row.append(", ")
                row.append(name, style="name")
            rows.append(row)
        if self._current_type_progress is not None:
            rows.append(self._current_type_progress)
            rows.extend(self._output_lines[-6:])
        return Group(*rows)

    def _ensure_live_started(self) -> None:
        if self._live is None:
            self._live = Live(
                self._make_renderable(),
                console=_console,
                refresh_per_second=15,
                transient=True,
            )
            self._live.start()

    def begin_section(self, type_label: str, hook_count: int) -> None:
        self._ensure_live_started()
        self._current_type_progress = Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("[name]{task.fields[hook]}[/name]"),
            console=_console,
        )
        self._current_task_id = self._current_type_progress.add_task(
            f"   {type_label}", total=hook_count, hook=""
        )
        self._current_type_label = type_label
        self._output_lines = []
        assert self._live is not None
        self._live.update(self._make_renderable())

    def on_hook_start(self, hook_name: str) -> None:
        assert self._current_type_progress is not None
        assert self._live is not None
        self._output_lines = []
        self._current_type_progress.update(self._current_task_id, hook=hook_name)  # ty:ignore[invalid-argument-type]
        self._live.update(self._make_renderable())

    def on_output_line(self, line: str) -> None:
        assert self._live is not None
        self._output_lines.append(Text(line, style="hook"))
        self._live.update(self._make_renderable())

    def on_hook_done(self) -> None:
        assert self._current_type_progress is not None
        assert self._live is not None
        self._current_type_progress.advance(self._current_task_id)  # ty:ignore[invalid-argument-type]
        self._output_lines = []
        self._live.update(self._make_renderable())

    def on_section_done(self, type_label: str, hook_names: list[str]) -> None:
        assert self._live is not None
        self._completed_types.append((type_label, hook_names))
        self._current_type_label = None
        self._current_type_progress = None
        self._live.update(self._make_renderable())

    def _print_type_rows(self) -> None:
        for type_label, hook_names in self._completed_types:
            row = Text.assemble(("✓", "bold green"), f"    {type_label}: ")
            for i, name in enumerate(hook_names):
                if i > 0:
                    row.append(", ")
                row.append(name, style="name")
            _console.print(row)

    def _finalize(self, success: bool) -> None:
        if self._live is None:
            return
        self._live.stop()
        self._live = None
        if success:
            _console.print(Text.assemble(("✓", "bold green"), "  Running hooks"))
            self._print_type_rows()
        else:
            _console.print(Text.assemble(("✗", "bold red"), "  Running hooks"))
            self._print_type_rows()
            if self._current_type_label is not None:
                _console.print(Text.assemble(("✗", "bold red"), f"    {self._current_type_label}"))


class _RichAssetProgress:
    def __init__(self, label: str) -> None:
        self._label = label
        self._live: Live | None = None
        self._applied: list[tuple[str, str]] = []

    def _start(self) -> None:
        spinner = Spinner("dots", text=f" Applying {self._label}")
        self._live = Live(spinner, console=_console, refresh_per_second=15, transient=True)
        self._live.start()

    def on_asset_applied(self, src: str, dst: str) -> None:
        self._applied.append((src, dst))

    def _finalize(self, success: bool) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None
        if success:
            _console.print(f"[success]✓[/success]  Applying {self._label}")
            for src, dst in self._applied:
                _console.print(f"[success]✓[/success]    {styled_asset(src)} → {styled_asset(dst)}")
        else:
            _console.print(f"[error]✗[/error]  Applying {self._label}")


class RichUI:
    def step(self, msg: str) -> None:
        _console.print(f"  {msg}")

    def success(self, msg: str) -> None:
        _console.print(f"[success]✓[/success]  {msg}")

    def error(self, msg: str) -> None:
        _console.print(f"[error]✗[/error]  {msg}")

    @contextmanager
    def spinner(self, label: str) -> Iterator[None]:
        spinner = Spinner("dots", text=f" {label}")
        with Live(spinner, console=_console, refresh_per_second=15, transient=True):
            yield

    @contextmanager
    def hook_display(self) -> Iterator[HookProgress]:
        progress = _RichHookProgress()
        try:
            yield progress
        except GeneratorExit:
            raise
        except BaseException:
            progress._finalize(success=False)
            raise
        else:
            progress._finalize(success=True)

    @contextmanager
    def asset_display(self, label: str) -> Iterator[AssetProgress]:
        progress = _RichAssetProgress(label)
        progress._start()
        try:
            yield progress
        except GeneratorExit:
            raise
        except BaseException:
            progress._finalize(success=False)
            raise
        else:
            progress._finalize(success=True)


class _PlainHookProgress:
    def __init__(self) -> None:
        self._started = False
        self._current_type_label: str | None = None

    def begin_section(self, type_label: str, hook_count: int) -> None:
        self._started = True
        self._current_type_label = type_label

    def on_hook_start(self, hook_name: str) -> None:
        _console.print(f"[magenta]→[/magenta]  Running: {styled_asset(hook_name)}")

    def on_output_line(self, line: str) -> None:
        _console.print(f"{line}", style="dim")

    def on_hook_done(self) -> None:
        pass

    def on_section_done(self, type_label: str, hook_names: list[str]) -> None:
        self._current_type_label = None

    def _finalize(self, success: bool) -> None:
        if not self._started:
            return
        if not success:
            _console.print(Text.assemble(("✗", "bold red"), "  Running hooks"))
            if self._current_type_label is not None:
                _console.print(Text.assemble(("✗", "bold red"), f"    {self._current_type_label}"))


class _PlainAssetProgress:
    def __init__(self, label: str) -> None:
        self._label = label
        self._applied: list[tuple[str, str]] = []

    def on_asset_applied(self, src: str, dst: str) -> None:
        self._applied.append((src, dst))

    def _finalize(self, success: bool) -> None:
        if self._label == "links":
            verb = "Linked"
        else:
            verb = "Copied"

        if success:
            for src, dst in self._applied:
                _console.print(
                    f"[magenta]→[/magenta]  {verb}:  {styled_asset(src)} → {styled_asset(dst)}"
                )
        else:
            _console.print(f"[error]✗[/error]  Applying {self._label}")


class PlainUI:
    def step(self, msg: str) -> None:
        _console.print(f"  {msg}")

    def success(self, msg: str) -> None:
        _console.print(f"[success]✓[/success]  {msg}")

    def error(self, msg: str) -> None:
        _console.print(f"[error]✗[/error]  {msg}")

    @contextmanager
    def spinner(self, label: str) -> Iterator[None]:
        _console.print(f"  {label}...")
        yield

    @contextmanager
    def hook_display(self) -> Iterator[HookProgress]:
        progress = _PlainHookProgress()
        try:
            yield progress
        except GeneratorExit:
            raise
        except BaseException:
            progress._finalize(success=False)
            raise
        else:
            progress._finalize(success=True)

    @contextmanager
    def asset_display(self, label: str) -> Iterator[AssetProgress]:
        progress = _PlainAssetProgress(label)
        try:
            yield progress
        except GeneratorExit:
            raise
        except BaseException:
            progress._finalize(success=False)
            raise
        else:
            progress._finalize(success=True)


class _UIProxy:
    """
    Module-level UI singleton. Delegates to the active strategy (RichUI or
    PlainUI). Call configure() once from the CLI callback to switch strategies.
    Also exposes print() so callers can pass Rich renderables (e.g. Table)
    directly to the underlying Rich console.
    """

    def __init__(self) -> None:
        self._impl: UI = PlainUI()

    def configure(self, plain: bool) -> None:
        self._impl = PlainUI() if plain or not sys.stderr.isatty() else RichUI()

    def step(self, msg: str) -> None:
        self._impl.step(msg)

    def success(self, msg: str) -> None:
        self._impl.success(msg)

    def error(self, msg: str) -> None:
        self._impl.error(msg)

    def spinner(self, label: str) -> AbstractContextManager[None]:
        return self._impl.spinner(label)

    def hook_display(self) -> AbstractContextManager[HookProgress]:
        return self._impl.hook_display()

    def asset_display(self, label: str) -> AbstractContextManager[AssetProgress]:
        return self._impl.asset_display(label)

    def print(self, *args: Any, **kwargs: Any) -> None:
        _console.print(*args, **kwargs)


console = _UIProxy()


def styled_branch(name: str) -> str:
    return f"[branch]{name}[/branch]"


def styled_path(p: Path | str) -> str:
    return f"[path]{p}[/path]"


def styled_asset(name: str) -> str:
    return f"[name]{name}[/name]"
