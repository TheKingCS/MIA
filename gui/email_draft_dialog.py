"""
gui.email_draft_dialog
========================

The email draft window (2026-10-01, core/email_drafts.py): what MIA
wrote, editable, with **Send** (only here, only when pressed, from your
own address, core/mail_send.py), **Copy**, and **Open in my mail app**.
Closing keeps the draft. `SendingSetupDialog` sets up sending
(Settings → Sending Email).
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from core.email_drafts import DISCARDED, addresses_in, as_text, mailto_url
from core.mail_send import SendError, guess_server, send_in_background, sender_for


class EmailDraftDialog(QDialog):
    def __init__(self, context, draft, profile_id=None, parent=None) -> None:
        super().__init__(parent)
        self.context, self.draft, self.profile_id = context, draft, profile_id
        self.setWindowTitle("Email draft")
        self.setMinimumSize(520, 460)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.to_edit = QLineEdit(", ".join(draft.to))
        self.to_edit.setPlaceholderText("name@example.com")
        self.subject_edit = QLineEdit(draft.subject)
        form.addRow("To:", self.to_edit)
        form.addRow("Subject:", self.subject_edit)
        layout.addLayout(form)
        self.body_edit = QTextEdit()
        self.body_edit.setPlainText(draft.body)
        layout.addWidget(self.body_edit, stretch=1)
        self.status_label = QLabel("MIA never sends without you pressing Send.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        row = QHBoxLayout()
        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("ModuleButton")
        self.send_button.clicked.connect(self._on_send)
        copy_button = QPushButton("Copy")
        copy_button.clicked.connect(self._on_copy)
        mail_app_button = QPushButton("Open in my mail app")
        mail_app_button.clicked.connect(self._on_mail_app)
        discard_button = QPushButton("Discard")
        discard_button.clicked.connect(self._on_discard)
        close_button = QPushButton("Keep for later")
        close_button.clicked.connect(self._on_keep)
        for button in (self.send_button, copy_button, mail_app_button, discard_button, close_button):
            row.addWidget(button)
        layout.addLayout(row)

        sender = sender_for(context, profile_id)
        if not sender.configured:
            self.send_button.setEnabled(False)
            self.send_button.setToolTip("Set up sending in Settings, Sending Email. Copy and your mail app work now.")

    # ------------------------------------------------------------------

    def _drafts(self):
        personal = getattr(self.context, "personal_data", None)
        view = personal.view(self.profile_id) if personal is not None and self.profile_id else self.context
        return view.email_drafts

    def _save_edits(self):
        draft = self._drafts().update(self.draft.draft_id, to=addresses_in(self.to_edit.text()),
                                      subject=self.subject_edit.text(), body=self.body_edit.toPlainText())
        if draft is not None:
            self.draft = draft
        return self.draft

    def _on_copy(self) -> None:
        QGuiApplication.clipboard().setText(as_text(self._save_edits()))
        self.status_label.setText("Copied. Paste it into any email.")

    def _on_mail_app(self) -> None:
        QDesktopServices.openUrl(QUrl(mailto_url(self._save_edits())))
        self.status_label.setText("Opened in your mail app. Send it from there.")

    def _on_keep(self) -> None:
        self._save_edits()
        self.accept()

    def _on_discard(self) -> None:
        self._drafts().mark(self.draft.draft_id, DISCARDED)
        self.reject()

    def _on_send(self) -> None:
        draft = self._save_edits()
        if not draft.to:
            self.status_label.setText("Who should it go to? Add their email address.")
            return
        sender = sender_for(self.context, self.profile_id)
        if not sender.unlocked:
            passphrase, ok = QInputDialog.getText(self, "Unlock sending", "Your sending passphrase:",
                                                  QLineEdit.EchoMode.Password)
            if not ok:
                return
            if not sender.unlock(passphrase):
                self.status_label.setText("That passphrase doesn't match.")
                return
        self.send_button.setEnabled(False)
        self.status_label.setText("Sending...")
        send_in_background(self.context, self.profile_id, draft.draft_id, self._on_sent)

    def _on_sent(self, ok: bool, message: str) -> None:
        self.status_label.setText(message)
        if ok:
            self.send_button.setText("Sent")
        else:
            self.send_button.setEnabled(True)


class SendingSetupDialog(QDialog):
    """Your address, your mail password (an app password for Gmail) and a
    passphrase that encrypts it."""

    def __init__(self, context, profile_id=None, parent=None) -> None:
        super().__init__(parent)
        self.context, self.profile_id = context, profile_id
        self.sender = sender_for(context, profile_id)
        self.setWindowTitle("Sending email")
        self.setMinimumWidth(440)
        layout = QVBoxLayout(self)
        intro = QLabel("Let MIA send the drafts you approve from your own address. For Gmail, make an app password "
                       "(Google Account, Security, 2-Step Verification, App passwords). MIA keeps it encrypted with "
                       "your passphrase and only sends when you press Send.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.address_edit = QLineEdit(self.sender.address)
        self.address_edit.setPlaceholderText("you@gmail.com")
        self.address_edit.textChanged.connect(self._on_address_changed)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText("asked once per session before sending")
        self.host_edit = QLineEdit(self.sender.setting("host", "") or "")
        self.host_edit.setPlaceholderText("smtp.example.com (filled in for common providers)")
        form.addRow("Your email:", self.address_edit)
        form.addRow("Mail password:", self.password_edit)
        form.addRow("Passphrase:", self.passphrase_edit)
        form.addRow("Mail server:", self.host_edit)
        layout.addLayout(form)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e06666;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        if self.sender.configured:
            turn_off = buttons.addButton("Turn sending off", QDialogButtonBox.ButtonRole.DestructiveRole)
            turn_off.clicked.connect(self._on_turn_off)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_address_changed(self, text: str) -> None:
        guessed = guess_server(text)
        if guessed is not None:
            self.host_edit.setText(guessed[0])

    def _on_save(self) -> None:
        guessed = guess_server(self.address_edit.text())
        host = self.host_edit.text().strip()
        custom = host and (guessed is None or host != guessed[0])
        try:
            self.sender.setup(self.address_edit.text(), self.password_edit.text(), self.passphrase_edit.text(),
                              host=host if custom else "", port=587 if custom else 0, security="starttls" if custom else "")
        except SendError as exc:
            self.error_label.setText(str(exc))
            return
        self.accept()

    def _on_turn_off(self) -> None:
        self.sender.forget()
        self.accept()
