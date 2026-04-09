from pathlib import Path

import pytest

from git_workspace.manifest import Hooks, Link, Manifest, Prune, read_manifest


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "manifest.toml"
    p.write_text(content)
    return p


def test_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    manifest = read_manifest(tmp_path / "nonexistent.toml")

    assert manifest.version == 1
    assert manifest.base_branch == "main"
    assert manifest.hooks == Hooks()
    assert manifest.links == []
    assert manifest.vars == {}
    assert manifest.prune is None


def test_returns_defaults_when_file_is_invalid_toml(tmp_path: Path) -> None:
    path = _write(tmp_path, "this is not [ valid toml !!!")

    manifest = read_manifest(path)

    assert manifest.version == 1
    assert manifest.base_branch == "main"


def test_parses_version_and_base_branch(tmp_path: Path) -> None:
    path = _write(tmp_path, """
version = 2
base_branch = "develop"
""")

    manifest = read_manifest(path)

    assert manifest.version == 2
    assert manifest.base_branch == "develop"


def test_missing_fields_use_defaults(tmp_path: Path) -> None:
    path = _write(tmp_path, "")

    manifest = read_manifest(path)

    assert manifest.version == 1
    assert manifest.base_branch == "main"


def test_parses_vars(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[vars]
db_url = "postgres://localhost/mydb"
api_key = "secret"
""")

    manifest = read_manifest(path)

    assert manifest.vars == {"db_url": "postgres://localhost/mydb", "api_key": "secret"}


def test_parses_hooks(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[hooks]
after_setup = ["install.sh", "configure.sh"]
before_activate = ["pre.sh"]
after_activate = ["activate.sh"]
before_remove = ["teardown.sh"]
after_remove = ["cleanup.sh"]
""")

    manifest = read_manifest(path)

    assert manifest.hooks == Hooks(
        after_setup=["install.sh", "configure.sh"],
        before_activate=["pre.sh"],
        after_activate=["activate.sh"],
        before_remove=["teardown.sh"],
        after_remove=["cleanup.sh"],
    )


def test_missing_hook_fields_default_to_empty(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[hooks]
after_setup = ["install.sh"]
""")

    manifest = read_manifest(path)

    assert manifest.hooks.after_setup == ["install.sh"]
    assert manifest.hooks.before_activate == []
    assert manifest.hooks.after_activate == []
    assert manifest.hooks.before_remove == []
    assert manifest.hooks.after_remove == []


def test_parses_links(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[[links]]
source = "env"
target = ".env"

[[links]]
source = "secrets"
target = ".secrets"
override = true
""")

    manifest = read_manifest(path)

    assert manifest.links == [
        Link(source="env", target=".env", override=False),
        Link(source="secrets", target=".secrets", override=True),
    ]


def test_link_override_defaults_to_false(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[[links]]
source = "env"
target = ".env"
""")

    manifest = read_manifest(path)

    assert manifest.links[0].override is False


def test_parses_prune(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[prune]
older_than_days = 14
exclude_branches = ["main", "develop"]
""")

    manifest = read_manifest(path)

    assert manifest.prune == Prune(older_than_days=14, exclude_branches=["main", "develop"])


def test_prune_fields_default_when_section_present(tmp_path: Path) -> None:
    path = _write(tmp_path, """
[prune]
""")

    manifest = read_manifest(path)

    assert manifest.prune == Prune(older_than_days=30, exclude_branches=[])


def test_prune_is_none_when_section_absent(tmp_path: Path) -> None:
    path = _write(tmp_path, "")

    manifest = read_manifest(path)

    assert manifest.prune is None


def test_parses_full_manifest(tmp_path: Path) -> None:
    path = _write(tmp_path, """
version = 1
base_branch = "main"

[vars]
db_url = "sqlite://"

[hooks]
after_setup = ["install.sh"]
after_activate = ["activate.sh"]

[[links]]
source = "env"
target = ".env"

[prune]
older_than_days = 7
exclude_branches = ["main"]
""")

    manifest = read_manifest(path)

    assert manifest == Manifest(
        version=1,
        base_branch="main",
        vars={"db_url": "sqlite://"},
        hooks=Hooks(after_setup=["install.sh"], after_activate=["activate.sh"]),
        links=[Link(source="env", target=".env")],
        prune=Prune(older_than_days=7, exclude_branches=["main"]),
    )
