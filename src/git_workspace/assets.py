import logging
import re
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from types import TracebackType

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from git_workspace import git
from git_workspace.errors import WorkspaceCopyError, WorkspaceLinkError
from git_workspace.manifest import Asset, Copy, Link
from git_workspace.ui import console, print_success
from git_workspace.workspace import Workspace
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

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
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
        builder = []

        builder.append(self.BEGIN_IGNORE_MARKER)
        for ignore_entry in ignore_entries:
            builder.append(str(ignore_entry))
        builder.append(self.END_IGNORE_MARKER)

        return "\n".join(builder)

    def sync(self, ignore_entries: list[Path]) -> None:
        """
        Rewrites the git-workspace block in `.git/info/exclude` with the given entries.

        Any previously written block is removed before the new block is appended,
        leaving user-managed lines intact.

        :param ignore_entries: Absolute paths to be added to the exclude file.
        """
        file_content = self._workspace.paths.ignore_file.read_text()
        clean_file_content = self.MATCH_REGEX.sub("", file_content)
        ignore_block = self._compose_ignore_block(ignore_entries)
        new_file_content = clean_file_content + "\n" + ignore_block
        self._workspace.paths.ignore_file.write_text(new_file_content)


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
        workspace: Workspace,
        worktree: Worktree,
        ignore: IgnoreManager,
        assets: list[T],
    ) -> None:
        self._workspace = workspace
        self._worktree_dir = worktree.dir
        self._ignore = ignore
        self._assets = assets

    @abstractmethod
    def _apply_with_override(self, source: Path, target: Path) -> None: ...

    @abstractmethod
    def _apply_without_override(self, source: Path, target: Path) -> None: ...

    def _apply(self, asset: T) -> None:
        source = (self._workspace.paths.assets / asset.source).absolute()
        target = (self._worktree_dir / asset.target).absolute()

        target.parent.mkdir(parents=True, exist_ok=True)

        if asset.override:
            git.skip_worktree(target)
            self._apply_with_override(source, target)
        else:
            self._apply_without_override(source, target)
            self._ignore.collect(Path(asset.target))

    def apply(self) -> None:
        """
        Applies all assets, registering non-override targets with the
        shared :class:`IgnoreManager`.
        """
        if self._assets:
            with Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task(
                    f"  Applying {self.asset_name_plural}", total=len(self._assets)
                )
                for asset in self._assets:
                    progress.update(task, description=f"  [path]{asset.target}[/path]")
                    self._apply(asset)
                    progress.advance(task)
            print_success(f"  {len(self._assets)} {self.asset_name}(s) applied")


class Linker(AssetManager[Link]):
    """
    Applies symbolic links from ``.workspace/assets`` into a worktree.

    Override links replace existing tracked files; non-override links fail
    if the target already exists or is a symlink pointing elsewhere.
    """

    asset_name = "link"
    asset_name_plural = "links"

    def __init__(self, workspace: Workspace, worktree: Worktree, ignore: IgnoreManager) -> None:
        super().__init__(workspace, worktree, ignore, workspace.manifest.links)

    def _apply_with_override(self, source: Path, target: Path) -> None:
        if target.exists() or target.is_symlink():
            logger.debug("unlinking existing target before override: %s", target)
            target.unlink()

        logger.debug("symlinking (override) %s -> %s", target, source)
        target.symlink_to(source)

    def _apply_without_override(self, source: Path, target: Path) -> None:
        if target.is_symlink():
            if target.readlink() == source:
                logger.debug("symlink already correct, skipping: %s", target)
                return
            logger.warning("target %s is a symlink pointing elsewhere, cannot link", target)
            raise WorkspaceLinkError("can't link to link")

        if target.exists():
            logger.warning("target %s already exists, cannot link without override", target)
            raise WorkspaceLinkError("can't link to existing file")

        logger.debug("symlinking %s -> %s", target, source)
        target.symlink_to(source)


class Copier(AssetManager[Copy]):
    """
    Copies files from ``.workspace/assets`` into a worktree.

    Unlike links, copies are idempotent: non-override copies silently
    overwrite existing files on reapplication. The only error case is
    attempting to copy over an existing symlink.
    """

    asset_name = "copy"
    asset_name_plural = "copies"

    def __init__(self, workspace: Workspace, worktree: Worktree, ignore: IgnoreManager) -> None:
        super().__init__(workspace, worktree, ignore, workspace.manifest.copies)

    def _apply_with_override(self, source: Path, target: Path) -> None:
        if target.exists() or target.is_symlink():
            logger.debug("removing existing target before override: %s", target)
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()

        logger.debug("copying (override) %s -> %s", source, target)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

    def _apply_without_override(self, source: Path, target: Path) -> None:
        if target.is_symlink():
            logger.warning("target %s is a symlink, cannot copy over it", target)
            raise WorkspaceCopyError("can't copy to symlink")

        logger.debug("copying %s -> %s", source, target)
        if source.is_dir():
            if target.is_dir():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
