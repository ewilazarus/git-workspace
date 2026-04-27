import io
from unittest.mock import MagicMock

import pytest
import typer
from pytest_mock import MockerFixture

from git_workspace.cli.commands.cache import exists, get, set
from git_workspace.errors import CacheError, InvalidCacheKeyError


@pytest.fixture(autouse=True)
def mock_cache_from_env(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("git_workspace.cli.commands.cache.Cache.from_env")


class TestNamespaceMissing:
    def test_get_exits_when_namespace_unset(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.side_effect = CacheError("namespace not set")
        with pytest.raises(typer.Exit) as exc:
            get(key="k")
        assert exc.value.exit_code == 1

    def test_set_exits_when_namespace_unset(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.side_effect = CacheError("namespace not set")
        with pytest.raises(typer.Exit) as exc:
            set(key="k")
        assert exc.value.exit_code == 1

    def test_exists_exits_when_namespace_unset(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.side_effect = CacheError("namespace not set")
        with pytest.raises(typer.Exit) as exc:
            exists(key="k")
        assert exc.value.exit_code == 1


class TestGet:
    def test_writes_content_to_stdout_on_hit(
        self,
        mock_cache_from_env: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        mock_cache_from_env.return_value.get.return_value = b"value"
        buf = io.BytesIO()
        mocker.patch("sys.stdout", new=mocker.MagicMock(buffer=buf))
        get(key="k")
        assert buf.getvalue() == b"value"

    def test_exits_1_on_miss(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.get.return_value = None
        with pytest.raises(typer.Exit) as exc:
            get(key="k")
        assert exc.value.exit_code == 1

    def test_exits_1_on_invalid_key(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.get.side_effect = InvalidCacheKeyError("bad")
        with pytest.raises(typer.Exit) as exc:
            get(key="../bad")
        assert exc.value.exit_code == 1

    def test_calls_from_env(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.get.return_value = b""
        get(key="k")
        mock_cache_from_env.assert_called_once_with()


class TestSet:
    def test_writes_with_explicit_content(self, mock_cache_from_env: MagicMock) -> None:
        set(key="k", content="hello")
        mock_cache_from_env.return_value.set.assert_called_once_with("k", "hello")

    def test_writes_with_default_content_when_omitted(self, mock_cache_from_env: MagicMock) -> None:
        set(key="k")
        mock_cache_from_env.return_value.set.assert_called_once_with("k", None)

    def test_exits_1_on_invalid_key(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.set.side_effect = InvalidCacheKeyError("bad")
        with pytest.raises(typer.Exit) as exc:
            set(key="../bad")
        assert exc.value.exit_code == 1


class TestExists:
    def test_exits_0_when_key_present(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.exists.return_value = True
        exists(key="k")  # no exception → exit 0

    def test_exits_1_when_key_missing(self, mock_cache_from_env: MagicMock) -> None:
        mock_cache_from_env.return_value.exists.return_value = False
        with pytest.raises(typer.Exit) as exc:
            exists(key="k")
        assert exc.value.exit_code == 1
