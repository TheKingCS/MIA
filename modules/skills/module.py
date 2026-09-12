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

Read-only for this first pass, matching docs/ROADMAP.md's dated
entry's Phase 1 scope. A true graphical tree view (nodes connected by
lines showing prerequisite relationships) is real future scope, not
built here — this pass shows the same information (locked/unlocked,
prerequisites named per card) as a scannable categorized grid instead,
same "ship the real information first, the fancier visualization
later" bias modules/missions/module.py's own MissionCard took before
its 2026-07-18 redesign.
"""

from __future__ import annotations

from typing import Optional

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
from core.skill_leveling import compute_skill_level_progress
from core.skill_manager import SkillDefinition
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


def format_skills_trained_summary(trained_count: int, total_count: int) -> str:
    """Pure formatting logic — testable without Qt."""
    return f"{trained_count} of {total_count} skills trained"


def format_prerequisites_line(prereq_names: list[str]) -> str:
    """Pure formatting logic — testable without Qt."""
    return "Requires: " + ", ".join(prereq_names)


def format_capability_status_label(status: str) -> str:
    """Pure formatting logic — testable without Qt. Title-cases one of
    core.skill_leveling.CAPABILITY_STATUSES ("learning" -> "Learning")."""
    return status.capitalize()


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

    def on_load(self) -> None:
        super().on_load()
        # Subscribed here, not __init__, so an unopened Skills module
        # costs nothing at boot beyond the cheap attribute assignment
        # above — same "__init__ must stay cheap, real setup belongs in
        # on_load()" rule every module in this codebase follows.
        self.context.events.subscribe("profile.skill_xp_changed", self._on_skill_xp_changed)
        self.context.events.subscribe("profile.xp_changed", self._on_profile_xp_changed)

    def get_widget(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Skills")
        title.setObjectName("TitleLabel")
        header.addWidget(title)
        header.addStretch()
        self._level_label = QLabel()
        self._level_label.setObjectName("SubtitleLabel")
        header.addWidget(self._level_label)
        layout.addLayout(header)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("SubtitleLabel")
        layout.addWidget(self._summary_label)

        self._tabs_row = QHBoxLayout()
        self._tabs_row.setSpacing(6)
        layout.addLayout(self._tabs_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(12)
        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, stretch=1)

        self._widget_built = True
        categories = self.context.skills.categories() if self.context.skills else []
        self._current_category = categories[0] if categories else None
        self._build_category_tabs(categories)
        self._refresh()
        return root

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
        self._refresh_level_label()
        self._refresh_summary()
        self._refresh_grid()

    def _active_profile_id(self) -> Optional[str]:
        if self.context.profiles is None:
            return None
        active = self.context.profiles.get_active_profile()
        return active.profile_id if active else None

    def _refresh_level_label(self) -> None:
        if self.context.profiles is None:
            self._level_label.setText("")
            return
        active = self.context.profiles.get_active_profile()
        if active is None:
            self._level_label.setText("")
            return
        level, xp_into, xp_needed = compute_level_progress(active.total_xp)
        self._level_label.setText(format_level_footer_line(level, xp_into, xp_needed))

    def _refresh_summary(self) -> None:
        if self.context.skills is None:
            self._summary_label.setText("")
            return
        profile_id = self._active_profile_id()
        total = len(self.context.skills.all_skills())
        trained = len(self.context.skills.progress_for_profile(profile_id)) if profile_id else 0
        self._summary_label.setText(format_skills_trained_summary(trained, total))

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
            return

        profile_id = self._active_profile_id()
        skills = self.context.skills.skills_in_category(self._current_category)
        columns = 3
        for index, definition in enumerate(skills):
            card = self._build_skill_card(definition, profile_id)
            self._grid_layout.addWidget(card, index // columns, index % columns)

    def _build_skill_card(self, definition: SkillDefinition, profile_id: Optional[str]) -> QFrame:
        card = QFrame()
        card.setObjectName("DashboardCard")
        locked = profile_id is not None and not self.context.skills.is_unlocked(profile_id, definition.skill_id)
        card.setProperty("locked", locked)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(6)

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
        card_layout.addWidget(name_label)

        progress = self.context.skills.get_progress(profile_id, definition.skill_id) if profile_id else None
        total_xp = progress.total_xp if progress else 0
        level, xp_into, xp_needed = compute_skill_level_progress(total_xp)

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

        # Capability status tiers (2026-09-11) — only for unlocked
        # skills; a locked card already says "(Locked) <name>" via
        # format_locked_skill_name() above, so a second "Locked" label
        # here would just repeat it.
        if not locked and profile_id is not None:
            status = self.context.skills.capability_status(profile_id, definition.skill_id)
            status_label = QLabel(format_capability_status_label(status))
            status_label.setObjectName("SkillCardStatus")
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
        self._refresh_summary()
        self._refresh_grid()

    def _on_profile_xp_changed(self, profile_id: str) -> None:
        if not self._widget_built or profile_id != self._active_profile_id():
            return
        self._refresh_level_label()
