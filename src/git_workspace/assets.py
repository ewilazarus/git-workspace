import logging
import re
from pathlib import Path

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from git_workspace import git
from git_workspace.errors import WorkspaceLinkError
from git_workspace.manifest import Link
from git_workspace.ui import console, print_success
from git_workspace.workspace import Workspace
from git_workspace.worktree import Worktree

logger = logging.getLogger(__name__)


class IgnoreManager:
    """
    Manages the git-workspace-owned block inside `.git/info/exclude`.

    Wraps a clearly delimited section in the exclude file so that entries
    added by git-workspace can be replaced atomically on each sync without
    disturbing any lines written by the user.
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


class Linker:
    """
    Applies symbolic links defined in the workspace manifest into a worktree.

    For each link, the source is resolved relative to `.workspace/assets` and
    the target relative to the worktree root. Links marked as overrides replace
    existing tracked files (using ``git update-index --skip-worktree``); all
    other links are recorded in `.git/info/exclude` to keep them out of source
    control.
    """

    def __init__(self, workspace: Workspace, worktree: Worktree) -> None:
        self._workspace = workspace
        self._links = workspace.manifest.links
        self._worktree_dir = worktree.dir
        self._ignore_manager = IgnoreManager(workspace)

    def _apply_with_override(self, source: Path, target: Path) -> None:
        git.skip_worktree(target)

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

    def _apply(self, link: Link, ignore_entries: list[Path]) -> None:
        source = (self._workspace.paths.assets / link.source).absolute()
        target = (self._worktree_dir / link.target).absolute()

        if link.override:
            self._apply_with_override(source, target)
        else:
            self._apply_without_override(source, target)
            ignore_entries.append(target)

    def apply(self) -> None:
        """
        Creates all symlinks defined in the manifest and syncs the ignore file.

        Iterates over each link entry, creates the symlink (with or without
        override semantics), then writes all non-override targets into the
        managed block of `.git/info/exclude`.

        :raises WorkspaceLinkError: If a non-override link conflicts with an
            existing file or a symlink pointing elsewhere.
        """
        ignore_entries: list[Path] = []

        if self._links:
            with Progress(
                SpinnerColumn(),
                TextColumn("{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
                transient=True,
            ) as progress:
                task = progress.add_task("  Applying links", total=len(self._links))
                for link in self._links:
                    progress.update(task, description=f"  [path]{link.target}[/path]")
                    self._apply(link, ignore_entries)
                    progress.advance(task)
            print_success(f"  {len(self._links)} link(s) applied")

        self._ignore_manager.sync(ignore_entries)
