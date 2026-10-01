"""
modules.inbox.module
=======================

Inbox: the document inbox's screen (2026-09-28). Receipts, manuals,
warranties and other documents that were dropped in the inbox folder,
sent from the phone, or emailed in, each with MIA's reading of it:
what it is, which of your things it's for, the receipt's total/date/
store, the manual's maintenance schedule. Correct anything, then File
It (or Dismiss). All logic lives in core/inbox_manager.py
(self.context.inbox); this is the Qt wrapper.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.budget_manager import EXPENSE_CATEGORIES
from core.inbox_classify import DOC_TYPE_LABELS, INVOICE, RECEIPT
from core.inbox_manager import DISMISSED, FILED, PENDING, InboxItem
from core.secrets_manager import SecretsError
from modules.module_base import ModuleBase
from core.region import money

_STATUS_MARK = {PENDING: "●", FILED: "✓", DISMISSED: "✕"}


def format_inbox_row(item: InboxItem, asset_name: str = "") -> str:
    """Pure formatting logic."""
    text = f"{_STATUS_MARK.get(item.status, '')} {item.label}"
    if item.reading:
        text += "  (reading…)"
    if asset_name:
        text += f"  →  {asset_name}"
    return text + f"   ({item.received_at[:10]}, {item.source})"


def _item_text(line: dict) -> str:
    qty = line.get("quantity")
    return f"{line.get('description', '')}" + (f" ×{qty:g}" if qty and qty != 1 else "") + f"  {money(line.get('amount', 0), ',.2f')}"


def describe_item(item: InboxItem, asset_name: str = "", project_name: str = "") -> str:
    """Pure formatting logic: what MIA read, in plain lines."""
    lines = [f"<b>{DOC_TYPE_LABELS.get(item.doc_type, 'Document')}</b> · from {item.source} · {item.received_at.replace('T', ' ')[:16]}"]
    if item.subject:
        lines.append(f"Subject: {item.subject}")
    if item.sender:
        lines.append(f"From: {item.sender}")
    if item.doc_type in (RECEIPT, INVOICE):
        amount = f"{money(item.amount, ',.2f')}" if item.amount is not None else "not found"
        lines.append(f"Total: {amount}" + (f" (read from {item.amount_basis})" if item.amount_basis else ""))
        lines.append(f"Date: {item.doc_date or 'not found'} · Store: {item.vendor or 'not found'}")
    if item.items:
        shown = [f"&nbsp;&nbsp;• {html.escape(_item_text(i))}" for i in item.items[:8]]
        more = f"<br>&nbsp;&nbsp;…and {len(item.items) - 8} more" if len(item.items) > 8 else ""
        lines.append("Items:<br>" + "<br>".join(shown) + more)
        if item.items_note:
            lines.append(f"<i>{html.escape(item.items_note)}</i>")
    lines.append(f"For: {asset_name or 'no match'}" + (f" · Build: {project_name}" if project_name else ""))
    if not item.readable or item.note:
        lines.append(f"<i>{item.note}</i>")
    if item.filed_note:
        lines.append(f"<b>{item.filed_note}</b>")
    return "<br>".join(lines)


class InboxModule(ModuleBase):
    module_id = "inbox"
    display_name = "Inbox"
    description = "Receipts, manuals and documents MIA files for you."
    icon = "\U0001F4E5"  # inbox tray

    def __init__(self, context) -> None:
        super().__init__(context)
        self._list: Optional[QListWidget] = None

    # ------------------------------------------------------------------

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)
        hint = QLabel(
            "Drop files in the inbox folder, send them from your phone, or email them to MIA's mailbox. "
            "MIA reads each one and suggests where it goes; nothing is filed until you say so."
        )
        hint.setObjectName("SubtitleLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        top = QHBoxLayout()
        for text, handler in (("Add Files…", self._on_add_files), ("Check Now", self._on_check_now),
                              ("Email Settings…", self._on_email_settings), ("Open Inbox Folder", self._on_open_folder)):
            button = QPushButton(text)
            button.clicked.connect(handler)
            top.addWidget(button)
        layout.addLayout(top)
        self._email_status = QLabel("")
        self._email_status.setObjectName("SubtitleLabel")
        layout.addWidget(self._email_status)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.currentItemChanged.connect(lambda _c, _p: self._show_selected())
        splitter.addWidget(self._list)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        self._summary = QLabel("")
        self._summary.setWordWrap(True)
        self._summary.setTextFormat(Qt.TextFormat.RichText)
        detail_layout.addWidget(self._summary)
        form = QFormLayout()
        self._asset_combo = QComboBox()
        self._project_combo = QComboBox()
        self._amount_spin = QDoubleSpinBox()
        self._amount_spin.setRange(0, 1_000_000)
        self._amount_spin.setDecimals(2)
        self._amount_spin.setPrefix("$")
        self._category_combo = QComboBox()
        self._category_combo.addItems(EXPENSE_CATEGORIES)
        form.addRow("For item:", self._asset_combo)
        form.addRow("For build:", self._project_combo)
        form.addRow("Amount:", self._amount_spin)
        form.addRow("Category:", self._category_combo)
        detail_layout.addLayout(form)
        self._details_label = QLabel("Update its page (tick what to fill in):")
        detail_layout.addWidget(self._details_label)
        self._details_list = QListWidget()
        self._details_list.setMaximumHeight(120)
        detail_layout.addWidget(self._details_list)
        detail_layout.addWidget(QLabel("Maintenance schedule found (tick to add as tasks):"))
        self._schedule_list = QListWidget()
        detail_layout.addWidget(self._schedule_list, stretch=1)
        self._asset_combo.currentIndexChanged.connect(lambda _i: self._show_detail_proposals())
        actions = QHBoxLayout()
        for text, handler in (("File It", self._on_file), ("Dismiss", self._on_dismiss), ("Open File", self._on_open_file)):
            button = QPushButton(text)
            button.clicked.connect(handler)
            actions.addWidget(button)
        detail_layout.addLayout(actions)
        splitter.addWidget(detail)
        splitter.setSizes([360, 520])
        layout.addWidget(splitter, stretch=1)

        self._refresh()
        # core/application.py publishes this when its folder scan takes
        # in new documents (including emails the background check saved).
        self.context.events.unsubscribe("inbox.updated", self._on_inbox_updated)
        self.context.events.subscribe("inbox.updated", self._on_inbox_updated)
        return widget

    def _on_inbox_updated(self, **_kwargs) -> None:
        try:
            self._refresh()
        except RuntimeError:  # the screen's widgets are gone
            self.context.events.unsubscribe("inbox.updated", self._on_inbox_updated)

    # ------------------------------------------------------------------

    @property
    def _inbox(self):
        return self.context.inbox

    def _asset_name(self, asset_id: str) -> str:
        maintenance = self.context.maintenance
        asset = maintenance.get_asset(asset_id) if maintenance and asset_id else None
        return asset.name if asset else ""

    def _project_name(self, project_id: str) -> str:
        projects = self.context.projects
        project = projects.get_project(project_id) if projects and project_id else None
        return project.name if project else ""

    def _refresh(self) -> None:
        if self._list is None or self._inbox is None:
            return
        selected = self._selected_id()
        self._list.clear()
        for item in self._inbox.all_items():
            row = QListWidgetItem(format_inbox_row(item, self._asset_name(item.asset_id)))
            row.setData(Qt.ItemDataRole.UserRole, item.item_id)
            self._list.addItem(row)
            if item.item_id == selected:
                self._list.setCurrentItem(row)
        if self._list.count() and self._list.currentItem() is None:
            self._list.setCurrentRow(0)
        self._refresh_email_status()
        self._show_selected()

    def _refresh_email_status(self) -> None:
        mail = self.context.inbox_mail
        if mail is None or not mail.settings.configured:
            text = "Email: not set up (optional)."
        elif not mail.vault.unlocked:
            text = "Email: set up, locked. Unlock it (Email Settings) or unlock the Private Journal with the same passphrase."
        else:
            text = f"Email: checking {mail.settings.get('username')} every 10 minutes. {mail.last_result}"
        self._email_status.setText(text)

    def _selected_id(self) -> Optional[str]:
        row = self._list.currentItem() if self._list else None
        return row.data(Qt.ItemDataRole.UserRole) if row is not None else None

    def _selected(self) -> Optional[InboxItem]:
        item_id = self._selected_id()
        return self._inbox.get_item(item_id) if item_id else None

    def _show_selected(self) -> None:
        item = self._selected()
        self._asset_combo.clear()
        self._project_combo.clear()
        self._schedule_list.clear()
        self._details_list.clear()
        if item is None:
            self._summary.setText("Nothing in the inbox yet.")
            return
        self._summary.setText(describe_item(item, self._asset_name(item.asset_id), self._project_name(item.project_id)))
        self._asset_combo.blockSignals(True)
        self._asset_combo.addItem("(none)", "")
        for asset in self.context.maintenance.all_assets() if self.context.maintenance else []:
            self._asset_combo.addItem(asset.name, asset.asset_id)
        self._asset_combo.setCurrentIndex(max(0, self._asset_combo.findData(item.asset_id)))
        self._asset_combo.blockSignals(False)
        self._project_combo.addItem("(none)", "")
        for project in self.context.projects.all_projects() if self.context.projects else []:
            self._project_combo.addItem(project.name, project.project_id)
        self._project_combo.setCurrentIndex(max(0, self._project_combo.findData(item.project_id)))
        is_money = item.doc_type in (RECEIPT, INVOICE)
        self._amount_spin.setEnabled(is_money)
        self._category_combo.setEnabled(is_money)
        self._amount_spin.setValue(item.amount or 0)
        if item.category:
            self._category_combo.setCurrentText(item.category)
        for step in item.schedule:
            text = step["task"] + (f", every {step['interval_hours']:g} hours" if step.get("interval_hours")
                                   else f", every {step['interval_miles']:g} miles" if step.get("interval_miles")
                                   else f", every {step['interval_days']} days")
            row = QListWidgetItem(text)
            row.setToolTip(step.get("source", ""))
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked)
            self._schedule_list.addItem(row)
        self._show_detail_proposals()
        pending = item.status == PENDING
        for widget in (self._asset_combo, self._project_combo, self._schedule_list, self._details_list):
            widget.setEnabled(pending)
        if not pending:
            self._amount_spin.setEnabled(False)
            self._category_combo.setEnabled(False)

    def _show_detail_proposals(self) -> None:
        """The detail updates for whichever item is chosen in "For item"."""
        self._details_list.clear()
        item = self._selected()
        proposals = self._inbox.detail_proposals(item, self._asset_combo.currentData() or "") if item else []
        if item is not None and item.status != PENDING:
            proposals = []
        for proposal in proposals:
            row = QListWidgetItem(proposal.text)
            row.setData(Qt.ItemDataRole.UserRole, proposal.field)
            row.setToolTip(f"From: {proposal.source}" if proposal.source else "")
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked if proposal.default_on else Qt.CheckState.Unchecked)
            self._details_list.addItem(row)
        self._details_label.setVisible(bool(proposals))
        self._details_list.setVisible(bool(proposals))

    # ------------------------------------------------------------------

    def _on_add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(None, "Add to Inbox", str(Path.home()),
                                                "Documents (*.pdf *.txt *.eml *.jpg *.jpeg *.png *.heic);;All files (*)")
        for path in paths:
            self._inbox.receive_file(Path(path).name, Path(path).read_bytes(), source="folder")
        if paths:
            self._inbox.scan(now=float("inf"))
            self._refresh()

    def _on_check_now(self) -> None:
        mail = self.context.inbox_mail
        checking = mail is not None and mail.check_now()  # background; new mail shows up within a minute
        self._inbox.scan(now=float("inf"))
        self._refresh()
        if checking:
            self._email_status.setText("Checking email in the background… new messages will show up here within a minute.")

    def _on_open_folder(self) -> None:
        self._inbox.folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._inbox.folder)))

    def _on_open_file(self) -> None:
        item = self._selected()
        if item and item.files:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._inbox.item_folder(item.item_id) / item.files[-1])))

    def _on_file(self) -> None:
        item = self._selected()
        if item is None or item.status != PENDING:
            return
        chosen = [i for i in range(self._schedule_list.count())
                  if self._schedule_list.item(i).checkState() == Qt.CheckState.Checked]
        try:
            note = self._inbox.file_item(
                item.item_id, asset_id=self._asset_combo.currentData() or "", project_id=self._project_combo.currentData() or "",
                amount=self._amount_spin.value() if self._amount_spin.isEnabled() else None,
                category=self._category_combo.currentText() if self._category_combo.isEnabled() else None,
                schedule_indexes=chosen,
                detail_fields=[self._details_list.item(i).data(Qt.ItemDataRole.UserRole)
                               for i in range(self._details_list.count())
                               if self._details_list.item(i).checkState() == Qt.CheckState.Checked],
            )
        except (ValueError, OSError) as exc:
            QMessageBox.warning(None, "File It", str(exc))
            return
        QMessageBox.information(None, "File It", note)
        self._refresh()

    def _on_dismiss(self) -> None:
        item = self._selected()
        if item is not None and item.status == PENDING:
            self._inbox.dismiss(item.item_id)
            self._refresh()

    def _on_email_settings(self) -> None:
        mail = self.context.inbox_mail
        if mail is None:
            return
        if mail.settings.configured and not mail.vault.unlocked:
            passphrase, ok = QInputDialog.getText(None, "Unlock Email", "Passphrase:", QLineEdit.EchoMode.Password)
            if ok and passphrase:
                if not mail.vault.try_unlock(passphrase):
                    QMessageBox.warning(None, "Unlock Email", "That passphrase didn't work.")
                self._refresh_email_status()
            return
        host, ok = QInputDialog.getText(None, "Email Settings", "Mail server (IMAP), e.g. imap.gmail.com:",
                                        text=mail.settings.get("host", "") or "imap.gmail.com")
        if not ok or not host.strip():
            return
        username, ok = QInputDialog.getText(None, "Email Settings", "Email address:", text=mail.settings.get("username", "") or "")
        if not ok or not username.strip():
            return
        password, ok = QInputDialog.getText(None, "Email Settings", "Password (for Gmail, an app password):", QLineEdit.EchoMode.Password)
        if not ok or not password:
            return
        passphrase, ok = QInputDialog.getText(
            None, "Email Settings", "Passphrase to encrypt it (use your vault/journal passphrase to unlock everything at once):",
            QLineEdit.EchoMode.Password,
        )
        if not ok or len(passphrase) < 8:
            QMessageBox.warning(None, "Email Settings", "Use a passphrase of at least 8 characters. Nothing was saved.")
            return
        try:
            mail.vault.store(password, passphrase)
        except (SecretsError, OSError) as exc:
            QMessageBox.warning(None, "Email Settings", str(exc))
            return
        mail.settings.save(host, username)
        QMessageBox.information(None, "Email Settings", "Saved. MIA will check this mailbox every 10 minutes while unlocked.")
        self._refresh_email_status()
