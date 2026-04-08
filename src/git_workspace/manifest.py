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
class Manifest:
    version: int
    base_branch: str | None = None
    links: list[Link] = field(default_factory=list)
    hooks: Hooks | None = None


def read_manifest(path: Path) -> Manifest:
    raise NotImplementedError
