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

The Theme Studio (step 2: preview, tweak, save your own; web/studio.html):
- `choices_of(theme)` (pure): a theme as the Studio's few choices (accent,
  background, panels, text, lines, corners, font, material, the room's
  levels and palette).
- `build_theme(choices, base, theme_id, name)` (pure): the tokens and room
  from those choices (the same arithmetic as web/studio.js's live preview),
  refused when the accent would read as a warning colour (`accent_problem`)
  or the text would be hard to read (`contrast` under 4.5:1).
- `custom_themes(context)`, `all_themes(context)`, `choices(context)`: a
  person's own saved themes (person_settings `display.custom_themes`, up to
  12) beside the built-in ones.
- `studio(context)`: the Studio's screen: every theme with its choices, the
  one in use, the fonts, materials and level ranges.
Saving and deleting go through actions (core/theme_actions.py), so they're
approved and undoable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

KEY = "display.theme"
CUSTOM_KEY = "display.custom_themes"
MAX_CUSTOM = 12
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


# The Studio's fonts: system stacks only (MIA is offline, DEC-0023).
FONTS: dict[str, tuple[str, str]] = {
    "system": ("System (Segoe UI)", '"Segoe UI Variable Text", "Segoe UI", system-ui, -apple-system, Roboto, '
                                    '"Helvetica Neue", Arial, sans-serif'),
    "display": ("Display (light, wide)", '"Segoe UI Variable Display", "Segoe UI", system-ui, -apple-system, '
                                         '"Helvetica Neue", sans-serif'),
    "y2k": ("Y2K (Trebuchet)", '"Trebuchet MS", Verdana, "Segoe UI", system-ui, sans-serif'),
    "technical": ("Technical (Bahnschrift)", 'Bahnschrift, "DIN Alternate", "Roboto Condensed", "Arial Narrow", '
                                             'system-ui, sans-serif'),
    "rounded": ("Rounded", '"Segoe UI Variable Small", "Nunito", "Varela Round", "Arial Rounded MT Bold", system-ui, '
                           'sans-serif'),
    "mono": ("Monospace", 'ui-monospace, "Cascadia Mono", "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace'),
}
# Stark's values, which live in web/tokens.css rather than in its (empty) token list.
STARK_CHOICES = {"accent": "#35d4ff", "background": "#05070a", "panel": "#0c1016", "text": "#e6eef6",
                 "line": "#96b6d4", "radius": 6, "font": "system", "material": "solid",
                 "fire": 1.0, "bloom": 1.0, "mist": 1.0, "scan": 0.0, "grain": 0.0, "palette": [],
                 # DEC-0140: a picture MIA painted, behind every page and on the room's far wall, and how strongly
                 "backdrop": "", "backdrop_strength": 0.6}
_ART_ID = re.compile(r"^[a-f0-9]{12}$")
# Hues that mean something (DEC-0014): an accent near them would read as a warning, an error or "done".
MEANING_HUES = (("amber, which means something needs you", 39), ("red, which means an error", 2),
                ("green, which means done", 151), ("gold, which means a reward", 45))


def _rgb(hex_colour: str) -> tuple[int, int, int]:
    """Pure logic. "#rrggbb" as (r, g, b)."""
    n = int(hex_colour[1:7], 16)
    return n >> 16 & 255, n >> 8 & 255, n & 255


def _hex(rgb: tuple) -> str:
    """Pure logic. (r, g, b) as "#rrggbb"."""
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in rgb)


def mix(a: str, b: str, t: float) -> str:
    """Pure logic. Colour a moved t of the way to b (web/studio.js mixes the same way)."""
    x, y = _rgb(a), _rgb(b)
    return _hex(tuple(x[i] + (y[i] - x[i]) * t for i in range(3)))


def triplet(hex_colour: str) -> str:
    """Pure logic. "#rrggbb" as the "r, g, b" the --rgb-* tokens take."""
    return ", ".join(str(v) for v in _rgb(hex_colour))


def contrast(a: str, b: str) -> float:
    """Pure logic. The WCAG contrast ratio of two colours (1 to 21)."""
    def lum(c):
        def ch(v):
            v /= 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        r, g, bl = (ch(v) for v in _rgb(c))
        return 0.2126 * r + 0.7152 * g + 0.0722 * bl
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def accent_problem(hex_colour: str) -> Optional[str]:
    """Pure logic. Why this accent can't be a theme's (it would read as amber, red, green or gold), or None. Pale and
    grey accents are fine whatever their hue."""
    import colorsys

    r, g, b = (v / 255 for v in _rgb(hex_colour))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if sat < 0.35 or light > 0.85 or light < 0.12:
        return None
    degrees = hue * 360
    for meaning, centre in MEANING_HUES:
        if min(abs(degrees - centre), 360 - abs(degrees - centre)) < 20:
            return f"That accent would look like {meaning}. Try a blue, violet, pink, cyan or white."
    return None


