"""
core.theme_design
===================

MIA designs a theme from a description (DEC-0136, Theme Studio step 4; Zac
2026-11-08: "allow MIA to help design new themes from descriptions"): "a
rainy Tokyo night", "calm ocean glass", "loud 2000s rave". The words are
read in code, not by the model (MIA's facts are assembled in code), so the
same words always give the same theme and every result goes through the
same checks as a theme made by hand (core/themes.build_theme: no accent that
reads as a warning colour, readable text).

- `design(description)` (pure): {name, line, base, choices, understood,
  missed}: the theme it starts from (a place or mood picks Stark, Y2K Cyber,
  Cyberpunk or Glass), its accent and field colours (from colour words and
  places: ocean, forest, sunset, space, snow...), the room's mood (calm,
  wild, misty, retro...), material, font and corners; `understood` says
  what each word did, in her words, and `missed` names what she couldn't
  use (a warm accent that would look like a warning, a light theme).

The Studio previews the design before anything is kept (web/studio.js); by
voice (`design_theme`) she saves it as one of yours and puts it on, which
"undo" or "go back to Stark" reverses.
"""

from __future__ import annotations

import re

from core.themes import STARK_CHOICES, THEMES, as_data, choices_of

# A place or a mood: (words, base theme, what it gives, the field colours it sets).
SCENES: tuple[tuple[str, str, str, dict], ...] = (
    (r"tokyo|neon|cyber ?punk|city|blade runner|night ?club|arcade", "cyberpunk", "a neon city",
     {}),
    (r"y2k|2000s|two thousands|myspace|rave|vapou?r ?wave|chrome|retro|90s|nineties", "y2k", "early-2000s internet",
     {}),
    (r"calm|minimal|zen|spa|soft|clean|frosted|glass|quiet|gentle|serene", "glass", "calm frosted glass",
     {}),
    (r"ocean|sea|underwater|deep water|reef|lagoon", "glass", "the deep ocean",
     {"accent": "#2aa8ff", "background": "#030a12", "panel": "#0a1824", "line": "#8fd0ff", "palette": ["#2aa8ff", "#2ad1c9", "#6fc6ff"]}),
    (r"forest|jungle|woods|moss|grove", "stark", "a forest at night",
     {"accent": "#2ad1c9", "background": "#040b08", "panel": "#0b1712", "line": "#9fd8c4", "palette": ["#2ad1c9", "#35d4ff", "#8fd0ff"]}),
    (r"sunset|dusk|twilight|evening", "stark", "a sunset",
     {"accent": "#ff8ad8", "background": "#0d0610", "panel": "#1a0f1c", "line": "#e6b8e0", "palette": ["#ff8ad8", "#9b6bff", "#ff5ce6"]}),
    (r"space|galaxy|cosmic|stars|nebula|astral", "stark", "deep space",
     {"accent": "#8a5cff", "background": "#04030a", "panel": "#0e0b1c", "line": "#c4b4ff", "palette": ["#8a5cff", "#4a8cff", "#ff5ce6"]}),
    (r"snow|winter|ice|arctic|frost|glacier", "glass", "a winter night",
     {"accent": "#bfefff", "background": "#070b10", "panel": "#141c26", "line": "#dfeef8", "palette": ["#bfefff", "#96d6ff", "#ffffff"]}),
    (r"rain|rainy|storm|stormy", "stark", "rain",
     {"background": "#05080d", "panel": "#0e141c", "line": "#9fb8cf"}),
    (r"midnight|dark|night", "stark", "a dark night",
     {"background": "#030406", "panel": "#0a0d12"}),
)
# Accent colours by name; warm ones are kept out (they'd read as amber, red or green: DEC-0014).
COLOURS = {"cyan": "#35d4ff", "blue": "#3f7bff", "ice": "#96d6ff", "sky": "#6fc6ff", "violet": "#8a5cff",
           "purple": "#9b6bff", "lavender": "#b9a8ff", "pink": "#ff5ce6", "magenta": "#ff2ea6", "rose": "#ff8ad8",
           "white": "#e8f0ff", "silver": "#c0c8d4", "teal": "#2ad1c9", "turquoise": "#2ad1c9", "indigo": "#6a5cff"}
