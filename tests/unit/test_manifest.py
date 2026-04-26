from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.fingerprint import DEFAULT_ALGORITHM, DEFAULT_LENGTH
from git_workspace.manifest import (
    Fingerprint,
    HookGroup,
    Hooks,
    Link,
    Manifest,
    Prune,
)


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

    def test_parses_non_string_vars_as_strings(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[vars]
PORT = 8080
DEBUG = true
"""

        result = Manifest.load(workspace)

        assert result.vars == {"PORT": "8080", "DEBUG": "True"}

    def test_parses_hooks_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
commands = ["setup.sh"]

[[hooks.on_attach]]
commands = ["attach.sh"]

[[hooks.on_detach]]
commands = ["detach.sh"]

[[hooks.on_teardown]]
commands = ["teardown.sh"]
"""

        result = Manifest.load(workspace)

        assert result.hooks == Hooks(
            on_setup=[HookGroup(commands=["setup.sh"])],
            on_attach=[HookGroup(commands=["attach.sh"])],
            on_detach=[HookGroup(commands=["detach.sh"])],
            on_teardown=[HookGroup(commands=["teardown.sh"])],
        )

    def test_returns_default_hooks_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.hooks == Hooks()


class TestParseHooks:
    @pytest.fixture
    def workspace(self, mocker: MockerFixture) -> MagicMock:
        return mocker.MagicMock()

    def test_missing_commands_defaults_to_empty(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
"""

        result = Manifest.load(workspace)

        assert result.hooks.on_setup == [HookGroup(commands=[])]

    def test_missing_conditions_is_none(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
commands = ["setup.sh"]
"""

        result = Manifest.load(workspace)

        assert result.hooks.on_setup[0].conditions is None

    def test_if_branch_matches_condition(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
conditions = { if_branch_matches = "gabriel/*" }
commands = ["setup.sh"]
"""

        result = Manifest.load(workspace)

        cond = result.hooks.on_setup[0].conditions
        assert cond is not None
        assert cond.if_branch_matches == "gabriel/*"
        assert cond.if_branch_not_matches is None

    def test_if_branch_not_matches_condition(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
conditions = { if_branch_not_matches = "feat/wip-*" }
commands = ["setup.sh"]
"""

        result = Manifest.load(workspace)

        cond = result.hooks.on_setup[0].conditions
        assert cond is not None
        assert cond.if_branch_not_matches == "feat/wip-*"
        assert cond.if_branch_matches is None

    def test_both_condition_keys_present(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
conditions = { if_branch_matches = "gabriel/*", if_branch_not_matches = "gabriel/wip-*" }
commands = ["setup.sh"]
"""

        result = Manifest.load(workspace)

        cond = result.hooks.on_setup[0].conditions
        assert cond is not None
        assert cond.if_branch_matches == "gabriel/*"
        assert cond.if_branch_not_matches == "gabriel/wip-*"

    def test_unknown_condition_keys_captured(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
conditions = { if_branch_match = "typo/*" }
commands = ["setup.sh"]
"""

        result = Manifest.load(workspace)

        cond = result.hooks.on_setup[0].conditions
        assert cond is not None
        assert "if_branch_match" in cond.unknown_keys

    def test_multiple_groups_preserve_order(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[hooks.on_setup]]
commands = ["first.sh"]

[[hooks.on_setup]]
conditions = { if_branch_matches = "feat/*" }
commands = ["second.sh"]

[[hooks.on_setup]]
commands = ["third.sh"]
"""

        result = Manifest.load(workspace)

        assert len(result.hooks.on_setup) == 3
        assert result.hooks.on_setup[0].commands == ["first.sh"]
        assert result.hooks.on_setup[1].commands == ["second.sh"]
        assert result.hooks.on_setup[2].commands == ["third.sh"]

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

    def test_parses_fingerprint_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[fingerprint]]
name = "docker-deps"
files = ["package.json", "package-lock.json"]
algorithm = "md5"
length = 8
"""

        result = Manifest.load(workspace)

        assert result.fingerprints == [
            Fingerprint(
                name="docker-deps",
                files=["package.json", "package-lock.json"],
                algorithm="md5",
                length=8,
            )
        ]

    def test_fingerprint_algorithm_defaults_to_sha256(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[fingerprint]]
name = "deps"
files = ["a.txt"]
"""

        result = Manifest.load(workspace)

        assert result.fingerprints[0].algorithm == DEFAULT_ALGORITHM

    def test_fingerprint_length_defaults_to_12(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[fingerprint]]
name = "deps"
files = ["a.txt"]
"""

        result = Manifest.load(workspace)

        assert result.fingerprints[0].length == DEFAULT_LENGTH

    def test_parses_multiple_fingerprint_blocks_in_order(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = """
[[fingerprint]]
name = "alpha"
files = ["a.txt"]

[[fingerprint]]
name = "beta"
files = ["b.txt"]
"""

        result = Manifest.load(workspace)

        assert [fp.name for fp in result.fingerprints] == ["alpha", "beta"]

    def test_returns_empty_fingerprints_when_absent_from_toml(self, workspace: MagicMock) -> None:
        workspace.paths.manifest.read_text.return_value = ""

        result = Manifest.load(workspace)

        assert result.fingerprints == []
