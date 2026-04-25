import logging
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from git_workspace.workspace import Workspace

logger = logging.getLogger(__name__)

KNOWN_CONDITION_KEYS: frozenset[str] = frozenset({"if_branch_matches", "if_branch_not_matches"})


@dataclass
class Asset:
    """
    Base for manifest-defined assets that are applied into worktrees.

    ``source`` is resolved relative to ``.workspace/assets``, ``target``
    relative to the worktree root. If ``override`` is True the target is
    marked with ``git update-index --skip-worktree`` before being applied.
    """

    source: str
    target: str
    override: bool = False


@dataclass
class Link(Asset):
    """An asset applied as a symbolic link."""

    ...


@dataclass
class Copy(Asset):
    """An asset applied as a file copy."""

    overwrite: bool = True


@dataclass
class HookConditions:
    """
    Conditions that gate whether a hook group runs.

    Both fields use POSIX glob syntax (fnmatch). When both are set, they are
    AND-ed: the group runs only when the branch matches ``if_branch_matches``
    AND does not match ``if_branch_not_matches``.

    Unknown keys found in the manifest conditions table are captured in
    ``unknown_keys`` for ``doctor`` to surface as warnings.
    """

    if_branch_matches: str | None = None
    if_branch_not_matches: str | None = None
    unknown_keys: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class HookGroup:
    """
    A group of hook commands with an optional set of conditions.

    When ``conditions`` is ``None`` the group always runs.
    When ``commands`` is empty the group is a no-op (doctor warns about this).
    """

    commands: list[str] = field(default_factory=list)
    conditions: HookConditions | None = None


@dataclass
class Hooks:
    """
    Defines lifecycle hooks executed during workspace operations.

    Each hook event holds an ordered list of ``HookGroup`` objects. Groups are
    evaluated top-to-bottom; a group runs only when its conditions match the
    effective branch (or when it has no conditions). Each command within a
    matching group is executed in order.

    Available hook events:

    - on_setup: executed after a worktree is first created or on reset (worktree lifetime)
    - on_attach: executed on ``up`` in interactive mode (session lifetime)
    - on_detach: executed on ``down`` and before ``rm`` (session lifetime)
    - on_teardown: executed on ``rm``, after on_detach, before deletion (worktree lifetime)
    """

    on_setup: list[HookGroup] = field(default_factory=list)
    on_attach: list[HookGroup] = field(default_factory=list)
    on_detach: list[HookGroup] = field(default_factory=list)
    on_teardown: list[HookGroup] = field(default_factory=list)


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
class Fingerprint:
    """
    Defines a named hash over a set of files at the worktree root.

    The resulting value is exposed as ``GIT_WORKSPACE_FINGERPRINT_<NORMALIZED_NAME>``
    in hook and exec environments, letting hooks gate expensive steps (e.g. docker
    builds, npm installs) on whether the relevant files have changed.

    - name: identifier for the fingerprint; normalized the same way as variable names.
    - files: paths relative to the worktree root; sorted alphabetically before hashing.
    - algorithm: ``"sha256"`` or ``"md5"``; defaults to ``"sha256"``.
    - length: prefix size of the hex digest to expose; defaults to 12.
    """

    name: str
    files: list[str] = field(default_factory=list)
    algorithm: str = "sha256"
    length: int = 12


