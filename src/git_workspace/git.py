from git_workspace.errors import GitCloneError
import subprocess
import structlog

logger = structlog.get_logger(__name__)


def clone(url: str, target: str | None = None, bare: bool = False) -> None:
    """
    Clones a git repository

    :param url: The url of the git repository
    :param target: The target folder to clone to
    :param bare: Whether to clone bare or not
    :raises GitCloneError: If the clone fails
    """
    log = logger.bind(url=url, target=target, bare=bare)

    cmd = ["git", "clone", url]
    if bare:
        cmd.append("--bare")
    if target:
        cmd.append(target)

    log.debug("Attempting to clone git repository")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitCloneError(f"Failed to clone {url!r}")

    log.debug("Git repository cloned successfully")
