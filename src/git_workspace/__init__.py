import logging

import structlog

from git_workspace import cli


def main() -> None:
    # Route structlog through stdlib logging with a NullHandler so no debug
    # output appears until configure_logging() sets up the rotating file sink.
    logging.getLogger().addHandler(logging.NullHandler())
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    cli.app()
