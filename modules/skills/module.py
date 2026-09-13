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

from core.leveling import compute_level_progress
from core.skill_leveling import (
    CAPABILITY_STATUSES,
    capability_status_for_level,
    compute_skill_level_progress,
    next_honest_step,
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


def format_header_stats_line(profile_level: int, trained: int, total: int, demonstrated: int) -> str:
    """Pure formatting logic — testable without Qt. "PROFILE LEVEL 7 ·
    SKILLS TOUCHED 23/96 · DEMONSTRATED 4"."""
    return f"PROFILE LEVEL {profile_level} · SKILLS TOUCHED {trained}/{total} · DEMONSTRATED {demonstrated}"


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

        column_layout.addStretch(1)
        return column

    def _build_category_tabs(self, categories: list[str]) -> None:
        for category in categories:
            button = QPushButton(category)
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
        profile_level = compute_level_progress(active.total_xp)[0] if active else 0
        profile_id = self._active_profile_id()
        total = len(self.context.skills.all_skills())
        trained = len(self.context.skills.progress_for_profile(profile_id)) if profile_id else 0
        demonstrated = self._demonstrated_count(profile_id)
        self._stats_label.setText(format_header_stats_line(profile_level, trained, total, demonstrated))

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
