from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from git_workspace.assets import IgnoreManager


@pytest.fixture
def workspace(mocker: MockerFixture) -> MagicMock:
    mock = mocker.MagicMock()
    mock.paths.ignore_file = mocker.MagicMock()
    return mock


@pytest.fixture
def ignore_manager(workspace: MagicMock) -> IgnoreManager:
    return IgnoreManager(workspace)


class TestComposeIgnoreBlock:
    def test_wraps_entries_between_markers(self, ignore_manager: IgnoreManager) -> None:
        entries = [Path("/workspace/.env"), Path("/workspace/.config")]

        result = ignore_manager._compose_ignore_block(entries)

        assert result == (
            f"{IgnoreManager.BEGIN_IGNORE_MARKER}\n"
            "/workspace/.env\n"
            "/workspace/.config\n"
            f"{IgnoreManager.END_IGNORE_MARKER}"
        )

    def test_returns_empty_block_when_no_entries(
        self, ignore_manager: IgnoreManager
    ) -> None:
        result = ignore_manager._compose_ignore_block([])

        assert result == (
            f"{IgnoreManager.BEGIN_IGNORE_MARKER}\n{IgnoreManager.END_IGNORE_MARKER}"
        )


class TestSync:
    def test_reads_ignore_file(self, ignore_manager: MagicMock) -> None:
        ignore_manager._workspace.paths.ignore_file.read_text.return_value = ""

        ignore_manager.sync([])

        ignore_manager._workspace.paths.ignore_file.read_text.assert_called_once()

    def test_removes_existing_managed_block(self, ignore_manager: MagicMock) -> None:
        existing_block = (
            f"{IgnoreManager.BEGIN_IGNORE_MARKER}\n"
            "old_entry\n"
            f"{IgnoreManager.END_IGNORE_MARKER}"
        )
        ignore_manager._workspace.paths.ignore_file.read_text.return_value = (
            f"existing content\n{existing_block}"
        )

        ignore_manager.sync([])

        written = ignore_manager._workspace.paths.ignore_file.write_text.call_args.args[
            0
        ]
        assert IgnoreManager.BEGIN_IGNORE_MARKER not in written.split("\n")[0]
        assert "old_entry" not in written

    def test_writes_new_block_to_ignore_file(self, ignore_manager: MagicMock) -> None:
        ignore_manager._workspace.paths.ignore_file.read_text.return_value = ""
        entry = Path("/workspace/.env")

        ignore_manager.sync([entry])

        written = ignore_manager._workspace.paths.ignore_file.write_text.call_args.args[
            0
        ]
        assert str(entry) in written
        assert IgnoreManager.BEGIN_IGNORE_MARKER in written
        assert IgnoreManager.END_IGNORE_MARKER in written

    def test_preserves_existing_content_outside_managed_block(
        self, ignore_manager: MagicMock
    ) -> None:
        ignore_manager._workspace.paths.ignore_file.read_text.return_value = (
            "pre-existing line"
        )

        ignore_manager.sync([])

        written = ignore_manager._workspace.paths.ignore_file.write_text.call_args.args[
            0
        ]
        assert "pre-existing line" in written
