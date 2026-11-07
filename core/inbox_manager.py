"""
core.inbox_manager
=====================

The document inbox (2026-09-28): "an email inbox that I can send
receipts and owners manuals and all kinds of business documents to and
it be able to classify it and determine where to put it, like storing
the manual and user guide and maintenance schedule for the mower and
automatically assigning it to the mower."

**One intake, several ways in.** Everything lands in the inbox folder
(`inbox/` at the repo root, configurable `inbox.folder`, gitignored like
every other folder of the owner's files):
- dropping a file there (or "Add Files" in the Inbox screen);
- the phone: the web app's "Send a file" posts to /api/inbox/upload;
- email, optionally: core/inbox_mail.py checks a mailbox the owner
  chooses and saves each new message into the folder as a .eml file.
So MIA works fully offline; email is just one more way to drop a file.

**Propose, then the owner confirms.** Each new document becomes an
InboxItem with MIA's reading of it (core/inbox_classify.py: what kind,
whose, the receipt's total/date/store, the manual's maintenance
schedule) and a status of "pending". Nothing is filed until the owner
says so, in the Inbox screen or by voice. Filing:
- a manual or warranty goes onto the item's page (Maintenance
  documents), and the maintenance steps the owner ticks become tasks;
- a receipt or invoice becomes a Budget expense (tagged to the tool
  or build it's for, Finance #2) and the receipt goes on the item's page.

**Emailed receipts file themselves** (Zac, 2026-11-07: "automated, but
a clear way to undo"): `auto_file()` files a receipt that came by email
(not one already logged, and only while `inbox.auto_file` is on), with
its ticked effects (core/receipt_effects.py). Every filing keeps exactly
what it did (the expense's id, each effect's undo record), so `unfile()`
takes back just that, days later too, and leaves everything changed since
alone; the Inbox lists what MIA filed with an Undo, and "undo the Kroger
receipt" works by voice.

New documents are announced through the communication gate, merged
with anything else MIA has to say (core/communication_gate.py), what
she filed on her own first, with how to undo it.
"""

from __future__ import annotations

from core import life_events

import json
import re
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.document_text import EMAIL_SUFFIXES, extract
from core.ocr import IMAGE_SUFFIXES, read_result, unavailable_note
from core.inbox_classify import (
    DOC_TYPE_LABELS, INVOICE, MANUAL, RECEIPT, WARRANTY, DetailProposal, ScheduleItem, detail_proposals, document_details,
    document_type, expense_category, maintenance_schedule, match_asset, match_project, receipt_fields, receipt_items,
)
from core.logger import get_logger
from core.region import money

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FOLDER = _PROJECT_ROOT / "inbox"
_DATA_DIR = _PROJECT_ROOT / "data"
_ITEMS_FILE = _DATA_DIR / "inbox.json"
_MIN_QUIET_SECONDS = 3.0  # a file still being copied in is left for the next scan
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
# A file MIA saved itself (receive_file(), the phone's Share): written whole
# under a hidden name and renamed, so it's ready the moment it appears.
_SENT = re.compile(r"^\d{8}-\d{6}(?:-[0-9a-f]{4})?\.(phone|email|folder|note)\.(.+)$")

PENDING, FILED, DISMISSED = "pending", "filed", "dismissed"
_DETAIL_WORDS = {"model": "model", "serial_number": "serial number", "manufacturer": "maker",
                 "purchase": "purchase price", "warranty_until": "warranty date"}


