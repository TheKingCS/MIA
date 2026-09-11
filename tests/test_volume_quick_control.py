"""
tests.test_volume_quick_control
==================================

Unit tests for gui.widgets.volume_quick_control's pure
format_volume_line() — moved here 2026-09-11 from
tests/test_home_dashboard.py, alongside removing gui/home_dashboard.py's
own dead copy of this function (and the entire dashboard-grid Volume
widget it only ever served) — see that module's 2026-07-18 docstring
note: Volume moved into the header profile menu, and
gui/widgets/volume_quick_control.py's own format_volume_line() has been
the real, live one ever since. This is real test coverage that
previously only existed for the dead copy.
"""

from __future__ import annotations

from core.volume_manager import VolumeStatus
from gui.widgets.volume_quick_control import format_volume_line


def test_format_volume_line_unavailable():
    assert format_volume_line(None) == "Not available on this device."


def test_format_volume_line_normal():
    assert format_volume_line(VolumeStatus(percent=62, muted=False)) == "62%"


def test_format_volume_line_muted():
    assert format_volume_line(VolumeStatus(percent=62, muted=True)) == "62%  —  Muted"
