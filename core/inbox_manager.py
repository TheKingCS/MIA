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

New documents are announced through the communication gate, merged
with anything else MIA has to say (core/communication_gate.py).
"""

from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.document_text import EMAIL_SUFFIXES, extract
from core.ocr import IMAGE_SUFFIXES, read_result, unavailable_note
from core.inbox_classify import (
    DOC_TYPE_LABELS, INVOICE, MANUAL, RECEIPT, WARRANTY, DetailProposal, ScheduleItem, detail_proposals, document_details,
    document_type, expense_category, maintenance_schedule, match_asset, match_project, receipt_fields,
)
from core.logger import get_logger

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FOLDER = _PROJECT_ROOT / "inbox"
_DATA_DIR = _PROJECT_ROOT / "data"
_ITEMS_FILE = _DATA_DIR / "inbox.json"
_MIN_QUIET_SECONDS = 3.0  # a file still being copied in is left for the next scan
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

PENDING, FILED, DISMISSED = "pending", "filed", "dismissed"
_DETAIL_WORDS = {"model": "model", "serial_number": "serial number", "manufacturer": "maker",
                 "purchase": "purchase price", "warranty_until": "warranty date"}


@dataclass
class InboxItem:
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

    @staticmethod
    def from_dict(data: dict) -> "InboxItem":
        fields = InboxItem.__dataclass_fields__
        return InboxItem(**{k: v for k, v in data.items() if k in fields})

    @property
    def label(self) -> str:
        """A short name for lists and speech: 'Lowe's receipt, $38.89'."""
        kind = DOC_TYPE_LABELS.get(self.doc_type, "Document")
        who = self.vendor or self.subject or (self.files[0] if self.files else "document")
        text = f"{who} {kind.lower()}" if self.doc_type != "other" else who
        if self.amount is not None and self.doc_type in (RECEIPT, INVOICE):
            text += f", ${self.amount:,.2f}"
        return text


class InboxManager:
    def __init__(self, context) -> None:
        self.context = context
        self._items: list[InboxItem] = []
        self._load()

    # ------------------------------------------------------------------
    # Storage
    # ------------------------------------------------------------------

    @property
    def folder(self) -> Path:
        configured = self.context.config.get("inbox.folder", "") if self.context.config else ""
        return Path(configured) if configured else _DEFAULT_FOLDER

    def item_folder(self, item_id: str) -> Path:
        return self.folder / "items" / item_id

    def _load(self) -> None:
        if not _ITEMS_FILE.exists():
            return
        try:
            self._items = [InboxItem.from_dict(d) for d in json.loads(_ITEMS_FILE.read_text(encoding="utf-8"))]
        except (json.JSONDecodeError, OSError, TypeError):
            log.exception("inbox.json unreadable — starting empty.")
            notify_data_corruption(self.context, "inbox.json")
            self._items = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_ITEMS_FILE, json.dumps([asdict(i) for i in self._items], indent=2))

    def all_items(self) -> list[InboxItem]:
        """Pending first, then newest first."""
        newest_first = sorted(self._items, key=lambda i: i.received_at, reverse=True)
        return sorted(newest_first, key=lambda i: i.status != PENDING)

    def pending(self) -> list[InboxItem]:
        return sorted((i for i in self._items if i.status == PENDING), key=lambda i: i.received_at)

    def get_item(self, item_id: str) -> Optional[InboxItem]:
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
        and pick up finished OCR. Returns the items that are ready to
        announce: new ones MIA could read right away, and photos/scans
        whose reading just finished (not ones still being read)."""
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
                if now - path.stat().st_mtime < _MIN_QUIET_SECONDS:
                    continue
                try:
                    item = self._ingest(path)
                except OSError:
                    log.exception("Couldn't take %s into the inbox.", path)
                    continue
                changed = True
                if not item.reading:
                    ready.append(item)
        if changed:
            self._save()
        return ready

    def _ingest(self, path: Path) -> InboxItem:
        source, name = "folder", path.name
        m = re.match(r"^\d{8}-\d{6}(?:-[0-9a-f]{4})?\.(phone|email|folder)\.(.+)$", path.name)
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
        item.amount, item.amount_basis, item.doc_date, item.vendor, item.category = None, "", "", "", ""
        item.schedule, item.details = [], {}
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

    def file_item(
        self, item_id: str, asset_id: Optional[str] = None, project_id: Optional[str] = None,
        amount: Optional[float] = None, category: Optional[str] = None, schedule_indexes: Optional[list[int]] = None,
        detail_fields: Optional[list[str]] = None,
    ) -> str:
        """File a pending item with MIA's proposal, or the owner's
        corrections. `detail_fields`: which detail updates to apply
        ("model", "serial_number", "manufacturer", "purchase",
        "warranty_until"); None applies the ones ticked by default (the
        item's empty fields). Returns what was done, in one sentence."""
        item = self.get_item(item_id)
        if item is None or item.status != PENDING:
            raise ValueError("That item isn't waiting in the inbox.")
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
            budget.add_expense(
                amount=amount,
                category=category or ("Tools & Equipment" if is_purchase else item.category) or "Shopping",
                description=(f"Bought {asset.name}" if is_purchase and asset else
                             f"{item.vendor or 'Receipt'}" + (f" ({asset.name})" if asset else "")),
                date=item.doc_date or date.today().isoformat(), payee=item.vendor,
                asset_id=asset_id or "", project_id=project_id or "", notes=f"From the inbox: {', '.join(item.files)}",
                # The purchase itself counts once in the tool's cost (core/homestead_costs.py).
                asset_purchase=is_purchase,
            )
            done.append(f"logged ${amount:,.2f}" + (f" for the {asset.name}" if asset else ""))
            if project_id and getattr(self.context, "projects", None):
                project = self.context.projects.get_project(project_id)
                if project:
                    done[-1] += f" on {project.name}"

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
        return item.filed_note

    def _documents_to_attach(self, item: InboxItem) -> list[str]:
        """The real documents: an email's attachments rather than the
        email itself, unless the email is all there is."""
        attachments = [f for f in item.files if not f.lower().endswith(".eml")]
        return attachments or item.files

    def dismiss(self, item_id: str) -> None:
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


def describe_detail_updates(proposals: list[DetailProposal]) -> str:
    """Pure logic. 'serial number and warranty date' for the updates ticked by default."""
    names = [_DETAIL_WORDS[p.field] for p in proposals if p.default_on]
    if not names:
        return ""
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def describe_new_items(items: list[InboxItem], context) -> str:
    """Pure-ish: the announcement for newly arrived documents."""
    maintenance = getattr(context, "maintenance", None)
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
    return "New in your inbox: " + "; ".join(parts) + more + ". Open Inbox to file them, or tell me \"file it\"."
