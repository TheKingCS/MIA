"""
modules.skills.module
========================

Skills — "My Hero's Path" (2026-09-11), the screen for the skill-tree
layer core/skill_manager.py adds underneath the existing profile-wide
Level/Missions system. A categorized grid of skill cards (icon, name,
level, XP progress bar), locked skills shown dimmed with a lock badge
and their prerequisites named, refreshing live as
"profile.skill_xp_changed"/"profile.xp_changed" events fire from any
of the real activity hooks (Workout/Kitchen/Maintenance/Budget/
Missions) that grant skill XP — same live-refresh convention as
gui/main_window.py's header Level badge.

**Design restyle Phase 4 (2026-09-12)**: the "true graphical tree
view" this module's own docstring used to defer arrives here — a
gui.widgets.skill_tree_canvas.SkillTreeCanvas draws real prerequisite
connector lines behind the (now 4-column) card grid, straight lines
only (see the Phase 4 plan/ROADMAP entry for why the mockup's one
curved convergence isn't replicated). Also adds a right-hand column:
a capability-status legend, a real achievements panel (the most recent
NotificationManager entries with source="achievements" —
core.skill_manager.SkillManager._notify_achievements() already raises
these; nothing new to derive), and a "NEXT HONEST STEP" card naming
core.skill_leveling.next_honest_step()'s pick — a plain heuristic, not
a smart-suggestion system. That same skill also gets the visual
"current focus" border, since no other field names one.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.leveling import (
    compute_prestige_level_progress,
    is_eligible_to_prestige,
    prestige_color_for_tier,
)
from core.skill_leveling import (
    CAPABILITY_STATUSES,
    capability_status_for_level,
    compute_skill_level_progress,
    next_honest_step,
)
from core.rarity import rarity_color_for_index, rarity_name_for_index
from core.rewards_manager import (
    CHALLENGE_CHAINS,
    STAT_DEFINITIONS,
    highest_unlocked_tier,
    next_locked_tier,
    reward_progress_fraction,
)
from core.skill_manager import SkillDefinition
from gui.widgets.blueprint_frame import BlueprintFrame
from gui.widgets.glow import apply_panel_glow
from gui.widgets.photo_background_frame import PhotoBackgroundFrame
from gui.widgets.skill_tree_canvas import SkillTreeCanvas
from modules.missions.module import format_level_footer_line
from modules.module_base import ModuleBase

# Maximum width for a skill card's wrapping labels (see
# _build_skill_card()'s own comment on why this is needed at all — Qt
# word-wrap inside a QGridLayout/QScrollArea needs a concrete width to
# wrap against, or long text just clips instead of flowing to a second
# line). Deliberately capped on the LABELS, not the card itself — a
# card's own width still comes from the grid as before, so this can
# never force the grid wider than the scroll area actually has room
# for (an earlier version of this fix set a fixed card width instead
# and that overflowed the viewport, producing a horizontal scrollbar
# and visually overlapping cards — worse than the bug it fixed).
_LABEL_MAX_WIDTH = 230


def format_skill_subtitle(level: int, xp_into_level: int, xp_needed: int) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_skills_module.py)."""
    return f"Lv. {level} · {xp_into_level}/{xp_needed} XP"


def format_locked_skill_name(name: str) -> str:
    """Pure formatting logic — testable without Qt. Plain ASCII "(Locked)"
    rather than a lock emoji, deliberately — verified headless that the
    U+1F512 lock glyph isn't in this app's font fallback chain the way
    the rest of its emoji vocabulary is, and one unsupported codepoint
    in a QLabel poisons font shaping for the WHOLE string (every
    character rendered in a wrong fallback font, not just the glyph
    that's missing) — a real, reproduced rendering bug, not a style
    preference."""
    return f"(Locked) {name}"


