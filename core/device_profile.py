"""
core.device_profile
======================

MIA runs as one codebase across two editions — docs/ROADMAP.md
milestone 13.1: **Core** (the Pi 5 + AI HAT+ 2, resource-constrained, a
field data-gathering tool) and **Home** (a desktop workstation, more
storage/resources), distinguished only by `config.system.device_profile`.

Deliberately **not** auto-detected from hardware (e.g.
`platform.machine()`) — explicit config is more robust: a Pi running in
a non-kiosk dev/test mode, or a desktop dev sandbox standing in for
either edition, shouldn't silently misdetect based on CPU architecture.
This is a thin helper, not a manager — there's no state to own beyond
the one config value, so it's plain functions over
`context.config.get(...)` rather than a class with its own `__init__`/
load/save (nothing to load or save that ConfigManager doesn't already
own).

Used to gate resource-weight choices (e.g. the default theme — see
gui/theme_manager.py) and, in future milestones, feature availability
between the two editions.
"""

from __future__ import annotations

from core.app_context import AppContext

CORE = "core"
HOME = "home"


def get_device_profile(context: AppContext) -> str:
    return context.config.get("system.device_profile", CORE)


def is_core_profile(context: AppContext) -> bool:
    return get_device_profile(context) == CORE


def is_home_profile(context: AppContext) -> bool:
    return get_device_profile(context) == HOME
