"""
tests.test_orb_presence
=========================

MIA's floating desktop orb (gui/orb_presence.py, Zac 2026-11-08): a frameless, transparent, always-on-top window
that reuses the presence orb with no label, bobs where it stands, and wakes her (emits `activated`) on Enter or a
plain click but not a drag.
"""

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication


@pytest.fixture
def qapp():
    """One offscreen QApplication for the Qt widgets (conftest sets QT_QPA_PLATFORM=offscreen)."""
    return QApplication.instance() or QApplication([])


def _press(pos):
    """A left-button press at a point."""
    return QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPointF(*pos), QPointF(*pos),
                       Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)


def _release(pos):
    """A left-button release at a point."""
    return QMouseEvent(QMouseEvent.Type.MouseButtonRelease, QPointF(*pos), QPointF(*pos),
                       Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)


def _move(pos):
    """A move at a point with the left button held."""
    return QMouseEvent(QMouseEvent.Type.MouseMove, QPointF(*pos), QPointF(*pos),
                       Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)


def test_the_orb_window_is_frameless_translucent_on_top_and_unlabelled(qapp):
    from gui.orb_presence import OrbPresence

    orb = OrbPresence(diameter=200)
    flags = orb.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert orb.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert (orb.width(), orb.height()) == (200, 200)
    assert orb._orb._glyph == ""  # just the orb and the rings, no label
    orb.close()


def test_it_bobs_in_place_without_drifting_sideways(qapp):
    from gui.orb_presence import OrbPresence

    orb = OrbPresence(diameter=120)
    orb.show_centered()
    x0 = orb.x()
    ys = set()
    for _ in range(40):
        orb._float_tick()
        ys.add(orb.y())
        assert orb.x() == x0  # bobs vertically only
    assert len(ys) > 1  # it actually moves
    orb.close()


def test_enter_wakes_her_and_escape_hides_her(qapp):
    from gui.orb_presence import OrbPresence

    orb = OrbPresence(diameter=120)
    woke = []
    orb.activated.connect(lambda: woke.append(1))
    orb.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.KeyboardModifier.NoModifier))
    assert woke == [1]
    orb.show()
    orb.keyPressEvent(QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier))
    assert orb.isHidden()
    orb.close()


def test_a_plain_click_wakes_her_but_a_drag_does_not(qapp):
    from gui.orb_presence import OrbPresence

    orb = OrbPresence(diameter=120)
    orb.show_centered()
    woke = []
    orb.activated.connect(lambda: woke.append(1))

    orb.mousePressEvent(_press((10, 10)))
    orb.mouseReleaseEvent(_release((10, 11)))  # within the slop -> a click
    assert woke == [1]

    orb.mousePressEvent(_press((10, 10)))
    orb.mouseMoveEvent(_move((80, 90)))  # travelled -> a drag
    orb.mouseReleaseEvent(_release((80, 90)))
    assert woke == [1]  # still just the one wake
    orb.close()