def format_prerequisites_line(prereq_names: list[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    return "Requires: " + ", ".join(prereq_names)


def format_reward_status_line(description: str, unit: str, value: float, threshold: float, unlocked: bool) -> str:
    """Pure formatting logic — testable without Qt. Locked rows show
    real progress against the threshold; unlocked rows drop the numbers
    entirely (the description alone reads better once it's done)."""
    if unlocked:
        return f"Unlocked — {description}"
    unit_suffix = f" {unit}" if unit else ""
    return f"{value:g}/{threshold:g}{unit_suffix} — {description}"


def format_earned_title_line(icon: str, name: str) -> str:
    """Pure formatting logic — testable without Qt. The highest tier
    already earned in a challenge chain."""
    return f"Earned: {icon} {name}"


def format_chain_maxed_line(icon: str, name: str) -> str:
    """Pure formatting logic — testable without Qt. Shown once every
    tier in a challenge chain has been unlocked."""
    return f"\U0001F3C6 Maxed out — {icon} {name}"


def format_capability_status_label(status: str) -> str:
    """Pure formatting logic — testable without Qt. Title-cases one of
    core.skill_leveling.CAPABILITY_STATUSES ("learning" -> "Learning")."""
    return status.capitalize()


# ----------------------------------------------------------------------
# Design restyle Phase 4 (2026-09-12) — new pure formatting helpers.
# ----------------------------------------------------------------------

def format_skill_status_line(level: int, status: str) -> str:
    """Pure formatting logic — testable without Qt. "LV 5 · DEMONSTRATED"."""
    return f"LV {level} · {status.upper()}"


def format_tier_chip(tier: int) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"T{tier}"


def order_categories_by_interest(categories: list[str], interests: list[str]) -> list[str]:
    """Pure logic — testable without Qt. Profile-creation interview
    (2026-09-14): interest categories sort first (preserving their
    relative order in `categories`, i.e. alphabetical since
    core.skill_manager.SkillManager.categories() is already sorted),
    then everything else, same order as before. Never drops or adds a
    category — just reorders."""
    interest_set = set(interests)
    return [c for c in categories if c in interest_set] + [c for c in categories if c not in interest_set]


def format_category_tab_label(category: str, is_interest: bool) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"★ {category}" if is_interest else category


def format_achievement_title_for_display(title: str) -> str:
    """Pure formatting logic — testable without Qt. Strips a leading
    emoji + space for display, per the design handoff's own copy note
    ("the real notification strings are emoji-led... the design renders
    them without the emoji to keep the chrome clean"). The real
    core.achievements.py format functions are untouched — this only
    affects how this one screen renders an already-real title."""
    head, sep, rest = title.partition(" ")
    if sep and not head.isascii():
        return rest
    return title


def format_header_stats_line(
    profile_level: int, trained: int, total: int, demonstrated: int, prestige_tier: int = 0
) -> str:
    """Pure formatting logic — testable without Qt. "PROFILE LEVEL 7 ·
    SKILLS TOUCHED 23/96 · DEMONSTRATED 4", with "· PRESTIGE 2" inserted
    once the user has actually prestiged at least once — omitted
    entirely at tier 0 (never prestiged), same "don't show a zero-value
    stat" restraint every other glance stat in this app follows.
    `prestige_tier` defaults to 0 so every existing call site keeps
    working unchanged."""
    prestige_part = f" · PRESTIGE {prestige_tier}" if prestige_tier > 0 else ""
    return f"PROFILE LEVEL {profile_level}{prestige_part} · SKILLS TOUCHED {trained}/{total} · DEMONSTRATED {demonstrated}"


def format_prestige_status(level: int, eligible: bool, prestige_tier: int) -> str:
    """Pure formatting logic — testable without Qt. Quiet progress
    copy while not yet eligible; a real celebratory line once level
    100 is maxed out and Prestige is available."""
    if eligible:
        next_color = prestige_color_for_tier(prestige_tier + 1)
        return f"Level 100 maxed out! Prestige now — next badge color: {next_color}."
    return f"Level {level}/100 — prestige unlocks once you max out level 100."


def format_next_honest_step_line(skill_name: Optional[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    if skill_name is None:
        return "Nothing to suggest right now — every skill is locked."
    return f"Put some real time toward {skill_name} next."


class SkillsModule(ModuleBase):
    module_id = "skills"
    display_name = "Skills"
    description = "My Hero's Path — skill tree and character progression."
    icon = "\U00002694"  # crossed swords

    def __init__(self, context) -> None:
        super().__init__(context)
        self._current_category: Optional[str] = None
        self._category_buttons: dict[str, QPushButton] = {}
        self._widget_built = False
        # Profile-creation interview (2026-09-14) — the active
        # profile's own picked interests, read once in get_widget() and
        # used by _build_category_tabs() to star the ones they said
        # they care about. Empty set with no active profile/no picks.
        self._interest_categories: set[str] = set()
        # Design restyle Phase 4 (2026-09-12) — whichever skill_id
        # core.skill_leveling.next_honest_step() names, set by
        # _refresh_next_step() and read by _build_skill_card() to draw
        # the current-focus border. None until the first refresh.
        self._focus_skill_id: Optional[str] = None

    def on_load(self) -> None:
        super().on_load()
        # Subscribed here, not __init__, so an unopened Skills module
        # costs nothing at boot beyond the cheap attribute assignment
        # above — same "__init__ must stay cheap, real setup belongs in
        # on_load()" rule every module in this codebase follows.
        self.context.events.subscribe("profile.skill_xp_changed", self._on_skill_xp_changed)
        self.context.events.subscribe("profile.xp_changed", self._on_profile_xp_changed)

    def get_widget(self) -> QWidget:
        """Nature re-skin (2026-09-14) — hero-only pass: a photo hero
        replaces the old plain-text title row, the level/XP stats
        label moves into it (same info, relocated). Everything below
        (category tabs, skill tree canvas, capability/achievements/
        next-step cards, their teal-HUD styling) is untouched — this
        screen already went through its own earlier, separate design
        pass (2026-09-12's Phase 4 skill tree restyle) rather than
        starting plain, so it gets the smaller hero-only scope, same
        as modules/missions/module.py."""
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hero = PhotoBackgroundFrame()
        hero.setFixedHeight(120)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(28, 16, 28, 16)
        hero_layout.setSpacing(12)

        icon_badge = QLabel(self.icon)
        icon_badge.setObjectName("NatureIconBadge")
        icon_badge.setFixedSize(40, 40)
        icon_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hero_layout.addWidget(icon_badge)

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title = QLabel("Skills")
        title.setObjectName("NatureHeaderTitle")
        title_column.addWidget(title)
        tagline = QLabel("Do the thing. Earn the level. Unlock the next thing.")
        tagline.setObjectName("NatureHeaderTagline")
        title_column.addWidget(tagline)
        hero_layout.addLayout(title_column, stretch=1)

        self._stats_label = QLabel()
        self._stats_label.setObjectName("NatureHeaderTagline")
        hero_layout.addWidget(self._stats_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(hero)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 0, 24, 24)
        body_layout.setSpacing(12)

        self._tabs_row = QHBoxLayout()
        self._tabs_row.setSpacing(6)
        body_layout.addLayout(self._tabs_row)

        split_row = QHBoxLayout()
        split_row.setSpacing(20)

        left_column = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_container = SkillTreeCanvas()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(12)
        scroll.setWidget(self._grid_container)
        left_column.addWidget(scroll, stretch=1)
        split_row.addLayout(left_column, stretch=1)

        split_row.addWidget(self._build_right_column())
        body_layout.addLayout(split_row, stretch=1)

        layout.addWidget(body, stretch=1)

        self._widget_built = True
        categories = self.context.skills.categories() if self.context.skills else []
        # Profile-creation interview (2026-09-14) — a profile's own
        # picked interests (core/profile_manager.py's Profile.interests,
        # real category names) sort first, so the categories the user
        # actually said they care about are the ones they land on.
        # Falls back to plain alphabetical (categories() is already
        # sorted) with no active profile or no interests picked —
        # unchanged from before this existed.
        active = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        if active is not None and active.interests:
            categories = order_categories_by_interest(categories, active.interests)
            self._interest_categories = set(active.interests)
        self._current_category = categories[0] if categories else None
        self._build_category_tabs(categories)
        self._refresh()
        return root

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        column.setFixedWidth(360)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)

        legend_card = BlueprintFrame()
        legend_card.setObjectName("DashboardCard")
        apply_panel_glow(legend_card)
        legend_layout = QVBoxLayout(legend_card)
        legend_title = QLabel("CAPABILITY STATUS")
        legend_title.setObjectName("MonitorTileEyebrow")
        legend_layout.addWidget(legend_title)
        for status in CAPABILITY_STATUSES:
            row = QLabel(f"{format_capability_status_label(status)}")
            row.setObjectName("SkillCardStatus")
            row.setProperty("status", status)
            legend_layout.addWidget(row)
        footnote = QLabel("Locked is display only — XP still lands.")
        footnote.setObjectName("SkillCardPrereq")
        footnote.setWordWrap(True)
        legend_layout.addWidget(footnote)
        column_layout.addWidget(legend_card)

        achievements_card = BlueprintFrame()
        achievements_card.setObjectName("DashboardCard")
        apply_panel_glow(achievements_card)
        self._achievements_layout = QVBoxLayout(achievements_card)
        achievements_title = QLabel("ACHIEVEMENTS")
        achievements_title.setObjectName("MonitorTileEyebrow")
        self._achievements_layout.addWidget(achievements_title)
        column_layout.addWidget(achievements_card)

        next_step_card = BlueprintFrame(accent=True)
        next_step_card.setObjectName("DashboardCard")
        apply_panel_glow(next_step_card)
        self._next_step_layout = QVBoxLayout(next_step_card)
        next_step_title = QLabel("NEXT HONEST STEP")
        next_step_title.setObjectName("MonitorTileEyebrow")
        self._next_step_layout.addWidget(next_step_title)
        self._next_step_body = QLabel()
        self._next_step_body.setWordWrap(True)
        self._next_step_layout.addWidget(self._next_step_body)
        column_layout.addWidget(next_step_card)

        # Prestige (2026-09-14) — the user's own fully-designed system
        # (same XP curve every tier, Borderlands white/green/blue/
        # purple/orange scale capping at orange), finally built.
        prestige_card = BlueprintFrame(accent=True)
        prestige_card.setObjectName("DashboardCard")
        apply_panel_glow(prestige_card)
        self._prestige_layout = QVBoxLayout(prestige_card)
        prestige_title = QLabel("PRESTIGE")
        prestige_title.setObjectName("MonitorTileEyebrow")
        self._prestige_layout.addWidget(prestige_title)
        self._prestige_body = QLabel()
        self._prestige_body.setWordWrap(True)
        self._prestige_layout.addWidget(self._prestige_body)
        self._prestige_button = QPushButton("Prestige Now")
        self._prestige_button.clicked.connect(self._on_prestige_clicked)
        self._prestige_button.hide()
        self._prestige_layout.addWidget(self._prestige_button, alignment=Qt.AlignmentFlag.AlignLeft)
        column_layout.addWidget(prestige_card)

        # Rewards (2026-09-14) — the user's own "Call of Duty
        # headshots/kills/bloodthirstys" motivational-stats ask: real
        # lifetime stats (engine hours, workout hours, missions
        # completed) unlocking real cosmetic rewards at thresholds.
        # Character-art illustration is deliberately deferred (see
        # core/rewards_manager.py's own docstring); plain emoji icons
        # for now, same convention as every other not-yet-illustrated
        # part of this app. Also lists Prestige N emblems already
        # reached, derived live — the same "collection" the user asked
        # for, in one place.
        rewards_card = BlueprintFrame(accent=True)
        rewards_card.setObjectName("DashboardCard")
        apply_panel_glow(rewards_card)
        self._rewards_layout = QVBoxLayout(rewards_card)
        rewards_title = QLabel("REWARDS")
        rewards_title.setObjectName("MonitorTileEyebrow")
        self._rewards_layout.addWidget(rewards_title)
        column_layout.addWidget(rewards_card)

        column_layout.addStretch(1)
        return column

    def _build_category_tabs(self, categories: list[str]) -> None:
        for category in categories:
            label = format_category_tab_label(category, category in self._interest_categories)
            button = QPushButton(label)
            button.setObjectName("SkillCategoryTab")
            button.setProperty("active", category == self._current_category)
            button.clicked.connect(lambda checked=False, c=category: self._select_category(c))
            self._tabs_row.addWidget(button)
            self._category_buttons[category] = button
        self._tabs_row.addStretch()

    def _select_category(self, category: str) -> None:
        self._current_category = category
        for name, button in self._category_buttons.items():
            button.setProperty("active", name == category)
            button.style().unpolish(button)
            button.style().polish(button)
        self._refresh_grid()

    def _refresh(self) -> None:
        self._refresh_stats_label()
        # _refresh_next_step() sets self._focus_skill_id, which
        # _refresh_grid()'s cards read to draw the current-focus
        # border — must run first, or the very first render never
        # shows a focus border at all.
        self._refresh_next_step()
        self._refresh_grid()
        self._refresh_achievements()
        self._refresh_prestige_card()
        self._refresh_rewards_card()

    def _active_profile_id(self) -> Optional[str]:
        if self.context.profiles is None:
            return None
        active = self.context.profiles.get_active_profile()
        return active.profile_id if active else None

    def _demonstrated_count(self, profile_id: Optional[str]) -> int:
        if self.context.skills is None or profile_id is None:
            return 0
        return sum(
            1 for definition in self.context.skills.all_skills()
            if self.context.skills.capability_status(profile_id, definition.skill_id) == "demonstrated"
        )

    def _refresh_stats_label(self) -> None:
        if self.context.profiles is None or self.context.skills is None:
            self._stats_label.setText("")
            return
        active = self.context.profiles.get_active_profile()
        profile_level = 0
        prestige_tier = 0
        if active is not None:
            profile_level = compute_prestige_level_progress(active.total_xp, active.prestige_tier)[0]
            prestige_tier = active.prestige_tier
        profile_id = self._active_profile_id()
        total = len(self.context.skills.all_skills())
        trained = len(self.context.skills.progress_for_profile(profile_id)) if profile_id else 0
        demonstrated = self._demonstrated_count(profile_id)
        self._stats_label.setText(format_header_stats_line(profile_level, trained, total, demonstrated, prestige_tier))
        color = prestige_color_for_tier(prestige_tier) if prestige_tier > 0 else None
        self._stats_label.setStyleSheet(f"color: {color};" if color else "")

    def _refresh_prestige_card(self) -> None:
        active = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        if active is None:
            self._prestige_body.setText("No active profile.")
            self._prestige_button.hide()
            return

        level, _xp_into, _xp_needed = compute_prestige_level_progress(active.total_xp, active.prestige_tier)
        eligible = is_eligible_to_prestige(active.total_xp, active.prestige_tier)
        self._prestige_body.setText(format_prestige_status(level, eligible, active.prestige_tier))
        self._prestige_button.setVisible(eligible)

    def _on_prestige_clicked(self) -> None:
        if self.context.profiles is None:
            return
        active = self.context.profiles.get_active_profile()
        if active is None:
            return
        # ProfileManager.prestige() re-checks eligibility itself
        # (never trusts the UI already gated this) and returns None if
        # it's rejected — refreshing either way keeps the card honest.
        self.context.profiles.prestige(active.profile_id)
        self._refresh_stats_label()
        self._refresh_prestige_card()
        self._refresh_rewards_card()

    def _refresh_rewards_card(self) -> None:
        while self._rewards_layout.count() > 1:  # keep the eyebrow title (index 0)
            item = self._rewards_layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self.context.rewards is None or self.context.profiles is None:
            return
        active = self.context.profiles.get_active_profile()
        if active is None:
            empty = QLabel("No active profile.")
            empty.setObjectName("SubtitleLabel")
            self._rewards_layout.addWidget(empty)
            return

        # Snappy "check on view" unlock feedback — safe to call every
        # refresh, scan_for_new_unlocks() is idempotent (see its own
        # docstring); the daily-occasion timer in core/application.py
        # also calls this so it fires even if this page is never opened.
        self.context.rewards.scan_for_new_unlocks(active.profile_id)
        self.context.rewards.scan_for_new_hidden_achievements(active.profile_id)
        stat_values = self.context.rewards.all_stat_values(active.profile_id)
        stat_by_id = {definition.stat_id: definition for definition in STAT_DEFINITIONS}
        unlocked_ids = set(self.context.rewards.unlocked_reward_ids(active.profile_id))

        # Challenge chains (2026-09-14 rarity/tiered-chain pass) — one
        # chain per real stat, escalating tiers with Borderlands-style
        # rarity (core.rarity) instead of the old flat one-shot
        # rewards. Each chain shows its earned title (if any, colored
        # by rarity) plus real progress toward the next locked tier, or
        # a "maxed out" line once every tier is earned.
        for index, chain in enumerate(CHALLENGE_CHAINS):
            if index > 0:
                rule = QFrame()
                rule.setFrameShape(QFrame.Shape.HLine)
                rule.setObjectName("HairlineRule")
                self._rewards_layout.addWidget(rule)

            stat = stat_by_id.get(chain.stat_id)
            header = QLabel(f"{stat.icon if stat else ''} {stat.name if stat else chain.chain_id}".strip())
            header.setObjectName("SkillCardTitle")
            self._rewards_layout.addWidget(header)

            upcoming = next_locked_tier(chain.tiers, unlocked_ids)
            if upcoming is None:
                # Every tier unlocked — show one "maxed out" line for
                # the last tier rather than both an "Earned" line and
                # a redundant "Maxed out" line for the same tier.
                last_tier = chain.tiers[-1]
                maxed_label = QLabel(format_chain_maxed_line(last_tier.icon, last_tier.name))
                maxed_label.setStyleSheet(f"color: {rarity_color_for_index(last_tier.rarity_index)};")
                self._rewards_layout.addWidget(maxed_label)
                continue

            earned = highest_unlocked_tier(chain.tiers, unlocked_ids)
            if earned is not None:
                earned_label = QLabel(format_earned_title_line(earned.icon, earned.name))
                earned_label.setWordWrap(True)
                earned_label.setStyleSheet(f"color: {rarity_color_for_index(earned.rarity_index)};")
                self._rewards_layout.addWidget(earned_label)

            value = stat_values.get(chain.stat_id, 0.0)
            status = QLabel(format_reward_status_line(
                upcoming.description, stat.unit if stat else "", value, upcoming.threshold, False,
            ))
            status.setWordWrap(True)
            status.setObjectName("SkillCardPrereq")
            self._rewards_layout.addWidget(status)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(reward_progress_fraction(value, upcoming.threshold) * 100))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            self._rewards_layout.addWidget(bar)

        # Hidden achievements (2026-09-14) — only ever shown once
        # already unlocked (see core/rewards_manager.py's own
        # docstring); the section itself is omitted entirely when none
        # have been found yet, same "don't show a zero-value stat"
        # restraint as everywhere else, and doubles here as not
        # spoiling that hidden achievements exist at all until one is.
        hidden_found = self.context.rewards.unlocked_hidden_achievements(active.profile_id)
        if hidden_found:
            rule = QFrame()
            rule.setFrameShape(QFrame.Shape.HLine)
            rule.setObjectName("HairlineRule")
            self._rewards_layout.addWidget(rule)
            hidden_title = QLabel("Hidden Achievements")
            hidden_title.setObjectName("SkillCardTitle")
            self._rewards_layout.addWidget(hidden_title)
            for achievement in hidden_found:
                hidden_label = QLabel(format_earned_title_line(achievement.icon, achievement.name))
                hidden_label.setWordWrap(True)
                hidden_label.setStyleSheet(f"color: {rarity_color_for_index(achievement.rarity_index)};")
                self._rewards_layout.addWidget(hidden_label)

        prestige_rewards = self.context.rewards.prestige_rewards_for_profile(active.profile_id)
        if prestige_rewards:
            rule = QFrame()
            rule.setFrameShape(QFrame.Shape.HLine)
            rule.setObjectName("HairlineRule")
            self._rewards_layout.addWidget(rule)
            emblem_title = QLabel("Prestige Emblems")
            emblem_title.setObjectName("SkillCardTitle")
            self._rewards_layout.addWidget(emblem_title)
            for entry in prestige_rewards:
                emblem_label = QLabel(f"\U0001F3C6 {entry['name']}")
                emblem_label.setStyleSheet(f"color: {entry['color']};")
                self._rewards_layout.addWidget(emblem_label)

    def _refresh_achievements(self) -> None:
        while self._achievements_layout.count() > 1:  # keep the eyebrow title (index 0)
            item = self._achievements_layout.takeAt(1)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self.context.notifications is None:
            return
        achievements = [n for n in self.context.notifications.list_all() if n.source == "achievements"][:3]
        if not achievements:
            empty = QLabel("No achievements logged yet.")
            empty.setObjectName("SubtitleLabel")
            self._achievements_layout.addWidget(empty)
            return

        for index, notification in enumerate(achievements):
            if index > 0:
                rule = QFrame()
                rule.setFrameShape(QFrame.Shape.HLine)
                rule.setObjectName("HairlineRule")
                self._achievements_layout.addWidget(rule)
            title = QLabel(format_achievement_title_for_display(notification.title))
            title.setObjectName("SkillCardTitle")
            title.setWordWrap(True)
            self._achievements_layout.addWidget(title)
            message = QLabel(notification.message)
            message.setWordWrap(True)
            self._achievements_layout.addWidget(message)
            meta = QLabel(f"{notification.created_at} · source=achievements")
            meta.setObjectName("SkillCardPrereq")
            self._achievements_layout.addWidget(meta)

    def _refresh_next_step(self) -> None:
        self._focus_skill_id = None
        if self.context.skills is None:
            self._next_step_body.setText(format_next_honest_step_line(None))
            return
        profile_id = self._active_profile_id()
        definitions = self.context.skills.all_skills()
        xp_by_skill_id = {
            definition.skill_id: self.context.skills.get_progress(profile_id, definition.skill_id).total_xp
            for definition in definitions
        } if profile_id else {}
        skill_id = next_honest_step(definitions, xp_by_skill_id)
        self._focus_skill_id = skill_id
        skill_name = self.context.skills.get_skill(skill_id).name if skill_id else None
        self._next_step_body.setText(format_next_honest_step_line(skill_name))

    def _refresh_grid(self) -> None:
        # deleteLater() alone isn't enough here — it only schedules
        # removal for a future DeferredDelete event, so a taken-out
        # widget can still be visible (still parented to
        # _grid_container) for one or more repaint cycles. hide() +
        # setParent(None) detaches it from view immediately; deleteLater()
        # still reclaims it once the event loop is idle.
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        if self.context.skills is None or self._current_category is None:
            self._grid_container.set_connections([])
            return

        profile_id = self._active_profile_id()
        # Sorted by tier so a prerequisite's card never lands in a
        # *later* grid row than its dependent's — real connector lines
        # need that to read as a tree at all. Caught in this phase's
        # own manual verification: raw definitions.json order put
        # gardening and seed_starting (its dependent) in the same row,
        # making the straight-line connector invisible/meaningless.
        skills = sorted(self.context.skills.skills_in_category(self._current_category), key=lambda d: (d.tier, d.name))
        columns = 4
        cards_by_skill_id: dict[str, QFrame] = {}
        for index, definition in enumerate(skills):
            card = self._build_skill_card(definition, profile_id)
            cards_by_skill_id[definition.skill_id] = card
            self._grid_layout.addWidget(card, index // columns, index % columns)

        # Connector lines only between nodes that actually share this
        # grid — a prerequisite in a different category (e.g.
        # greenhouse_automation needing "automation") draws no line
        # this pass; see the Phase 4 plan/ROADMAP entry.
        connections = [
            (cards_by_skill_id[prereq_id], card)
            for definition in skills
            for prereq_id in definition.prerequisite_skill_ids
            if prereq_id in cards_by_skill_id
            for card in [cards_by_skill_id[definition.skill_id]]
        ]
        self._grid_container.set_connections(connections)

    def _build_skill_card(self, definition: SkillDefinition, profile_id: Optional[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        locked = profile_id is not None and not self.context.skills.is_unlocked(profile_id, definition.skill_id)
        card.setProperty("locked", locked)
        card.setProperty("focus", bool(profile_id) and definition.skill_id == self._focus_skill_id)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

        name_row = QHBoxLayout()
        # Locked cards use format_locked_skill_name()'s plain-ASCII
        # "(Locked)" marker rather than the skill's own icon — see that
        # function's own docstring for the real, reproduced font-
        # fallback bug this avoids.
        if locked:
            name_text = format_locked_skill_name(definition.name)
        else:
            name_text = f"{definition.icon}  {definition.name}" if definition.icon else definition.name
        name_label = QLabel(name_text)
        name_label.setObjectName("SkillCardTitle")
        name_label.setWordWrap(True)
        # QLabel word-wrap doesn't reliably compute its wrapped height
        # inside a QGridLayout nested in a QScrollArea (a known Qt
        # heightForWidth-propagation gap) — without a concrete width to
        # wrap against, long text just clips at the card edge instead
        # of flowing to a second line. Capping the LABEL's own max
        # width (not the card's — see _LABEL_MAX_WIDTH's own comment)
        # sidesteps that.
        name_label.setMaximumWidth(_LABEL_MAX_WIDTH)
        name_row.addWidget(name_label, stretch=1)
        tier_chip = QLabel(format_tier_chip(definition.tier))
        tier_chip.setObjectName("SkillCardTier")
        name_row.addWidget(tier_chip)
        card_layout.addLayout(name_row)

        progress = self.context.skills.get_progress(profile_id, definition.skill_id) if profile_id else None
        total_xp = progress.total_xp if progress else 0
        level, xp_into, xp_needed = compute_skill_level_progress(total_xp)

        if locked:
            # No bar, no status line — matches the design's own
            # "locked/untouched nodes... no bar" spec. The "(Locked)
            # <name>" title above and the "Requires: ..." prereq line
            # below already tell the whole story for this card.
            pass
        elif total_xp == 0:
            # Unlocked but never touched — same "no bar" treatment,
            # distinct wording from the locked case since there's
            # nothing to require here, just nothing logged yet.
            untouched_label = QLabel("No XP logged yet")
            untouched_label.setObjectName("SkillCardPrereq")
            card_layout.addWidget(untouched_label)
        else:
            subtitle = QLabel(format_skill_subtitle(level, xp_into, xp_needed))
            subtitle.setObjectName("SubtitleLabel")
            subtitle.setWordWrap(True)
            subtitle.setMaximumWidth(_LABEL_MAX_WIDTH)
            card_layout.addWidget(subtitle)

            bar = QProgressBar()
            bar.setRange(0, xp_needed)
            bar.setValue(min(xp_into, xp_needed))
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            card_layout.addWidget(bar)

            # Capability status (2026-09-11) — only reached for
            # unlocked skills with real XP; locked/untouched cards
            # already said everything they need to above.
            if profile_id is not None:
                status = self.context.skills.capability_status(profile_id, definition.skill_id)
                status_label = QLabel(format_skill_status_line(level, status))
                status_label.setObjectName("SkillCardStatus")
                status_label.setProperty("status", status)
                card_layout.addWidget(status_label)

        if definition.prerequisite_skill_ids:
            prereq_names = []
            for prereq_id in definition.prerequisite_skill_ids:
                prereq_def = self.context.skills.get_skill(prereq_id)
                prereq_names.append(prereq_def.name if prereq_def else prereq_id)
            prereq_label = QLabel(format_prerequisites_line(prereq_names))
            prereq_label.setObjectName("SkillCardPrereq")
            prereq_label.setWordWrap(True)
            prereq_label.setMaximumWidth(_LABEL_MAX_WIDTH)
            card_layout.addWidget(prereq_label)

        return card

    def _on_skill_xp_changed(self, profile_id: str, skill_id: str) -> None:
        if not self._widget_built or profile_id != self._active_profile_id():
            return
        self._refresh_stats_label()
        self._refresh_next_step()
        self._refresh_grid()
        self._refresh_achievements()

    def _on_profile_xp_changed(self, profile_id: str) -> None:
        if not self._widget_built or profile_id != self._active_profile_id():
            return
        self._refresh_stats_label()
