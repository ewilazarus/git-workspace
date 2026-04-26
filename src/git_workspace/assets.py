import logging
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from types import TracebackType

from git_workspace import git
from git_workspace.errors import WorkspaceCopyError, WorkspaceLinkError
from git_workspace.manifest import Asset, Copy, Link
from git_workspace.ui import console
from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)


class IgnoreManager:
    """
    Manages the git-workspace-owned block inside `.git/info/exclude`.

    Intended to be used as a context manager around one or more
    ``AssetManager.apply()`` calls. Each non-override asset collects its
    target path via :meth:`collect`; on exit the full set is written to the
    exclude file in a single atomic sync.
    """

    BEGIN_IGNORE_MARKER = "# >>> git-workspace managed >>>"
    END_IGNORE_MARKER = "# <<< git-workspace managed <<<"
    MATCH_REGEX = re.compile(
        rf"\n?{BEGIN_IGNORE_MARKER}"
        r".*?"
        rf"{END_IGNORE_MARKER}\n?",
        flags=re.DOTALL,
    )

    def __init__(self, worktree: Worktree) -> None:
        self._worktree = worktree
        self._entries: list[Path] = []

    def __enter__(self) -> IgnoreManager:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is None:
            self.sync(self._entries)

    def collect(self, entry: Path) -> None:
        self._entries.append(entry)

    def _compose_ignore_block(self, ignore_entries: list[Path]) -> str:
        lines = [self.BEGIN_IGNORE_MARKER, *map(str, ignore_entries), self.END_IGNORE_MARKER]
        return "\n".join(lines)

    def sync(self, ignore_entries: list[Path]) -> None:
        """
        Rewrites the git-workspace block in `.git/info/exclude` with the given entries.

        Any previously written block is removed before the new block is appended,
        leaving user-managed lines intact.

        :param ignore_entries: Absolute paths to be added to the exclude file.
        """
        logger.debug("syncing exclude file with %d entries", len(ignore_entries))
        ignore_file = self._worktree.workspace.paths.ignore_file
        file_content = ignore_file.read_text()
        clean_file_content = self.MATCH_REGEX.sub("", file_content)
        ignore_block = self._compose_ignore_block(ignore_entries)
        ignore_file.write_text(clean_file_content + "\n" + ignore_block)


class AssetManager[T: Asset](ABC):
    """
    Base class for applying manifest-defined assets into a worktree.

    Subclasses implement ``_apply_with_override`` and ``_apply_without_override``
    to define how an individual asset is materialised (e.g. symlink vs copy).
    Override assets are marked with ``git update-index --skip-worktree``;
    non-override assets are registered with the shared :class:`IgnoreManager`.
    """

    asset_name: str
    asset_name_plural: str

    def __init__(
        self,
        worktree: Worktree,
        ignore: IgnoreManager,
        assets: list[T],
    ) -> None:
        self._worktree = worktree
        self._ignore = ignore
        self._assets = assets

    @abstractmethod
    def _apply_with_override(self, source: Path, target: Path) -> int: ...

    @abstractmethod
    def _apply_without_override(self, source: Path, target: Path) -> int: ...

    def _apply(self, asset: T) -> int:
        source = (self._worktree.workspace.paths.assets / asset.source).absolute()
        target = (self._worktree.dir / asset.target).absolute()

        target.parent.mkdir(parents=True, exist_ok=True)

        if asset.override:
            git.skip_worktree(target)
            return self._apply_with_override(source, target)
        else:
            count = self._apply_without_override(source, target)
            self._ignore.collect(Path(asset.target))
            return count

    def apply(self) -> None:
        """
        Applies all assets, registering non-override targets with the
        shared :class:`IgnoreManager`.
        """
        if not self._assets:
            return

        with console.asset_display(self.asset_name_plural) as progress:
            for asset in self._assets:
                count = self._apply(asset)
                progress.on_asset_applied(asset.source, asset.target, count)


