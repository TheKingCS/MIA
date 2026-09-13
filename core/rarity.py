"""
core.rarity
=============

Shared Borderlands-style five-tier rarity vocabulary, from the user's
2026-09-14 "Prestige, Rarity & Character Progression" design handoff
(see the [[project_mia_prestige_rarity_vision]] memory) — Common
through Legendary, the same white/green/blue/purple/orange scale
`core.leveling.PRESTIGE_COLORS` already uses for Prestige tiers.

Kept as its own tiny module rather than folded into `core.leveling`:
the handoff's own framing is that rarity should eventually tag
achievements, cosmetics, equipment, titles, badges, rewards, quests,
and milestones broadly — not just Prestige tiers specifically.
`core.rewards_manager`'s challenge chains are the first real consumer.

Per the handoff's own accessibility note ("do NOT make the system
dependent on color alone"), `RARITY_NAMES` is the primary label — the
color is a secondary visual cue, never the only one.
"""

from __future__ import annotations

RARITY_NAMES: tuple[str, ...] = ("Common", "Uncommon", "Rare", "Epic", "Legendary")

#: Same palette as core.leveling.PRESTIGE_COLORS, kept as its own tuple
#: here (rather than importing it) so this module has zero dependency
#: on the Prestige system — rarity is the more general concept.
RARITY_COLORS: tuple[str, ...] = ("white", "green", "blue", "purple", "orange")


def rarity_name_for_index(index: int) -> str:
    """Pure logic — testable without Qt. Clamped to a valid index."""
    clamped = min(max(index, 0), len(RARITY_NAMES) - 1)
    return RARITY_NAMES[clamped]


def rarity_color_for_index(index: int) -> str:
    """Pure logic — testable without Qt. Same clamp as rarity_name_for_index()."""
    clamped = min(max(index, 0), len(RARITY_COLORS) - 1)
    return RARITY_COLORS[clamped]
