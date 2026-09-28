"""
Document inbox: classification (core/inbox_classify.py), intake and
filing (core/inbox_manager.py), email checking (core/inbox_mail.py),
the voice tools, the phone upload endpoint and the Inbox screen.
"""

import imaplib
from email.message import EmailMessage
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

import core.budget_manager as budget_module
import core.config_manager as config_module
import core.data_logger_manager as data_logger_module
import core.inbox_mail as inbox_mail_module
import core.inbox_manager as inbox_module
import core.maintenance_manager as maintenance_module
import core.project_manager as project_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.data_logger_manager import DataLoggerManager
from core.event_bus import EventBus
from core.inbox_classify import (
    MANUAL, OTHER, RECEIPT, WARRANTY, document_type, expense_category, maintenance_schedule, match_asset, receipt_fields,
)
from core.inbox_mail import MailChecker, MailSettings, MailVault, fetch_new_messages
from core.inbox_manager import DISMISSED, FILED, PENDING, InboxManager, describe_new_items
from core.maintenance_manager import MaintenanceManager
from core.project_manager import ProjectManager
from tests.assistant_registry import build_desktop_registry
from tests.test_textbook_tutor import write_pdf

RECEIPT_TEXT = """LOWE'S HOME CENTERS
Store 1234  09/28/2026  10:42 AM
2X4X8 PINE STUD      6 @ 3.98   23.88
DECK SCREWS 1LB              9.98
SUBTOTAL                    33.86
SALES TAX                    2.37
TOTAL                       36.23
VISA ************1234       36.23
Thank you for shopping at Lowe's"""

MANUAL_PAGES = [
    "Operator's Manual\nZ315E Residential ZTrak Mower\nJohn Deere",
    "Maintenance Schedule\nChange engine oil every 50 hours.\nReplace air filter every 100 hours.\n"
    "Sharpen mower blades every 25 hours.\nCheck tire pressure every 30 days.",
]

_MODULES = [budget_module, data_logger_module, maintenance_module, project_module, inbox_module, inbox_mail_module]


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ctx(tmp_path, monkeypatch, qapp):
    for module in _MODULES:
        original = module._DATA_DIR
        for attr, value in list(vars(module).items()):
            if isinstance(value, Path) and (value == original or original in value.parents):
                monkeypatch.setattr(module, attr, tmp_path / "data" / value.relative_to(original.parent))
    monkeypatch.setattr(maintenance_module, "_DOCUMENT_ROOT", tmp_path / "maintenance_documents")
    monkeypatch.setattr(inbox_module, "_DEFAULT_FOLDER", tmp_path / "inbox")
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    context.data_logger = DataLoggerManager(context)
    context.maintenance = MaintenanceManager(context)
    context.projects = ProjectManager(context)
    context.inbox = InboxManager(context)
    context.assistant_actions = build_desktop_registry()
    context.mower = context.maintenance.add_asset("Riding Mower", manufacturer="John Deere", model="Z315E", serial_number="1GXZ315EXKJ123456")
    context.truck = context.maintenance.add_asset("Pickup Truck", manufacturer="Ford", model="F-150")
    context.greenhouse = context.projects.add_project("Greenhouse", status="Active")
    context.tmp = tmp_path
    return context


def say(ctx, action, **arguments):
    return ctx.assistant_actions.execute(ctx, action, arguments)


def drop(ctx, name, data, source="folder"):
    ctx.inbox.receive_file(name, data if isinstance(data, bytes) else data.encode("utf-8"), source=source)
    return ctx.inbox.scan(now=float("inf"))


def manual_pdf(ctx):
    return write_pdf(ctx.tmp / "Z315E_manual.pdf", MANUAL_PAGES, None).read_bytes()


# ------------------------------------------------------------------ classification


def test_document_types():
    assert document_type(RECEIPT_TEXT) == RECEIPT
    assert document_type("\n".join(MANUAL_PAGES)) == MANUAL
    assert document_type("Limited warranty. Coverage period is 3 years with proof of purchase.") == WARRANTY
    assert document_type("Hi, see you at the picnic Saturday.") == OTHER
    assert document_type("", filename="mower_receipt.pdf", subject="") == RECEIPT


def test_receipt_fields_read_the_total_not_the_subtotal():
    fields = receipt_fields(RECEIPT_TEXT)
    assert fields.amount == 36.23 and "TOTAL" in fields.amount_basis
    assert fields.date == "2026-09-28"
    assert fields.vendor == "Lowe's"


def test_receipt_fields_fallbacks():
    fields = receipt_fields("Order placed Sep 3, 2026\nWidget 12.50\nGadget 40.00", sender='"Bob\'s Parts" <bob@example.com>')
    assert fields.amount == 40.00 and "largest" in fields.amount_basis
    assert fields.date == "2026-09-03"
    assert fields.vendor == "Bob's Parts"


