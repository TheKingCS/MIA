"""
core.inbox_classify
======================

Pure logic behind the document inbox (core/inbox_manager.py,
2026-09-28): given a document's text, what is it, whose is it, and what
does it say that MIA can file.

Everything here is **deterministic** (keywords, regular expressions,
name matching), not the language model: a 3B model reading a receipt
will sometimes invent a total, and a wrong number filed as an expense
is worse than none. Each result is a **proposal** the owner confirms
before anything is filed, and the inbox shows what it was based on.

- `document_type()`: receipt, invoice, manual, warranty or other.
- `match_asset()` / `match_project()`: which of the owner's things it's
  about, from serial number, model, full name, maker; only a clear,
  unique best match counts.
- `receipt_fields()`: total, date, store.
- `maintenance_schedule()`: "change the oil every 50 hours" lines from a
  manual, as proposed maintenance tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional
from core.region import money

RECEIPT, INVOICE, MANUAL, WARRANTY, OTHER = "receipt", "invoice", "manual", "warranty", "other"
DOC_TYPE_LABELS = {RECEIPT: "Receipt", INVOICE: "Invoice", MANUAL: "Manual", WARRANTY: "Warranty", OTHER: "Document"}

_KEYWORDS = {
    RECEIPT: ("receipt", "subtotal", "sub total", "sales tax", "change due", "thank you for shopping", "visa", "mastercard",
              "amex", "debit", "cash tendered", "order total", "qty", "item #", "sku", "paid"),
    INVOICE: ("invoice", "amount due", "balance due", "bill to", "remit to", "net 30", "due date", "invoice number"),
    MANUAL: ("owner's manual", "owners manual", "operator's manual", "operators manual", "user manual", "user guide",
             "instruction manual", "maintenance schedule", "specifications", "safety instructions", "troubleshooting",
             "assembly instructions", "table of contents", "operating instructions"),
    WARRANTY: ("warranty", "limited warranty", "warranty registration", "coverage period", "proof of purchase"),
}

KNOWN_STORES = (
    "Lowe's", "Home Depot", "Tractor Supply", "Walmart", "Amazon", "Harbor Freight", "Menards", "Ace Hardware",
    "AutoZone", "O'Reilly", "NAPA", "Costco", "Sam's Club", "Target", "Northern Tool", "Rural King", "True Value",
)
_HARDWARE_STORES = {"Lowe's", "Home Depot", "Menards", "Ace Hardware", "True Value", "Harbor Freight", "Northern Tool"}
_AUTO_STORES = {"AutoZone", "O'Reilly", "NAPA"}

_MONEY = re.compile(r"[$£€]?\s?(\d{1,3}(?:,\d{3})*|\d+)\.(\d{2})\b")
_TOTAL_LINE = re.compile(r"\b(grand total|order total|total due|amount paid|amount due|balance due|total)\b", re.IGNORECASE)
_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _norm(text: str) -> str:
    return text.lower().replace("’", "'")


def document_type(text: str, filename: str = "", subject: str = "") -> str:
    """Pure logic. The kind with the most keyword hits; 'other' below two."""
    haystack = _norm(f"{subject}\n{filename}\n{text[:20000]}")
    scores = {kind: sum(haystack.count(word) for word in words) for kind, words in _KEYWORDS.items()}
    # A subject or file name saying what it is counts extra.
    head = _norm(f"{subject} {filename}")
    for kind in _KEYWORDS:
        if kind in head:
            scores[kind] += 3
    best = max(scores, key=scores.get)
    return best if scores[best] >= 2 else OTHER


def _contains_phrase(haystack: str, phrase: str) -> bool:
    phrase = _norm(phrase).strip()
    return bool(phrase) and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", haystack) is not None


def match_asset(text: str, assets) -> Optional[object]:
    """Pure logic. The asset the document is about, or None when there's
    no clear, unique best match."""
    haystack = _norm(text)
    scored = []
    for asset in assets:
        score = 0
        if getattr(asset, "serial_number", "") and _contains_phrase(haystack, asset.serial_number):
            score += 10
        if getattr(asset, "model", "") and len(asset.model) >= 3 and _contains_phrase(haystack, asset.model):
            score += 6
        if _contains_phrase(haystack, asset.name):
            score += 5
        if getattr(asset, "manufacturer", "") and _contains_phrase(haystack, asset.manufacturer):
            score += 2
        if score:
            scored.append((score, asset))
    if not scored:
        return None
    scored.sort(key=lambda pair: -pair[0])
    if scored[0][0] < 5 or (len(scored) > 1 and scored[1][0] == scored[0][0]):
        return None
    return scored[0][1]


def match_project(text: str, projects) -> Optional[object]:
    """Pure logic. A build named in full in the document, if exactly one."""
    haystack = _norm(text)
    hits = [p for p in projects if len(p.name) >= 4 and _contains_phrase(haystack, p.name)]
    return hits[0] if len(hits) == 1 else None


def _parse_date(text: str) -> Optional[str]:
    """Pure logic. The first real date: 2026-09-28, 9/28/2026, 9/28/26, Sep 28, 2026."""
    lowered = text.lower()
    candidates = []
    for m in re.finditer(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", lowered):
        candidates.append((m.start(), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(20\d{2}|\d{2})\b", lowered):
        year = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        candidates.append((m.start(), year, int(m.group(1)), int(m.group(2))))
    for m in re.finditer(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+(20\d{2})\b", lowered):
        candidates.append((m.start(), int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2))))
    for _, year, month, day in sorted(candidates):
        try:
            return date(year, month, day).isoformat()
        except ValueError:
            continue
    return None


def _money_value(match: re.Match) -> float:
    return float(match.group(1).replace(",", "") + "." + match.group(2))


@dataclass
class ReceiptFields:
    amount: Optional[float] = None
    date: Optional[str] = None
    vendor: str = ""
    amount_basis: str = ""  # what the amount was read from, shown to the owner


def receipt_fields(text: str, sender: str = "") -> ReceiptFields:
    """Pure logic. Total, date and store from a receipt or invoice."""
    fields = ReceiptFields()
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in reversed(lines):  # the total is near the bottom
        if _TOTAL_LINE.search(line) and "subtotal" not in line.lower() and "sub total" not in line.lower():
            amounts = list(_MONEY.finditer(line))
            if amounts:
                fields.amount = _money_value(amounts[-1])
                fields.amount_basis = f'the line "{line[:60]}"'
                break
    if fields.amount is None:
        amounts = [_money_value(m) for m in _MONEY.finditer(text)]
        if amounts:
            fields.amount = max(amounts)
            fields.amount_basis = "the largest amount on it (no total line found)"
    fields.date = _parse_date(text)
    lowered = _norm(f"{sender}\n{text[:3000]}")
    fields.vendor = next((store for store in KNOWN_STORES if _norm(store) in lowered or _norm(store).replace("'", "") in lowered), "")
    if not fields.vendor and sender:
        fields.vendor = re.sub(r"\s*<.*?>\s*", "", sender).strip().strip('"')
    if not fields.vendor and lines:
        fields.vendor = lines[0][:40]
    return fields


def expense_category(vendor: str, asset, project, text: str) -> str:
    """Pure logic. A sensible Budget category for a filed receipt."""
    lowered = _norm(text)
    if asset is not None:
        if re.search(r"\b(oil|filter|blade|belt|spark plug|repair|service|parts?|tune)\b", lowered):
            return "Maintenance"
        return "Tools & Equipment"
    if project is not None or vendor in _HARDWARE_STORES:
        return "Building Materials"
    if vendor in _AUTO_STORES:
        return "Transportation"
    return "Shopping"


# ---------------------------------------------------------------------------
# Maintenance schedules in manuals
# ---------------------------------------------------------------------------

_VERBS = r"(change|replace|clean|inspect|check|sharpen|lubricate|grease|drain|adjust|service|rotate|flush|tighten|test)"
_INTERVAL = re.compile(
    r"every\s+(\d{1,4})\s*(hours?|hrs?\.?|days?|weeks?|months?|years?|miles?)\b"
    r"|\b(annually|yearly|monthly|weekly|every season|each season|every year)\b",
    re.IGNORECASE,
)
_UNIT_DAYS = {"day": 1, "week": 7, "month": 30, "year": 365}
_WORD_DAYS = {"annually": 365, "yearly": 365, "every year": 365, "monthly": 30, "weekly": 7,
              "every season": 90, "each season": 90}


@dataclass
class ScheduleItem:
    task: str
    interval_days: Optional[int] = None
    interval_hours: Optional[float] = None
    interval_miles: Optional[float] = None
    source: str = ""  # the manual's own sentence

    def describe(self) -> str:
        if self.interval_hours:
            return f"{self.task}, every {self.interval_hours:g} hours"
        if self.interval_miles:
            return f"{self.task}, every {self.interval_miles:g} miles"
        return f"{self.task}, every {self.interval_days} days"


def maintenance_schedule(text: str, limit: int = 12) -> list[ScheduleItem]:
    """Pure logic. Maintenance steps with an interval, one per task."""
    items: list[ScheduleItem] = []
    seen: set[str] = set()
    sentences = re.split(r"(?<=[.;:!?])\s+|\n", text)
    for sentence in sentences:
        interval = _INTERVAL.search(sentence)
        verb = re.search(rf"\b{_VERBS}\b\s+(?:the\s+)?((?:[a-z/\-]+\s+){{0,3}}[a-z/\-]+)", sentence, re.IGNORECASE)
        if not interval or not verb:
            continue
        noun = re.split(r"\s+(?:every|each|at|after|annually|yearly|monthly|weekly|and|or|if|when|to)\b", verb.group(2), maxsplit=1,
                        flags=re.IGNORECASE)[0].strip(" ,.")
        if not noun:
            continue
        task = f"{verb.group(1).capitalize()} {noun.lower()}"
        key = task.lower()
        if key in seen:
            continue
        item = ScheduleItem(task=task, source=" ".join(sentence.split())[:160])
        if interval.group(1):
            value, unit = float(interval.group(1)), interval.group(2).lower().rstrip(".").rstrip("s")
            if unit in ("hour", "hr"):
                item.interval_hours = value
            elif unit == "mile":
                item.interval_miles = value
            else:
                item.interval_days = int(value * _UNIT_DAYS[unit])
        else:
            item.interval_days = _WORD_DAYS[interval.group(3).lower()]
        seen.add(key)
        items.append(item)
        if len(items) >= limit:
            break
    return items


# ---------------------------------------------------------------------------
# Details for the item's page (2026-09-28): "update information based on
# those documents". Read here, offered in the Inbox with a tick box each;
# empty fields are ticked, a different existing value is offered unticked.
# ---------------------------------------------------------------------------

KNOWN_MAKERS = (
    "John Deere", "Husqvarna", "Craftsman", "Cub Cadet", "Troy-Bilt", "Toro", "Honda", "Stihl", "Echo", "Ryobi",
    "DeWalt", "Milwaukee", "Makita", "Kubota", "Kohler", "Briggs & Stratton", "Greenworks", "EGO", "Snapper",
    "Ariens", "Poulan", "Generac", "Champion", "Ford", "Chevrolet", "GMC", "Toyota", "Ram", "Dodge", "Nissan",
    "Polaris", "Can-Am", "Yamaha", "Kawasaki", "Mahindra", "New Holland", "Bobcat", "Whirlpool", "GE",
    "Samsung", "LG", "Maytag", "Kenmore", "Rheem", "Carrier", "Trane",
)
_SERIAL = re.compile(r"\b(?:serial(?:\s*(?:number|no\.?|#))?|s/n)\s*[:#.]?\s*([A-Z0-9][A-Z0-9\-]{4,24})\b", re.IGNORECASE)
_MODEL = re.compile(r"\bmodel(?:\s*(?:number|no\.?|#))?\s*[:#.]?\s*([A-Z0-9][A-Z0-9\-]{1,20})\b", re.IGNORECASE)
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "ten": 10}
_WARRANTY_LENGTH = re.compile(
    r"\b(\d{1,2}|one|two|three|four|five|six|seven|ten)[- ](year|yr|month)s?\s+(?:limited\s+|full\s+|residential\s+)?warranty"
    r"|\bwarranty\s+(?:period\s+|coverage\s+)?(?:of|is|for|lasts)\s+(\d{1,2}|one|two|three|four|five|six|seven|ten)\s+(year|month)s?",
    re.IGNORECASE,
)
_WARRANTY_UNTIL = re.compile(r"\bwarranty\s+(?:expires|ends|valid\s+(?:until|through)|coverage\s+ends)(?:\s+on)?\s*:?\s*(.{6,20})", re.IGNORECASE)
_PARTS_WORDS = re.compile(r"\b(oil|filter|blade|belt|spark plug|repair|service|parts?|tune|labor)\b", re.IGNORECASE)

DETAIL_LABELS = {
    "model": "Model", "serial_number": "Serial number", "manufacturer": "Maker",
    "purchase": "Purchase", "warranty_until": "Warranty until",
}


def _line_of(text: str, match: re.Match) -> str:
    start = text.rfind("\n", 0, match.start()) + 1
    end = text.find("\n", match.end())
    return " ".join(text[start:end if end != -1 else None].split())[:120]


def _count(word: str) -> int:
    return int(word) if word.isdigit() else _NUMBER_WORDS[word.lower()]


def document_details(text: str, doc_type: str, receipt: Optional[ReceiptFields] = None) -> dict:
    """Pure logic. What the document says about the thing it's for:
    {field: {"value": ..., "source": the line it came from}}. Fields:
    model, serial_number, manufacturer, warranty (months, or an until
    date), purchase (a receipt that looks like buying the item itself,
    not parts)."""
    details: dict = {}
    for key, pattern in (("serial_number", _SERIAL), ("model", _MODEL)):
        for match in pattern.finditer(text):
            value = match.group(1).upper().strip("-")
            if any(ch.isdigit() for ch in value) and value.lower() not in ("year",):
                details[key] = {"value": value, "source": _line_of(text, match)}
                break
    lowered = _norm(text)
    found = [(lowered.find(_norm(m)), m) for m in KNOWN_MAKERS if _contains_phrase(lowered, m)]
    if found:
        index, maker = min(found)
        details["manufacturer"] = {"value": maker, "source": " ".join(text[max(0, index - 30):index + 50].split())}
    until = _WARRANTY_UNTIL.search(text)
    if until and _parse_date(until.group(1)):
        details["warranty"] = {"until": _parse_date(until.group(1)), "source": _line_of(text, until)}
    else:
        length = _WARRANTY_LENGTH.search(text)
        if length:
            count, unit = (length.group(1), length.group(2)) if length.group(1) else (length.group(3), length.group(4))
            months = _count(count) * (1 if unit.lower() == "month" else 12)
            details["warranty"] = {"months": months, "source": _line_of(text, length)}
    if doc_type in (RECEIPT, INVOICE) and receipt is not None and receipt.amount and not _PARTS_WORDS.search(text):
        details["purchase"] = {"price": receipt.amount, "date": receipt.date or "", "source": receipt.amount_basis}
    return details


def _add_months(start: str, months: int) -> Optional[str]:
    try:
        day = date.fromisoformat(start)
    except ValueError:
        return None
    year, month = divmod(day.month - 1 + months, 12)
    year, month = day.year + year, month + 1
    for d in (day.day, 30, 29, 28):
        try:
            return date(year, month, min(day.day, d)).isoformat()
        except ValueError:
            continue
    return None


@dataclass
class DetailProposal:
    field: str  # "model", "serial_number", "manufacturer", "purchase", "warranty_until"
    value: object  # str, or (price, date) for "purchase"
    text: str  # what the Inbox shows: 'Serial number: 1GX…'
    current: str = ""  # what the item has now, if anything
    default_on: bool = True
    source: str = ""


def detail_proposals(details: dict, asset) -> list[DetailProposal]:
    """Pure logic. The changes the document suggests for `asset`, empty
    fields ticked by default; unchanged values left out."""
    if asset is None or not details:
        return []
    proposals: list[DetailProposal] = []
    for key in ("model", "serial_number", "manufacturer"):
        if key not in details:
            continue
        value, current = details[key]["value"], str(getattr(asset, key, "") or "")
        if current.strip().lower() == value.lower():
            continue
        text = f"{DETAIL_LABELS[key]}: {value}" + (f" (now {current})" if current else "")
        proposals.append(DetailProposal(key, value, text, current, not current, details[key]["source"]))
    purchase = details.get("purchase")
    purchase_date = ""
    if purchase and not getattr(asset, "purchase_price", 0):
        purchase_date = purchase.get("date") or ""
        when = f" on {purchase_date}" if purchase_date else ""
        proposals.append(DetailProposal(
            "purchase", (purchase["price"], purchase_date), f"Bought for {money(purchase['price'], ',.2f')}{when}",
            "", True, purchase.get("source", ""),
        ))
    warranty = details.get("warranty")
    if warranty:
        until = warranty.get("until")
        if not until and warranty.get("months"):
            start = getattr(asset, "purchase_date", "") or purchase_date
            until = _add_months(start, warranty["months"]) if start else None
        current = str(getattr(asset, "warranty_until", "") or "")
        if until and until != current:
            text = f"Warranty until {until}" + (f" (now {current})" if current else "")
            proposals.append(DetailProposal("warranty_until", until, text, current, not current, warranty["source"]))
    return proposals


# ---------------------------------------------------------------------------
# Line items (2026-09-28): what was bought, not just the total
# ---------------------------------------------------------------------------

_ITEM_LINE = re.compile(
    r"^(?P<desc>.*?[A-Za-z].*?)\s+"
    r"(?:(?P<qty>\d+(?:\.\d+)?)\s*(?:@|x|X|EA\s*@)\s*[$£€]?(?P<unit>\d+\.\d{2})\s+)?"
    r"[$£€]?(?P<amount>\d{1,3}(?:,\d{3})*\.\d{2})\s*[A-Z]{0,2}$"
)
_NOT_AN_ITEM = re.compile(
    r"\b(sub\s?total|total|tax|change|cash|visa|mastercard|amex|discover|debit|credit|balance|tender|payment|paid|"
    r"amount due|savings|you saved|discount|coupon|rewards|points|card|auth|approval|ref|tip)\b",
    re.IGNORECASE,
)
_SUBTOTAL = re.compile(r"\bsub\s?total\b.*?(\d{1,3}(?:,\d{3})*\.\d{2})", re.IGNORECASE)


@dataclass
class LineItem:
    description: str
    amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None

    def describe(self) -> str:
        qty = f" ×{self.quantity:g}" if self.quantity and self.quantity != 1 else ""
        return f"{self.description}{qty} {money(self.amount, ',.2f')}"


def receipt_items(text: str) -> tuple[list[LineItem], str]:
    """Pure logic. (items, a note about how far to trust them). The note
    says when the items don't add up to the receipt's subtotal, so a
    misread line is visible instead of silently wrong."""
    items: list[LineItem] = []
    for raw in text.splitlines():
        line = " ".join(raw.split())
        if not line or _NOT_AN_ITEM.search(line):
            continue
        match = _ITEM_LINE.match(line)
        if not match:
            continue
        description = match.group("desc").strip(" .:-*#")
        if len(description) < 2 or re.fullmatch(r"[\d\W]+", description):
            continue
        amount = float(match.group("amount").replace(",", ""))
        quantity = float(match.group("qty")) if match.group("qty") else None
        unit_price = float(match.group("unit")) if match.group("unit") else None
        items.append(LineItem(description.title() if description.isupper() else description, amount, quantity, unit_price))
    if not items:
        return [], ""
    total = round(sum(i.amount for i in items), 2)
    subtotal = _SUBTOTAL.search(text)
    if subtotal:
        expected = float(subtotal.group(1).replace(",", ""))
        if abs(expected - total) <= 0.01:
            return items, f"The items add up to the subtotal ({money(expected, ',.2f')})."
        return items, f"The items add up to {money(total, ',.2f')} but the subtotal is {money(expected, ',.2f')}; a line may be misread or missing."
    return items, f"The items add up to {money(total, ',.2f')} (no subtotal on the receipt to check against)."
