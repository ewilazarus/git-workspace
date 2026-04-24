import logging
import os
import sys

from git_workspace import cli
from git_workspace.errors import GitWorkspaceError
from git_workspace.ui import console

LOG_LEVEL = getattr(
    logging, os.environ.get("GIT_WORKSPACE_LOG_LEVEL", "").upper(), logging.CRITICAL
)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        cli.app()
    except GitWorkspaceError as e:
        console.error(str(e))
        logger.exception("Failed to run command")
