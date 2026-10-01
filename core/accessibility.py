"""
core.accessibility
====================

Making MIA comfortable for anyone (2026-10-01): bigger text, a
high-contrast look, and reading the screen aloud. Each person's own
choices (core/person_settings.py: `display.text_size`,
`display.high_contrast`), applied when they sign in.

Pure logic here (no Qt): the sizes, scaling a stylesheet's font sizes,
and turning a screen's visible text into something worth hearing. The
look is put together in gui/theme_manager.py's `build_stylesheet()`;
reading aloud is gui/read_aloud.py.
"""

from __future__ import annotations

import re

from core import person_settings

TEXT_SIZES: dict[str, tuple[str, float]] = {
    "normal": ("Normal", 1.0),
    "larger": ("Larger", 1.15),
    "largest": ("Largest", 1.3),
    "huge": ("Huge", 1.5),
}
DEFAULT_SIZE = "normal"

_FONT_SIZE = re.compile(r"(font-size\s*:\s*)(\d+(?:\.\d+)?)(px|pt)", re.IGNORECASE)


def text_scale(size_id: str) -> float:
    return TEXT_SIZES.get(size_id, TEXT_SIZES[DEFAULT_SIZE])[1]


def scale_font_sizes(stylesheet: str, factor: float) -> str:
    """Pure logic. Every `font-size: Npx/pt` times `factor`, rounded."""
    if abs(factor - 1.0) < 0.001:
        return stylesheet
    return _FONT_SIZE.sub(lambda m: f"{m.group(1)}{max(1, round(float(m.group(2)) * factor))}{m.group(3)}", stylesheet)


def look_for(context) -> tuple[str, bool]:
    """(text size id, high contrast?) for the signed-in person."""
    size = person_settings.get(context, "display.text_size", DEFAULT_SIZE) or DEFAULT_SIZE
    return (size if size in TEXT_SIZES else DEFAULT_SIZE,
            bool(person_settings.get(context, "display.high_contrast", False)))


def screen_text(lines: list[str], limit: int = 1500) -> str:
    """Pure logic. The visible text of a screen as one readable passage:
    trimmed, blank and duplicate lines dropped, symbols-only lines
    skipped, and cut at a sentence near `limit` characters."""
    seen, kept = set(), []
    for line in lines:
        clean = " ".join(str(line).replace("—", ",").split())
        if not clean or clean in seen or not any(ch.isalnum() for ch in clean):
            continue
        seen.add(clean)
        kept.append(clean if clean[-1] in ".!?:" else clean + ".")
    text = " ".join(kept)
    if len(text) <= limit:
        return text
    cut = text.rfind(". ", 0, limit)
    return text[: cut + 1 if cut > 0 else limit] + " That's the start of this screen."
