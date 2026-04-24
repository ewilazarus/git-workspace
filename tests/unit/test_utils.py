from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.utils import directory_birthtime, normalize_variable_name


class TestNormalizeVariableName:
    def test_converts_to_uppercase(self) -> None:
        assert normalize_variable_name("hotfix") == "HOTFIX"

    def test_replaces_slashes_with_underscores(self) -> None:
        assert normalize_variable_name("fix/my-feature") == "FIX_MY_FEATURE"

    def test_replaces_dots_with_underscores(self) -> None:
        assert normalize_variable_name("release/1.2.3") == "RELEASE_1_2_3"

    def test_preserves_digits(self) -> None:
        assert normalize_variable_name("branch42") == "BRANCH42"

    def test_already_normalized_is_unchanged(self) -> None:
        assert normalize_variable_name("FIX_MY_FEATURE") == "FIX_MY_FEATURE"

    def test_mixed_separators(self) -> None:
        assert normalize_variable_name("feat/some-thing.else") == "FEAT_SOME_THING_ELSE"


@pytest.fixture
def mock_dir(mocker: MockerFixture) -> MagicMock:
    d = mocker.MagicMock(spec=Path)
    return d


class TestDirectoryBirthtime:
    def test_uses_st_birthtime_when_available(self, mock_dir: MagicMock) -> None:
        mock_dir.stat.return_value = MagicMock(st_birthtime=1000.0, st_ctime=2000.0)

        result = directory_birthtime(mock_dir)

        assert result == datetime.fromtimestamp(1000.0)

    def test_falls_back_to_st_ctime_when_st_birthtime_is_absent(self, mock_dir: MagicMock) -> None:
        stat = MagicMock(spec=["st_ctime"], st_ctime=2000.0)
        mock_dir.stat.return_value = stat

        result = directory_birthtime(mock_dir)

        assert result == datetime.fromtimestamp(2000.0)

    def test_returns_datetime(self, mock_dir: MagicMock) -> None:
        mock_dir.stat.return_value = MagicMock(st_birthtime=1000.0)

        assert isinstance(directory_birthtime(mock_dir), datetime)
