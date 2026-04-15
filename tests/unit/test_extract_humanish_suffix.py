import pytest

from git_workspace import utils
from git_workspace.errors import InvalidInputError


@pytest.mark.parametrize(
    "url, expected_suffix",
    [
        ("https://github.com/ewilazarus/dotfiles", "dotfiles"),
        ("https://github.com/ewilazarus/dotfiles.git", "dotfiles"),
        ("git@github.com:ewilazarus/dotfiles", "dotfiles"),
        ("git@github.com:ewilazarus/dotfiles.git", "dotfiles"),
        ("https://example.com/archive.tar.gz", "archive"),
        ("https://example.com/assets/app.min.js", "app"),
        ("https://example.com/some/path/project/", "project"),
        ("ssh://git@github.com/ewilazarus/dotfiles.git", "dotfiles"),
        ("file:///Users/ewilazarus/code/dotfiles.git", "dotfiles"),
        ("https://example.com/foo.bar.baz", "foo"),
    ],
)
def test_when_url_contains_a_valid_humanish_suffix_then_succeeds_to_extract_it(
    url: str,
    expected_suffix: str,
) -> None:
    suffix = utils.extract_humanish_suffix(url)

    assert suffix == expected_suffix


@pytest.mark.parametrize(
    "url",
    [
        (""),
        ("https://github.com"),
        ("https://github.com/"),
        ("git@github.com:"),
        ("ssh://git@github.com"),
        ("file:///"),
        ("/"),
    ],
)
def test_when_url_does_not_contain_a_valid_humanish_suffix_then_fails_to_extract_it(
    url: str,
) -> None:
    with pytest.raises(InvalidInputError):
        utils.extract_humanish_suffix(url)
