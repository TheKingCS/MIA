"""
gui.widgets.glow
====================

apply_panel_glow() — a thin, shared wrapper around
`QGraphicsDropShadowEffect`, the "MIA Smart User OS Design" handoff's
HUD panel glow (that bundle's README.md, "v2 additions — the HUD
layer": panel glow `0 0 26px rgba(56,217,201,.10)`). Same technique
`gui/home_dashboard.py`'s existing card-lift shadow already uses
(`QGraphicsDropShadowEffect` with a blur radius, offset, and color) —
just parameterized for a colored glow instead of a generic black
drop-shadow, shared here so it isn't reimplemented per call site.

QSS has no `box-shadow` — glows are necessarily applied in Python on
the widget itself, not the stylesheet (see `gui/styles.py`'s own note
on this), and `QGraphicsDropShadowEffect` is an approximation of CSS's
box-shadow, not a pixel-exact translation of it.
"""

from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

# #38d9c9 (this theme's accent teal) at low alpha — approximates the
# design handoff's rgba(56,217,201,.10) panel glow.
_DEFAULT_GLOW_COLOR = QColor(56, 217, 201, 60)
_DEFAULT_BLUR_RADIUS = 26


def apply_panel_glow(
    widget: QWidget, color: QColor = _DEFAULT_GLOW_COLOR, blur: int = _DEFAULT_BLUR_RADIUS
) -> None:
    """Applies a soft colored glow around `widget`. Call once per
    widget (e.g. right after building it) — this replaces any existing
    graphics effect on `widget`, same as `home_dashboard.py`'s own
    card-shadow calls do, so don't call it twice on the same widget
    expecting effects to stack."""
    glow = QGraphicsDropShadowEffect(widget)
    glow.setBlurRadius(blur)
    glow.setXOffset(0)
    glow.setYOffset(0)
    glow.setColor(color)
    widget.setGraphicsEffect(glow)