WARM = {"orange", "red", "yellow", "green", "gold", "amber", "lime", "brown", "copper", "fire", "lava"}
# The room's mood and the panels: (words, changes, what it does).
MOODS: tuple[tuple[str, dict, str], ...] = (
    (r"calm|quiet|gentle|soft|serene|relax|cozy|cosy", {"fire": 0.4, "bloom": 0.8, "mist": 0.8}, "a quieter room"),
    (r"loud|wild|intense|energetic|epic|party|rave|bright", {"fire": 1.7, "bloom": 1.5}, "more fire and glow"),
    (r"misty|foggy|fog|mist|rain|rainy|storm|smoky|smoke|steam", {"mist": 2.2}, "heavy mist"),
    (r"retro|crt|old tv|vhs|arcade|scanline", {"scan": 0.5, "grain": 0.5}, "scanlines and grain"),
    (r"film|grainy|gritty|grunge", {"grain": 0.7}, "film grain"),
    (r"rounded|round|bubbly|soft edges|curvy", {"radius": 20}, "round corners"),
    (r"sharp|hard|angular|edgy|brutal", {"radius": 2}, "sharp corners"),
    (r"glass|frosted|translucent", {"material": "glass"}, "frosted glass panels"),
    (r"chrome|metal|metallic|shiny", {"material": "chrome"}, "chrome panels"),
    (r"wire|hacker|terminal|tech|technical|matrix", {"material": "wire", "font": "technical"}, "wireframe panels"),
    (r"elegant|minimal|luxury|refined", {"font": "display"}, "a lighter font"),
    (r"terminal|hacker|code|matrix", {"font": "mono"}, "a monospace font"),
)
_LIGHT = re.compile(r"\b(light mode|light theme|white background|bright background|daytime|pastel)\b", re.I)
_SKIP = {"a", "an", "the", "theme", "look", "like", "make", "me", "with", "and", "of", "in", "on", "my", "mia",
         "please", "something", "kind", "style", "vibe", "vibes", "feel", "very", "really", "some", "it", "for", "that"}


def _name(description: str) -> str:
    """Pure logic. A short title from the description's own words ("a rainy Tokyo night" -> "Rainy Tokyo Night")."""
    words = [w for w in re.findall(r"[A-Za-z0-9']+", description) if w.lower() not in _SKIP]
    return " ".join(w if w[:1].isupper() else w.capitalize() for w in words[:3])[:40] or "My Theme"


def design(description: str) -> dict:
    """Pure logic. A theme from a description: {name, line, base, choices, understood, missed} (see the module)."""
    text = " ".join((description or "").split())[:300]
    low = text.lower()
    understood: list[str] = []
    missed: list[str] = []
    base_id, scene_fields = "stark", {}
    for words, theme_id, gives, fields in SCENES:
        hit = re.search(rf"\b({words})\b", low)
        if hit:
            if not understood:
                base_id = theme_id
            scene_fields = {**fields, **scene_fields} if understood else dict(fields)
            understood.append(f"{hit.group(1)}: {gives}")
    picks = dict(choices_of(as_data(THEMES[base_id])))
    picks.update({k: v for k, v in scene_fields.items()})
    for word, hex_colour in COLOURS.items():
        if re.search(rf"\b{word}\b", low):
            picks["accent"] = hex_colour
            picks["palette"] = [hex_colour] + [p for p in picks.get("palette") or [] if p != hex_colour][:3]
            understood.append(f"{word}: the accent")
            break
    for word in sorted(WARM):
        if re.search(rf"\b{word}\b", low):
            missed.append(f"{word}: a warm accent would look like a warning colour, so the warmth goes into the "
                          "portal pictures and the room's fire instead")
            break
    for words, changes, does in MOODS:
        hit = re.search(rf"\b({words})\b", low)
        if hit:
            picks.update(changes)
            understood.append(f"{hit.group(1)}: {does}")
    if _LIGHT.search(low):
        missed.append("light: MIA's themes are dark for now (the glasses and the 3D room need a dark field)")
    if not understood:
        missed.append("nothing in that matched a place, mood or colour MIA knows yet, so it starts from Stark")
    merged: dict[str, list[str]] = {}  # one line per word: "rainy: rain, heavy mist"
    for line in understood:
        word, does = line.split(": ", 1)
        if does not in merged.setdefault(word, []):
            merged[word].append(does)
    understood = [f"{word}: {', '.join(does)}" for word, does in merged.items()]
    name = _name(text)
    return {"name": name, "line": f"Designed by MIA from \"{text}\"."[:160], "base": base_id, "choices": picks,
            "understood": understood, "missed": missed}


def summary(result: dict) -> str:
    """Pure logic. What she made, in one or two sentences (for the voice tool and the Studio)."""
    did = "; ".join(result["understood"][:4])
    out = f"I made {result['name']}, starting from {THEMES[result['base']].name}" + (f" ({did})" if did else "") + "."
    if result["missed"]:
        out += " " + result["missed"][0][0].upper() + result["missed"][0][1:] + "."
    return out
