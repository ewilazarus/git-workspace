import pytest

from git_workspace.cli.commands.prune import prune


class TestPrune:
    def test_raises_not_implemented_error(self) -> None:
        with pytest.raises(NotImplementedError):
            prune()
