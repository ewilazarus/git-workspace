import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


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

    - on_setup: executed after a worktree is created or rebuilt (also on reset)
    - on_activate: executed on every up invocation (attached and detached)
    - on_attach: executed only when up runs in attached mode
    - on_remove: executed when a worktree is removed
    """

    on_setup: list[str] = field(default_factory=list)
    on_activate: list[str] = field(default_factory=list)
    on_attach: list[str] = field(default_factory=list)
    on_remove: list[str] = field(default_factory=list)


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
    - vars: optional set of variables to be injected as environment variables
        during hooks execution
    """

    version: int
    base_branch: str
    links: list[Link] = field(default_factory=list)
    vars: dict[str, str] = field(default_factory=dict)
    hooks: Hooks = field(default_factory=Hooks)
    prune: Prune | None = None


_DEFAULT_MANIFEST = Manifest(version=1, base_branch="main")


def read_manifest(path: Path) -> Manifest:
    """
    Reads and parses a workspace manifest from disk.

    The manifest is expected to be a TOML file located under `.workspace`,
    describing workspace configuration such as hooks, links, and prune rules.
    If the file cannot be read or parsed, sane defaults are returned.

    :param path: Path to the manifest file
    :returns: Parsed Manifest instance
    """
    log = logger.bind(path=str(path))

    log.debug("Attempting to read manifest")

    try:
        data = tomllib.loads(path.read_text())
    except OSError as e:
        log.debug("Manifest file unreadable, using defaults", error=str(e))
        return _DEFAULT_MANIFEST
    except tomllib.TOMLDecodeError as e:
        log.debug("Manifest file unparseable, using defaults", error=str(e))
        return _DEFAULT_MANIFEST

    hooks_data = data.get("hooks", {})
    hooks = Hooks(
        on_setup=hooks_data.get("on_setup", []),
        on_activate=hooks_data.get("on_activate", []),
        on_attach=hooks_data.get("on_attach", []),
        on_remove=hooks_data.get("on_remove", []),
    )

    links = [
        Link(
            source=lnk["source"],
            target=lnk["target"],
            override=lnk.get("override", False),
        )
        for lnk in data.get("link", [])
    ]

    prune_data = data.get("prune")
    prune = (
        Prune(
            older_than_days=prune_data.get("older_than_days", 30),
            exclude_branches=prune_data.get("exclude_branches", []),
        )
        if prune_data is not None
        else None
    )

    manifest = Manifest(
        version=data.get("version", 1),
        base_branch=data.get("base_branch", "main"),
        links=links,
        vars=data.get("vars", {}),
        hooks=hooks,
        prune=prune,
    )

    log.debug(
        "Manifest read successfully",
        version=manifest.version,
        base_branch=manifest.base_branch,
        num_links=len(manifest.links),
        hooks=hooks,
        vars=list(manifest.vars.keys()),
        prune=prune,
    )

    return manifest
