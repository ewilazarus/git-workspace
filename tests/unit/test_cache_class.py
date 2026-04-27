import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.cache import NAMESPACE_ENV_VAR, Cache
from git_workspace.errors import CacheError, InvalidCacheKeyError


@pytest.fixture
def cache_root(tmp_path: Path) -> Path:
    return tmp_path / ".cache"


@pytest.fixture
def cache(cache_root: Path) -> Cache:
    return Cache(cache_root, "hooks/install_deps.sh")


class TestSetAndGet:
    def test_round_trips_string_content_verbatim(self, cache: Cache) -> None:
        cache.set("k", "hello world")
        assert cache.get("k") == b"hello world"

    def test_round_trips_bytes_content_verbatim(self, cache: Cache) -> None:
        cache.set("k", b"\x00\x01\x02 raw")
        assert cache.get("k") == b"\x00\x01\x02 raw"

    def test_no_trailing_newline_added(self, cache: Cache) -> None:
        cache.set("k", "abc")
        assert cache.get("k") == b"abc"

    def test_default_content_is_iso_timestamp(self, cache: Cache) -> None:
        before = datetime.datetime.now(datetime.UTC)
        cache.set("k")
        after = datetime.datetime.now(datetime.UTC)

        raw = cache.get("k")
        assert raw is not None
        parsed = datetime.datetime.fromisoformat(raw.decode())
        assert before <= parsed <= after

    def test_get_returns_none_on_miss(self, cache: Cache) -> None:
        assert cache.get("nope") is None

    def test_overwrites_existing_value(self, cache: Cache) -> None:
        cache.set("k", "first")
        cache.set("k", "second")
        assert cache.get("k") == b"second"


class TestExists:
    def test_returns_false_for_missing_key(self, cache: Cache) -> None:
        assert cache.exists("nope") is False

    def test_returns_true_after_set(self, cache: Cache) -> None:
        cache.set("k", "v")
        assert cache.exists("k") is True


class TestStorageLayout:
    def test_set_creates_cache_root(self, cache_root: Path, cache: Cache) -> None:
        assert not cache_root.exists()
        cache.set("k", "v")
        assert cache_root.is_dir()

    def test_set_creates_gitignore_with_expected_content(
        self, cache_root: Path, cache: Cache
    ) -> None:
        cache.set("k", "v")
        gitignore = cache_root / ".gitignore"
        assert gitignore.is_file()
        assert gitignore.read_text() == "*\n!.gitignore\n"

    def test_set_does_not_overwrite_existing_gitignore(
        self, cache_root: Path, cache: Cache
    ) -> None:
        cache_root.mkdir()
        (cache_root / ".gitignore").write_text("custom\n")
        cache.set("k", "v")
        assert (cache_root / ".gitignore").read_text() == "custom\n"

    def test_set_creates_namespace_dir(self, cache_root: Path, cache: Cache) -> None:
        cache.set("k", "v")
        assert (cache_root / "hooks" / "install_deps.sh" / "k").is_file()

    def test_multi_segment_key_lands_in_subdirectory(self, cache_root: Path, cache: Cache) -> None:
        cache.set("fingerprints/deps", "v")
        assert (cache_root / "hooks" / "install_deps.sh" / "fingerprints" / "deps").is_file()


class TestPathSafety:
    @pytest.mark.parametrize(
        "key",
        [
            "",
            "..",
            "../escape",
            "foo/../../escape",
            "/etc/passwd",
            "with\x00nul",
            ".",
        ],
    )
    def test_rejects_unsafe_keys(self, cache: Cache, key: str) -> None:
        with pytest.raises(InvalidCacheKeyError):
            cache.set(key, "v")

    @pytest.mark.parametrize(
        "namespace",
        [
            "",
            "..",
            "../escape",
            "/abs",
            "with\x00nul",
            ".",
        ],
    )
    def test_rejects_unsafe_namespaces(self, cache_root: Path, namespace: str) -> None:
        with pytest.raises(InvalidCacheKeyError):
            Cache(cache_root, namespace)

    def test_writes_no_file_when_key_is_unsafe(self, cache_root: Path, cache: Cache) -> None:
        with pytest.raises(InvalidCacheKeyError):
            cache.set("../escape", "v")
        # Cache root shouldn't even be created
        assert not cache_root.exists()

    def test_symlink_escape_is_caught(self, tmp_path: Path) -> None:
        cache_root = tmp_path / ".cache"
        cache_root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        # Plant a symlink under the namespace dir pointing outside the cache
        ns_dir = cache_root / "ns"
        ns_dir.mkdir()
        (ns_dir / "leak").symlink_to(outside)

        cache = Cache(cache_root, "ns")
        with pytest.raises(InvalidCacheKeyError):
            cache.set("leak/file", "v")


class TestFromEnv:
    @pytest.fixture
    def mock_workspace_resolve(self, mocker: MockerFixture) -> MagicMock:
        mock = mocker.patch("git_workspace.cache.Workspace.resolve")
        mock.return_value.paths.cache = Path("/workspace/.workspace/.cache")
        return mock

    def test_raises_when_namespace_unset(
        self,
        mock_workspace_resolve: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv(NAMESPACE_ENV_VAR, raising=False)
        with pytest.raises(CacheError):
            Cache.from_env()

    def test_resolves_workspace_from_cwd(
        self,
        mock_workspace_resolve: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(NAMESPACE_ENV_VAR, "hooks/test.sh")
        Cache.from_env()
        mock_workspace_resolve.assert_called_once_with(None)

    def test_returns_cache_with_correct_root_and_namespace(
        self,
        mock_workspace_resolve: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(NAMESPACE_ENV_VAR, "hooks/test.sh")
        cache = Cache.from_env()
        assert cache._cache_root == Path("/workspace/.workspace/.cache")
        assert cache._namespace == "hooks/test.sh"
