"""
Configure structlog to write logs to a rotating file.

Call configure_logging(workspace_root) once per command invocation, after the
workspace root is resolved. Logs are written to:

<workspace_root>/.workspace/git-workspace.log

The file rotates at 1 MB.
"""

import logging
import logging.handlers
from pathlib import Path

import structlog


def configure_logging(workspace_root: Path) -> None:
    log_file = workspace_root / ".workspace" / "git-workspace.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s  %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(handler)

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
