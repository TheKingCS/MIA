"""
gui.private_journal_panel
============================

The Private Journal tab in Notes (Cognitive Extension slice A, see
docs/COGNITIVE_EXTENSION_PROPOSAL.md): set up the encrypted journal,
unlock it, read and delete what MIA saved from journaling
conversations. Everything here goes through
self.context.private_journal (core/private_journal.py).

Unlocking uses one passphrase for everything MIA keeps encrypted: when
the Plaid vault is set up, locked, and opens with the same passphrase,
it's unlocked too, so "unlock MIA once per boot" is one prompt.
"""

from __future__ import annotations

import html
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.logger import get_logger
from core.private_journal import PrivateJournalEntry
from core.secrets_manager import SecretsError

log = get_logger(__name__)


def format_private_entry_row(entry: PrivateJournalEntry) -> str:
    """Pure formatting logic."""
    mood = f"  · {entry.mood}" if entry.mood else ""
    return f"{entry.created_at[:10]}  {entry.title}{mood}"


def render_private_entry_html(entry: PrivateJournalEntry) -> str:
    """Pure formatting logic: the reading view for one entry."""
    esc = html.escape
    parts = [f"<h3>{esc(entry.title)}</h3>", f"<p><i>{esc(entry.created_at.replace('T', ' ')[:16])}</i></p>"]
    if entry.mood:
        parts.append(f"<p><b>Mood:</b> {esc(entry.mood)}</p>")
    if entry.themes:
        parts.append(f"<p><b>Themes:</b> {esc(', '.join(entry.themes))}</p>")
    if entry.summary:
        parts.append(f"<p>{esc(entry.summary)}</p>")
    parts.append("<hr>")
    for exchange in entry.exchanges:
        speaker = "You" if exchange.role == "user" else "MIA"
        parts.append(f"<p><b>{speaker}:</b> {esc(exchange.content)}</p>")
    return "\n".join(parts)


