from pathlib import Path

from rich.console import Console
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

console = Console(stderr=True, theme=_theme, highlight=False)


def styled_branch(name: str) -> str:
    return f"[branch]{name}[/branch]"


def styled_path(p: Path | str) -> str:
    return f"[path]{p}[/path]"


def print_step(msg: str) -> None:
    console.print(f"  {msg}")


def print_success(msg: str) -> None:
    console.print(f"[success]✓[/success]  {msg}")


def print_error(msg: str) -> None:
    console.print(f"[error]✗[/error]  {msg}")
