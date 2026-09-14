"""
core.product_manager
=======================

MIA Home's finished-goods products — the third slice of the proposed
`mia_home_schema.sql` (see `docs/VISION.md`'s "MIA Home's expanded
scope" section, `core/material_manager.py`'s docstring for the first
slice, and `core/job_manager.py`'s for the second), adapted to this
project's persisted-JSON-manager convention. Same shape as every other
manager here: `data/products.json`, a dataclass with
`to_dict`/`from_dict`, a manager class wrapping load/save.

`product_listings` was its own top-level table in the proposed schema;
here it nests as a plain list on each `Product` instead — a listing
without a product to belong to doesn't mean anything, and one product
can genuinely have several (Etsy, a web store, local sales), same
"a record owns a list of its own sub-items" shape
`core/job_manager.py`'s `Job.material_consumption` and
`core/mission_manager.py`'s `Mission.objectives` already established.

`JobManager.produce_product()` (in `core/job_manager.py`, not here) is
the other half of this slice — a job that finishes now genuinely
credits a product's `quantity_in_stock`, closing the loop
`consume_material()` opened: a job consumes raw materials and produces
finished goods, and both sides of that are real inventory movements,
not two independent lists that happen to reference each other.

`revenue`/`expenses` (the proposed schema's actual sales-ledger tables)
are NOT built yet — a later slice once Products is proven, same
one-piece-at-a-time discipline as every other MIA Home addition.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PRODUCTS_FILE = _DATA_DIR / "products.json"
# Multi-user pass (2026-09-14) — the "shared object + user relationship"
# pattern's fifth real application (see core.material_manager.
# MaterialUsageEntry's own docstring for the fourth). Product itself
# stays shared/household; this file holds one real per-adjustment
# event. Genuinely the easiest of the five to wire up: adjust_stock()
# already existed and both real event sources
# (core.job_manager.JobManager.produce_product() and
# core.ledger_manager.LedgerManager.record_sale()) already call it, so
# logging inside adjust_stock() itself covers both with zero further
# rewiring — unlike Materials, which needed consume_material() rewired
# by hand.
_USAGE_LOG_FILE = _DATA_DIR / "product_usage_log.json"

LISTING_STATUSES = ("Active", "Inactive", "Sold Out")


@dataclass
class ProductListing:
    listing_id: str
    platform: str  # e.g. "Etsy", "Web Store", "Local"
    price: float = 0.0
    status: str = "Active"  # one of LISTING_STATUSES
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "listing_id": self.listing_id,
            "platform": self.platform,
            "price": self.price,
            "status": self.status,
            "url": self.url,
        }

    @staticmethod
    def from_dict(data: dict) -> "ProductListing":
        return ProductListing(
            listing_id=data.get("listing_id", uuid.uuid4().hex[:10]),
            platform=data.get("platform", ""),
            price=data.get("price", 0.0),
            status=data.get("status", "Active"),
            url=data.get("url", ""),
        )


@dataclass
class Product:
    product_id: str
    name: str
    description: str = ""
    job_id: str = ""  # optional — the job that most recently produced/restocked this product, "" if none
    quantity_in_stock: float = 0.0
    base_price: float = 0.0
    listings: list[ProductListing] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""
    # Multi-user pass (2026-09-14) — who first added this product, same
    # role core.material_manager.Material.added_by_profile_id/
    # core.component_manager.Component.added_by_profile_id play.
    added_by_profile_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "job_id": self.job_id,
            "quantity_in_stock": self.quantity_in_stock,
            "base_price": self.base_price,
            "listings": [listing.to_dict() for listing in self.listings],
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "added_by_profile_id": self.added_by_profile_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "Product":
        return Product(
            product_id=data.get("product_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            job_id=data.get("job_id", ""),
            quantity_in_stock=data.get("quantity_in_stock", 0.0),
            base_price=data.get("base_price", 0.0),
            listings=[ProductListing.from_dict(entry) for entry in data.get("listings", [])],
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            added_by_profile_id=data.get("added_by_profile_id"),
        )


@dataclass
class ProductUsageEntry:
    """One real stock adjustment, attributed to whoever was active when
    it happened — same shape as core.material_manager.MaterialUsageEntry
    (a real `float` delta). Populated inside adjust_stock() itself, so
    both real sources of a product's stock changing
    (JobManager.produce_product() crediting a finished job, and
    LedgerManager.record_sale() debiting a real sale) become attributed
    usage automatically, no rewiring needed at either call site.
    times_sold()/last_sold() (not times_used()/last_used(), unlike the
    other three applications of this pattern) since "used" doesn't fit
    a product the way it does a consumable — the real business question
    here is who sold it."""

    entry_id: str
    product_id: str
    delta: float
    profile_id: Optional[str] = None
    timestamp: str = ""  # ISO datetime

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "product_id": self.product_id,
            "delta": self.delta,
            "profile_id": self.profile_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(data: dict) -> "ProductUsageEntry":
        return ProductUsageEntry(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:10]),
            product_id=data.get("product_id", ""),
            delta=data.get("delta", 0.0),
            profile_id=data.get("profile_id"),
            timestamp=data.get("timestamp", ""),
        )


class ProductManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._products: list[Product] = []
        self._usage_log: list[ProductUsageEntry] = []
        self._load()
        self._load_usage_log()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _PRODUCTS_FILE.exists():
            self._products = []
            return
        try:
            raw = json.loads(_PRODUCTS_FILE.read_text(encoding="utf-8"))
            self._products = [Product.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load products.json — starting with an empty list.")
            notify_data_corruption(self.context, "products.json")
            self._products = []

    def _load_usage_log(self) -> None:
        if not _USAGE_LOG_FILE.exists():
            self._usage_log = []
            return
        try:
            raw = json.loads(_USAGE_LOG_FILE.read_text(encoding="utf-8"))
            self._usage_log = [ProductUsageEntry.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load product_usage_log.json — starting with an empty list.")
            notify_data_corruption(self.context, "product_usage_log.json")
            self._usage_log = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PRODUCTS_FILE,
            json.dumps([p.to_dict() for p in self._products], indent=2),
            encoding="utf-8",
        )

    def _save_usage_log(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            _USAGE_LOG_FILE,
            json.dumps([e.to_dict() for e in self._usage_log], indent=2),
            encoding="utf-8",
        )

    def _active_profile_id(self) -> Optional[str]:
        active_profile = self.context.profiles.get_active_profile() if self.context.profiles is not None else None
        return active_profile.profile_id if active_profile is not None else None

    # ------------------------------------------------------------------
    # Writing — products
    # ------------------------------------------------------------------

    def add_product(
        self,
        name: str,
        description: str = "",
        job_id: str = "",
        quantity_in_stock: float = 0.0,
        base_price: float = 0.0,
        notes: str = "",
    ) -> Product:
        now = datetime.now().isoformat(timespec="seconds")
        product = Product(
            product_id=uuid.uuid4().hex[:10],
            name=name,
            description=description,
            job_id=job_id,
            quantity_in_stock=max(0.0, quantity_in_stock),
            base_price=max(0.0, base_price),
            notes=notes,
            created_at=now,
            updated_at=now,
            added_by_profile_id=self._active_profile_id(),
        )
        self._products.append(product)
        self._save()
        log.info("Product added: '%s' (qty %s)", name, product.quantity_in_stock)
        return product

    def update_product(self, product_id: str, **fields) -> Product:
        product = self.get_product(product_id)
        if product is None:
            raise ValueError(f"No product with id '{product_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "updated_at"):
                raise ValueError(f"'{key}' can't be set through update_product().")
            if not hasattr(product, key):
                raise ValueError(f"Product has no field '{key}'.")
            setattr(product, key, value)
        if product.quantity_in_stock < 0:
            product.quantity_in_stock = 0
        if product.base_price < 0:
            product.base_price = 0
        product.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return product

    def delete_product(self, product_id: str) -> None:
        self._products = [p for p in self._products if p.product_id != product_id]
        self._save()

    def adjust_stock(self, product_id: str, delta: float) -> Product:
        """Adds `delta` (negative to reduce) to quantity_in_stock,
        clamped at zero — the manual counterpart to
        core/job_manager.py's produce_product(), for stock changes not
        tied to a specific job (e.g. a manual recount, a sale recorded
        by hand before the Revenue slice exists).

        Multi-user pass (2026-09-14) — a real, non-zero delta also
        appends a ProductUsageEntry attributed to whoever's active.
        Both `core.job_manager.JobManager.produce_product()` (a
        positive delta) and `core.ledger_manager.LedgerManager.
        record_sale()` (a negative delta) already call this method
        rather than mutating quantity_in_stock directly, so both real
        event sources become attributed usage with no further
        rewiring — see ProductUsageEntry's own docstring."""
        product = self.get_product(product_id)
        if product is None:
            raise ValueError(f"No product with id '{product_id}'.")
        product.quantity_in_stock = max(0.0, product.quantity_in_stock + delta)
        product.updated_at = datetime.now().isoformat(timespec="seconds")
        if delta != 0:
            self._usage_log.append(ProductUsageEntry(
                entry_id=uuid.uuid4().hex[:10],
                product_id=product_id,
                delta=delta,
                profile_id=self._active_profile_id(),
                timestamp=product.updated_at,
            ))
            self._save_usage_log()
        self._save()
        return product

    # ------------------------------------------------------------------
    # Writing — listings
    # ------------------------------------------------------------------

    def add_listing(
        self, product_id: str, platform: str, price: float = 0.0, status: str = "Active", url: str = ""
    ) -> Product:
        product = self.get_product(product_id)
        if product is None:
            raise ValueError(f"No product with id '{product_id}'.")
        listing = ProductListing(
            listing_id=uuid.uuid4().hex[:10],
            platform=platform,
            price=max(0.0, price),
            status=status if status in LISTING_STATUSES else "Active",
            url=url,
        )
        product.listings.append(listing)
        product.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return product

    def remove_listing(self, product_id: str, listing_id: str) -> Product:
        product = self.get_product(product_id)
        if product is None:
            raise ValueError(f"No product with id '{product_id}'.")
        product.listings = [listing for listing in product.listings if listing.listing_id != listing_id]
        product.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return product

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_product(self, product_id: str) -> Optional[Product]:
        for product in self._products:
            if product.product_id == product_id:
                return product
        return None

    def all_products(self) -> list[Product]:
        return sorted(self._products, key=lambda p: p.name.lower())

    def search(self, query: str) -> list[Product]:
        """Case-insensitive substring match over name, description, and notes."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for product in self._products:
            haystack = f"{product.name} {product.description} {product.notes}".lower()
            if query_lower in haystack:
                matches.append(product)
        return sorted(matches, key=lambda p: p.name.lower())

    # ------------------------------------------------------------------
    # Usage (multi-user pass, 2026-09-14) — see ProductUsageEntry's own
    # docstring; direct analog of
    # core.material_manager.MaterialManager's usage_log_for_material()/
    # times_used()/last_used(), renamed times_sold()/last_sold() here
    # since "used" doesn't fit a finished-goods product.
    # ------------------------------------------------------------------

    def usage_log_for_product(self, product_id: str) -> list[ProductUsageEntry]:
        """Every real stock adjustment (both production and sales/reductions) for this product, oldest first."""
        return [e for e in self._usage_log if e.product_id == product_id]

    def times_sold(self, product_id: str, profile_id: Optional[str] = None) -> int:
        """Real stock REDUCTIONS only (delta < 0) — a production credit
        isn't a sale. `profile_id=None` (the default) is the real
        household total; a real profile_id counts only entries
        attributed to that profile OR unattributed — same semantics
        every other application of this pattern already established."""
        return sum(
            1 for e in self._usage_log
            if e.product_id == product_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        )

    def last_sold(self, product_id: str, profile_id: Optional[str] = None) -> Optional[ProductUsageEntry]:
        """Same `profile_id` semantics as times_sold() above. Picks the
        last MATCHING entry by real append order, not by comparing
        `timestamp` strings — see
        core.inventory_manager.InventoryManager.last_used()'s own
        docstring for why."""
        matches = [
            e for e in self._usage_log
            if e.product_id == product_id and e.delta < 0
            and (profile_id is None or e.profile_id is None or e.profile_id == profile_id)
        ]
        if not matches:
            return None
        return matches[-1]
