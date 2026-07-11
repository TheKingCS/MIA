"""
tests.test_diagnostics_log_viewer
====================================

Unit tests for the pure tail/filter helpers backing the Diagnostics
module's log viewer (modules.diagnostics.module.tail_lines /
filter_lines). The QWidget-building side of get_widget() needs a live
Qt event loop and is exercised manually instead — see
docs/testing/2.6_system_logs_viewer.md.
"""

from __future__ import annotations

from modules.diagnostics.module import filter_lines, tail_lines


def _make_line(level: str, message: str, name: str = "mia.core") -> str:
    # Mirrors core.logger's formatter: "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
    return f"2026-07-11 09:00:00 [{level:<8}] {name}: {message}"


def test_tail_lines_missing_file_returns_empty(tmp_path):
    assert tail_lines(tmp_path / "does_not_exist.log", max_lines=10) == []


def test_tail_lines_returns_all_lines_when_under_limit(tmp_path):
    log_file = tmp_path / "mia.log"
    log_file.write_text("line1\nline2\nline3\n")
    assert tail_lines(log_file, max_lines=10) == ["line1", "line2", "line3"]


def test_tail_lines_returns_only_the_last_n_lines(tmp_path):
    log_file = tmp_path / "mia.log"
    log_file.write_text("\n".join(f"line{i}" for i in range(1, 21)) + "\n")
    result = tail_lines(log_file, max_lines=5)
    assert result == ["line16", "line17", "line18", "line19", "line20"]


def test_filter_lines_by_level_matches_padded_formatter_output():
    lines = [
        _make_line("DEBUG", "debug message"),
        _make_line("INFO", "info message"),
        _make_line("WARNING", "warning message"),
        _make_line("ERROR", "error message"),
        _make_line("CRITICAL", "critical message"),
    ]
    assert filter_lines(lines, level="INFO", query="") == [lines[1]]
    assert filter_lines(lines, level="CRITICAL", query="") == [lines[4]]


def test_filter_lines_level_all_returns_everything():
    lines = [_make_line("DEBUG", "a"), _make_line("INFO", "b")]
    assert filter_lines(lines, level="ALL", query="") == lines


def test_filter_lines_by_query_is_case_insensitive():
    lines = [
        _make_line("INFO", "Discovered module: Notes", name="mia.core.module_manager"),
        _make_line("INFO", "Discovered module: Music", name="mia.core.module_manager"),
    ]
    assert filter_lines(lines, level="ALL", query="notes") == [lines[0]]


def test_filter_lines_combines_level_and_query():
    lines = [
        _make_line("INFO", "hello"),
        _make_line("ERROR", "hello"),
        _make_line("ERROR", "goodbye"),
    ]
    assert filter_lines(lines, level="ERROR", query="hello") == [lines[1]]
