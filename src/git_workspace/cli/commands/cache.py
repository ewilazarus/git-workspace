import sys
from typing import Annotated

import typer

from git_workspace.cache import Cache
from git_workspace.errors import CacheError
from git_workspace.ui import console

app = typer.Typer(
    name="cache",
    help="Read and write entries in the workspace's file-based cache.",
    no_args_is_help=True,
    hidden=True,
)


@app.command("get")
def get(
    key: Annotated[str, typer.Argument(help="The cache key to read.")],
) -> None:
    """
    Print the cached value for KEY to stdout.

    Exits 0 if the key exists (with the file bytes written verbatim to stdout,
    no trailing newline added) and 1 if it does not. Silent on miss.
    """
    try:
        cache = Cache.from_env()
        content = cache.get(key)
    except CacheError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from e

    if content is None:
        raise typer.Exit(code=1)

    sys.stdout.buffer.write(content)
    sys.stdout.buffer.flush()


@app.command("set")
def set(
    key: Annotated[str, typer.Argument(help="The cache key to write.")],
    content: Annotated[
        str | None,
        typer.Argument(help="The value to store. If omitted, the current UTC timestamp is used."),
    ] = None,
) -> None:
    """
    Write CONTENT under KEY in the cache.

    Creates the cache directory and namespace structure on demand. When CONTENT
    is omitted, the current UTC timestamp in ISO-8601 format is stored instead.
    """
    try:
        cache = Cache.from_env()
        cache.set(key, content)
    except CacheError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from e


@app.command("exists")
def exists(
    key: Annotated[str, typer.Argument(help="The cache key to check.")],
) -> None:
    """
    Exit 0 if KEY exists in the cache, 1 otherwise. Silent.
    """
    try:
        cache = Cache.from_env()
        present = cache.exists(key)
    except CacheError as e:
        console.error(str(e))
        raise typer.Exit(code=1) from e

    if not present:
        raise typer.Exit(code=1)
