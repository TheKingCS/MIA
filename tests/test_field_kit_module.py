"""
tests.test_field_kit_module
==============================

Unit test for modules.field_kit.module.format_script_row — pure
formatting logic, no Qt event loop needed. Same shape as
tests/test_notes_module.py's format_entry_row test: the widget-building
(QTabWidget, device list, script list) and worker-thread wiring in
FieldKitModule needs a real Qt event loop to exercise meaningfully, so
that was verified with a manual headless smoke test instead (offscreen
QPA platform) rather than unit-tested here.
"""

from __future__ import annotations

from core.script_library_manager import Script
from modules.field_kit.module import format_script_row


def test_formats_script_with_category():
    script = Script(script_id="1", name="Ping Sweep", interpreter="shell", category="Network")
    assert format_script_row(script) == "[Network]  Ping Sweep  (shell)"


def test_formats_script_without_category():
    script = Script(script_id="1", name="Ping Sweep", interpreter="python", category="")
    assert format_script_row(script) == "Ping Sweep  (python)"
