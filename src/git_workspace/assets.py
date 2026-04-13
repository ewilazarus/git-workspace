import re
from git_workspace.worktree import Worktree
from git_workspace.manifest import Link
from git_workspace.errors import WorkspaceLinkError
from pathlib import Path

from git_workspace import git
from git_workspace.workspace import Workspace


class IgnoreManager:
    BEGIN_IGNORE_MARKER = "# >>> git-workspace managed >>>"
    END_IGNORE_MARKER = "# <<< git-workspace managed <<<"
    MATCH_REGEX = re.compile(
        rf"\n?{BEGIN_IGNORE_MARKER}"
        r".*?"
        rf"{END_IGNORE_MARKER}\n?",
        flags=re.DOTALL,
    )

    def __init__(self, workspace: Workspace) -> None:
        self._ignore_file = workspace.directory / ".git" / "info" / "exclude"

    def _compose_ignore_block(self, ignore_entries: list[Path]) -> str:
        builder = []

        builder.append(self.BEGIN_IGNORE_MARKER)
        for ignore_entry in ignore_entries:
            builder.append(str(ignore_entry))
        builder.append(self.END_IGNORE_MARKER)

        return "\n".join(builder)

    def sync(self, ignore_entries: list[Path]) -> None:
        file_content = self._ignore_file.read_text()
        clean_file_content = self.MATCH_REGEX.sub("", file_content)
        ignore_block = self._compose_ignore_block(ignore_entries)
        new_file_content = clean_file_content + "\n" + ignore_block
        self._ignore_file.write_text(new_file_content)


class Linker:
    def __init__(self, workspace: Workspace, worktree: Worktree) -> None:
        self._links = workspace.manifest.links
        self._assets_directory = workspace.directory / ".workspace" / "assets"
        self._worktree_directory = worktree.directory
        self._ignore_manager = IgnoreManager(workspace)

    def _apply_with_override(self, source: Path, target: Path) -> None:
        git.skip_worktree(target)

        if target.exists() or target.is_symlink():
            target.unlink()

        target.symlink_to(source)

    def _apply_without_override(self, source: Path, target: Path) -> None:
        if target.is_symlink():
            if target.readlink() == source:
                return
            raise WorkspaceLinkError("can't link to link")

        if target.exists():
            raise WorkspaceLinkError("can't link to existing file")

        target.symlink_to(source)

    def _apply(self, link: Link, ignore_entries: list[Path]) -> None:
        source = (self._assets_directory / link.source).absolute()
        target = (self._worktree_directory / link.target).absolute()

        if link.override:
            self._apply_with_override(source, target)
        else:
            self._apply_without_override(source, target)
            ignore_entries.append(target)

    def apply(self) -> None:
        ignore_entries = []

        for link in self._links:
            self._apply(link, ignore_entries)

        self._ignore_manager.sync(ignore_entries)
