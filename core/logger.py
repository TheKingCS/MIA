"""
core.logger
===========

Centralized logging setup for MIA

Every part of the system (core services, modules, GUI) should log through
the logger returned by `get_logger()` rather than using `print()`. This
keeps a persistent record in logs/ that's essential for an offline field
tool where the user may not have easy access to a developer console.

Usage
-----
    from core.logger import get_logger
    log = get_logger(__name__)
    log.info("Module loaded")

An exception that ends a background thread (the phone server's helpers,
the desktop's workers, sync) is logged here too, with its traceback
(2026-11-10): before, Python printed it to a console nobody sees and it
never reached logs/, so a thread could fail quietly for days.
"""

from __future__ import annotations

import logging
import logging.handlers
import threading
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "mia.log"
_CONFIGURED = False


def _configure_root_logger() -> None:
    """Set up the root 'mia' logger once, with both file and console output, and thread exceptions logged."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("mia")
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating file handler: keeps logs from growing unbounded over the
    # lifetime of a long-running field deployment.
    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    _log_thread_exceptions()

    _CONFIGURED = True


def _log_thread_exceptions() -> None:
    """Makes an exception that ends a thread go to MIA's log (as an error, with the traceback) before Python's own
    handler reports it as it always did."""
    previous = threading.excepthook

    def hook(args) -> None:
        """Logs the thread's exception, then hands it on."""
        if args.exc_type is not SystemExit:
            name = args.thread.name if args.thread is not None else "a thread"
            logging.getLogger("mia.threads").error("The thread %s stopped on an error.", name,
                                                   exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        previous(args)

    threading.excepthook = hook


def get_logger(name: str = "mia") -> logging.Logger:
    """
    Return a logger namespaced under 'mia'.

    Modules should call this with __name__ so log lines are traceable to
    their source, e.g. get_logger(__name__) inside modules/notes/module.py
    produces log lines tagged 'mia.modules.notes.module'.
    """
    _configure_root_logger()
    if name == "mia" or name.startswith("mia."):
        return logging.getLogger(name)
    return logging.getLogger(f"mia.{name}")
