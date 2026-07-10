#!/usr/bin/env python3
"""
main.py
=======

Entry point for M.I.A. (Multifunctional Intelligent Assistant).

This file is intentionally minimal and should stay that way. All
startup sequencing lives in core.application.MIAApplication — see that
module for the boot flow (splash -> core init -> module discovery ->
setup wizard or main window).
"""

import sys

from core.application import MIAApplication
from core.logger import get_logger

log = get_logger(__name__)


def _log_uncaught_exceptions(exc_type, exc_value, exc_traceback) -> None:
    """
    Ensure any crash is written to logs/mia.log (and thus journalctl,
    when running as the systemd service) before the process exits.
    Without this, a kiosk-mode crash on a headless Pi leaves no trace
    of what went wrong. systemd's Restart=always then brings M.I.A.
    back up automatically — see deploy/mia.service.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log.critical("Unhandled exception — M.I.A. is crashing.", exc_info=(exc_type, exc_value, exc_traceback))


def main() -> int:
    sys.excepthook = _log_uncaught_exceptions
    app = MIAApplication()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
