"""
core.display_style
====================

Which look MIA's screens use (DEC-0135, Zac 2026-11-08: "selectable themes
that change which variant of display you get: the spatial portal design or
the organized cards design"). Each person's own choice (person_settings
`display.style`), changed in Settings or by voice ("switch to the cards
look"), never device-wide.

- `STYLES`: the choices and their words. "spatial" opens on the Nexus and
  draws each area as a room you stand in (web/nexus3d.js); "cards" opens on
  the Dashboard's cards and shows each area's hub as organized cards (the
  design the phone app had); "auto", the default, is spatial on a computer
  and cards on a phone.
- `style_of(context)`: the person's choice ("auto" when unset or unknown).
- `resolve(style, phone)` (pure): the look a device actually shows.
- `wants_style(words)` (pure): "spatial", "cards" or "auto" from how
  someone says it ("portals", "the old look", "cards on my phone"...), else None.

The web asks `shell()["display"]` and decides the device's side itself
(only it knows whether it's a phone); the glasses keep their own flat look
whatever this says.
"""

from __future__ import annotations

import re
from typing import Optional

STYLES: dict[str, tuple[str, str]] = {
    "auto": ("By device", "Spatial on the computer, cards on the phone."),
    "spatial": ("Spatial", "Opens on the Nexus: portals round MIA, and each area a room you stand in."),
    "cards": ("Cards", "Opens on the Dashboard: organized cards, and each area's apps as cards."),
}
DEFAULT_STYLE = "auto"
KEY = "display.style"


def style_of(context) -> str:
    """The person's display style ("auto" when they haven't picked, or the value isn't one)."""
    from core import person_settings

    value = person_settings.get(context, KEY, DEFAULT_STYLE) or DEFAULT_STYLE
    return value if value in STYLES else DEFAULT_STYLE


def resolve(style: str, phone: bool) -> str:
    """Pure logic. The look a device shows: "spatial" or "cards" ("auto" is spatial on a computer, cards on a
    phone)."""
    if style in ("spatial", "cards"):
        return style
    return "cards" if phone else "spatial"


_SPATIAL = re.compile(r"\b(spatial|portals?|nexus|3d|three d|rooms?|game ?like|new look)\b", re.I)
_CARDS = re.compile(r"\b(cards?|classic|old look|previous look|dashboard|tiles?|organi[sz]ed|simple)\b", re.I)
_AUTO = re.compile(r"\b(auto|automatic|default|both|depends|phone.*cards?|cards?.*phone)\b", re.I)


def wants_style(words: str) -> Optional[str]:
    """Pure logic. The style someone asked for, from their words: "auto" when they name both or the default
    ("cards on my phone, spatial on the computer"), "spatial" or "cards" when they name one, else None."""
    text = words or ""
    spatial, cards = bool(_SPATIAL.search(text)), bool(_CARDS.search(text))
    if _AUTO.search(text) and (spatial == cards or re.search(r"\bphone\b", text, re.I)):
        return "auto"
    if spatial and not cards:
        return "spatial"
    if cards and not spatial:
        return "cards"
    return None