@dataclass
class InboxItem:
    """One document that came into the inbox (from the folder, the phone or email): its files, the email's subject,
    sender and date, and MIA's reading of it, all only proposed until the person files it: what kind of document,
    whether it could be read, the item or project it's for, a receipt's amount, date, vendor, category and lines, a
    manual's maintenance schedule, details about the thing it's for, whether OCR is still reading it, for a receipt
    what it says happened (groceries, a car service, building supplies) with the effects offered, and once filed what
    the filing did (the expense, each effect's undo record) and whether MIA filed it on her own.
    """
    item_id: str
    received_at: str
    source: str  # "folder" | "phone" | "email"
    files: list[str] = field(default_factory=list)  # names inside the item's own folder
    subject: str = ""
    sender: str = ""
    doc_type: str = "other"
    readable: bool = True
    note: str = ""  # e.g. why nothing could be read
    excerpt: str = ""
    asset_id: str = ""
    project_id: str = ""
    amount: Optional[float] = None
    amount_basis: str = ""
    doc_date: str = ""
    vendor: str = ""
    category: str = ""
    schedule: list[dict] = field(default_factory=list)  # ScheduleItem dicts
    status: str = PENDING
    filed_note: str = ""
    email_date: str = ""  # an emailed document's sent date, the fallback receipt date
    reading: bool = False  # waiting on OCR (core/ocr.py) for a photo or scan
    # What it says about the item it's for (model, serial, maker, warranty,
    # a purchase), core/inbox_classify.document_details(); offered as
    # updates to the item's page when filing.
    details: dict = field(default_factory=dict)
    # A receipt's lines (core/inbox_classify.receipt_items) and how far
    # to trust them; saved on the expense when filed.
    items: list[dict] = field(default_factory=list)
    # What the receipt says happened (core/receipt_effects.py): groceries, a car service or building supplies, and
    # the effects offered (stock the pantry, mark the oil change done, add materials), done only when filed.
    receipt_kind: str = ""
    effects: list[dict] = field(default_factory=list)
    # Filing, kept so it can be undone exactly (Zac, 2026-11-07): the expense it logged, each effect's undo record,
    # and whether MIA filed it on her own (an emailed receipt) rather than the person.
    expense_id: str = ""
    undo: list[dict] = field(default_factory=list)
    auto: bool = False
    items_note: str = ""

    @staticmethod
    def from_dict(data: dict) -> "InboxItem":
        """An item from its saved dict, keeping only the fields an item knows."""
        fields = InboxItem.__dataclass_fields__
        return InboxItem(**{k: v for k, v in data.items() if k in fields})

    @property
    def label(self) -> str:
        """A short name for lists and speech: 'Lowe's receipt, $38.89'."""
        kind = DOC_TYPE_LABELS.get(self.doc_type, "Document")
        who = self.vendor or self.subject or (self.files[0] if self.files else "document")
        text = f"{who} {kind.lower()}" if self.doc_type != "other" else who
        if self.amount is not None and self.doc_type in (RECEIPT, INVOICE):
            text += f", {money(self.amount, ',.2f')}"
        return text


