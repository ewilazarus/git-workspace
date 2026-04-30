from unittest.mock import MagicMock

from git_workspace.cli.callbacks import Context


def make_context(workspace_dir: str | None = None) -> MagicMock:
    ctx = MagicMock()
    ctx.obj = Context(workspace_dir)
    ctx.args = []
    return ctx
