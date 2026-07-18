import pytest

from git_workspace import main
from git_workspace.errors import GitWorkspaceError


class TestMain:
    def test_exits_non_zero_on_domain_error(self, mocker):
        mocker.patch("git_workspace.cli.app", side_effect=GitWorkspaceError("boom"))

        with pytest.raises(SystemExit) as excinfo:
            main()

        assert excinfo.value.code == 1

    def test_returns_normally_on_success(self, mocker):
        mocker.patch("git_workspace.cli.app", return_value=None)

        main()