class InboxManager:
    """The document inbox: the household's inbox.json (written through atomic_write_text) and the inbox folder each
    document is moved into (inbox/items/<id>/). Every document is read and classified, but nothing is filed until the
    person says so.
    """
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        """Points at the household's file (data/ by default) and loads it."""
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._items_file = self.data_dir / "inbox.json" if data_dir is not None else _ITEMS_FILE
        self.context = context
        self._items: list[InboxItem] = []
        self._load()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    @property
    def folder(self) -> Path:
        """The inbox folder: inbox.folder when configured, else inbox/ at the repo root."""
        configured = self.context.config.get("inbox.folder", "") if self.context.config else ""
        return Path(configured) if configured else _DEFAULT_FOLDER

    def item_folder(self, item_id: str) -> Path:
        """Where one item's files are kept."""
        return self.folder / "items" / item_id

    def _load(self) -> None:
        """Reads the items; an unreadable file is logged, reported and starts empty."""
        if not self._items_file.exists():
            return
        try:
            self._items = [InboxItem.from_dict(d) for d in json.loads(self._items_file.read_text(encoding="utf-8"))]
        except (json.JSONDecodeError, OSError, TypeError):
            log.exception("inbox.json unreadable — starting empty.")
            notify_data_corruption(self.context, "inbox.json")
            self._items = []

    def _save(self) -> None:
        """Writes every item atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._items_file, json.dumps([asdict(i) for i in self._items], indent=2))

    def all_items(self) -> list[InboxItem]:
        """Pending first, then newest first."""
        newest_first = sorted(self._items, key=lambda i: i.received_at, reverse=True)
        return sorted(newest_first, key=lambda i: i.status != PENDING)

    def pending(self) -> list[InboxItem]:
        """The items waiting to be filed, oldest first."""
        return sorted((i for i in self._items if i.status == PENDING), key=lambda i: i.received_at)

    def get_item(self, item_id: str) -> Optional[InboxItem]:
        """The item with this id, or None."""
        return next((i for i in self._items if i.item_id == item_id), None)

    # ------------------------------------------------------------------
    # Intake
    # ------------------------------------------------------------------

    def receive_file(self, filename: str, data: bytes, source: str = "phone") -> Path:
        """Save an incoming file into the inbox folder for the next scan.
        Safe to call from the phone server's thread: it only writes a file.
        The source rides along in the name (".phone."), read back by scan()."""
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError("That file is over 25 MB.")
        name = Path(filename or "upload").name.strip() or "upload"
        name = re.sub(r"[^\w.\- ]", "_", name)
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.folder / f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}.{source}.{name}"
        # Written under a hidden name (scan() skips those) and renamed, so
        # a scan can never take in a half-written file.
        partial = self.folder / f".{path.name}.part"
        partial.write_bytes(data)
        partial.replace(path)
        return path

    def scan(self, now: Optional[float] = None) -> list[InboxItem]:
        """Turn every settled file in the inbox folder into a pending item,
        and pick up finished OCR; an emailed receipt then files itself
        (`auto_file`). Returns the items that are ready to announce: new
        ones MIA could read right away, and photos/scans whose reading
        just finished (not ones still being read)."""
        ready: list[InboxItem] = []
        changed = False
        for item in [i for i in self._items if i.reading and i.status == PENDING]:
            self._read(item)
            changed = True
            if not item.reading:
                ready.append(item)
        if self.folder.exists():
            now = now or time.time()
            for path in sorted(self.folder.iterdir()):
                if not path.is_file() or path.name.startswith("."):
                    continue
                if now - path.stat().st_mtime < _MIN_QUIET_SECONDS and not _SENT.match(path.name):
                    continue
                try:
                    item = self._ingest(path)
                except OSError:
                    log.exception("Couldn't take %s into the inbox.", path)
                    continue
                changed = True
                if not item.reading:
                    ready.append(item)
        for item in ready:  # an emailed receipt files itself (and can be undone)
            self.auto_file(item)
        if changed:
            self._save()
        return ready

    def _ingest(self, path: Path) -> InboxItem:
        """Takes in one new file: moves it into a new item's folder (its name says if it came from the phone or email),
        unpacks an email's attachments beside it (names made safe), then reads and classifies it.
        """
        source, name = "folder", path.name
        m = _SENT.match(path.name)
        if m:
            source, name = m.group(1), m.group(2)
        item = InboxItem(item_id=uuid.uuid4().hex[:10], received_at=datetime.now().isoformat(timespec="seconds"), source=source)
        target = self.item_folder(item.item_id)
        target.mkdir(parents=True, exist_ok=True)
        stored = target / name
        shutil.move(str(path), stored)
        item.files.append(stored.name)
        if stored.suffix.lower() in EMAIL_SUFFIXES:
            message = extract(stored)
            item.subject, item.sender, item.email_date = message.title, message.sender, message.date
            for attachment in message.attachments:
                attachment_path = target / re.sub(r"[^\w.\- ]", "_", attachment.filename)
                attachment_path.write_bytes(attachment.data)
                item.files.append(attachment_path.name)
        self._items.append(item)
        self._read(item)
        log.info("Inbox: %s from %s (%s%s)", item.label, source, item.doc_type, ", reading" if item.reading else "")
        return item

    def _ocr_output(self, item: InboxItem, name: str) -> Path:
        """Where OCR writes the text of one of an item's files."""
        return self.item_folder(item.item_id) / ".ocr" / f"{name}.json"

    def _read(self, item: InboxItem) -> None:
        """Read every file of the item (an email's body and each
        attachment), with OCR for photos and scans, then classify it.
        Photos/scans not read yet are queued and the item is marked
        `reading`; called again by scan() until they're done."""
        folder = self.item_folder(item.item_id)
        ocr = getattr(self.context, "ocr", None)
        texts: list[str] = []
        notes: list[str] = []
        waiting = False
        for name in item.files:
            path = folder / name
            document = extract(path)
            if not item.subject and document.title:
                item.subject = document.title
            if document.readable:
                texts += document.pages
                continue
            prefix = f"{name}: " if len(item.files) > 1 else ""
            if not document.needs_ocr:
                notes.append(prefix + document.note)
                continue
            result = read_result(self._ocr_output(item, name))
            if result is not None:
                if result.error:
                    notes.append(prefix + result.error)
                elif result.text.strip():
                    texts.append(result.text)
                else:
                    notes.append(prefix + "No text could be found in it.")
            elif ocr is not None and ocr.submit(f"inbox:{item.item_id}/{name}", path, self._ocr_output(item, name)):
                waiting = True
            else:
                notes.append(prefix + unavailable_note("photo" if path.suffix.lower() in IMAGE_SUFFIXES else "scan"))
        item.reading = waiting
        item.readable = any(t.strip() for t in texts)
        item.note = "Reading the text in it (OCR)…" if waiting else " ".join(notes)
        main_name = next((f for f in item.files if not f.lower().endswith(".eml")), item.files[0] if item.files else "")
        self._classify(item, "\n".join(texts), main_name, item.email_date)

    def _classify(self, item: InboxItem, text: str, filename: str, email_date: str) -> None:
        # Start clean: an item is classified again once its OCR finishes.
        """MIA's reading of a document's text (starting clean, so it can run again once OCR finishes): its kind, the
        asset or project it's about, for a receipt or invoice the amount, date (the email's when none), vendor, category
        and lines and what it says happened (core/receipt_effects.py), details about the thing it's for, and for a
        manual or warranty its maintenance schedule.
        """
        item.amount, item.amount_basis, item.doc_date, item.vendor, item.category = None, "", "", "", ""
        item.schedule, item.details, item.items, item.items_note = [], {}, [], ""
        item.receipt_kind, item.effects = "", []
        item.excerpt = " ".join(text.split())[:400]
        haystack = f"{item.subject}\n{filename}\n{text}"
        item.doc_type = document_type(text, filename, item.subject)
        maintenance = getattr(self.context, "maintenance", None)
        projects = getattr(self.context, "projects", None)
        asset = match_asset(haystack, maintenance.all_assets()) if maintenance else None
        project = match_project(haystack, projects.all_projects()) if projects else None
        item.asset_id = asset.asset_id if asset else ""
        item.project_id = project.project_id if project else ""
        fields = None
        if item.doc_type in (RECEIPT, INVOICE):
            fields = receipt_fields(text, item.sender)
            item.amount, item.amount_basis = fields.amount, fields.amount_basis
            item.doc_date = fields.date or email_date or ""
            item.vendor = fields.vendor
            item.category = expense_category(item.vendor, asset, project, text)
            fields.date = item.doc_date
            lines, item.items_note = receipt_items(text)
            item.items = [asdict(line) for line in lines]
            from core.receipt_effects import propose

            item.receipt_kind, item.effects = propose(self.context, item, haystack)
        item.details = document_details(text, item.doc_type, fields)
        if item.doc_type in (MANUAL, WARRANTY) or (item.doc_type == "other" and asset is not None):
            item.schedule = [asdict(s) for s in maintenance_schedule(text)]

    # ------------------------------------------------------------------
    # Filing
    # ------------------------------------------------------------------

    def detail_proposals(self, item: InboxItem, asset_id: Optional[str] = None) -> list[DetailProposal]:
        """What filing would update on the item's page (for `asset_id`, or
        the item it was matched to)."""
        maintenance = getattr(self.context, "maintenance", None)
        asset_id = item.asset_id if asset_id is None else asset_id
        asset = maintenance.get_asset(asset_id) if maintenance and asset_id else None
        return detail_proposals(item.details, asset)

    @life_events.on_change("document_filed", "a document", "inbox_item")
    def file_item(
        self, item_id: str, asset_id: Optional[str] = None, project_id: Optional[str] = None,
        amount: Optional[float] = None, category: Optional[str] = None, schedule_indexes: Optional[list[int]] = None,
        detail_fields: Optional[list[str]] = None, effect_indexes: Optional[list[int]] = None,
    ) -> str:
        """File a pending item with MIA's proposal, or the owner's
        corrections. `detail_fields`: which detail updates to apply
        ("model", "serial_number", "manufacturer", "purchase",
        "warranty_until"); None applies the ones ticked by default (the
        item's empty fields). `effect_indexes`: which of a receipt's
        effects to do (core/receipt_effects.py: stock the pantry, mark a
        service done, add materials); None does the ticked ones. What it
        did is kept on the item (the expense's id, each effect's undo
        record) so `unfile()` can take it back exactly. Returns what was
        done, in one sentence."""
        item = self.get_item(item_id)
        if item is None or item.status != PENDING:
            raise ValueError("That item isn't waiting in the inbox.")
        corrected = reading_corrections(item, amount, category, asset_id)
        asset_id = item.asset_id if asset_id is None else asset_id
        project_id = item.project_id if project_id is None else project_id
        amount = item.amount if amount is None else amount
        maintenance = getattr(self.context, "maintenance", None)
        asset = maintenance.get_asset(asset_id) if maintenance and asset_id else None
        proposals = detail_proposals(item.details, asset)
        chosen_details = [p for p in proposals if (p.default_on if detail_fields is None else p.field in detail_fields)]
        is_purchase = any(p.field == "purchase" for p in chosen_details)
        done: list[str] = []

        if item.doc_type in (RECEIPT, INVOICE):
            if not amount or amount <= 0:
                raise ValueError("I need the amount before I can file this receipt.")
            budget = self.context.budget
            expense = budget.add_expense(
                amount=amount,
                category=category or ("Tools & Equipment" if is_purchase else item.category) or "Shopping",
                description=(f"Bought {asset.name}" if is_purchase and asset else
                             f"{item.vendor or 'Receipt'}" + (f" ({asset.name})" if asset else "")),
                date=item.doc_date or date.today().isoformat(), payee=item.vendor,
                asset_id=asset_id or "", project_id=project_id or "", notes=f"From the inbox: {', '.join(item.files)}",
                # The purchase itself counts once in the tool's cost (core/homestead_costs.py).
                asset_purchase=is_purchase,
                items=item.items,
            )
            done.append(f"logged {money(amount, ',.2f')}" + (f" for the {asset.name}" if asset else ""))
            if project_id and getattr(self.context, "projects", None):
                project = self.context.projects.get_project(project_id)
                if project:
                    done[-1] += f" on {project.name}"
            item.expense_id = getattr(expense, "entry_id", "") or ""
            if item.effects:
                from core.receipt_effects import apply

                said, item.undo = apply(self.context, item.effects, effect_indexes)
                done += said

        if asset is not None:
            attached = 0
            for name in self._documents_to_attach(item):
                maintenance.add_document(asset.asset_id, self.item_folder(item.item_id) / name)
                attached += 1
            if attached:
                done.append(f"put {'it' if attached == 1 else f'{attached} files'} on the {asset.name}'s page")
            chosen = [item.schedule[i] for i in (schedule_indexes or []) if 0 <= i < len(item.schedule)]
            for raw in chosen:
                step = ScheduleItem(**raw)
                if step.interval_hours:
                    maintenance.add_task(asset.asset_id, step.task, trigger_type="runtime", meter_unit="engine hours",
                                         meter_interval=step.interval_hours, notes=f"From the manual: {step.source}")
                elif step.interval_miles:
                    maintenance.add_task(asset.asset_id, step.task, trigger_type="mileage", meter_unit="miles",
                                         meter_interval=step.interval_miles, notes=f"From the manual: {step.source}")
                else:
                    maintenance.add_task(asset.asset_id, step.task, interval_days=step.interval_days,
                                         notes=f"From the manual: {step.source}")
            if chosen:
                done.append(f"added {len(chosen)} maintenance task{'s' if len(chosen) != 1 else ''}")
            if chosen_details:
                updates: dict = {}
                for proposal in chosen_details:
                    if proposal.field == "purchase":
                        price, when = proposal.value
                        updates["purchase_price"] = float(amount if amount else price)
                        if when and not asset.purchase_date:
                            updates["purchase_date"] = when
                    else:
                        updates[proposal.field] = proposal.value
                maintenance.update_asset(asset.asset_id, **updates)
                names = [_DETAIL_WORDS[p.field] for p in chosen_details]
                done.append("filled in its " + (names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]))
        if not done:
            done.append("kept it in the inbox's filed documents")

        item.status = FILED
        item.asset_id, item.project_id = asset_id or "", project_id or ""
        item.filed_note = "Filed: " + ", ".join(done) + "."
        self._save()
        self._note_reading(item, corrected)
        return item.filed_note

    def _note_reading(self, item, corrected: list[str]) -> None:
        """For the inbox.reading loop (build plan step 4): each filed item, which of the fields MIA read the person
        corrected (field names only, never values)."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.data_dir / "inbox_reading.jsonl", "a", encoding="utf-8") as out:
                out.write(json.dumps({"at": datetime.now().isoformat(timespec="seconds"), "doc_type": item.doc_type,
                                      "corrected": corrected}) + "\n")
        except OSError:
            log.exception("Inbox: couldn't note the reading")

    def readings(self, days: int = 60) -> list[dict]:
        """The record of how filed documents were read and what the person corrected, for the last `days` days (what the
        inbox-reading loop learns from).
        """
        since = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        try:
            lines = (self.data_dir / "inbox_reading.jsonl").read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        out = []
        for line in lines:
            try:
                found = json.loads(line)
            except ValueError:
                continue
            if found.get("at", "") >= since:
                out.append(found)
        return out

    def _documents_to_attach(self, item: InboxItem) -> list[str]:
        """The real documents: an email's attachments rather than the
        email itself, unless the email is all there is."""
        attachments = [f for f in item.files if not f.lower().endswith(".eml")]
        return attachments or item.files

    # ------------------------------------------------------------------
    # Filing on her own, and undoing a filing (Zac, 2026-11-07: "automated, but a clear way to undo")
    # ------------------------------------------------------------------

    def auto_file(self, item: InboxItem) -> bool:
        """Files an emailed receipt on MIA's own, when it's safe to: inbox.auto_file is on (the default), it's a
        receipt (not an invoice: a bill still to pay) with a total, and it isn't logged already (`_logged_already`: a
        forwarded copy, or an order email and its receipt). Its ticked effects are done. Returns whether it
        filed; one it can't is left waiting, with why."""
        config = getattr(self.context, "config", None)
        if config is not None and config.get("inbox.auto_file", True) is False:
            return False
        if item.status != PENDING or item.source != "email" or item.doc_type != RECEIPT or not item.amount:
            return False
        if self._logged_already(item):
            item.note = "Not filed on its own: an expense like it is already logged (an order and its receipt?)."
            return False
        try:
            self.file_item(item.item_id)
        except ValueError as problem:
            item.note = f"Not filed on its own: {problem}"
            return False
        item.auto = True
        item.filed_note = item.filed_note.replace("Filed:", "Filed by MIA:", 1)
        self._save()
        try:
            from core import corrections

            corrections.mia_changed(self.context, "inbox.auto_file", {"item_id": item.item_id})
        except Exception:
            log.exception("Inbox: noting an automatic filing failed")
        return True

    def _logged_already(self, item: InboxItem) -> bool:
        """Whether the same amount is already logged: within a day from any store (a forwarded copy reads its store
        from the forwarder), or within 3 days from the same store (an order email and its receipt)."""
        budget = getattr(self.context, "budget", None)
        if budget is None:
            return False
        try:
            when = date.fromisoformat(item.doc_date or item.email_date or date.today().isoformat())
        except ValueError:
            when = date.today()
        store = (item.vendor or "").lower().strip()
        for expense in budget.all_expenses(include_uncounted=True):
            if abs(float(expense.amount) - float(item.amount)) > 0.005:
                continue
            try:
                days = abs((date.fromisoformat(expense.date) - when).days)
            except ValueError:
                continue
            payee = (expense.payee or expense.description or "").lower()
            if days <= 1 or (days <= 3 and (not store or store in payee or payee in store)):
                return True  # the same cents the same day is the same purchase whatever the store reads as (a forward)
        return False

    def unfile(self, item_id: str) -> str:
        """Undoes a filing exactly: the expense it logged is deleted and each of its effects put back (pantry
        quantities, a service's done date, materials...), leaving everything changed since alone; the item waits again,
        to be filed right or dismissed. ValueError when it isn't filed. Returns what was undone."""
        from core.receipt_effects import reverse

        item = self.get_item(item_id)
        if item is None or item.status != FILED:
            raise ValueError("That isn't filed, so there's nothing to undo.")
        undone = []
        budget = getattr(self.context, "budget", None)
        if item.expense_id and budget is not None and budget.get_expense(item.expense_id) is not None:
            budget.delete_expense(item.expense_id)
            undone.append("took the expense out of Money")
        put_back = reverse(self.context, item.undo)
        if put_back:
            undone.append(f"put back {put_back} change{'s' if put_back != 1 else ''} it made")
        was_auto = item.auto
        item.status, item.auto, item.undo, item.expense_id = PENDING, False, [], ""
        item.filed_note = ""
        item.note = "Undone: " + (", ".join(undone) or "nothing it changed was left") + ". File it again or dismiss it."
        self._save()
        if was_auto:
            try:
                from core import corrections

                corrections.undone(self.context, "inbox.auto_file")
            except Exception:
                log.exception("Inbox: noting an undone filing failed")
        return f"Undid {item.label}: " + (", ".join(undone) or "nothing it changed was left") + "."

    def auto_filed(self, days: int = 30) -> list[InboxItem]:
        """What MIA filed on her own in the last `days`, newest first (for Undo on the Inbox screen and by voice)."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        return sorted((i for i in self._items if i.auto and i.status == FILED and i.received_at >= cutoff),
                      key=lambda i: i.received_at, reverse=True)

    def dismiss(self, item_id: str) -> None:
        """Dismisses an item without filing it (ValueError when it's gone)."""
        item = self.get_item(item_id)
        if item is None:
            raise ValueError("No such inbox item.")
        item.status = DISMISSED
        item.filed_note = "Dismissed."
        self._save()

    def find_pending(self, words: str) -> Optional[InboxItem]:
        """A pending item from the owner's words ('the Lowe's receipt',
        'the mower manual'); the only/oldest pending one when no words."""
        pending = self.pending()
        if not pending:
            return None
        wanted = {w for w in re.findall(r"[a-z0-9']+", words.lower()) if len(w) > 2 and w not in ("the", "that", "this", "one", "file")}
        if not wanted:
            return pending[0]
        best, best_score = None, 0
        maintenance = getattr(self.context, "maintenance", None)
        for item in pending:
            asset = maintenance.get_asset(item.asset_id) if maintenance and item.asset_id else None
            haystack = " ".join([item.label, item.subject, item.doc_type, " ".join(item.files), asset.name if asset else ""]).lower()
            score = sum(1 for w in wanted if w.rstrip("s") in haystack)
            if score > best_score:
                best, best_score = item, score
        return best


def reading_corrections(item: InboxItem, amount, category, asset_id) -> list[str]:
    """Pure logic. Which of the fields MIA read from a document the person changed when filing it (build plan
    step 4's inbox.reading): "amount", "amount missed" (she read none), "category", "equipment". Names only."""
    out = []
    if amount is not None:
        if not item.amount:
            out.append("amount missed")
        elif abs(float(amount) - float(item.amount)) > 0.005:
            out.append("amount")
    if category and item.category and category != item.category:
        out.append("category")
    if asset_id is not None and item.asset_id and asset_id != item.asset_id:
        out.append("equipment")
    return out


def describe_detail_updates(proposals: list[DetailProposal]) -> str:
    """Pure logic. 'serial number and warranty date' for the updates ticked by default."""
    names = [_DETAIL_WORDS[p.field] for p in proposals if p.default_on]
    if not names:
        return ""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def describe_new_items(items: list[InboxItem], context) -> str:
    """Pure-ish: the announcement for newly arrived documents: what MIA filed from email on her own (with how to undo
    it), then what waits to be filed."""
    maintenance = getattr(context, "maintenance", None)
    filed = [i for i in items if i.auto]
    items = [i for i in items if not i.auto]
    said = ""
    if filed:
        said = ("Filed from your email: " + "; ".join(f"{i.label} ({i.filed_note.replace('Filed by MIA: ', '').rstrip('.')})"
                                                     for i in filed[:3])
                + (f" and {len(filed) - 3} more" if len(filed) > 3 else "")
                + ". If I got one wrong, Undo it in the Inbox or tell me \"undo the receipt\".")
    if not items:
        return said
    parts = []
    for item in items[:4]:
        text = item.label
        asset = maintenance.get_asset(item.asset_id) if maintenance and item.asset_id else None
        if asset is not None:
            text += f" (looks like it's for the {asset.name}"
            news = describe_detail_updates(detail_proposals(item.details, asset))
            text += f"; it has its {news})" if news else ")"
        parts.append(text)
    more = f" and {len(items) - 4} more" if len(items) > 4 else ""
    return ((said + " ") if said else "") + "New in your inbox: " + "; ".join(parts) + more + \
        ". Open Inbox to file them, or tell me \"file it\"."
