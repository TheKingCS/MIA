"""
core.whimsy
=============

A little grounded inspiration toward the slow, made, hand-crafted life — the whimsy and art Zac asked MIA to keep
alive (2026-11-08: "slow down, draw, create, think about forest creatures, make stuff, dream, do", and his shift from
consumer to producer). The standing directions (`core/direction.py`) hold *that* he wants this; this module turns it
into a concrete little **seed** he can act on today.

Facts in code, the model only phrases — the same rule the rest of MIA follows. A seed is composed here from real
things: the season (today's date), what's actually on the workshop shelf (`core/material_manager.py`), and which
directions the person has set. Nothing is improvised by the model, and nothing personal is hard-coded — the themes
come from the person's own words. The direction nudge (`core/application.py`) prefers a seed over a canned line when
one fits, and the communication gate paces it, so it stays a rare delight and never a nag.

A seed only ever grows from a direction the person actually set: with no matching direction active, `a_seed` returns
"" and the caller falls back to the plain nudge (or nothing).
"""

from __future__ import annotations

from typing import Iterable, Sequence

# The season, by month, with a few gentle motifs to sketch or sit with. Northern-hemisphere; a later pass can read the
# person's region (core/region.py) if that ever matters, but the motifs are mild enough to travel.
_SEASONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "winter": ("winter", ("bare branches", "woodsmoke", "frost on the glass", "a sleepy field")),
    "spring": ("spring", ("the first green", "nesting birds", "rain on the roof", "new buds")),
    "summer": ("summer", ("long light", "a lazy bee", "tall grass", "the evening cool")),
    "autumn": ("autumn", ("falling leaves", "a foraging squirrel", "the first frost", "bare-footed mushrooms")),
}


def season_of(month: int) -> tuple[str, tuple[str, ...]]:
    """The season and its motifs for a month (1–12). Defaults to winter for anything out of range."""
    if month in (12, 1, 2):
        return _SEASONS["winter"]
    if month in (3, 4, 5):
        return _SEASONS["spring"]
    if month in (6, 7, 8):
        return _SEASONS["summer"]
    if month in (9, 10, 11):
        return _SEASONS["autumn"]
    return _SEASONS["winter"]


# Each seed is one short, warm, second-person line. Its tags say which standing-direction themes it suits; a seed with
# no tag ("whimsy" aside) is universal to the slow/made life. {motif} is filled from the season, {material} from the
# shelf — a seed using {material} is only ever offered when there's really something there.
_SEEDS: tuple[tuple[frozenset, str], ...] = (
    # whimsy — slowness, drawing, dreaming, forest creatures (the unconditional ask)
    (frozenset({"whimsy"}), "Ten quiet minutes with a pencil — sketch the {motif} out the window, no plan, just the line."),
    (frozenset({"whimsy"}), "Put the kettle on, leave the screen, and watch the {motif} for a while. The day can wait."),
    (frozenset({"whimsy"}), "Dream one small thing onto paper today — a creature, a shop sign, a corner of the world in your head."),
    (frozenset({"whimsy"}), "Draw a little forest creature from memory and give it a name and a trade."),
    (frozenset({"whimsy"}), "Leave one lovely, unfinished thing on the bench just to walk past and enjoy it."),
    (frozenset({"whimsy"}), "Run today a half-step slower than it asks — one thing by hand, made to be enjoyed, not rushed."),
    # produce — make / restore / upcycle before buying
    (frozenset({"produce"}), "Before you buy it, sketch how you'd make it — even badly. That's where the good ones start."),
    (frozenset({"produce"}), "Mend one thing today instead of replacing it; the slow fix is its own small pleasure."),
    (frozenset({"produce"}), "What's something you'd usually order that you could make instead this week? Start with your hands."),
    # material — only when the shelf actually holds something
    (frozenset({"material"}), "You've got {material} on the shelf — what little thing wants to be made from it this week?"),
    (frozenset({"material"}), "That {material} in the workshop is asking to become something. A feeder, a sign, a gift?"),
    # grow — food from scratch, natural over processed
    (frozenset({"grow"}), "Start one thing from scratch today that you'd usually buy — the smell alone earns it."),
    (frozenset({"grow"}), "Cook one real, slow thing today and skip the packaged version; make the kitchen smell like something."),
    # cafe — the slow coffee ritual, running life like your own little shop
    (frozenset({"cafe"}), "A slow pour this morning, the good beans, no rush — run the day like your own little shop."),
    (frozenset({"cafe"}), "Make today's first coffee by hand, properly, and sit with it a minute before anything else."),
)

# Which words in a person's active directions light up which seed themes. Matched against the lowercased title +
# statement of each active direction — so the themes are the person's own, never assumed.
_THEME_WORDS: dict[str, tuple[str, ...]] = {
    "whimsy": ("whims", "art", "draw", "creat", "slow", "tranquil", "dream", "creature", "aesthetic"),
    "produce": ("produc", "make", "made", "restore", "upcycle", "mend", "thrift", "3d print", "build", "craft"),
    "grow": ("grow", "garden", "from scratch", "natural food", "cook", "homegrown", "processed"),
    "cafe": ("cafe", "café", "coffee", "espresso", "brew", "tavern", "shop", "barista"),
}


def _themes_active(direction_blobs: Iterable[str]) -> set[str]:
    """The seed themes a person's active directions light up — from their own words (lowercased title + statement)."""
    text = " ".join(b.lower() for b in direction_blobs)
    return {theme for theme, words in _THEME_WORDS.items() if any(w in text for w in words)}


def _pick(seq: Sequence, roll: float):
    """A deterministic choice from a non-empty sequence by a 0–1 roll (so a given roll always yields the same seed)."""
    if not seq:
        return None
    idx = min(int(roll * len(seq)), len(seq) - 1)
    return seq[idx]


def a_seed(direction_blobs: Iterable[str], materials: Sequence[str], month: int, roll: float) -> str:
    """One grounded little inspiration toward the person's standing directions, or "" when none is active.

    `direction_blobs` are the active directions' own words (title + statement, any case); `materials` are the names on
    the workshop shelf (may be empty); `month` sets the season's motif; `roll` (0–1) chooses the seed and the motif
    deterministically. Material seeds are only ever offered when the shelf isn't empty.
    """
    blobs = list(direction_blobs or [])
    themes = _themes_active(blobs)
    if not themes:
        return ""
    live = set(themes)
    if "material" not in live and "produce" in live and materials:
        live.add("material")  # a maker with a stocked shelf gets the "make it from what's here" seeds too
    pool = [text for tags, text in _SEEDS if tags & live and not ("material" in tags and not materials)]
    seed = _pick(pool, roll)
    if not seed:
        return ""
    if "{motif}" in seed:
        _, motifs = season_of(month)
        seed = seed.replace("{motif}", _pick(motifs, (roll * 7) % 1.0) or motifs[0])
    if "{material}" in seed:
        name = _pick(sorted(materials), (roll * 13) % 1.0) if materials else ""
        if not name:
            return ""
        seed = seed.replace("{material}", name)
    return seed