@dataclass
class Manifest:
    """
    Represents the workspace manifest configuration.

    The manifest defines how a workspace behaves, including branch creation,
    hooks, links, and cleanup rules.

    - version: schema version of the manifest
    - base_branch: default base branch used when creating new branches that do
      not exist locally or remotely
    - copies: files copied into each worktree from ``.workspace/assets``
    - links: symbolic links applied to each worktree from ``.workspace/assets``
    - hooks: optional lifecycle hooks configuration
    - prune: optional prune configuration for workspace cleanup
    - vars: optional set of variables to be injected as environment variables
        during hooks execution
    - fingerprints: optional list of file-hash definitions exposed as
        ``GIT_WORKSPACE_FINGERPRINT_*`` environment variables
    """

    DEFAULT_VERSION = 1
    DEFAULT_BRANCH = "main"

    version: int
    base_branch: str
    copies: list[Copy] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)
    vars: dict[str, str] = field(default_factory=dict)
    fingerprints: list[Fingerprint] = field(default_factory=list)
    hooks: Hooks = field(default_factory=Hooks)
    prune: Prune | None = None

    @classmethod
    def _parse_version(cls, data: dict[str, Any]) -> int:
        return data.get("version", cls.DEFAULT_VERSION)

    @classmethod
    def _parse_base_branch(cls, data: dict[str, Any]) -> str:
        return data.get("base_branch", cls.DEFAULT_BRANCH)

    @classmethod
    def _parse_copies(cls, data: dict[str, Any]) -> list[Copy]:
        return [
            Copy(
                source=asset_data["source"],
                target=asset_data["target"],
                override=asset_data.get("override", False),
                overwrite=asset_data.get("overwrite", True),
            )
            for asset_data in data.get("copy", [])
        ]

    @classmethod
    def _parse_links(cls, data: dict[str, Any]) -> list[Link]:
        return [
            Link(
                source=asset_data["source"],
                target=asset_data["target"],
                override=asset_data.get("override", False),
            )
            for asset_data in data.get("link", [])
        ]

    @classmethod
    def _parse_vars(cls, data: dict[str, Any]) -> dict[str, str]:
        return {k: str(v) for k, v in data.get("vars", {}).items()}

    @classmethod
    def _parse_fingerprints(cls, data: dict[str, Any]) -> list[Fingerprint]:
        return [
            Fingerprint(
                name=fp_data["name"],
                files=fp_data.get("files", []),
                algorithm=fp_data.get("algorithm", "sha256"),
                length=fp_data.get("length", 12),
            )
            for fp_data in data.get("fingerprint", [])
        ]

    @classmethod
    def _parse_hook_group(cls, group_data: dict[str, Any]) -> HookGroup:
        commands = group_data.get("commands", [])
        conditions_data = group_data.get("conditions")
        if conditions_data is None:
            return HookGroup(commands=commands)

        unknown = tuple(k for k in conditions_data if k not in KNOWN_CONDITION_KEYS)
        return HookGroup(
            commands=commands,
            conditions=HookConditions(
                if_branch_matches=conditions_data.get("if_branch_matches"),
                if_branch_not_matches=conditions_data.get("if_branch_not_matches"),
                unknown_keys=unknown,
            ),
        )

    @classmethod
    def _parse_hooks(cls, data: dict[str, Any]) -> Hooks:
        hooks_data = data.get("hooks", {})
        return Hooks(
            on_setup=[cls._parse_hook_group(g) for g in hooks_data.get("on_setup", [])],
            on_attach=[cls._parse_hook_group(g) for g in hooks_data.get("on_attach", [])],
            on_detach=[cls._parse_hook_group(g) for g in hooks_data.get("on_detach", [])],
            on_teardown=[cls._parse_hook_group(g) for g in hooks_data.get("on_teardown", [])],
        )

    @classmethod
    def _parse_prune(cls, data: dict[str, Any]) -> Prune | None:
        prune_data = data.get("prune")
        return (
            Prune(
                older_than_days=prune_data.get("older_than_days", 30),
                exclude_branches=prune_data.get("exclude_branches", []),
            )
            if prune_data is not None
            else None
        )

    @classmethod
    def load(cls, workspace: Workspace) -> Manifest:
        """
        Reads and parses a workspace manifest from disk.

        The manifest is expected to be a TOML file located under `.workspace`,
        describing workspace configuration such as hooks, links, and prune rules.
        If the file cannot be read or parsed, sane defaults are returned.

        :param workspace: The workspace whose manifest should be loaded.
        :returns: Parsed Manifest instance
        """
        logger.debug("loading manifest from %s", workspace.paths.manifest)
        try:
            data = tomllib.loads(workspace.paths.manifest.read_text())
        except OSError, tomllib.TOMLDecodeError:
            logger.warning(
                "failed to read manifest at %s, falling back to defaults",
                workspace.paths.manifest,
            )
            return Manifest(
                version=cls.DEFAULT_VERSION,
                base_branch=cls.DEFAULT_BRANCH,
            )

        version = cls._parse_version(data)
        base_branch = cls._parse_base_branch(data)
        copies = cls._parse_copies(data)
        links = cls._parse_links(data)
        vars = cls._parse_vars(data)
        fingerprints = cls._parse_fingerprints(data)
        hooks = cls._parse_hooks(data)
        prune = cls._parse_prune(data)

        logger.debug(
            "manifest loaded: version=%d base_branch=%r copies=%d links=%d fingerprints=%d"
            " hooks=(on_setup=%d on_attach=%d on_detach=%d on_teardown=%d) prune=%s",
            version,
            base_branch,
            len(copies),
            len(links),
            len(fingerprints),
            len(hooks.on_setup),
            len(hooks.on_attach),
            len(hooks.on_detach),
            len(hooks.on_teardown),
            f"older_than_days={prune.older_than_days}" if prune else None,
        )
        return Manifest(version, base_branch, copies, links, vars, fingerprints, hooks, prune)
