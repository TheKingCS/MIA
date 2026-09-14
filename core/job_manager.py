"""
core.job_manager
===================

MIA Home's fabrication jobs — the second slice of the proposed
`mia_home_schema.sql` (see `docs/VISION.md`'s "MIA Home's expanded
scope" section and `core/material_manager.py`'s docstring for the
first slice), adapted to this project's persisted-JSON-manager
convention. Same shape as every other manager here: `data/jobs.json`,
a dataclass with `to_dict`/`from_dict`, a manager class wrapping
load/save.

`material_consumption` was its own top-level table in the proposed
schema; here it nests as a plain list on each `Job` instead — same
"a record owns a list of its own sub-items" shape as
`core/mission_manager.py`'s `Mission.objectives` or
`core/trip_manager.py`'s gear list, rather than a fourth separate
manager for what's really just line items belonging to one job.

`cost_rates`/`labor_rate` (simple scalar settings in the proposed
schema, not many-record entities) become a single config key,
`workshop.labor_rate_per_hour`, per the prediction already written into
`docs/VISION.md` when Materials was built — resolved now that a real
consumer (job costing) exists. `job_material_cost()`/`job_labor_cost()`/
`job_total_cost()` are plain Python functions over already-loaded
`Job`/`Material` records — same "compute on demand" precedent as
`core/memory_manager.py`/`core/material_manager.py`'s
`materials_needing_restock()` — rather than persisting a cost figure
that could drift from the real material prices/labor rate.

`consume_material()`/`produce_product()` are the places this manager
reaches across to `core/material_manager.py`/`core/product_manager.py`
(`self.context.materials`/`self.context.products`), same
cross-manager-reference pattern already established by
`core/mission_manager.py`'s `_trip_elapsed_hours()` reaching into
`self.context.trips` — resolved lazily at call time, not cached at
construction, so construction-order between these managers in
`core/application.py` doesn't matter here (unlike Trips/Missions, which
*does* have a real ordering requirement). `produce_product()`
(2026-07-16) is `consume_material()`'s other half — a job consumes raw
materials and produces finished goods, both real inventory movements,
closing the loop between all three managers.

`revenue`/`expenses` (the proposed schema's actual sales-ledger tables)
are NOT built yet — a later slice once Products is proven, same "one
piece at a time" discipline as every other MIA Home addition.
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
from core.material_manager import Material
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_JOBS_FILE = _DATA_DIR / "jobs.json"

JOB_STATUSES = ("Planned", "In Progress", "Complete", "Cancelled")

_LABOR_RATE_CONFIG_KEY = "workshop.labor_rate_per_hour"


@dataclass
class MaterialConsumptionEntry:
    material_id: str
    quantity_used: float

    def to_dict(self) -> dict:
        return {"material_id": self.material_id, "quantity_used": self.quantity_used}

    @staticmethod
    def from_dict(data: dict) -> "MaterialConsumptionEntry":
        return MaterialConsumptionEntry(
            material_id=data.get("material_id", ""),
            quantity_used=data.get("quantity_used", 0.0),
        )


@dataclass
class ProductionEntry:
    """One job producing some quantity of a finished product — see
    JobManager.produce_product(). A job can produce more than one
    product (or the same product across more than one run), same
    reasoning material_consumption supports more than one material."""

    product_id: str
    quantity_produced: float

    def to_dict(self) -> dict:
        return {"product_id": self.product_id, "quantity_produced": self.quantity_produced}

    @staticmethod
    def from_dict(data: dict) -> "ProductionEntry":
        return ProductionEntry(
            product_id=data.get("product_id", ""),
            quantity_produced=data.get("quantity_produced", 0.0),
        )


@dataclass
class Job:
    job_id: str
    name: str
    description: str = ""
    status: str = "Planned"  # one of JOB_STATUSES
    material_consumption: list[MaterialConsumptionEntry] = field(default_factory=list)
    products_produced: list[ProductionEntry] = field(default_factory=list)
    labor_hours: float = 0.0
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "material_consumption": [entry.to_dict() for entry in self.material_consumption],
            "products_produced": [entry.to_dict() for entry in self.products_produced],
            "labor_hours": self.labor_hours,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "Job":
        return Job(
            job_id=data.get("job_id", uuid.uuid4().hex[:10]),
            name=data.get("name", ""),
            description=data.get("description", ""),
            status=data.get("status", "Planned"),
            material_consumption=[
                MaterialConsumptionEntry.from_dict(entry) for entry in data.get("material_consumption", [])
            ],
            products_produced=[
                ProductionEntry.from_dict(entry) for entry in data.get("products_produced", [])
            ],
            labor_hours=data.get("labor_hours", 0.0),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


def job_material_cost(job: Job, materials_by_id: dict[str, Material]) -> float:
    """Pure logic — testable without I/O. Sums quantity_used * the
    material's own unit_cost for every consumption entry; an entry
    whose material_id no longer resolves (the material was deleted
    since) is skipped rather than raising — a job's historical record
    of what it consumed shouldn't become unreadable just because the
    material behind it was later removed from inventory."""
    total = 0.0
    for entry in job.material_consumption:
        material = materials_by_id.get(entry.material_id)
        if material is not None:
            total += entry.quantity_used * material.unit_cost
    return total


def job_labor_cost(job: Job, labor_rate_per_hour: float) -> float:
    """Pure logic — testable without I/O."""
    return job.labor_hours * labor_rate_per_hour


def job_total_cost(job: Job, materials_by_id: dict[str, Material], labor_rate_per_hour: float) -> float:
    """Pure logic — testable without I/O."""
    return job_material_cost(job, materials_by_id) + job_labor_cost(job, labor_rate_per_hour)


class JobManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._jobs: list[Job] = []
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _JOBS_FILE.exists():
            self._jobs = []
            return
        try:
            raw = json.loads(_JOBS_FILE.read_text(encoding="utf-8"))
            self._jobs = [Job.from_dict(d) for d in raw]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load jobs.json — starting with an empty list.")
            notify_data_corruption(self.context, "jobs.json")
            self._jobs = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_JOBS_FILE,
            json.dumps([j.to_dict() for j in self._jobs], indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def add_job(
        self,
        name: str,
        description: str = "",
        status: str = "Planned",
        labor_hours: float = 0.0,
        notes: str = "",
    ) -> Job:
        now = datetime.now().isoformat(timespec="seconds")
        job = Job(
            job_id=uuid.uuid4().hex[:10],
            name=name,
            description=description,
            status=status if status in JOB_STATUSES else "Planned",
            labor_hours=max(0.0, labor_hours),
            notes=notes,
            created_at=now,
            updated_at=now,
        )
        self._jobs.append(job)
        self._save()
        log.info("Job added: '%s' (status %s)", name, job.status)
        return job

    def update_job(self, job_id: str, **fields) -> Job:
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"No job with id '{job_id}'.")
        for key, value in fields.items():
            if key in ("created_at", "updated_at"):
                raise ValueError(f"'{key}' can't be set through update_job().")
            if not hasattr(job, key):
                raise ValueError(f"Job has no field '{key}'.")
            setattr(job, key, value)
        if job.status not in JOB_STATUSES:
            job.status = "Planned"
        if job.labor_hours < 0:
            job.labor_hours = 0
        job.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        return job

    def delete_job(self, job_id: str) -> None:
        self._jobs = [j for j in self._jobs if j.job_id != job_id]
        self._save()

    def consume_material(self, job_id: str, material_id: str, quantity_used: float) -> Job:
        """
        Records a material_consumption entry on the job *and* deducts
        the same quantity from core/material_manager.py's own
        quantity_on_hand — the whole point of linking the two. Clamped
        to zero rather than raising if quantity_used exceeds what's on
        hand (same "never go negative, but don't block the action"
        stance as core/material_manager.py's own update_material() —
        a real inventory count can drift from the on-hand figure, and
        the job still genuinely happened either way.
        """
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"No job with id '{job_id}'.")
        quantity_used = max(0.0, quantity_used)

        job.material_consumption.append(MaterialConsumptionEntry(material_id=material_id, quantity_used=quantity_used))
        job.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()

        # Routed through adjust_quantity() rather than update_material()
        # directly (multi-user pass, 2026-09-14) — a real Job consuming
        # stock is real, attributed usage, the same as a manual
        # quantity tweak; see MaterialManager.adjust_quantity()'s own
        # docstring for why both paths need to share one method.
        if self.context.materials is not None:
            material = self.context.materials.get_material(material_id)
            if material is not None:
                self.context.materials.adjust_quantity(material_id, -quantity_used)
        return job

    def produce_product(self, job_id: str, product_id: str, quantity_produced: float) -> Job:
        """
        Records a production entry on the job *and* credits the same
        quantity onto core/product_manager.py's own quantity_in_stock —
        the other half of consume_material()'s consume-and-deduct
        pattern, closing the loop: a job consumes raw materials and
        produces finished goods, both real inventory movements.
        """
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"No job with id '{job_id}'.")
        quantity_produced = max(0.0, quantity_produced)

        job.products_produced.append(ProductionEntry(product_id=product_id, quantity_produced=quantity_produced))
        job.updated_at = datetime.now().isoformat(timespec="seconds")
        self._save()

        if self.context.products is not None:
            product = self.context.products.get_product(product_id)
            if product is not None:
                self.context.products.adjust_stock(product_id, quantity_produced)
        return job

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> Optional[Job]:
        for job in self._jobs:
            if job.job_id == job_id:
                return job
        return None

    def all_jobs(self) -> list[Job]:
        return sorted(self._jobs, key=lambda j: j.created_at, reverse=True)

    def search(self, query: str) -> list[Job]:
        """Case-insensitive substring match over name, description, and notes."""
        query_lower = query.strip().lower()
        if not query_lower:
            return []

        matches = []
        for job in self._jobs:
            haystack = f"{job.name} {job.description} {job.notes}".lower()
            if query_lower in haystack:
                matches.append(job)
        return sorted(matches, key=lambda j: j.name.lower())

    # ------------------------------------------------------------------
    # Costing
    # ------------------------------------------------------------------

    def total_cost(self, job_id: str) -> Optional[float]:
        """None if job_id doesn't resolve; otherwise the job's material
        cost (via core/material_manager.py's live Material records,
        looked up fresh — not a snapshot that could go stale if a
        material's unit_cost changes later) plus labor cost at the
        configured workshop.labor_rate_per_hour (defaults to 0.0 — a
        rate the user hasn't set yet shouldn't silently inflate every
        job's cost with a made-up number)."""
        job = self.get_job(job_id)
        if job is None:
            return None
        materials_by_id = {}
        if self.context.materials is not None:
            materials_by_id = {m.material_id: m for m in self.context.materials.all_materials()}
        labor_rate = self.context.config.get(_LABOR_RATE_CONFIG_KEY, 0.0) if self.context.config else 0.0
        return job_total_cost(job, materials_by_id, labor_rate)
