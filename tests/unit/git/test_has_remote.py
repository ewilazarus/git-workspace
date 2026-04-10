from unittest.mock import MagicMock

from git_workspace import git


def test_returns_true_when_origin_exists(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="origin\n")

    assert git.has_remote() is True


def test_returns_false_when_no_remotes(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="")

    assert git.has_remote() is False


def test_returns_false_when_origin_not_in_remotes(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="upstream\n")

    assert git.has_remote() is False


def test_returns_true_for_custom_remote_name(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="upstream\n")

    assert git.has_remote("upstream") is True


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0, stdout="origin\n")

    git.has_remote()

    subprocess.run.assert_called_with(["git", "remote"], capture_output=True, text=True, cwd=None)
