import logging
import os
import sys

from git_workspace import cli
from git_workspace.errors import GitWorkspaceError
from git_workspace.ui import print_error

_level_name = os.environ.get("GIT_WORKSPACE_LOG_LEVEL", "").upper()
_level = getattr(logging, _level_name, logging.CRITICAL)
logging.basicConfig(
    level=_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        cli.app()
    except GitWorkspaceError as e:
        print_error(str(e))
        logger.exception("Failed to run command")
