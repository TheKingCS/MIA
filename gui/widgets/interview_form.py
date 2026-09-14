"""
gui.widgets.interview_form
=============================

InterviewForm — the reusable "tell MIA about yourself" content used
by both the first-run SetupWizard (gui/setup_wizard.py's own new
_InterviewPage) and ProfileInterviewDialog (shown right after adding
any later profile, gui/profile_interview_dialog.py). One real QWidget,
not duplicated between a QWizardPage and a QDialog, since both host
the exact same checkboxes + free-text field.

Per the user's own Master Vision handoff (2026-09-14): "a kind of user
interview upon profile creation to get a feel of the user's life,
hobbies, goals, and interests." This is the v1 scope, deliberately
real and small — a structured pick from `core.skill_manager`'s own
real category taxonomy (never a hardcoded, drift-prone duplicate list)
plus one free-text field, persisted verbatim onto the new
`Profile.interests`/`Profile.interview_notes` fields
(core/profile_manager.py). What this does NOT do yet, on purpose: no
mission/module generation from the answers (the vision doc's own
"MIA can generate personalized missions" is real, separate, larger
future scope — nothing in this codebase proposes new Missions from
free text yet), and `interview_notes` is stored as plain read-only
color today, not parsed by anything.
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QGridLayout, QLabel, QTextEdit, QVBoxLayout, QWidget


def format_interview_intro(profile_name: str) -> str:
    """Pure formatting logic — testable without Qt (see
    tests/test_interview_form.py)."""
    name = profile_name.strip() or "there"
    return (
        f"Hey {name} — tell MIA a bit about your life. This helps MIA "
        f"know which skills, missions, and modules actually fit you. "
        f"You can skip this and fill it in anytime later."
    )


class InterviewForm(QWidget):
    def __init__(self, context, profile_name: str = "", parent: QWidget = None) -> None:
        super().__init__(parent)
        self._checkboxes: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._intro_label = QLabel(format_interview_intro(profile_name))
        self._intro_label.setWordWrap(True)
        layout.addWidget(self._intro_label)

        categories_label = QLabel("What parts of life do you want MIA tracking for you?")
        categories_label.setWordWrap(True)
        layout.addWidget(categories_label)

        categories = context.skills.categories() if context is not None and context.skills is not None else []
        grid = QGridLayout()
        for index, category in enumerate(categories):
            checkbox = QCheckBox(category)
            self._checkboxes[category] = checkbox
            grid.addWidget(checkbox, index // 3, index % 3)
        layout.addLayout(grid)

        notes_label = QLabel("Anything else MIA should know about your goals, hobbies, or responsibilities?")
        notes_label.setWordWrap(True)
        layout.addWidget(notes_label)

        self._notes_edit = QTextEdit()
        self._notes_edit.setPlaceholderText(
            "e.g. \"I want to get better at woodworking\" or \"I take care of our garden\""
        )
        self._notes_edit.setMaximumHeight(90)
        layout.addWidget(self._notes_edit)

    def set_profile_name(self, profile_name: str) -> None:
        """Updates the greeting once the real name is known — the
        first-run wizard builds this page before the user has typed
        their name on the earlier Welcome page (see
        gui/setup_wizard.py's own _InterviewPage.initializePage())."""
        self._intro_label.setText(format_interview_intro(profile_name))

    def selected_interests(self) -> list[str]:
        return [category for category, checkbox in self._checkboxes.items() if checkbox.isChecked()]

    def entered_notes(self) -> str:
        return self._notes_edit.toPlainText().strip()
