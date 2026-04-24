from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from git_workspace.errors import InvalidInputError


def directory_birthtime(dir: Path) -> datetime:
    """
    Return the creation time of a directory.

    Falls back to ctime on platforms that do not expose birthtime (e.g. Linux ext4).

    :param dir: The directory whose creation time should be returned.
    :returns: The creation timestamp as a ``datetime``.
    """
    stat = dir.stat()
    ts = getattr(stat, "st_birthtime", None) or stat.st_ctime
    return datetime.fromtimestamp(ts)


def extract_humanish_suffix(url: str) -> str:
    """
    Extracts a human-readable suffix from a URL.

    Examples:
    - https://github.com/ewilazarus/dotfiles -> dotfiles
    - https://github.com/ewilazarus/dotfiles.git -> dotfiles
    - git@github.com:ewilazarus/dotfiles -> dotfiles
    - https://example.com/archive.tar.gz -> archive

    :param url: The URL to have the suffix extracted from
    :return: The extracted suffix
    :raises InvalidInputError: If no valid suffix can be extracted
    """
    if not url:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    # Handle SCP-like URLs such as git@github.com:user/repo
    if "://" not in url and "@" in url and ":" in url:
        path = url.split(":", 1)[1]
    else:
        path = urlparse(url).path

    path = path.rstrip("/")

    if not path:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    name = PurePosixPath(path).name

    if not name:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    while True:
        stem = PurePosixPath(name).stem
        if stem == name:
            break
        name = stem

    if not name:
        raise InvalidInputError(f"Could not extract suffix from URL: {url!r}")

    return name
