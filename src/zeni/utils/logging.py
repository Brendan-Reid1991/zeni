"""Logging configuration for Zeni."""

import logging
import sys

_DEFAULT_FMT = "%(levelname)-8s %(name)s: %(message)s"
_FILE_FMT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """Configure logging for the zeni package.

    Parameters
    ----------
    level : str
        Console log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    log_file : str, optional
        Path to a log file. When provided, all DEBUG+ messages are
        written to the file regardless of the console level.
    """
    root = logging.getLogger("zeni")
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(getattr(logging, level.upper()))
    console.setFormatter(logging.Formatter(_DEFAULT_FMT))
    root.addHandler(console)

    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_FILE_FMT))
        root.addHandler(fh)