def test_asset_match_needs_a_clear_unique_winner(ctx):
    assets = ctx.maintenance.all_assets()
    assert match_asset("Z315E operator's manual", assets).name == "Riding Mower"
    assert match_asset("Serial 1GXZ315EXKJ123456", assets).name == "Riding Mower"
    assert match_asset("John Deere catalog", assets) is None  # maker alone isn't enough
    assert match_asset("a manual for something else", assets) is None


def test_maintenance_schedule_from_a_manual():
    steps = maintenance_schedule("\n".join(MANUAL_PAGES))
    described = [s.describe() for s in steps]
    assert "Change engine oil, every 50 hours" in described
    assert "Replace air filter, every 100 hours" in described
    assert "Check tire pressure, every 30 days" in described
    assert all(s.source for s in steps)
    assert maintenance_schedule("Inspect the belts annually.")[0].interval_days == 365


def test_expense_category():
    assert expense_category("Lowe's", None, None, "") == "Building Materials"
    assert expense_category("AutoZone", None, None, "") == "Transportation"
    assert expense_category("Walmart", SimpleNamespace(), None, "oil filter") == "Maintenance"
    assert expense_category("Amazon", None, None, "") == "Shopping"


# ------------------------------------------------------------------ intake


def test_scan_takes_in_settled_files_and_leaves_fresh_ones(ctx):
    ctx.inbox.receive_file("receipt.txt", RECEIPT_TEXT.encode(), source="phone")
    assert ctx.inbox.scan() == []  # still "being copied"
    [item] = ctx.inbox.scan(now=float("inf"))
    assert item.source == "phone" and item.files == ["receipt.txt"]
    assert item.doc_type == RECEIPT and item.amount == 36.23 and item.vendor == "Lowe's"
    assert item.category == "Building Materials" and item.status == PENDING
    assert item.label == "Lowe's receipt, $36.23"
    assert not any(p.is_file() for p in ctx.inbox.folder.iterdir())  # moved into the item's folder
    assert (ctx.inbox.item_folder(item.item_id) / "receipt.txt").exists()
    # Persisted.
    assert InboxManager(ctx).get_item(item.item_id).amount == 36.23


def test_same_name_arrivals_dont_overwrite_each_other(ctx):
    for _ in range(3):
        ctx.inbox.receive_file("message.eml", b"Subject: hi\n\nhello", source="email")
    assert len(ctx.inbox.scan(now=float("inf"))) == 3


def test_oversized_upload_is_refused(ctx, monkeypatch):
    monkeypatch.setattr(inbox_module, "MAX_UPLOAD_BYTES", 10)
    with pytest.raises(ValueError):
        ctx.inbox.receive_file("big.pdf", b"x" * 11)


def test_a_manual_pdf_is_matched_to_the_mower(ctx):
    [item] = drop(ctx, "Z315E_manual.pdf", manual_pdf(ctx))
    assert item.doc_type == MANUAL and item.asset_id == ctx.mower.asset_id
    assert len(item.schedule) == 4
    assert "Riding Mower" in describe_new_items([item], ctx)


def test_an_image_is_kept_but_marked_unreadable(ctx):
    [item] = drop(ctx, "photo.jpg", b"\xff\xd8\xff\xe0 not really a jpeg")
    assert not item.readable and item.note


def test_email_with_a_pdf_attachment(ctx):
    message = EmailMessage()
    message["Subject"] = "Your mower manual"
    message["From"] = "Deere <no-reply@deere.com>"
    message.set_content("Attached is the operator's manual for your Z315E.")
    message.add_attachment(manual_pdf(ctx), maintype="application", subtype="pdf", filename="Z315E_manual.pdf")
    [item] = drop(ctx, "message.eml", message.as_bytes(), source="email")
    assert item.source == "email" and item.subject == "Your mower manual"
    assert item.files == ["message.eml", "Z315E_manual.pdf"]
    assert item.doc_type == MANUAL and item.asset_id == ctx.mower.asset_id and item.schedule


# ------------------------------------------------------------------ filing


def test_filing_a_receipt_logs_a_tagged_expense(ctx):
    [item] = drop(ctx, "receipt.txt", RECEIPT_TEXT)
    note = ctx.inbox.file_item(item.item_id, project_id=ctx.greenhouse.project_id)
    [expense] = ctx.budget.all_expenses()
    assert expense.amount == 36.23 and expense.payee == "Lowe's" and expense.date == "2026-09-28"
    assert expense.project_id == ctx.greenhouse.project_id and expense.category == "Building Materials"
    assert "$36.23" in note and "Greenhouse" in note
    assert ctx.inbox.get_item(item.item_id).status == FILED
    with pytest.raises(ValueError):
        ctx.inbox.file_item(item.item_id)  # only once


