"""
MIA Homestead — Bed Planting Tracker
v0.2

Tracks what's actually planted in each grow bed. The useful thing this
enables beyond record-keeping: checking whether everything currently
sharing one cell's water actually wants compatible conditions, since a
cell has ONE set of water chemistry for every bed on it.

v0.2 adds real PLANNING (2026-09-01, user request): a 'planned' status
distinct from 'active' — stage a future planting (bed + species +
target date) before it's physically done, then convert it to active
once it actually happens. plant() (immediate, already-done planting)
is unchanged and still the right call for "I just planted this" — plan()
is for "I intend to plant this on/around this date." Compatibility
checking (_check_cell_compatibility) runs on ACTIVE plantings only —
a planned planting doesn't yet compete for the cell's real water
chemistry, so checking it there would be a false alarm about a
condition that doesn't exist yet; get_bed_layout() below still surfaces
a planned planting's species range for the visual to warn about
up front, just not as a live alert.
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
        """Records a planting that has ALREADY happened, right now —
        planted_date is set to the real current time. For a future
        planting you're staging ahead of time, use plan() instead."""
        cur = self.db.execute(
            "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, variety, "
            "expected_harvest_date, quantity_planted, expected_yield_amount, expected_yield_unit, "
            "planted_date, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'active')",
            (grow_bed_name, cell_id, species_id, variety, expected_harvest_date,
             quantity_planted, expected_yield_amount, expected_yield_unit),
        )
        self.db.commit()
        planting_id = cur.lastrowid

        self._check_cell_compatibility(cell_id)
        return planting_id

    def plan(self, grow_bed_name: str, cell_id: int, species_id: int,
             target_plant_date: str = None, variety: str = None,
             expected_harvest_date: str = None, quantity_planted: int = None,
             expected_yield_amount: float = None, expected_yield_unit: str = None,
             notes: str = None) -> int:
        """Stages a future planting — status 'planned', planted_date
        explicitly left NULL (nothing's actually gone in the ground/bed
        yet). Doesn't run the live cell-compatibility check: that's
        about ACTIVE plantings currently sharing real water chemistry,
        and a plan doesn't affect that yet. get_bed_layout() still
        surfaces the planned species' range so the visual can flag an
        incompatibility before it becomes a real problem."""
        cur = self.db.execute(
            "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, variety, "
            "expected_harvest_date, quantity_planted, expected_yield_amount, expected_yield_unit, "
            "target_plant_date, planted_date, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'planned', ?)",
            (grow_bed_name, cell_id, species_id, variety, expected_harvest_date,
             quantity_planted, expected_yield_amount, expected_yield_unit,
             target_plant_date, notes),
        )
        self.db.commit()
        return cur.lastrowid

    def convert_to_active(self, planting_id: int, quantity_planted: int = None) -> dict:
        """The real moment a planned planting actually happens — flips
        'planned' to 'active' and sets the real planted_date to now.
        quantity_planted can be corrected here if the real count ended
        up different from what was planned. Raises ValueError for a
        planting that isn't currently 'planned' — converting an
        already-active/harvested/failed row would silently rewrite
        real history, not stage a new plant."""
        row = self.db.execute(
            "SELECT status FROM bed_plantings WHERE id = ?", (planting_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"no planting {planting_id}")
        if row[0] != "planned":
            raise ValueError(
                f"planting {planting_id} is '{row[0]}', not 'planned' — "
                f"only a planned planting can be converted to active"
            )
        if quantity_planted is not None:
            self.db.execute(
                "UPDATE bed_plantings SET status = 'active', planted_date = datetime('now'), "
                "quantity_planted = ? WHERE id = ?",
                (quantity_planted, planting_id),
            )
        else:
            self.db.execute(
                "UPDATE bed_plantings SET status = 'active', planted_date = datetime('now') "
                "WHERE id = ?",
                (planting_id,),
            )
        self.db.commit()

        cell_id = self.db.execute(
            "SELECT cell_id FROM bed_plantings WHERE id = ?", (planting_id,)
        ).fetchone()[0]
        self._check_cell_compatibility(cell_id)
        return {"planting_id": planting_id, "status": "active"}

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
            SELECT bp.*, sp.common_name, sp.ph_min, sp.ph_max, sp.ec_min, sp.ec_max,
                   sp.temp_water_min, sp.temp_water_max
            FROM bed_plantings bp
            JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status = 'active'
        """
        params = ()
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params = (cell_id,)
        return [dict(r) for r in self.db.execute(q, params).fetchall()]

    def get_planned_plantings(self, cell_id: int = None) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        q = """
            SELECT bp.*, sp.common_name, sp.ph_min, sp.ph_max, sp.ec_min, sp.ec_max,
                   sp.temp_water_min, sp.temp_water_max
            FROM bed_plantings bp
            JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status = 'planned'
        """
        params = ()
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params = (cell_id,)
        return [dict(r) for r in self.db.execute(q, params).fetchall()]

    def get_bed_layout(self, cell_id: int = None) -> list[dict]:
        """Every real grow bed, with its planned/active/recent
        plantings grouped underneath — the data source for the
        planting-planner visual. Recently harvested/failed plantings
        (last 30 days) are included too, dimmed by status in the
        visual, since a bed that just got cleared is still useful
        context, not just an empty box."""
        self.db.row_factory = sqlite3.Row
        bed_q = "SELECT * FROM grow_beds"
        bed_params = ()
        if cell_id is not None:
            bed_q += " WHERE cell_id = ?"
            bed_params = (cell_id,)
        beds = [dict(r) for r in self.db.execute(bed_q, bed_params).fetchall()]

        planting_q = """
            SELECT bp.*, sp.common_name, sp.organism_type, sp.days_to_maturity,
                   sp.ph_min, sp.ph_max, sp.temp_water_min, sp.temp_water_max
            FROM bed_plantings bp
            JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status IN ('planned', 'active')
               OR (bp.status IN ('harvested', 'failed') AND bp.planted_date >= datetime('now', '-30 days'))
        """
        plantings = [dict(r) for r in self.db.execute(planting_q).fetchall()]

        for bed in beds:
            bed["plantings"] = [p for p in plantings if p["grow_bed_name"] == bed["name"]]
        return beds

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
        neither one thrives. This doesn't block the planting; it warns.

        Checks pH AND water temperature independently — a real gap found
        while seeding a broader species list (core/species_registry.py):
        Cucumber and Spinach share exactly one point of pH overlap (6.0)
        so a pH-only check passes them as "compatible", but their water
        temp ranges (70-80F vs 50-68F) don't overlap at all. Two
        independent checks, not one combined score, so each warning names
        the actual dimension that's incompatible rather than a vague
        "these don't match"."""
        plantings = self.get_current_plantings(cell_id)
        plant_only = [p for p in plantings if p["ph_min"] is not None]
        if len(plant_only) < 2:
            return

        names = ", ".join(p["common_name"] for p in plant_only)

        overlap_ph_min = max(p["ph_min"] for p in plant_only)
        overlap_ph_max = min(p["ph_max"] for p in plant_only)
        if overlap_ph_min > overlap_ph_max:
            message = (
                f"Cell {cell_id}: plantings ({names}) have NO overlapping pH range — "
                f"they cannot both thrive sharing this cell's water. Consider moving "
                f"one to a separate cell."
            )
            logger.warning(message)
            if self.notifier:
                self.notifier.dispatch("warning", message, source="bed_planting")

        temp_plantings = [p for p in plant_only if p["temp_water_min"] is not None and p["temp_water_max"] is not None]
        if len(temp_plantings) >= 2:
            overlap_temp_min = max(p["temp_water_min"] for p in temp_plantings)
            overlap_temp_max = min(p["temp_water_max"] for p in temp_plantings)
            if overlap_temp_min > overlap_temp_max:
                temp_names = ", ".join(p["common_name"] for p in temp_plantings)
                message = (
                    f"Cell {cell_id}: plantings ({temp_names}) have NO overlapping water "
                    f"temperature range — they cannot both thrive sharing this cell's water. "
                    f"Consider moving one to a separate cell."
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
                "since a cell has one water chemistry for every bed on it. Also supports real "
                "PLANNING: stage a future planting (bed + species + target date) before it's "
                "physically done, then convert it to active once it actually happens."
            ),
            data_produced=["current plantings per bed, with species/variety/planted date",
                            "planned (not-yet-planted) plantings, staged ahead of time",
                            "every real grow bed with its planned/active/recent plantings grouped, "
                            "for the planting-planner visual",
                            "expected vs actual yield comparisons", "water usage log with rationale"],
            actions_possible=["record a new planting that's already happened",
                               "stage a planned future planting (not yet real)",
                               "convert a planned planting to active once it actually happens",
                               "mark harvested or failed",
                               "record water usage with a reason",
                               "check whether current ACTIVE plantings in a cell are chemically "
                               "compatible"],
            limits_and_safety=(
                "Warns, does not block — planting something incompatible is allowed, "
                "you just get told about it. Compatibility check is a plausibility check "
                "against known ranges, not a guarantee of real-world outcome. The live "
                "compatibility check only ever runs against ACTIVE plantings — a planned "
                "planting doesn't yet compete for the cell's real water chemistry, so it's "
                "never checked there (a false alarm about a condition that doesn't exist yet); "
                "the planting-planner visual still surfaces a planned species' documented range "
                "so an incompatibility can be seen before it's staged for real. "
                "convert_to_active() refuses (raises) on anything that isn't currently "
                "'planned' — it can't be used to silently rewrite already-real history."
            ),
            example_questions=["What's planted in Cell A?", "Can lettuce and basil share a cell?",
                                "What's planned for Bed A1?", "Has the lettuce I planned actually gone in yet?"],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed compatible plantings (lettuce+basil, "
                "overlapping ranges) produce no warning; a fabricated incompatible species "
                "correctly triggered the warning",
                "scenarios.py::scenario_bed_planting_plan_and_convert — confirmed plan() creates "
                "a real 'planned' row with planted_date left NULL, convert_to_active() correctly "
                "flips it to 'active' with a real planted_date set, and the compatibility check "
                "only fires on the ACTIVE result, not while it was still planned",
                "scenarios.py::scenario_bed_planting_convert_guards_real_history — confirmed "
                "convert_to_active() refuses (raises ValueError) on an already-active planting, "
                "rather than silently rewriting its real planted_date",
                "scenarios.py::scenario_bed_planting_get_bed_layout — confirmed get_bed_layout() "
                "correctly groups a real bed's planned AND active plantings together, by bed name",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # record-keeping only, no hardware of its own
