"""
gui.add_trail_map_dialog
============================

Small dialog for cataloging one trail map PDF into
core.trail_map_library.TrailMapLibrary, used by modules/maps/module.py.
Same "validate-then-expose-via-properties on accept" shape as
gui/add_edit_waypoint_dialog.py. Source is exactly one of a URL or a
local file — picking one clears the other, since
TrailMapLibrary.add_from_url()/add_from_local_file() are two distinct
methods, not one call with an ambiguous source.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class AddTrailMapDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Trail Map")
        self.setFixedSize(420, 320)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Park name:"))
        self.park_name_edit = QLineEdit()
        self.park_name_edit.setPlaceholderText("e.g. Cumberland Falls State Resort Park")
        layout.addWidget(self.park_name_edit)

        layout.addWidget(QLabel("State:"))
        self.state_edit = QLineEdit()
        self.state_edit.setPlaceholderText("e.g. Kentucky")
        layout.addWidget(self.state_edit)

        layout.addWidget(QLabel("Trail map PDF URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://...")
        self.url_edit.textEdited.connect(self._on_url_edited)
        layout.addWidget(self.url_edit)

        layout.addWidget(QLabel("— or —"))

        browse_button = QPushButton("Browse for a PDF already on this device...")
        browse_button.clicked.connect(self._on_browse)
        layout.addWidget(browse_button)

        self._local_file_label = QLabel("No file selected.")
        self._local_file_label.setObjectName("DashboardSectionBody")
        layout.addWidget(self._local_file_label)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._local_file_path: Optional[str] = None
        self._park_name: str = ""
        self._state: str = ""
        self._url: str = ""

    def _on_url_edited(self, text: str) -> None:
        if text:
            self._local_file_path = None
            self._local_file_label.setText("No file selected.")

    def _on_browse(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Trail Map PDF", "", "PDF files (*.pdf)")
        if not file_path:
            return
        self._local_file_path = file_path
        self._local_file_label.setText(file_path)
        self.url_edit.clear()

    def _on_accept(self) -> None:
        park_name = self.park_name_edit.text().strip()
        state = self.state_edit.text().strip()
        url = self.url_edit.text().strip()

        if not park_name:
            self.park_name_edit.setPlaceholderText("Park name can't be empty!")
            return
        if not state:
            self.state_edit.setPlaceholderText("State can't be empty!")
            return
        if not url and not self._local_file_path:
            self.url_edit.setPlaceholderText("Enter a URL or browse for a local file!")
            return

        self._park_name = park_name
        self._state = state
        self._url = url
        self.accept()

    @property
    def entered_park_name(self) -> str:
        return self._park_name

    @property
    def entered_state(self) -> str:
        return self._state

    @property
    def entered_url(self) -> str:
        """"" if a local file was chosen instead — see entered_local_file_path."""
        return self._url

    @property
    def entered_local_file_path(self) -> Optional[str]:
        """None if a URL was chosen instead — see entered_url."""
        return self._local_file_path