def choices_of(theme: dict) -> dict:
    """Pure logic. A theme as the Studio's choices: its saved ones, else read back from its tokens, room and backdrop
    picture over Stark's."""
    if theme.get("choices"):
        return {**STARK_CHOICES, **theme["choices"]}
    tokens, room = theme.get("tokens") or {}, theme.get("room") or {}

    def rgb_token(name, fallback):
        value = tokens.get(name)
        if not value:
            return fallback
        try:
            return _hex(tuple(int(v) for v in value.split(",")))
        except ValueError:
            return fallback
    font = next((k for k, (_label, stack) in FONTS.items() if stack == tokens.get("--font")), "system")
    radius = tokens.get("--radius", "6px").rstrip("px")
    return {**STARK_CHOICES,
            "accent": tokens.get("--accent", STARK_CHOICES["accent"]),
            "background": tokens.get("--bg", STARK_CHOICES["background"]),
            "panel": rgb_token("--rgb-panel", STARK_CHOICES["panel"]),
            "text": tokens.get("--text", STARK_CHOICES["text"]),
            "line": rgb_token("--rgb-line", STARK_CHOICES["line"]),
            "radius": int(float(radius)) if radius.replace(".", "", 1).isdigit() else 6,
            "font": font, "material": theme.get("material") or "solid",
            **{k: room[k] for k in ROOM_LEVELS if k in room}, "palette": list(room.get("palette") or []),
            "backdrop": (theme.get("backdrop") or {}).get("art", ""),
            "backdrop_strength": (theme.get("backdrop") or {}).get("strength", 0.6)}


def build_theme(choices: dict, base: Optional[dict] = None, theme_id: str = "", name: str = "") -> dict:
    """Pure logic. A whole theme (cleaned) from the Studio's choices, on top of a base theme's other tokens (its
    backdrop gradient, label spacing, motion), with the backdrop picture the choices name (DEC-0140). Raises ValueError
    when a colour isn't #rrggbb, the accent would read as a meaning colour, or the text and background are under
    4.5:1."""
    c = {**STARK_CHOICES, **{k: v for k, v in (choices or {}).items() if v is not None}}
    for key in ("accent", "background", "panel", "text", "line"):
        if not _HEX.match(str(c[key])):
            raise ValueError(f"Pick a colour for the {key}.")
    problem = accent_problem(c["accent"])
    if problem:
        raise ValueError(problem)
    if contrast(c["text"], c["background"]) < 4.5 or contrast(c["text"], c["panel"]) < 4.5:
        raise ValueError("The text would be hard to read on that background. Make one lighter or darker.")
    radius = max(0, min(28, int(float(c["radius"]))))
    base = base or {}
    tokens = dict(base.get("tokens") or {})
    tokens.update({
        "--accent": c["accent"], "--rgb-accent": triplet(c["accent"]),
        "--accent-soft": mix(c["accent"], "#ffffff", 0.6), "--accent-deep": mix(c["accent"], "#000000", 0.45),
        "--bg": c["background"], "--rgb-bg": triplet(c["background"]), "--bg-soft": mix(c["background"], "#ffffff", 0.025),
        "--rgb-panel": triplet(c["panel"]), "--rgb-panel-2": triplet(mix(c["panel"], "#ffffff", 0.04)),
        "--rgb-panel-3": triplet(mix(c["panel"], "#ffffff", 0.09)), "--surface-solid": c["panel"],
        "--text": c["text"], "--text-dim": mix(c["text"], c["background"], 0.3),
        "--text-faint": mix(c["text"], c["background"], 0.45),
        "--rgb-line": triplet(c["line"]),
        "--radius": f"{radius}px", "--radius-sm": f"{round(radius * 0.66)}px",
        "--font": FONTS.get(c["font"], FONTS["system"])[1],
    })
    room = dict(base.get("room") or {})
    room.update({"accent": c["accent"], **{k: c[k] for k in ROOM_LEVELS if k in c}})
    palette = [p for p in (c.get("palette") or []) if _HEX.match(str(p))]
    if palette:
        room["palette"] = palette
    else:
        room.pop("palette", None)
    data = clean_theme({"id": theme_id or base.get("id") or "my_theme", "name": name or base.get("name") or "My theme",
                        "line": base.get("line", ""), "tokens": tokens, "material": c["material"], "room": room})
    art = str(c.get("backdrop") or "")
    if _ART_ID.match(art):
        try:
            strength = max(0.1, min(1.0, float(c.get("backdrop_strength", 0.6))))
        except (TypeError, ValueError):
            strength = 0.6
        data["backdrop"] = {"art": art, "strength": strength}
    data["choices"] = {k: c[k] for k in STARK_CHOICES}
    data["choices"]["radius"] = radius
    data["choices"]["palette"] = palette
    data["choices"]["backdrop"] = art if _ART_ID.match(art) else ""
    return data


