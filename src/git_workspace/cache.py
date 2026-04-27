import datetime
import logging
import os
from pathlib import Path, PurePosixPath

from git_workspace.errors import CacheError, InvalidCacheKeyError
from git_workspace.workspace import Workspace

logger = logging.getLogger(__name__)

NAMESPACE_ENV_VAR = "GIT_WORKSPACE_CACHE_NAMESPACE"


class Cache:
    """
    File-based cache scoped by namespace.

    The cache lives under ``<cache_root>/<namespace>/<key>``. Namespace and key
    are validated for path safety: empty input, absolute paths, ``..`` / ``.``
    segments, NUL bytes, and any path that escapes the cache root (including
    via symlinks) are rejected with :class:`InvalidCacheKeyError`.

    The ``.gitignore`` at the cache root is created lazily on first ``set``.
    """

    GITIGNORE_CONTENT = "*\n!.gitignore\n"

    @classmethod
    def from_env(cls) -> Cache:
        """
        Construct a :class:`Cache` from the current environment.

        Reads :data:`NAMESPACE_ENV_VAR` and resolves the workspace from cwd.

        :raises CacheError: If :data:`NAMESPACE_ENV_VAR` is not set.
        :raises InvalidCacheKeyError: If the namespace value is path-unsafe.
        :raises UnableToResolveWorkspaceError: If cwd is not inside a workspace.
        """
        namespace = os.environ.get(NAMESPACE_ENV_VAR)
        if not namespace:
            raise CacheError(
                f"{NAMESPACE_ENV_VAR} is not set. The cache subcommand is intended to "
                "run from inside hook scripts, where this variable is injected automatically."
            )
        workspace = Workspace.resolve(None)
        return cls(workspace.paths.cache, namespace)

    def __init__(self, cache_root: Path, namespace: str) -> None:
        self._cache_root = cache_root
        self._namespace = namespace
        self._namespace_dir = self._safe_join(cache_root, namespace, "namespace")

    @staticmethod
    def _safe_join(base: Path, raw: str, label: str) -> Path:
        if not raw:
            raise InvalidCacheKeyError(f"Cache {label} cannot be empty")
        if "\x00" in raw:
            raise InvalidCacheKeyError(f"Cache {label} contains NUL byte: {raw!r}")

        pure = PurePosixPath(raw)
        if pure.is_absolute():
            raise InvalidCacheKeyError(f"Cache {label} must be relative: {raw!r}")
        if not pure.parts:
            raise InvalidCacheKeyError(f"Cache {label} resolves to empty path: {raw!r}")
        for part in pure.parts:
            if part in ("..", "."):
                raise InvalidCacheKeyError(
                    f"Cache {label} contains invalid segment {part!r}: {raw!r}"
                )

        target = base / pure
        base_resolved = Path(os.path.realpath(base))
        target_resolved = Path(os.path.realpath(target))
        try:
            target_resolved.relative_to(base_resolved)
        except ValueError as e:
            raise InvalidCacheKeyError(f"Cache {label} escapes cache root: {raw!r}") from e
        return target

    def _resolve_key(self, key: str) -> Path:
        return self._safe_join(self._namespace_dir, key, "key")

    def exists(self, key: str) -> bool:
        """Return True if a cache entry for ``key`` exists in this namespace."""
        return self._resolve_key(key).is_file()

    def get(self, key: str) -> bytes | None:
        """
        Return the raw bytes stored under ``key``, or ``None`` if absent.

        :raises InvalidCacheKeyError: If ``key`` is unsafe.
        """
        path = self._resolve_key(key)
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None

    def _ensure_cache_dir(self, target_dir: Path) -> None:
        self._cache_root.mkdir(parents=True, exist_ok=True)
        gitignore = self._cache_root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(self.GITIGNORE_CONTENT)
        target_dir.mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, content: bytes) -> None:
        tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
        try:
            tmp.write_bytes(content)
            os.replace(tmp, path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    def set(self, key: str, content: bytes | str | None = None) -> None:
        """
        Write ``content`` under ``key``, creating cache and namespace dirs as needed.

        ``content`` is stored verbatim. When ``None``, the current UTC timestamp
        in ISO-8601 format is used. The write is atomic (temp file + rename).

        :raises InvalidCacheKeyError: If ``key`` is unsafe.
        """
        path = self._resolve_key(key)

        if content is None:
            content = datetime.datetime.now(datetime.UTC).isoformat()
        if isinstance(content, str):
            content = content.encode()

        self._ensure_cache_dir(path.parent)
        self._write(path, content)

        logger.debug("cache set: %s/%s (%d bytes)", self._namespace, key, len(content))
