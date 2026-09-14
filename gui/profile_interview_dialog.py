"""
gui.profile_interview_dialog
===============================

Shown right after a new profile is created from the profile-select
screen's "Add Profile" flow (gui/add_profile_dialog.py stays a small,
focused name+password dialog, unchanged — this is a separate, second
dialog, not folded into it, same reasoning `AddProfileDialog`'s own
docstring already gives for why IT stays small). See
gui/widgets/interview_form.py's own docstring for the full design;
this dialog is just Save/Skip chrome around that shared form.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from gui.widgets.interview_form import InterviewForm


class ProfileInterviewDialog(QDialog):
    def __init__(self, context, profile_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Tell MIA About You")
        self.setFixedSize(420, 420)

        layout = QVBoxLayout(self)
        self.form = InterviewForm(context, profile_name=profile_name)
        layout.addWidget(self.form)

        buttons = QDialogButtonBox()
        skip_button = buttons.addButton("Skip for now", QDialogButtonBox.ButtonRole.RejectRole)
        save_button = buttons.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        skip_button.clicked.connect(self.reject)
        save_button.clicked.connect(self.accept)
        layout.addWidget(buttons)