def clean_theme(data: dict) -> dict:
    """Pure logic. A theme's data as the page may use it: {id, name, line, tokens, material, room}, keeping only the
    tokens and room settings a theme may change, dropping any value that could break out of CSS (url(), braces,
    semicolons, angle brackets, backslashes) or runs long, clamping the room's levels, and keeping only #rrggbb
    colours in the room; a backdrop picture is kept only as a picture id with its strength (DEC-0140). Raises
    ValueError without an id or name."""
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
    out = {"id": theme_id, "name": name[:40], "line": str(data.get("line") or "")[:160], "tokens": tokens,
           "material": material, "room": room}
    backdrop = data.get("backdrop") if isinstance(data.get("backdrop"), dict) else {}
    if _ART_ID.match(str(backdrop.get("art", ""))):  # one of the person's pictures, by id (core/art_studio.py)
        try:
            strength = max(0.1, min(1.0, float(backdrop.get("strength", 0.6))))
        except (TypeError, ValueError):
            strength = 0.6
        out["backdrop"] = {"art": backdrop["art"], "strength": strength}
    return out


def as_data(theme: Theme) -> dict:
    """Pure logic. A built-in theme as plain data (what clean_theme takes)."""
    return {"id": theme.id, "name": theme.name, "line": theme.line, "tokens": dict(theme.tokens),
            "material": theme.material, "room": dict(theme.room)}


def custom_themes(context) -> list[dict]:
    """The person's own saved themes, each cleaned again on the way out (a bad one is skipped)."""
    from core import person_settings

    out = []
    for raw in person_settings.get(context, CUSTOM_KEY, []) or []:
        try:
            data = clean_theme(raw)
        except (ValueError, AttributeError, TypeError):
            continue
        if isinstance(raw, dict) and isinstance(raw.get("choices"), dict):
            data["choices"] = {k: raw["choices"][k] for k in STARK_CHOICES if k in raw["choices"]}
        out.append(data)
    return out[:MAX_CUSTOM]


def all_themes(context) -> dict[str, dict]:
    """Every theme this person can use: the built-in ones, then their own, by id."""
    found = {t.id: clean_theme(as_data(t)) for t in THEMES.values()}
    for data in custom_themes(context):
        found.setdefault(data["id"], data)
    return found


def choices(context) -> list[tuple[str, str]]:
    """Pure-ish. (id, name) for every theme this person can pick (Settings' list)."""
    return [(theme_id, data["name"]) for theme_id, data in all_themes(context).items()]


def theme_of(context) -> str:
    """The person's theme id ("stark" when they haven't picked, or it isn't one of theirs)."""
    from core import person_settings

    value = person_settings.get(context, KEY, DEFAULT_THEME) or DEFAULT_THEME
    return value if value in THEMES or value in {t["id"] for t in custom_themes(context)} else DEFAULT_THEME


def for_shell(context) -> dict:
    """The person's theme (built-in or their own), cleaned, for every page (/api/shell display.theme)."""
    return all_themes(context)[theme_of(context)]


def studio(context) -> dict:
    """The Theme Studio's screen: every theme with its Studio choices and its export file (built-in first, then
    theirs), the one in use, the fonts, materials, the room's level ranges, the file format, a few sample portals and
    the checks' values."""
    themes = all_themes(context)
    from core.theme_actions import export

    return {"current": theme_of(context),
            "themes": [{**data, "own": theme_id not in THEMES, "choices": choices_of(data), "file": export(data)}
                       for theme_id, data in themes.items()],
            "fonts": [{"id": k, "label": label, "stack": stack} for k, (label, stack) in FONTS.items()],
            "materials": list(MATERIALS), "levels": {k: list(v) for k, v in ROOM_LEVELS.items()},
            "max_own": MAX_CUSTOM, "sample": _sample_portals(), "file_format": "mia-theme/1",
            # the same checks build_theme makes, so the page can say so as you pick (core still decides on save)
            "meaning_hues": [{"meaning": m, "hue": h} for m, h in MEANING_HUES], "min_contrast": 4.5}


def _sample_portals() -> list[dict]:
    """A few areas for the Studio's little room (core/web_areas.AREAS), with their own colours."""
    from core.web_areas import AREAS

    return [{"id": a.id, "name": a.name, "icon": a.icon, "hue": a.hue, "needs": 1 if i == 1 else 0}
            for i, a in enumerate(AREAS[:5])]


def own_id(name: str, taken: set) -> str:
    """Pure logic. A new id for a theme of one's own: "my_" and its name, made unique."""
    slug = re.sub(r"[^a-z0-9]+", "_", (name or "theme").lower()).strip("_")
    slug = re.sub(r"^my_", "", slug)[:20] or "theme"  # "My Stark" is my_stark, not my_my_stark
    theme_id, n = f"my_{slug}", 2
    while theme_id in taken or theme_id in THEMES:
        theme_id, n = f"my_{slug}_{n}", n + 1
    return theme_id


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