def test_filing_a_manual_attaches_it_and_adds_the_ticked_tasks(ctx):
    [item] = drop(ctx, "Z315E_manual.pdf", manual_pdf(ctx))
    note = ctx.inbox.file_item(item.item_id, schedule_indexes=[0, 3])
    mower = ctx.maintenance.get_asset(ctx.mower.asset_id)
    assert mower.documents == ["Z315E_manual.pdf"]
    assert ctx.maintenance.document_path(mower.asset_id, "Z315E_manual.pdf").exists()
    tasks = {t.title: t for t in ctx.maintenance.all_tasks() if t.asset_id == mower.asset_id}
    assert set(tasks) == {"Change engine oil", "Check tire pressure"}
    assert tasks["Change engine oil"].trigger_type == "runtime" and tasks["Change engine oil"].meter_interval == 50
    assert tasks["Check tire pressure"].interval_days == 30
    assert "Riding Mower" in note and "2 maintenance tasks" in note


def test_filing_an_emailed_manual_attaches_the_pdf_not_the_email(ctx):
    message = EmailMessage()
    message["Subject"] = "manual"
    message.set_content("See attached.")
    message.add_attachment(manual_pdf(ctx), maintype="application", subtype="pdf", filename="Z315E_manual.pdf")
    [item] = drop(ctx, "message.eml", message.as_bytes(), source="email")
    ctx.inbox.file_item(item.item_id)
    assert ctx.maintenance.get_asset(ctx.mower.asset_id).documents == ["Z315E_manual.pdf"]


def test_a_receipt_without_an_amount_asks_for_one(ctx):
    [item] = drop(ctx, "receipt.txt", "Receipt\nThank you for shopping\nPaid in cash")
    with pytest.raises(ValueError):
        ctx.inbox.file_item(item.item_id)
    ctx.inbox.file_item(item.item_id, amount=12.5)
    assert ctx.budget.all_expenses()[0].amount == 12.5


def test_dismiss_and_find_pending(ctx):
    drop(ctx, "receipt.txt", RECEIPT_TEXT)
    drop(ctx, "Z315E_manual.pdf", manual_pdf(ctx))
    assert ctx.inbox.find_pending("the mower manual").doc_type == MANUAL
    assert ctx.inbox.find_pending("the Lowe's receipt").doc_type == RECEIPT
    oldest = ctx.inbox.find_pending("")
    ctx.inbox.dismiss(oldest.item_id)
    assert ctx.inbox.get_item(oldest.item_id).status == DISMISSED
    assert len(ctx.inbox.pending()) == 1
    assert ctx.inbox.all_items()[0].status == PENDING  # pending first


# ------------------------------------------------------------------ voice tools


def test_tools(ctx):
    assert "empty" in say(ctx, "list_inbox")
    drop(ctx, "receipt.txt", RECEIPT_TEXT)
    drop(ctx, "Z315E_manual.pdf", manual_pdf(ctx))
    listing = say(ctx, "list_inbox")
    assert listing.startswith("2 waiting") and "Riding Mower" in listing and "4 maintenance steps" in listing

    reply = say(ctx, "file_inbox_item", item="the Lowe's receipt", **{"for": "greenhouse"})
    assert "$36.23" in reply and "Greenhouse" in reply
    assert ctx.budget.all_expenses()[0].project_id == ctx.greenhouse.project_id

    reply = say(ctx, "file_inbox_item", item="mower manual", with_tasks="no")
    assert "Riding Mower" in reply and "task" not in reply
    assert "nothing waiting" in say(ctx, "file_inbox_item")


def test_tool_asks_which_machine_and_rejects_unknown_names(ctx):
    manual = "Operator's manual. Table of contents.\nChange the oil every 20 hours."
    drop(ctx, "manual.txt", manual)
    assert "Which tool" in say(ctx, "file_inbox_item")
    assert "don't have anything called" in say(ctx, "file_inbox_item", **{"for": "hovercraft"})
    reply = say(ctx, "file_inbox_item", **{"for": "pickup truck"})
    assert "Pickup Truck" in reply and "1 maintenance task" in reply


def test_dismiss_tool(ctx):
    drop(ctx, "receipt.txt", RECEIPT_TEXT)
    assert "without filing" in say(ctx, "dismiss_inbox_item", item="Lowe's")
    assert ctx.inbox.pending() == []


# ------------------------------------------------------------------ email


def test_mail_vault_round_trip(ctx):
    vault = MailVault()
    assert not vault.exists() and not vault.try_unlock("whatever passphrase")
    vault.store("app-password-1234", "correct horse battery")
    fresh = MailVault()
    assert not fresh.unlocked and not fresh.try_unlock("wrong passphrase!")
    assert fresh.try_unlock("correct horse battery") and fresh.password == "app-password-1234"
    assert b"app-password" not in inbox_mail_module._VAULT_FILE.read_bytes()
    fresh.lock()
    assert fresh.password is None


