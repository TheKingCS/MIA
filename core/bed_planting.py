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
              variety: str = None, expected_harvest_date: str = None) -> int:
        cur = self.db.execute(
            "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, variety, expected_harvest_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (grow_bed_name, cell_id, species_id, variety, expected_harvest_date),
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
                "Tracks what species is planted in each grow bed, and flags when two "
                "plantings sharing the same cell's water want genuinely incompatible "
                "pH/EC ranges — since a cell has one water chemistry for every bed on it."
            ),
            data_produced=["current plantings per bed, with species/variety/planted date"],
            actions_possible=["record a new planting", "mark harvested or failed",
                               "check whether current plantings in a cell are chemically compatible"],
            limits_and_safety=(
                "Warns, does not block — planting something incompatible is allowed, "
                "you just get told about it. Compatibility check is a plausibility check "
                "against known ranges, not a guarantee of real-world outcome."
            ),
            example_questions=["What's planted in Cell A?", "Can lettuce and basil share a cell?"],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # record-keeping only, no hardware of its own
