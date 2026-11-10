"""
tests.test_logger
===================

core/logger.py: an exception that ends a background thread reaches MIA's
log with its traceback (2026-11-10), and is still handed on to the hook
that was there before. pytest swaps in its own thread hook per test, so
the test installs MIA's over a stand-in and calls it directly.
"""

from __future__ import annotations

import logging
import sys
import threading
from types import SimpleNamespace

import core.logger as logger_module


def test_an_error_that_ends_a_thread_reaches_mia_s_log_and_is_handed_on(caplog, monkeypatch):
    handed_on = []
    monkeypatch.setattr(threading, "excepthook", handed_on.append)
    logger_module._log_thread_exceptions()
    caplog.set_level(logging.ERROR, logger="mia.threads")
    try:
        raise ValueError("the sync helper broke")
    except ValueError:
        kind, value, trace = sys.exc_info()
    args = SimpleNamespace(exc_type=kind, exc_value=value, exc_traceback=trace,
                           thread=SimpleNamespace(name="sync-helper"))
    threading.excepthook(args)
    assert any("sync-helper" in r.getMessage() and r.exc_info and r.exc_info[0] is ValueError for r in caplog.records)
    assert handed_on == [args]


def test_a_thread_that_exits_on_purpose_is_not_logged_as_an_error(caplog, monkeypatch):
    monkeypatch.setattr(threading, "excepthook", lambda args: None)
    logger_module._log_thread_exceptions()
    caplog.set_level(logging.ERROR, logger="mia.threads")
    threading.excepthook(SimpleNamespace(exc_type=SystemExit, exc_value=SystemExit(0), exc_traceback=None,
                                         thread=SimpleNamespace(name="done")))
    assert not caplog.records
