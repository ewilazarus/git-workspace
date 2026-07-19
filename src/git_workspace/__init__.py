import logging
import os
import sys

from git_workspace import cli
from git_workspace.errors import GitWorkspaceError, WorkspaceLockedError
from git_workspace.ui import console

# Exit code for lock contention (EX_TEMPFAIL): the operation did not run
# because another one holds the worktree's lifecycle lock. External hosts
# (e.g. the herdr plugin) treat this as "retry later", not as a failure.
EXIT_CODE_LOCKED = 75

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
    except WorkspaceLockedError as e:
        console.error(str(e))
        logger.exception("Failed to run command")
        sys.exit(EXIT_CODE_LOCKED)
    except GitWorkspaceError as e:
        console.error(str(e))
        logger.exception("Failed to run command")
        sys.exit(1)