class Linker(AssetManager[Link]):
    """
    Applies symbolic links from ``.workspace/assets`` into a worktree.

    Override links replace existing tracked files; non-override links fail
    if the target already exists or is a symlink pointing elsewhere.
    """

    asset_name = "link"
    asset_name_plural = "links"

    def __init__(self, worktree: Worktree, ignore: IgnoreManager) -> None:
        super().__init__(worktree, ignore, worktree.workspace.manifest.links)

    def _apply_with_override(self, source: Path, target: Path) -> int:
        if target.exists() or target.is_symlink():
            logger.debug("unlinking existing target before override: %s", target)
            target.unlink()

        logger.debug("symlinking (override) %s -> %s", target, source)
        target.symlink_to(source)
        return 0

    def _apply_without_override(self, source: Path, target: Path) -> int:
        if target.is_symlink():
            if target.readlink() == source:
                logger.debug("symlink already correct, skipping: %s", target)
                return 0
            logger.warning("target %s is a symlink pointing elsewhere, cannot link", target)
            raise WorkspaceLinkError(
                f"Cannot link {source!r} -> {target!r}: target is a symlink pointing elsewhere"
            )

        if target.exists():
            logger.warning("target %s already exists, cannot link without override", target)
            raise WorkspaceLinkError(f"Cannot link {source!r} -> {target!r}: target already exists")

        logger.debug("symlinking %s -> %s", target, source)
        target.symlink_to(source)
        return 0


class Copier(AssetManager[Copy]):
    """
    Copies files from ``.workspace/assets`` into a worktree.

    Unlike links, copies are idempotent: non-override copies silently
    overwrite existing files on reapplication. The only error case is
    attempting to copy over an existing symlink.

    Text files are inspected for ``{{ GIT_WORKSPACE_* }}`` placeholders and
    values are substituted from the provided environment dict. Binary files
    are copied as-is.
    """

    asset_name = "copy"
    asset_name_plural = "copies"

    PLACEHOLDER_RE = re.compile(r"\{\{\s*(GIT_WORKSPACE_\w+)\s*\}\}")

    def __init__(self, worktree: Worktree, ignore: IgnoreManager, env: dict[str, str]) -> None:
        super().__init__(worktree, ignore, worktree.workspace.manifest.copies)
        self._env = env

    def _resolve_placeholders(self, content: str) -> tuple[str, int]:
        count = 0

        def replace(m: re.Match) -> str:
            nonlocal count

            value = self._env.get(m.group(1))
            if value is not None:
                count += 1
                return value

            return m.group(0)

        return self.PLACEHOLDER_RE.sub(replace, content), count

    def _copy_with_substitution(self, source: Path, target: Path) -> int:
        try:
            content = source.read_text(encoding="utf-8")
            new_content, count = self._resolve_placeholders(content)
            target.write_text(new_content, encoding="utf-8")
            return count
        except UnicodeDecodeError, ValueError:
            logger.debug("copying %s as binary (not valid UTF-8 text)", source)
            shutil.copy2(source, target)
            return 0

    def _copy_dir_with_substitution(self, source: Path, target: Path) -> int:
        total = 0

        def copy_fn(s: str, d: str) -> None:
            nonlocal total
            total += self._copy_with_substitution(Path(s), Path(d))

        shutil.copytree(source, target, copy_function=copy_fn)
        return total

    def _skip_existing(self, asset: Copy) -> bool:
        target = (self._worktree.dir / asset.target).absolute()

        if asset.overwrite or not target.exists():
            return False

        logger.debug("skipping copy (overwrite=false, target exists): %s", target)

        if asset.override:
            git.skip_worktree(target)
        else:
            self._ignore.collect(Path(asset.target))

        return True

    def _apply(self, asset: Copy) -> int:
        if self._skip_existing(asset):
            return 0
        return super()._apply(asset)

    def _apply_with_override(self, source: Path, target: Path) -> int:
        if target.exists() or target.is_symlink():
            logger.debug("removing existing target before override: %s", target)
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()

        logger.debug("copying (override) %s -> %s", source, target)
        if source.is_dir():
            return self._copy_dir_with_substitution(source, target)
        else:
            return self._copy_with_substitution(source, target)

    def _apply_without_override(self, source: Path, target: Path) -> int:
        if target.is_symlink():
            logger.warning("target %s is a symlink, cannot copy over it", target)
            raise WorkspaceCopyError(f"Cannot copy {source!r} to {target!r}: target is a symlink")

        logger.debug("copying %s -> %s", source, target)
        if source.is_dir():
            if target.is_dir():
                shutil.rmtree(target)
            return self._copy_dir_with_substitution(source, target)
        else:
            return self._copy_with_substitution(source, target)
