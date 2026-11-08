"""
core.web_about
================

About MIA (web/about.html, DEC-0142): what MIA can honestly say about herself, on one page, every line from the facts
and never from the model: what she is and her real scale (the system map, DEC-0139: files of code, tools, improvement
loops, decisions on record, what's sealed on disk, what she's learned while building), what she's working on (her
Night School directive), what she's trained for (core/capabilities.specialty_list: each specialty read from the code
that makes it true), and what she knows about the person (their directions, how many memories, whether she's learning
how they like answers), with links to where each is kept.

Read only: nothing here changes anything. By voice the same facts answer "what are you?", "what are you trained for?"
and "what do you know about me?" (core/assistant_self_actions.py).
"""

from __future__ import annotations


def _safe(fn, default):
    """Run a reader; on any failure the default, so a missing source is a quiet gap on the page."""
    try:
        return fn()
    except Exception:  # noqa: BLE001 - the page shows what can be read
        return default


def numbers(scale: dict) -> list[dict]:
    """Pure logic. The scale tiles from the system map: each {label, value, note}, only those the map has."""
    arch = scale.get("architecture") or {}
    tiles = [
        ("Files of code", sum(arch.values()) if arch else 0, "core, apps, screens, server and tools"),
        ("Tools", (scale.get("capabilities") or {}).get("tools") or 0, "things she can do when you ask"),
        ("Improvement loops", (scale.get("loops") or {}).get("active") or 0, "watching how she works"),
        ("Decisions on record", len(scale.get("decisions") or []), "why she's built this way"),
        ("Lessons kept", (scale.get("knowledge") or {}).get("total") or 0, "what building her taught"),
        ("Sealed on disk", (scale.get("stores") or {}).get("sealed") or 0, "kinds of your records, encrypted"),
    ]
    return [{"label": label, "value": value, "note": note} for label, value, note in tiles if value]


def screen(context) -> dict:
    """About MIA: who she is, her scale, her focus, her specialties, and what she knows about the person."""
    from core import capabilities, self_knowledge, system_map

    scale = _safe(system_map.assemble, {})
    book = getattr(context, "direction", None)
    directions = [d.title for d in _safe(lambda: book.active(), [])] if book is not None else []
    memories = getattr(context, "user_memories", None)
    remembered = _safe(lambda: len(memories.all_memories()), 0) if memories is not None else 0
    style = getattr(context, "response_style", None)
    picks = len(getattr(style, "picks", []) or []) if style is not None else 0
    return {
        "about": _safe(self_knowledge.about_me, ""),
        "numbers": numbers(scale),
        "focus": _safe(self_knowledge.my_focus, ""),
        "specialties": [{"title": t, "line": line} for t, line in _safe(lambda: capabilities.specialty_list(context), [])],
        "you": {
            "line": _safe(lambda: self_knowledge.what_i_know_about_you(context), ""),
            "directions": directions,
            "memories": remembered,
            "style_picks": picks,
        },
    }