class FakeIMAP:
    def __init__(self, host, port):
        self.host, self.port, self.stored, self.logged_out = host, port, [], False
        self.messages = {b"1": b"Subject: one\n\nfirst", b"2": b"Subject: two\n\nsecond"}

    def login(self, user, password):
        if password != "pw":
            raise imaplib.IMAP4.error("bad login")

    def select(self, folder):
        return "OK", [b"2"]

    def search(self, charset, criterion):
        assert criterion == "UNSEEN"
        return "OK", [b"1 2"]

    def fetch(self, number, parts):
        return "OK", [(b"1 (RFC822 {10}", self.messages[number]), b")"]

    def store(self, number, flags, value):
        self.stored.append(number)

    def logout(self):
        self.logged_out = True


def test_fetch_new_messages_marks_them_read():
    clients = []

    def connect(host, port):
        clients.append(FakeIMAP(host, port))
        return clients[-1]

    assert fetch_new_messages("imap.example.com", "me", "pw", connect=connect) == [b"Subject: one\n\nfirst", b"Subject: two\n\nsecond"]
    assert clients[0].stored == [b"1", b"2"] and clients[0].logged_out
    with pytest.raises(imaplib.IMAP4.error):
        fetch_new_messages("imap.example.com", "me", "wrong", connect=connect)
    assert clients[1].logged_out


def test_mail_checker_saves_messages_into_the_inbox(ctx):
    settings, vault = MailSettings(ctx), MailVault()
    checker = MailChecker(ctx.inbox, settings, vault)
    assert not checker.check_now(fetch=lambda *a: [])  # not set up
    settings.save("imap.example.com", "mia@example.com")
    vault.store("pw", "correct horse battery")
    vault.lock()
    assert not checker.check_now(fetch=lambda *a: [])  # locked
    vault.unlock("correct horse battery")
    seen = []

    def fetch(host, username, password, port, folder):
        seen.append((host, username, password, port, folder))
        return [f"Subject: Receipt\n\n{RECEIPT_TEXT}".encode()]

    assert checker.check_now(fetch=fetch, wait=True)
    assert seen == [("imap.example.com", "mia@example.com", "pw", 993, "INBOX")]
    assert checker.last_result == "Checked email: 1 new."
    [item] = ctx.inbox.scan(now=float("inf"))
    assert item.source == "email" and item.doc_type == RECEIPT and item.amount == 36.23

    def failing(*args):
        raise OSError("network is down")

    checker.check_now(fetch=failing, wait=True)
    assert "network is down" in checker.last_result


# ------------------------------------------------------------------ phone upload


def test_upload_endpoint(ctx):
    from fastapi.testclient import TestClient

    import server.app as server_app

    ctx.profiles = SimpleNamespace(
        list_profiles=lambda: [SimpleNamespace(profile_id="p1", name="Zac", has_password=True)],
        verify_password=lambda pid, pw: pw == "pw",
    )
    ctx.voice = ctx.llm = ctx.push_subscriptions = None
    client = TestClient(server_app.create_app(ctx))
    headers = {"X-Filename": "Lowe%27s%20receipt.txt"}
    assert client.post("/api/inbox/upload", content=RECEIPT_TEXT, headers=headers).status_code == 401
    token = client.post("/api/login", json={"profile_id": "zac", "password": "pw"}).json()["token"]
    headers["Authorization"] = f"Bearer {token}"
    res = client.post("/api/inbox/upload", content=RECEIPT_TEXT, headers=headers)
    assert res.status_code == 200 and res.json()["received"] == "Lowe's receipt.txt"
    [item] = ctx.inbox.scan(now=float("inf"))
    assert item.source == "phone" and item.amount == 36.23
    assert client.post("/api/inbox/upload", content=b"", headers=headers).status_code == 400


# ------------------------------------------------------------------ Inbox screen


def test_inbox_screen(ctx):
    from modules.inbox.module import InboxModule, describe_item, format_inbox_row

    [item] = drop(ctx, "Z315E_manual.pdf", manual_pdf(ctx))
    assert "Riding Mower" in format_inbox_row(item, "Riding Mower") and format_inbox_row(item).startswith("●")
    assert "Manual" in describe_item(item, "Riding Mower") and "Riding Mower" in describe_item(item, "Riding Mower")
    ctx.inbox_mail = None
    module = InboxModule(ctx)
    widget = module.get_widget()
    assert module._list.count() == 1 and module._schedule_list.count() == 4
    assert module._asset_combo.currentData() == ctx.mower.asset_id
    drop(ctx, "receipt.txt", RECEIPT_TEXT)
    ctx.events.publish("inbox.updated")
    assert module._list.count() == 2
    widget.deleteLater()
