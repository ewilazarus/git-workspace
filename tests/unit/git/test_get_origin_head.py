from unittest.mock import MagicMock

from git_workspace import git


def test_happy_path(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(
        returncode=0, stdout="refs/remotes/origin/main\n"
    )

    result = git.get_origin_head()

    assert result == "main"


def test_when_origin_head_not_set_then_returns_none(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(returncode=128)

    result = git.get_origin_head()

    assert result is None


def test_invokes_git_correctly(subprocess: MagicMock) -> None:
    subprocess.run.return_value = MagicMock(
        returncode=0, stdout="refs/remotes/origin/main\n"
    )

    git.get_origin_head()

    subprocess.run.assert_called_with(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        capture_output=True,
        text=True,
        cwd=None,
    )
