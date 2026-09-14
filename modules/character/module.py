"""
modules.character.module
===========================

Character — the last remaining slice of the user's 2026-09-14
"Prestige, Rarity & Character Progression System" design handoff (see
the `project_mia_prestige_rarity_vision` memory): "a Character page
[that] should become one of the primary M.I.A. interfaces... a visual
archive of the user's actual life," not just an avatar.

**This is the SHELL, not the full vision** — the user explicitly
deferred real character art ("we will work on the artwork later, for
now let's build the system"), so there is no equip-able cosmetic
renderer here, just a `PhotoBackgroundFrame` placeholder standing in
for "the character" until real art exists, same convention as every
other not-yet-illustrated part of this app. What IS real: the actual
profile's real level/prestige, real lifetime stats
(`core.rewards_manager.RewardsManager.all_stat_values()`), a real
"collection" of every unlocked reward across every chain plus every
hidden achievement found (`all_unlocked_tiers()` /
`unlocked_hidden_achievements()` — flattened, unlike Skills' own
per-chain REWARDS card), a real rarity tally
(`rarity_tally_for_unlocked()`), and the real Prestige-emblem list
(`prestige_rewards_for_profile()`) — every number here is derived live
from the same managers Skills/Missions already read, nothing new
persisted or fabricated.

Deliberately its own top-level module (not folded into Skills) per the
handoff's own framing of Character as a primary interface in its own
right, not a sub-panel — Skills' own REWARDS card stays as-is
(per-chain progress toward the NEXT tier is that card's job; this
page's COLLECTION section is the finished-collection view instead,
across every chain and hidden achievement at once).

Same "Nature" hero + `#NatureAssetCard` visual system every other
active module already uses (see modules/household/module.py for the
simplest sibling example this one's structure mirrors).
"""

from __future__ import annotations

from typing import Optional, Union

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.leveling import compute_prestige_level_progress, prestige_color_for_tier
from core.rarity import rarity_color_for_index, rarity_name_for_index
from core.rewards_manager import STAT_DEFINITIONS, ChallengeTier, HiddenAchievement
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
from modules.module_base import ModuleBase


