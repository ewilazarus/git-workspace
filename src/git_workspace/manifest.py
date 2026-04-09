from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Link:
    """
    Defines a symbolic link from the workspace configuration into a worktree.

    Links are resolved from `.workspace/files` into the project root of each
    worktree.

    If `override` is True, the target path is first marked with
    `git update-index --skip-worktree` before the link is created. This allows
    the link to replace an existing tracked file.

    If `override` is False, the target is added to `.git/info/exclude` to avoid
    leaking the linked file into source control.
    """

    source: str
    target: str
    override: bool = False


@dataclass
class Hooks:
    """
    Defines lifecycle hooks executed during workspace operations.

    Each hook is a list of executables relative to `.workspace/bin`, executed in
    the order defined.

    Hooks allow customizing workspace behavior, such as installing dependencies,
    initializing the environment, or cleaning up resources.

    Available hooks:

    - after_setup: executed after a worktree is created or rebuilt
    - before_activate: executed before activating a worktree
    - after_activate: executed after activating a worktree
    - before_remove: executed before removing a worktree
    - after_remove: executed after removing a worktree
    """

    after_setup: list[str] = field(default_factory=list)
    before_activate: list[str] = field(default_factory=list)
    after_activate: list[str] = field(default_factory=list)
    before_remove: list[str] = field(default_factory=list)
    after_remove: list[str] = field(default_factory=list)


@dataclass
class Prune:
    """
    Defines rules used by the `prune` command to remove worktrees.

    These rules determine which worktrees are eligible for removal based on
    simple heuristics.

    - older_than_days: maximum age (in days) before a worktree is considered for
      pruning
    - exclude_branches: branches that are never pruned, regardless of age
    """

    older_than_days: int = 30
    exclude_branches: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    """
    Represents the workspace manifest configuration.

    The manifest defines how a workspace behaves, including branch creation,
    hooks, links, and cleanup rules.

    - version: schema version of the manifest
    - base_branch: default base branch used when creating new branches that do
      not exist locally or remotely
    - hooks: optional lifecycle hooks configuration
    - links: symbolic links applied to each worktree
    - prune: optional prune configuration for workspace cleanup
    """

    version: int = 1
    base_branch: str = "main"
    hooks: Hooks | None = None
    links: list[Link] = field(default_factory=list)
    prune: Prune | None = None


def read_manifest(path: Path) -> Manifest:
    """
    Reads and parses a workspace manifest from disk.

    The manifest is expected to be a TOML file located under `.workspace`,
    describing workspace configuration such as hooks, links, and prune rules.

    :param path: Path to the manifest file
    :returns: Parsed Manifest instance
    :raises ValueError: If the manifest is invalid or cannot be parsed
    """
    raise NotImplementedError
