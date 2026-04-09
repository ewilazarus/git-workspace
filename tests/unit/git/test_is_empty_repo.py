from unittest.mock import MagicMock

from git_workspace import git


def test_returns_true_when_head_does_not_resolve(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=1)

    assert git.is_empty_repo() is True


def test_returns_false_when_head_resolves(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=0)

    assert git.is_empty_repo() is False


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    git.is_empty_repo()

    subprocess.run.assert_called_with(
        ["git", "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
    )
