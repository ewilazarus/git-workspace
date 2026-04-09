from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Link:
    source: str
    target: str
    override: bool = False


@dataclass
class Hooks:
    after_setup: list[str] = field(default_factory=list)
    before_activate: list[str] = field(default_factory=list)
    after_activate: list[str] = field(default_factory=list)
    before_remove: list[str] = field(default_factory=list)
    after_remove: list[str] = field(default_factory=list)


@dataclass
class Prune:
    older_than_days: int = 30
    exclude_branches: list[str] = field(default_factory=list)


@dataclass
class Manifest:
    version: int = 1
    base_branch: str = "main"
    hooks: Hooks | None = None
    links: list[Link] = field(default_factory=list)
    prune: Prune | None = None


def read_manifest(path: Path) -> Manifest:
    raise NotImplementedError
