from pathlib import Path
from unittest.mock import MagicMock

from git_workspace import git

PATH = Path("/workspace/feat/001")


def test_get_commit_timestamp_happy_path(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="1712700000\n")

    result = git.get_commit_timestamp(PATH)

    assert result == 1712700000


def test_get_commit_timestamp_when_git_fails(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=128, stdout="")

    result = git.get_commit_timestamp(PATH)

    assert result is None


def test_get_commit_timestamp_with_invalid_output(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="not-a-number\n")

    result = git.get_commit_timestamp(PATH)

    assert result is None


def test_get_commit_timestamp_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="1712700000\n")

    git.get_commit_timestamp(PATH, ref="main")

    subprocess.run.assert_called_with(
        ["git", "log", "-1", "--format=%ct", "main"],
        capture_output=True,
        text=True,
        cwd=str(PATH),
    )


def test_get_short_commit_id_happy_path(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="abc1234\n")

    result = git.get_short_commit_id(PATH)

    assert result == "abc1234"


def test_get_short_commit_id_when_git_fails(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=128, stdout="")

    result = git.get_short_commit_id(PATH)

    assert result is None


def test_get_short_commit_id_with_whitespace_only(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="   \n")

    result = git.get_short_commit_id(PATH)

    assert result is None


def test_get_short_commit_id_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="abc1234\n")

    git.get_short_commit_id(PATH, ref="main")

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--short=7", "main"],
        capture_output=True,
        text=True,
        cwd=str(PATH),
    )
