"""
core.business_book
====================

Quotes, customers, orders and the portfolio (DEC-0030 phase C): the
business loop on top of crafting recipes (core/craft_recipes.py), builds
(Jobs) and the workshop ledger, never beside them.

- **Customers**: who buys or commissions; the household's own, never
  shown to a child.
- **Quotes**: a price for a customer, suggested from a recipe (its
  materials and hours, your labor rate, extras, your margin) or set by
  hand. Draft → Sent → Accepted (it becomes an order) or Declined.
- **Orders**: what was agreed. Payments (a deposit, the rest) go into the
  workshop ledger; **Start Build** makes the recipe's build and ties the
  payments to it, so the build's profit counts what the customer paid.
- **Portfolio**: finished builds with their photos, featured ones first.
- **Market days** (DEC-0036): a day at the stand or the market, with
  how many of each recipe's goods you took. Its sales are the Ledger's,
  noted with the day (core/goods.py's market_tag), so the day's tally is
  read from the books, never kept twice.

A household store (shared between partners), written through
atomic_write_text so every change can be undone.
"""

from __future__ import annotations

from core import life_events

import json
import math
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "business.json"

QUOTE_STATUSES = ("Draft", "Sent", "Accepted", "Declined")
ORDER_STATUSES = ("Open", "Building", "Ready", "Delivered", "Cancelled")


def _now() -> str:
    """Now, as an ISO timestamp to the second."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Customer:
    """Someone who buys or commissions: name, phone, email, notes. The household's own; never shown to a child."""
    customer_id: str
    name: str
    phone: str = ""
    email: str = ""
    notes: str = ""
    created_at: str = ""


@dataclass
class Quote:
    """A price offered to a customer: for a recipe and quantity, worked out from its materials and hours at the labor rate,
    plus extras and the margin (percent), unless a price is set by hand (0: use the suggested one). Draft, Sent,
    Accepted (then it has its order) or Declined.
    """
    quote_id: str
    title: str
    customer_id: str = ""
    recipe_id: str = ""
    quantity: int = 1
    labor_rate: float = 0.0
    margin: float = 20.0  # percent
    extras: float = 0.0  # delivery, hardware, anything else
    price: float = 0.0  # 0: use the suggested price
    valid_until: str = ""
    notes: str = ""
    status: str = "Draft"
    order_id: str = ""
    created_at: str = ""


@dataclass
class Order:
    """What was agreed: the customer, quote and recipe, quantity, price, due date, status, the builds (jobs) made for it
    and the payments taken (ledger revenue entries).
    """
    order_id: str
    title: str
    customer_id: str = ""
    quote_id: str = ""
    recipe_id: str = ""
    quantity: int = 1
    price: float = 0.0
    due_date: str = ""
    notes: str = ""
    status: str = "Open"
    job_ids: list[str] = field(default_factory=list)
    payment_ids: list[str] = field(default_factory=list)  # ledger revenue entries
    created_at: str = ""


@dataclass
class MarketDay:
    """A day at the stand or the market: where, when, how many of each recipe's goods were taken, open or closed. Its
    sales are the ledger's, tagged with the day.
    """
    market_id: str
    place: str = ""
    date: str = ""  # YYYY-MM-DD
    brought: dict = field(default_factory=dict)  # recipe_id → how many you took
    status: str = "open"  # open | closed
    notes: str = ""
    created_at: str = ""
    closed_at: str = ""


LABEL_FIELDS = ("business", "address", "statement")


def suggested_price(materials: float, hours: float, rate: float, extras: float, margin: float) -> float:
    """Pure logic. (materials + hours × rate + extras) plus the margin,
    rounded up to a whole dollar."""
    base = max(0.0, materials) + max(0.0, hours) * max(0.0, rate) + max(0.0, extras)
    return float(math.ceil(base * (1 + max(0.0, margin) / 100) - 1e-9)) if base else 0.0


