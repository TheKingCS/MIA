"""
core.themes
=============

MIA's themes (DEC-0136, Zac 2026-11-08: "One MIA. Multiple interface
experiences. Unlimited visual possibilities."). A theme is data, not code:
the design tokens it changes (colours, panels, type, shape, motion, an
extra backdrop layer), the material its panels are made of, and the 3D
room's light. The page applies it (web/shell.js), so every screen in both
experiences (DEC-0135: Spatial and Cards) follows, with nothing duplicated.
Plan: docs/design/EXPERIENCES_AND_THEMES.md.

- `THEMES`: the built-in ones: Stark (DEC-0023, the default), Y2K Cyber,
  Cyberpunk, Glass. First cuts for Muse to refine (DEC-0017).
- `TOKENS`, `MATERIALS`, `ROOM`: what a theme may change. Meaning colours
  (amber needs you, red errors, green ok, gold rewards, rarity, area hues)
  are not in the list, so no theme can hide a warning (DEC-0014, DEC-0130);
  high contrast still overrides every theme (web/tokens.css).
- `clean_theme(data)` (pure): a theme's data checked against those lists,
  values that could break out of CSS refused, numbers clamped. Every theme
  goes through it, built-in or (later) made in the Theme Studio or imported.
- `theme_of(context)`: the person's theme id ("stark" when unset).
- `for_shell(context)`: the person's theme, cleaned, for /api/shell.
- `wants_theme(words)` (pure): a theme id from how someone says it
  ("the Y2K one", "make it cyberpunk", "back to Stark"), else None.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

KEY = "display.theme"
DEFAULT_THEME = "stark"

# The tokens a theme may set (web/tokens.css). Meaning colours aren't here on purpose.
TOKENS = frozenset({
    "--rgb-bg", "--rgb-panel", "--rgb-panel-2", "--rgb-panel-3", "--bg", "--bg-soft", "--surface-solid",
    "--rgb-line", "--text", "--text-dim", "--text-faint",
    "--rgb-accent", "--accent", "--accent-soft", "--accent-deep",
    "--radius", "--radius-sm", "--font", "--font-mono", "--label-track", "--ease", "--dur-fast", "--dur",
    "--theme-backdrop",
})
# What panels are made of (web/themes.css draws each): solid graphite, glass, chrome, wire.
MATERIALS = ("solid", "glass", "chrome", "wire")
# The room's light (web/nexus3d.js): colours, a palette for the vapor and mist, and effect strengths.
ROOM_COLOURS = ("accent", "back_top", "back_bottom")
ROOM_LEVELS = {"fire": (0.0, 2.0), "bloom": (0.0, 2.0), "mist": (0.0, 2.5), "scan": (0.0, 1.0), "grain": (0.0, 1.0)}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_BAD = re.compile(r"url\(|expression|@import|javascript:|[;{}<>\\]", re.I)


@dataclass(frozen=True)
class Theme:
    """One theme: its id, name, a line about it, the tokens it sets, its panels' material, and the room's light."""
    id: str
    name: str
    line: str
    tokens: dict = field(default_factory=dict)
    material: str = "solid"
    room: dict = field(default_factory=dict)


THEMES: dict[str, Theme] = {t.id: t for t in (
    Theme("stark", "Stark", "Cyan holographic engineering: graphite panels, fine lines, one electric accent."),
    Theme("y2k", "Y2K Cyber", "Early-2000s internet: chrome, neon magenta and violet, liquid light, rounder edges.",
          tokens={
              "--rgb-bg": "8, 4, 18", "--bg": "#080412", "--bg-soft": "#0d0620",
              "--rgb-panel": "22, 12, 44", "--rgb-panel-2": "34, 18, 64", "--rgb-panel-3": "48, 26, 86",
              "--surface-solid": "#160c2c", "--rgb-line": "214, 176, 255",
              "--text": "#f6eeff", "--text-dim": "#c8b6e6", "--text-faint": "#a896c8",
              "--rgb-accent": "255, 92, 230", "--accent": "#ff5ce6", "--accent-soft": "#ffc4f6", "--accent-deep": "#a31f8f",
              "--radius": "14px", "--radius-sm": "10px",
              "--font": '"Trebuchet MS", Verdana, "Segoe UI", system-ui, sans-serif',
              "--theme-backdrop": "radial-gradient(900px 620px at 12% 8%, rgba(255, 92, 230, 0.20), transparent 60%), "
                                  "radial-gradient(820px 600px at 88% 26%, rgba(90, 140, 255, 0.18), transparent 60%), "
                                  "radial-gradient(760px 520px at 50% 104%, rgba(150, 80, 255, 0.20), transparent 62%)",
          },
          material="chrome",
          room={"accent": "#ff5ce6", "palette": ["#ff5ce6", "#8a5cff", "#4a8cff", "#ff8ad8", "#5cf2ff", "#c86bff"],
                "back_top": "#120626", "back_bottom": "#040108", "fire": 1.4, "bloom": 1.25, "mist": 1.6, "grain": 0.6}),
    Theme("cyberpunk", "Cyberpunk", "A dark neon city: hot magenta and electric blue, hard edges, scanlines.",
          tokens={
              "--rgb-bg": "6, 3, 12", "--bg": "#06030c", "--bg-soft": "#0a0514",
              "--rgb-panel": "16, 10, 26", "--rgb-panel-2": "24, 14, 38", "--rgb-panel-3": "34, 20, 52",
              "--surface-solid": "#100a1a", "--rgb-line": "110, 196, 255",
              "--text": "#eaf2ff", "--text-dim": "#a9b6d8", "--text-faint": "#8a96ba",
              "--rgb-accent": "255, 46, 166", "--accent": "#ff2ea6", "--accent-soft": "#ff9fd6", "--accent-deep": "#9e1466",
              "--radius": "2px", "--radius-sm": "1px", "--label-track": "0.2em",
              "--font": 'Bahnschrift, "DIN Alternate", "Roboto Condensed", "Arial Narrow", system-ui, sans-serif',
              "--theme-backdrop": "repeating-linear-gradient(0deg, rgba(110, 196, 255, 0.025) 0 1px, transparent 1px 4px), "
                                  "radial-gradient(900px 500px at 80% -10%, rgba(255, 46, 166, 0.16), transparent 62%), "
                                  "radial-gradient(800px 520px at 10% 110%, rgba(46, 155, 255, 0.14), transparent 62%)",
          },
          material="wire",
          room={"accent": "#ff2ea6", "palette": ["#ff2ea6", "#2e9bff", "#7a2eff", "#00e5ff"],
                "back_top": "#160822", "back_bottom": "#030106", "fire": 1.1, "bloom": 1.3, "mist": 1.9, "scan": 0.55,
                "grain": 0.3}),
    Theme("glass", "Glass", "Minimal and calm: frosted translucent panels, soft light, wide curves, gentle motion.",
          tokens={
              "--rgb-bg": "9, 13, 19", "--bg": "#090d13", "--bg-soft": "#0d121a",
              "--rgb-panel": "30, 38, 50", "--rgb-panel-2": "38, 47, 61", "--rgb-panel-3": "48, 58, 74",
              "--surface-solid": "#1e2632", "--rgb-line": "220, 232, 245",
              "--text": "#f2f6fa", "--text-dim": "#b6c2cf", "--text-faint": "#93a1b0",
              "--rgb-accent": "150, 214, 255", "--accent": "#96d6ff", "--accent-soft": "#d6efff", "--accent-deep": "#3d82b0",
              "--radius": "18px", "--radius-sm": "12px", "--label-track": "0.08em",
              "--font": '"Segoe UI Variable Display", "Segoe UI", system-ui, -apple-system, "Helvetica Neue", sans-serif',
              "--dur": "320ms", "--dur-fast": "180ms",
              "--theme-backdrop": "radial-gradient(700px 520px at 20% 15%, rgba(150, 214, 255, 0.12), transparent 65%), "
                                  "radial-gradient(760px 560px at 82% 70%, rgba(200, 170, 255, 0.10), transparent 65%)",
          },
          material="glass",
          room={"accent": "#96d6ff", "palette": ["#96d6ff", "#c8b4ff", "#dfe9f2"], "back_top": "#0e141d",
                "back_bottom": "#05070b", "fire": 0.45, "bloom": 0.8, "mist": 0.7}),
)}


def clean_theme(data: dict) -> dict:
    """Pure logic. A theme's data as the page may use it: {id, name, line, tokens, material, room}, keeping only the
    tokens and room settings a theme may change, dropping any value that could break out of CSS (url(), braces,
    semicolons, angle brackets, backslashes) or runs long, clamping the room's levels, and keeping only #rrggbb
    colours in the room. Raises ValueError without an id or name."""
    theme_id = str(data.get("id") or "").strip()
    name = str(data.get("name") or "").strip()
    if not re.fullmatch(r"[a-z0-9_]{1,32}", theme_id) or not name:
        raise ValueError("A theme needs an id (lowercase letters, digits, _) and a name.")
    tokens = {}
    for key, value in (data.get("tokens") or {}).items():
        value = str(value).strip()
        if key in TOKENS and value and len(value) <= 600 and not _BAD.search(value):
            tokens[key] = value
    room: dict = {}
    raw = data.get("room") or {}
    for key in ROOM_COLOURS:
        if _HEX.match(str(raw.get(key, ""))):
            room[key] = raw[key]
    palette = [c for c in (raw.get("palette") or []) if _HEX.match(str(c))][:6]
    if palette:
        room["palette"] = palette
    for key, (low, high) in ROOM_LEVELS.items():
        if key in raw:
            try:
                room[key] = max(low, min(high, float(raw[key])))
            except (TypeError, ValueError):
                pass
    material = data.get("material") if data.get("material") in MATERIALS else "solid"
    return {"id": theme_id, "name": name[:40], "line": str(data.get("line") or "")[:160], "tokens": tokens,
            "material": material, "room": room}


def as_data(theme: Theme) -> dict:
    """Pure logic. A built-in theme as plain data (what clean_theme takes)."""
    return {"id": theme.id, "name": theme.name, "line": theme.line, "tokens": dict(theme.tokens),
            "material": theme.material, "room": dict(theme.room)}


def theme_of(context) -> str:
    """The person's theme id ("stark" when they haven't picked, or it isn't one)."""
    from core import person_settings

    value = person_settings.get(context, KEY, DEFAULT_THEME) or DEFAULT_THEME
    return value if value in THEMES else DEFAULT_THEME


def for_shell(context) -> dict:
    """The person's theme, cleaned, for every page (/api/shell display.theme)."""
    return clean_theme(as_data(THEMES[theme_of(context)]))


_WORDS = (
    ("y2k", re.compile(r"\b(y2k|y 2 k|myspace|2000s|two thousands|rave|chrome|liquid)\b", re.I)),
    ("cyberpunk", re.compile(r"\b(cyber ?punk|neon city|blade runner)\b", re.I)),
    ("glass", re.compile(r"\b(glass|frosted|minimal|minimalist|calm|clean)\b", re.I)),
    ("stark", re.compile(r"\b(stark|jarvis|holographic|iron ?man|default|original|cyan)\b", re.I)),
)


def wants_theme(words: str) -> Optional[str]:
    """Pure logic. The theme someone asked for from their words, else None (the first match in the order above, so
    "the cyberpunk one, not the Y2K one" is ambiguous: two named means None)."""
    found = [theme_id for theme_id, pattern in _WORDS if pattern.search(words or "")]
    return found[0] if len(found) == 1 else None
