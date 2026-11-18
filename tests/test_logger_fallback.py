"""Tests for the logger's fallback (core/logger.py): a log folder that can't be written leaves console logging, so
her shell still starts on a read-only image (FW-03's first VM run)."""
import logging

from core import logger


def test_a_log_folder_that_cant_be_written_leaves_the_console(tmp_path, monkeypatch):
    """The folder is a file, so it can't be made: no file handler, a console one, and no exception."""
    blocked = tmp_path / "not_a_folder"
    blocked.write_text("x")
    monkeypatch.setattr(logger, "_LOG_DIR", blocked / "logs")
    monkeypatch.setattr(logger, "_LOG_FILE", blocked / "logs" / "mia.log")
    monkeypatch.setattr(logger, "_CONFIGURED", False)
    root = logging.getLogger("mia")
    kept = list(root.handlers)
    root.handlers = []
    try:
        logger._configure_root_logger()
        kinds = [type(h) for h in root.handlers]
        assert logging.handlers.RotatingFileHandler not in kinds and logging.StreamHandler in kinds
    finally:
        root.handlers = kept
