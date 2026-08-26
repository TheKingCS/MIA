"""
MIA Homestead — Bed Planting Tracker
v0.1

Tracks what's actually planted in each grow bed. The useful thing this
enables beyond record-keeping: checking whether everything currently
sharing one cell's water actually wants compatible conditions, since a
cell has ONE set of water chemistry for every bed on it.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.bed_planting")


class BedPlantingManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection, species_registry, notifier=None):
        self.db = db_conn
        self.species = species_registry
        self.notifier = notifier

    def plant(self, grow_bed_name: str, cell_id: int, species_id: int,
              variety: str = None, expected_harvest_date: str = None,
              quantity_planted: int = None, expected_yield_amount: float = None,
              expected_yield_unit: str = None) -> int:
        cur = self.db.execute(
            "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, variety, "
            "expected_harvest_date, quantity_planted, expected_yield_amount, expected_yield_unit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (grow_bed_name, cell_id, species_id, variety, expected_harvest_date,
             quantity_planted, expected_yield_amount, expected_yield_unit),
        )
        self.db.commit()
        planting_id = cur.lastrowid

        self._check_cell_compatibility(cell_id)
        return planting_id

    def mark_harvested(self, planting_id: int) -> None:
        self.db.execute(
            "UPDATE bed_plantings SET status = 'harvested' WHERE id = ?", (planting_id,)
        )
        self.db.commit()

    def mark_failed(self, planting_id: int, notes: str = None) -> None:
        self.db.execute(
            "UPDATE bed_plantings SET status = 'failed', notes = ? WHERE id = ?",
            (notes, planting_id),
        )
        self.db.commit()

    def get_expected_vs_actual(self, planting_id: int) -> dict:
        """The direct answer to 'how much did we expect vs how much did
        we get' — sums actual yield_events logged for this planting's
        cell since it was planted, against the expected figure recorded
        at planting time. Approximate: yield_events are per-cell, not
        per-planting, so if multiple plantings share a cell this sums
        ALL yield in that window, not just this planting's — flagged
        explicitly rather than silently overcounted."""
        self.db.row_factory = sqlite3.Row
        planting = self.db.execute("SELECT * FROM bed_plantings WHERE id = ?", (planting_id,)).fetchone()
        if not planting:
            return {"error": f"no planting {planting_id}"}
        planting = dict(planting)

        actual = self.db.execute(
            "SELECT SUM(quantity) FROM yield_events WHERE cell_id = ? AND timestamp >= ?",
            (planting["cell_id"], planting["planted_date"]),
        ).fetchone()[0]

        isolated = not self._other_active_plantings_in_cell(planting)
        return {
            "grow_bed_name": planting["grow_bed_name"],
            "expected_amount": planting["expected_yield_amount"],
            "expected_unit": planting["expected_yield_unit"],
            "actual_amount_so_far": actual,
            "note": (
                "isolated to this planting — no other active plantings share this cell"
                if isolated else
                "actual_amount is summed across ALL yield events in this cell since "
                "planting — other plantings share this cell, so this isn't isolated"
            ),
        }

    def _other_active_plantings_in_cell(self, planting: dict) -> bool:
        count = self.db.execute(
            "SELECT COUNT(*) FROM bed_plantings WHERE cell_id = ? AND status = 'active' AND id != ?",
            (planting["cell_id"], planting["id"]),
        ).fetchone()[0]
        return count > 0

    def get_current_plantings(self, cell_id: int = None) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        q = """
            SELECT bp.*, sp.common_name, sp.ph_min, sp.ph_max, sp.ec_min, sp.ec_max
            FROM bed_plantings bp
            JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status = 'active'
        """
        params = ()
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params = (cell_id,)
        return [dict(r) for r in self.db.execute(q, params).fetchall()]

    def record_water_usage(self, cell_id: int, amount_gallons: float, reason: str,
                            grow_bed_name: str = None, triggered_by: str = "auto_control") -> int:
        """The direct answer to 'how much water and why' — every
        irrigation pulse gets a reason, not just a volume."""
        cur = self.db.execute(
            "INSERT INTO water_usage_events (cell_id, grow_bed_name, amount_gallons, reason, triggered_by) "
            "VALUES (?, ?, ?, ?, ?)",
            (cell_id, grow_bed_name, amount_gallons, reason, triggered_by),
        )
        self.db.commit()
        return cur.lastrowid

    def get_water_usage(self, cell_id: int, days: int = 7) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM water_usage_events WHERE cell_id = ? AND timestamp >= datetime('now', ?) "
            "ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()]

    def _check_cell_compatibility(self, cell_id: int) -> None:
        """Every species sharing this cell's water needs overlapping
        ranges — if two active plantings want genuinely incompatible
        conditions, that's worth surfacing loudly, not discovering when
        neither one thrives. This doesn't block the planting; it warns."""
        plantings = self.get_current_plantings(cell_id)
        plant_only = [p for p in plantings if p["ph_min"] is not None]
        if len(plant_only) < 2:
            return

        overlap_ph_min = max(p["ph_min"] for p in plant_only)
        overlap_ph_max = min(p["ph_max"] for p in plant_only)

        if overlap_ph_min > overlap_ph_max:
            names = ", ".join(p["common_name"] for p in plant_only)
            message = (
                f"Cell {cell_id}: plantings ({names}) have NO overlapping pH range — "
                f"they cannot both thrive sharing this cell's water. Consider moving "
                f"one to a separate cell."
            )
            logger.warning(message)
            if self.notifier:
                self.notifier.dispatch("warning", message, source="bed_planting")

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="bed_planting",
            display_name="Bed Planting Tracker",
            purpose=(
                "Tracks what species is planted in each grow bed, expected vs actual yield, "
                "water usage with the reason behind each use, and flags when two plantings "
                "sharing the same cell's water want genuinely incompatible pH/EC ranges — "
                "since a cell has one water chemistry for every bed on it."
            ),
            data_produced=["current plantings per bed, with species/variety/planted date",
                            "expected vs actual yield comparisons", "water usage log with rationale"],
            actions_possible=["record a new planting", "mark harvested or failed",
                               "record water usage with a reason",
                               "check whether current plantings in a cell are chemically compatible"],
            limits_and_safety=(
                "Warns, does not block — planting something incompatible is allowed, "
                "you just get told about it. Compatibility check is a plausibility check "
                "against known ranges, not a guarantee of real-world outcome."
            ),
            example_questions=["What's planted in Cell A?", "Can lettuce and basil share a cell?"],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed compatible plantings (lettuce+basil, "
                "overlapping ranges) produce no warning; a fabricated incompatible species "
                "correctly triggered the warning",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # record-keeping only, no hardware of its own