def format_character_level_line(level: int, xp_into_level: int, xp_needed: int, prestige_tier: int) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_character_module.py). Same "omit at tier 0" restraint
    every other Prestige-aware display in this app already follows."""
    prestige_part = f" · PRESTIGE {prestige_tier}" if prestige_tier > 0 else ""
    return f"LEVEL {level} · {xp_into_level:,}/{xp_needed:,} XP{prestige_part}"


def format_stat_line(icon: str, name: str, value: float, unit: str) -> str:
    """Pure formatting logic — testable without Qt."""
    unit_suffix = f" {unit}" if unit else ""
    return f"{icon} {name} — {value:g}{unit_suffix}"


def format_collection_entry_title(icon: str, name: str) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{icon} {name}"


def format_rarity_tally_line(rarity_name: str, count: int) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{rarity_name} ×{count}"


def sorted_collection(
    tiers: list[ChallengeTier], hidden_achievements: list[HiddenAchievement],
) -> list[Union[ChallengeTier, HiddenAchievement]]:
    """Combines unlocked ChallengeTiers and HiddenAchievements into one
    list, highest rarity first then alphabetical — pure logic,
    testable without Qt. Both dataclasses expose `.rarity_index` /
    `.name` / `.icon` / `.description`, so this treats them
    interchangeably as "collection entries" without needing a shared
    base class."""
    combined: list[Union[ChallengeTier, HiddenAchievement]] = list(tiers) + list(hidden_achievements)
    return sorted(combined, key=lambda entry: (-entry.rarity_index, entry.name))


class CharacterModule(ModuleBase):
    module_id = "character"
    display_name = "Character"
    description = "A living record of what you've actually done."
    icon = "\U0001F464"  # bust in silhouette

    def __init__(self, context) -> None:
        super().__init__(context)
        self._hero_title: Optional[QLabel] = None
        self._hero_level_line: Optional[QLabel] = None
        self._body_layout: Optional[QVBoxLayout] = None

    def get_widget(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background-color: #070f0d;")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(150)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(28, 20, 28, 16)
        hero_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        icon_badge = QLabel(self.icon)
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_row.addWidget(icon_badge)
        self._hero_title = QLabel(self.display_name)
        self._hero_title.setObjectName("NatureHeaderTitle")
        header_row.addWidget(self._hero_title)
        header_row.addStretch(1)
        hero_layout.addLayout(header_row)

        self._hero_level_line = QLabel()
        self._hero_level_line.setObjectName("NatureHeaderTagline")
        hero_layout.addWidget(self._hero_level_line)
        hero_layout.addStretch(1)

        outer.addWidget(hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        self._body_layout = QVBoxLayout(content)
        self._body_layout.setContentsMargins(24, 20, 24, 24)
        self._body_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._body_layout.setSpacing(16)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        self._refresh()
        return page

    def _active_profile(self):
        if self.context.profiles is None:
            return None
        return self.context.profiles.get_active_profile()

    def _refresh(self) -> None:
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        active = self._active_profile()
        if active is None:
            self._hero_title.setText(self.display_name)
            self._hero_level_line.setText("No active profile.")
            empty = QLabel("Create or select a profile to see your character.")
            empty.setObjectName("NatureTileCaption")
            self._body_layout.addWidget(empty)
            return

        self._hero_title.setText(active.name)
        level, xp_into_level, xp_needed = compute_prestige_level_progress(active.total_xp, active.prestige_tier)
        self._hero_level_line.setText(
            format_character_level_line(level, xp_into_level, xp_needed, active.prestige_tier)
        )
        color = prestige_color_for_tier(active.prestige_tier) if active.prestige_tier > 0 else None
        self._hero_level_line.setStyleSheet(f"color: {color};" if color else "")

        if self.context.rewards is None:
            empty = QLabel("Rewards aren't available yet.")
            empty.setObjectName("NatureTileCaption")
            self._body_layout.addWidget(empty)
            return

        # Snappy "check on view" feedback — safe to call every refresh
        # (idempotent, see core/rewards_manager.py's own docstring);
        # real activity already auto-unlocks via the event-sourced
        # groundwork, this is just the same defense-in-depth Skills'
        # own refresh already does.
        self.context.rewards.scan_for_new_unlocks(active.profile_id)
        self.context.rewards.scan_for_new_hidden_achievements(active.profile_id)

        self._build_portrait_section()
        self._build_stats_section()
        self._build_collection_section(active.profile_id)
        self._build_rarity_tally_section(active.profile_id)
        self._build_prestige_section(active.profile_id)

    def _build_portrait_section(self) -> None:
        portrait = PhotoBackgroundFrame()
        portrait.setFixedHeight(220)
        portrait_layout = QVBoxLayout(portrait)
        portrait_layout.addStretch(1)
        caption = QLabel("Character art coming soon")
        caption.setObjectName("NatureHeaderTagline")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        portrait_layout.addWidget(caption)
        self._body_layout.addWidget(portrait)

    def _build_stats_section(self) -> None:
        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        title = QLabel("LIFETIME STATS")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        stat_values = self.context.rewards.all_stat_values()
        for definition in STAT_DEFINITIONS:
            line = QLabel(format_stat_line(
                definition.icon, definition.name, stat_values.get(definition.stat_id, 0.0), definition.unit,
            ))
            line.setObjectName("NatureAssetLine")
            layout.addWidget(line)

        self._body_layout.addWidget(card)

    def _build_collection_section(self, profile_id: str) -> None:
        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        title = QLabel("COLLECTION")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        tiers = self.context.rewards.all_unlocked_tiers(profile_id)
        hidden = self.context.rewards.unlocked_hidden_achievements(profile_id)
        entries = sorted_collection(tiers, hidden)

        if not entries:
            empty = QLabel("Nothing unlocked yet — go do something real.")
            empty.setObjectName("NatureAssetLine")
            layout.addWidget(empty)
        else:
            for index, entry in enumerate(entries):
                if index > 0:
                    rule = QFrame()
                    rule.setFrameShape(QFrame.Shape.HLine)
                    rule.setObjectName("HairlineRule")
                    layout.addWidget(rule)
                entry_title = QLabel(format_collection_entry_title(entry.icon, entry.name))
                entry_title.setObjectName("NatureAssetTitle")
                entry_title.setStyleSheet(f"color: {rarity_color_for_index(entry.rarity_index)};")
                layout.addWidget(entry_title)
                entry_description = QLabel(entry.description)
                entry_description.setObjectName("NatureAssetLine")
                entry_description.setWordWrap(True)
                layout.addWidget(entry_description)

        self._body_layout.addWidget(card)

    def _build_rarity_tally_section(self, profile_id: str) -> None:
        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        title = QLabel("RARITY")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(18)
        tally = self.context.rewards.rarity_tally(profile_id)
        for index, count in enumerate(tally):
            label = QLabel(format_rarity_tally_line(rarity_name_for_index(index), count))
            label.setObjectName("NatureAssetLine")
            label.setStyleSheet(f"color: {rarity_color_for_index(index)};")
            row.addWidget(label)
        row.addStretch(1)
        layout.addLayout(row)

        self._body_layout.addWidget(card)

    def _build_prestige_section(self, profile_id: str) -> None:
        prestige_rewards = self.context.rewards.prestige_rewards_for_profile(profile_id)
        if not prestige_rewards:
            return

        card = QFrame()
        card.setObjectName("NatureAssetCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)
        title = QLabel("PRESTIGE EMBLEMS")
        title.setObjectName("NatureSectionTitle")
        layout.addWidget(title)

        for entry in prestige_rewards:
            label = QLabel(f"\U0001F3C6 {entry['name']}")
            label.setObjectName("NatureAssetLine")
            label.setStyleSheet(f"color: {entry['color']};")
            layout.addWidget(label)

        self._body_layout.addWidget(card)
