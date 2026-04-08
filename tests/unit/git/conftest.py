from unittest.mock import MagicMock

import pytest

from pytest_mock import MockerFixture


@pytest.fixture
def subprocess(mocker: MockerFixture) -> MagicMock:
    subprocess = mocker.patch("git_workspace.git.subprocess")
    subprocess.run.return_value = MagicMock(returncode=0)
    return subprocess
