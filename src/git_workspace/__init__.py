import sys

import structlog

from git_workspace import cli


def main() -> None:
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
    cli.app()
