"""
gui.add_edit_playlist_dialog
===============================

Small dialog for creating or renaming a single Playlist
(modules/music/module.py's Playlists tab) — just a name, same minimal
single-field shape as gui/add_edit_task_dialog.py reduced down.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout

from core.music_manager import Playlist


class AddEditPlaylistDialog(QDialog):
    """Naming a new playlist or renaming one."""
    def __init__(self, parent=None, playlist: Optional[Playlist] = None) -> None:
        """The name field (the current name when renaming) with OK and Cancel."""
        super().__init__(parent)
        self.setWindowTitle("Rename Playlist" if playlist is not None else "New Playlist")
        self.setFixedSize(320, 130)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Road Trip, Focus, Dinner Party")
        layout.addWidget(self.name_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if playlist is not None:
            self.name_edit.setText(playlist.name)

        self._name: str = ""

    def _on_accept(self) -> None:
        """Keeps the name and closes; an empty name is pointed out in its box instead."""
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setPlaceholderText("Name can't be empty!")
            return
        self._name = name
        self.accept()

    @property
    def entered_name(self) -> str:
        """The name entered in the dialog (kept when OK is pressed)."""
        return self._name