class BusinessBook:
    """The household's business store (business.json): customers, quotes, orders, featured portfolio builds, market
    days and what labels say. Written through atomic_write_text, so every change can be undone.
    """
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the household's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads everything, keeping only fields each record knows (so a newer file loads); an unreadable file is logged,
        reported (notify_data_corruption) and starts empty.
        """
        self.customers: list[Customer] = []
        self.quotes: list[Quote] = []
        self.orders: list[Order] = []
        self.featured: list[str] = []
        self.markets: list[MarketDay] = []
        self.label: dict = {}  # DEC-0036: business, address, statement (the person's own words)
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.customers = [pick(Customer, d) for d in raw.get("customers", [])]
            self.quotes = [pick(Quote, d) for d in raw.get("quotes", [])]
            self.orders = [pick(Order, d) for d in raw.get("orders", [])]
            self.featured = [str(j) for j in raw.get("featured", [])]
            self.markets = [pick(MarketDay, d) for d in raw.get("markets", [])]
            self.label = {k: str(v) for k, v in (raw.get("label") or {}).items() if k in LABEL_FIELDS}
        except (json.JSONDecodeError, OSError, TypeError, AttributeError):
            log.exception("business.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes everything atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({
            "customers": [asdict(c) for c in self.customers], "quotes": [asdict(q) for q in self.quotes],
            "orders": [asdict(o) for o in self.orders], "featured": self.featured,
            "markets": [asdict(m) for m in self.markets], "label": self.label}, indent=2))

    # ---------------------------------------------------------------- shared CRUD

    @staticmethod
    def _set(item, fields: dict, numbers=(), ints=()) -> None:
        """Sets a record's fields, refusing unknown ones and ids other than the customer and recipe they point at; money
        fields are never negative and counts at least 1.
        """
        for name, value in fields.items():
            if not hasattr(item, name) or name.endswith("_id") and name not in ("customer_id", "recipe_id"):
                raise ValueError(f"No field '{name}'.")
            if name in numbers:
                value = max(0.0, float(value or 0))
            elif name in ints:
                value = max(1, int(float(value or 1)))
            setattr(item, name, value if value is not None else "")

    def _get(self, items: list, attr: str, item_id: str):
        """The item in a list whose id field matches, or None."""
        return next((i for i in items if getattr(i, attr) == item_id), None)

    # customers
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        """The customer with this id, or None."""
        return self._get(self.customers, "customer_id", customer_id)

    @life_events.on_change("customer_added", "a customer", "customer")
    def add_customer(self, name: str, **fields) -> Customer:
        """Adds a customer (a name is required)."""
        if not str(name or "").strip():
            raise ValueError("A customer needs a name.")
        c = Customer(customer_id=uuid.uuid4().hex[:10], name=name.strip(), created_at=_now())
        self._set(c, fields)
        self.customers.append(c)
        self._save()
        return c

    def update_customer(self, customer_id: str, **fields) -> Customer:
        """Changes a customer's fields (ValueError when they're gone)."""
        c = self.get_customer(customer_id)
        if c is None:
            raise ValueError("That customer isn't there anymore.")
        self._set(c, fields)
        self._save()
        return c

    @life_events.on_change("customer_removed", "a customer", "customer")
    def delete_customer(self, customer_id: str) -> None:
        """Deletes a customer."""
        self.customers = [c for c in self.customers if c.customer_id != customer_id]
        self._save()

    # quotes
    _Q_NUM, _Q_INT = ("labor_rate", "margin", "extras", "price"), ("quantity",)

    def get_quote(self, quote_id: str) -> Optional[Quote]:
        """The quote with this id, or None."""
        return self._get(self.quotes, "quote_id", quote_id)

    @life_events.on_change("quote_added", "a quote", "quote")
    def add_quote(self, title: str, **fields) -> Quote:
        """Adds a quote (a title is required)."""
        if not str(title or "").strip():
            raise ValueError("A quote needs a title.")
        q = Quote(quote_id=uuid.uuid4().hex[:10], title=title.strip(), created_at=_now())
        self._set(q, fields, self._Q_NUM, self._Q_INT)
        self.quotes.append(q)
        self._save()
        return q

    def update_quote(self, quote_id: str, **fields) -> Quote:
        """Changes a quote's fields, its status one of QUOTE_STATUSES (ValueError otherwise)."""
        q = self.get_quote(quote_id)
        if q is None:
            raise ValueError("That quote isn't there anymore.")
        if "status" in fields and fields["status"] not in QUOTE_STATUSES:
            raise ValueError("Unknown status.")
        self._set(q, fields, self._Q_NUM, self._Q_INT)
        self._save()
        return q

    @life_events.on_change("quote_removed", "a quote", "quote")
    def delete_quote(self, quote_id: str) -> None:
        """Deletes a quote."""
        self.quotes = [q for q in self.quotes if q.quote_id != quote_id]
        self._save()

    # orders
    def get_order(self, order_id: str) -> Optional[Order]:
        """The order with this id, or None."""
        return self._get(self.orders, "order_id", order_id)

    @life_events.on_change("order_added", "an order", "order")
    def add_order(self, title: str, **fields) -> Order:
        """Adds an order (a title is required), with the quote it came from; its builds and payments are added later."""
        if not str(title or "").strip():
            raise ValueError("An order needs a title.")
        o = Order(order_id=uuid.uuid4().hex[:10], title=title.strip(), created_at=_now())
        self._set(o, {k: v for k, v in fields.items() if k not in ("job_ids", "payment_ids", "quote_id")},
                  ("price",), ("quantity",))
        o.quote_id = str(fields.get("quote_id") or "")
        self.orders.append(o)
        self._save()
        return o

    def update_order(self, order_id: str, **fields) -> Order:
        """Changes an order's fields, including its builds and payments, its status one of ORDER_STATUSES."""
        o = self.get_order(order_id)
        if o is None:
            raise ValueError("That order isn't there anymore.")
        if "status" in fields and fields["status"] not in ORDER_STATUSES:
            raise ValueError("Unknown status.")
        for name in ("job_ids", "payment_ids"):
            if name in fields:
                setattr(o, name, list(fields.pop(name)))
        self._set(o, fields, ("price",), ("quantity",))
        self._save()
        return o

    @life_events.on_change("order_removed", "an order", "order")
    def delete_order(self, order_id: str) -> None:
        """Deletes an order."""
        self.orders = [o for o in self.orders if o.order_id != order_id]
        self._save()

    def toggle_featured(self, job_id: str) -> bool:
        """Features a finished build in the portfolio (first), or stops featuring it; returns whether it's featured now."""
        if job_id in self.featured:
            self.featured.remove(job_id)
        else:
            self.featured.insert(0, job_id)
        self._save()
        return job_id in self.featured

    # market days (DEC-0036)
    def get_market(self, market_id: str) -> Optional[MarketDay]:
        """The market day with this id, or None."""
        return self._get(self.markets, "market_id", market_id)

    def open_market(self) -> Optional[MarketDay]:
        """The market day under way, if one is."""
        return next((m for m in reversed(self.markets) if m.status == "open"), None)

    @life_events.on_change("market_started", "a market day", "market")
    def start_market(self, place: str, date: str, brought: dict, notes: str = "") -> MarketDay:
        """Opens a market day with what's being taken (only one open at a time; ValueError otherwise)."""
        if self.open_market() is not None:
            raise ValueError("A market day is already open: close it first.")
        m = MarketDay(market_id=uuid.uuid4().hex[:10], place=str(place or "").strip(), date=str(date or _now()[:10]),
                      brought={str(k): float(v) for k, v in (brought or {}).items() if float(v) > 0},
                      notes=str(notes or ""), created_at=_now())
        self.markets.append(m)
        self._save()
        return m

    def update_market(self, market_id: str, **fields) -> MarketDay:
        """Changes a market day's place, date, goods taken, status (open or closed), notes or closing time."""
        m = self.get_market(market_id)
        if m is None:
            raise ValueError("That market day isn't there anymore.")
        for name, value in fields.items():
            if name not in ("place", "date", "brought", "status", "notes", "closed_at"):
                raise ValueError(f"No field '{name}'.")
            if name == "status" and value not in ("open", "closed"):
                raise ValueError("Unknown status.")
            setattr(m, name, dict(value) if name == "brought" else value)
        self._save()
        return m

    def delete_market(self, market_id: str) -> None:
        """Deletes a market day (its sales stay in the ledger)."""
        self.markets = [m for m in self.markets if m.market_id != market_id]
        self._save()

    def set_label(self, **fields) -> dict:
        """Sets what labels say about the business (name, address, statement), in the person's own words."""
        for name, value in fields.items():
            if name not in LABEL_FIELDS:
                raise ValueError(f"No field '{name}'.")
            self.label[name] = str(value or "").strip()
        self._save()
        return dict(self.label)
