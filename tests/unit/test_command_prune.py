import pytest

from git_workspace.cli.commands.prune import prune
from git_workspace.errors import UnableToResolveWorkspaceError


class TestPrune:
    def test_raises_when_no_workspace_resolvable(self) -> None:
        with pytest.raises(UnableToResolveWorkspaceError):
            prune()
