"""
gui.add_edit_listing_dialog
==============================

Small dialog for adding a marketplace listing to a product, used by
modules/workshop/module.py's Products tab. platform/price/status (a
combo over core.product_manager.LISTING_STATUSES)/url. There's no
"edit listing" path yet — core/product_manager.py only exposes
add_listing()/remove_listing(), not update_listing(); this dialog is
add-only, matching that.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from core.product_manager import LISTING_STATUSES
from core.region import symbol


class AddListingDialog(QDialog):
    """Adding a listing for a product: the platform, price, status and link."""
    def __init__(self, parent=None) -> None:
        """The fields (platform, price in the person's currency, status, URL) with OK and Cancel."""
        super().__init__(parent)
        self.setWindowTitle("Add Listing")
        self.setFixedSize(340, 300)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Platform:"))
        self.platform_edit = QLineEdit()
        self.platform_edit.setPlaceholderText("e.g. Etsy, Web Store, Local")
        layout.addWidget(self.platform_edit)

        layout.addWidget(QLabel(f"Price ({symbol()}):"))
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 1_000_000)
        self.price_spin.setDecimals(2)
        layout.addWidget(self.price_spin)

        layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(LISTING_STATUSES)
        layout.addWidget(self.status_combo)

        layout.addWidget(QLabel("URL:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Listing URL (optional)")
        layout.addWidget(self.url_edit)

        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._platform: str = ""
        self._price: float = 0.0
        self._status: str = LISTING_STATUSES[0]
        self._url: str = ""

    def _on_accept(self) -> None:
        """Keeps what was entered and closes; an empty platform is pointed out in its box instead."""
        platform = self.platform_edit.text().strip()
        if not platform:
            self.platform_edit.setPlaceholderText("Platform can't be empty!")
            return

        self._platform = platform
        self._price = self.price_spin.value()
        self._status = self.status_combo.currentText()
        self._url = self.url_edit.text().strip()
        self.accept()

    @property
    def entered_platform(self) -> str:
        """The platform entered in the dialog (kept when OK is pressed)."""
        return self._platform

    @property
    def entered_price(self) -> float:
        """The price entered in the dialog (kept when OK is pressed)."""
        return self._price

    @property
    def entered_status(self) -> str:
        """The status entered in the dialog (kept when OK is pressed)."""
        return self._status

    @property
    def entered_url(self) -> str:
        """The url entered in the dialog (kept when OK is pressed)."""
        return self._url
