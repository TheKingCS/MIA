"""
core.web_inbox
================

The Inbox on the web and the phone (Zac, 2026-10-16: "Can you build the
inbox for sending stuff to MIA?"). The document inbox itself is
core/inbox_manager.py: a file sent in (from the phone's Share menu, the
Upload button, a dropped file, or email) becomes an item with MIA's
reading of it (a receipt's store, total and date; a manual's maintenance
schedule; what it says about the tool it's for) and waits until the
person files or dismisses it. `inbox_page` is that list; reading the
page first takes in anything new (`scan()`), so it works on the phone,
where nothing else checks the folder. Changes are actions in
core/inbox_actions.py; files come in through /api/inbox/upload.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

SOURCES = {"phone": "From your phone", "email": "By email", "folder": "Dropped in", "note": "A note"}


def _kind(name: str) -> str:
    from core.my_files import kind_of

    return "email" if name.lower().endswith(".eml") else kind_of(name)


def item_card(context, item) -> dict:
    """One inbox item as the screen shows it."""
    from core.inbox_classify import DOC_TYPE_LABELS, ScheduleItem
    from core.region import money

    maintenance = getattr(context, "maintenance", None)
    projects = getattr(context, "projects", None)
    asset = maintenance.get_asset(item.asset_id) if maintenance is not None and item.asset_id else None
    project = projects.get_project(item.project_id) if projects is not None and item.project_id else None
    schedule = []
    for i, raw in enumerate(item.schedule):
        try:
            schedule.append({"index": i, "text": ScheduleItem(**raw).describe(), "source": raw.get("source", "")})
        except TypeError:
            continue
    details = []
    if item.status == "pending":
        try:
            for p in context.inbox.detail_proposals(item):
                details.append({"field": p.field, "text": p.text, "current": p.current, "on": p.default_on})
        except Exception:
            log.exception("Inbox: detail proposals failed for %s", item.item_id)
    note = item.source == "note" and item.doc_type == "other" and item.files
    return {
        "id": item.item_id, "label": Path(item.files[0]).stem if note else item.label, "type": item.doc_type,
        "type_label": "Note" if note else DOC_TYPE_LABELS.get(item.doc_type, "Document"),
        "status": item.status, "source": SOURCES.get(item.source, item.source), "received": item.received_at[:16].replace("T", " "),
        "subject": item.subject, "sender": item.sender, "vendor": item.vendor,
        "amount": money(item.amount) if item.amount is not None else "", "amount_value": item.amount,
        "date": item.doc_date, "category": item.category,
        "asset": {"id": asset.asset_id, "name": asset.name} if asset is not None else None,
        "project": {"id": project.project_id, "name": project.name} if project is not None else None,
        "files": [{"name": f, "kind": _kind(f)} for f in item.files],
        "excerpt": item.excerpt, "note": item.note, "reading": item.reading, "readable": item.readable,
        "schedule": schedule, "details": details,
        "lines": [{"text": str(line.get("description") or line.get("name") or ""), "amount": money(line["amount"]) if line.get("amount") is not None else ""}
                  for line in (item.items or []) if isinstance(line, dict)][:30],
        "filed_note": item.filed_note,
        "needs_amount": item.doc_type in ("receipt", "invoice") and not item.amount,
    }


def inbox_page(context) -> dict:
    inbox = getattr(context, "inbox", None)
    if inbox is None:
        return {"available": False}
    try:
        inbox.scan()  # take in anything sent since the last look
    except Exception:
        log.exception("Inbox: scan failed")
    items = inbox.all_items()
    pending = [item_card(context, i) for i in items if i.status == "pending"]
    done = [item_card(context, i) for i in items if i.status != "pending"][:25]
    maintenance = getattr(context, "maintenance", None)
    projects = getattr(context, "projects", None)
    from core.budget_manager import EXPENSE_CATEGORIES

    return {
        "available": True,
        "pending": pending, "done": done,
        "counts": {"waiting": len(pending), "reading": sum(1 for p in pending if p["reading"]),
                   "filed": sum(1 for i in items if i.status == "filed")},
        "picks": {
            "assets": sorted(({"id": a.asset_id, "name": a.name} for a in maintenance.all_assets()), key=lambda a: a["name"].lower())
            if maintenance is not None else [],
            "projects": sorted(({"id": p.project_id, "name": p.name} for p in projects.all_projects()), key=lambda p: p["name"].lower())
            if projects is not None else [],
            "categories": list(EXPENSE_CATEGORIES),
        },
        "max_mb": 25,
    }


def item_file(context, item_id: str, name: str) -> Optional[Path]:
    """One of an inbox item's own files (never a path a request names)."""
    inbox = getattr(context, "inbox", None)
    item = inbox.get_item(item_id) if inbox is not None else None
    if item is None or name not in item.files:
        return None
    path = inbox.item_folder(item.item_id) / name
    return path if path.is_file() else None