class PrivateJournalPanel(QWidget):
    def __init__(self, context, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.context = context
        self._entries: list[PrivateJournalEntry] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        intro = QLabel(
            "Say \"I want to journal\" or \"just listen\" to MIA and she saves the conversation here, "
            "organized and encrypted. She can always save; reading needs your passphrase. "
            "Say \"off the record\" and nothing is saved."
        )
        intro.setObjectName("SubtitleLabel")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        status_row = QHBoxLayout()
        self._status_label = QLabel("")
        status_row.addWidget(self._status_label, stretch=1)
        self._setup_button = QPushButton("Set Up…")
        self._setup_button.clicked.connect(self._on_setup)
        status_row.addWidget(self._setup_button)
        self._unlock_button = QPushButton("Unlock…")
        self._unlock_button.clicked.connect(self._on_unlock)
        status_row.addWidget(self._unlock_button)
        self._lock_button = QPushButton("Lock")
        self._lock_button.clicked.connect(self._on_lock)
        status_row.addWidget(self._lock_button)
        layout.addLayout(status_row)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Search your journal…")
        self._filter_edit.textChanged.connect(lambda _text: self.refresh())
        layout.addWidget(self._filter_edit)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(lambda _cur, _prev: self._show_selected())
        splitter.addWidget(self._list)
        self._reader = QTextBrowser()
        splitter.addWidget(self._reader)
        splitter.setSizes([280, 520])
        layout.addWidget(splitter, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self._delete_button = QPushButton("Delete Selected")
        self._delete_button.clicked.connect(self._on_delete)
        button_row.addWidget(self._delete_button)
        layout.addLayout(button_row)

        self.refresh()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        # Refresh on show rather than on an event: journal entries are
        # also saved from the phone server's background thread, and Qt
        # widgets must only be touched from the GUI thread.
        super().showEvent(event)
        self.refresh()

    # ------------------------------------------------------------------

    @property
    def _journal(self):
        return self.context.private_journal

    def refresh(self) -> None:
        journal = self._journal
        set_up = journal is not None and journal.is_set_up()
        unlocked = set_up and journal.is_unlocked()

        if journal is None:
            self._status_label.setText("The private journal isn't available.")
        elif not set_up:
            self._status_label.setText("Not set up yet. Choose a passphrase to start.")
        elif not unlocked:
            count = journal.entry_count()
            self._status_label.setText(f"Locked. {count} entr{'y' if count == 1 else 'ies'} saved.")
        else:
            self._status_label.setText("Unlocked.")

        self._setup_button.setVisible(journal is not None and not set_up)
        self._unlock_button.setVisible(set_up and not unlocked)
        self._lock_button.setVisible(unlocked)
        self._filter_edit.setEnabled(unlocked)
        self._delete_button.setEnabled(unlocked)

        selected = self._selected_entry_id()
        self._list.clear()
        self._reader.clear()
        self._entries = []
        if not unlocked:
            return
        query = self._filter_edit.text().strip()
        self._entries = journal.search(query) if query else journal.all_entries()
        for entry in self._entries:
            item = QListWidgetItem(format_private_entry_row(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry.entry_id)
            self._list.addItem(item)
            if entry.entry_id == selected:
                self._list.setCurrentItem(item)

    def _selected_entry_id(self) -> Optional[str]:
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _show_selected(self) -> None:
        entry_id = self._selected_entry_id()
        entry = next((e for e in self._entries if e.entry_id == entry_id), None)
        self._reader.setHtml(render_private_entry_html(entry) if entry is not None else "")

    # ------------------------------------------------------------------

    def _ask_passphrase(self, title: str, label: str) -> Optional[str]:
        text, ok = QInputDialog.getText(self, title, label, QLineEdit.EchoMode.Password)
        return text if ok and text else None

    def _on_setup(self) -> None:
        passphrase = self._ask_passphrase(
            "Set Up Private Journal",
            "Choose a passphrase (8+ characters). You can use the same one as your Plaid vault.\n"
            "If you forget it, the journal can't be read by anyone, MIA included.",
        )
        if passphrase is None:
            return
        again = self._ask_passphrase("Set Up Private Journal", "Type the passphrase again:")
        if again != passphrase:
            QMessageBox.warning(self, "Private Journal", "The passphrases didn't match. Nothing was set up.")
            return
        try:
            self._journal.setup(passphrase)
        except SecretsError as exc:
            QMessageBox.warning(self, "Private Journal", str(exc))
            return
        self._unlock_plaid_too(passphrase)
        self.refresh()

    def _on_unlock(self) -> None:
        passphrase = self._ask_passphrase("Unlock Private Journal", "Passphrase:")
        if passphrase is None:
            return
        try:
            self._journal.unlock(passphrase)
        except SecretsError:
            QMessageBox.warning(self, "Private Journal", "That passphrase didn't work.")
            return
        self._unlock_plaid_too(passphrase)
        self.refresh()

    def _unlock_plaid_too(self, passphrase: str) -> None:
        # The document inbox's mailbox password shares the passphrase too.
        mail = getattr(self.context, "inbox_mail", None)
        if mail is not None and mail.vault.exists() and not mail.vault.unlocked:
            mail.vault.try_unlock(passphrase)
        plaid = getattr(self.context, "plaid", None)
        if plaid is None or not plaid.is_configured() or plaid.is_unlocked():
            return
        try:
            if plaid.verify_passphrase(passphrase):
                plaid.unlock(passphrase)
        except Exception:
            log.exception("Plaid unlock alongside the private journal failed.")

    def _on_lock(self) -> None:
        self._journal.lock()
        self.refresh()

    def _on_delete(self) -> None:
        entry_id = self._selected_entry_id()
        if entry_id is None:
            QMessageBox.information(self, "Private Journal", "Select an entry to delete.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete Journal Entry",
            "Delete this journal entry for good?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._journal.delete_entry(entry_id)
            self.refresh()
