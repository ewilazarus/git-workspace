from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.manifest import Hooks, Link, Manifest, Prune


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    return mocker.MagicMock()


class TestLoad:
    def test_returns_default_manifest_on_os_error(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.side_effect = OSError

        result = Manifest.load(workspace)

        assert result.version == Manifest.DEFAULT_VERSION
        assert result.base_branch == Manifest.DEFAULT_BRANCH

    def test_returns_default_manifest_on_toml_decode_error(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = "!!! invalid toml"

        result = Manifest.load(workspace)

        assert result.version == Manifest.DEFAULT_VERSION
        assert result.base_branch == Manifest.DEFAULT_BRANCH

    def test_parses_version_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = "version = 2"

        result = Manifest.load(workspace)

        assert result.version == 2

    def test_uses_default_version_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.version == Manifest.DEFAULT_VERSION

    def test_parses_base_branch_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = 'base_branch = "develop"'

        result = Manifest.load(workspace)

        assert result.base_branch == "develop"

    def test_uses_default_base_branch_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.base_branch == Manifest.DEFAULT_BRANCH

    def test_parses_links_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[link]]
source = "env"
target = ".env"
override = true
"""

        result = Manifest.load(workspace)

        assert result.links == [Link(source="env", target=".env", override=True)]

    def test_link_override_defaults_to_false_when_absent(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[link]]
source = "env"
target = ".env"
"""

        result = Manifest.load(workspace)

        assert result.links == [Link(source="env", target=".env", override=False)]

    def test_returns_empty_links_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.links == []

    def test_parses_vars_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[vars]
FOO = "bar"
BAZ = "qux"
"""

        result = Manifest.load(workspace)

        assert result.vars == {"FOO": "bar", "BAZ": "qux"}

    def test_returns_empty_vars_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.vars == {}

    def test_parses_hooks_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[hooks]
on_setup = ["setup.sh"]
on_activate = ["activate.sh"]
on_attach = ["attach.sh"]
on_deactivate = ["deactivate.sh"]
on_remove = ["remove.sh"]
"""

        result = Manifest.load(workspace)

        assert result.hooks == Hooks(
            on_setup=["setup.sh"],
            on_activate=["activate.sh"],
            on_attach=["attach.sh"],
            on_deactivate=["deactivate.sh"],
            on_remove=["remove.sh"],
        )

    def test_returns_default_hooks_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.hooks == Hooks()

    def test_parses_prune_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[prune]
older_than_days = 7
exclude_branches = ["main", "develop"]
"""

        result = Manifest.load(workspace)

        assert result.prune == Prune(
            older_than_days=7,
            exclude_branches=["main", "develop"],
        )

    def test_returns_none_for_prune_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.prune is None
