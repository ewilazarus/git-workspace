import pytest

from git_workspace.cli.commands.prune import prune


def test_raises_not_implemented_error() -> None:
    with pytest.raises(NotImplementedError):
        prune()
