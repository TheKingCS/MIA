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

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_PRODUCTS_FILE = _DATA_DIR / "products.json"

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
        )


class ProductManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._products: list[Product] = []
        self._load()

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
            self._products = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PRODUCTS_FILE,
            json.dumps([p.to_dict() for p in self._products], indent=2),
            encoding="utf-8",
        )

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
        by hand before the Revenue slice exists)."""
        product = self.get_product(product_id)
        if product is None:
            raise ValueError(f"No product with id '{product_id}'.")
        product.quantity_in_stock = max(0.0, product.quantity_in_stock + delta)
        product.updated_at = datetime.now().isoformat(timespec="seconds")
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
