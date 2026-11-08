"""
MIA Homestead — Succession Planning
v0.1

docs/SUSTAINING_FEATURES.md #19. bed_planting.py tracks current and
planned plantings but never proactively suggests what comes next as a
bed approaches harvest — it just becomes empty, with no forward-looking
suggestion.

Deliberately scoped as SUCCESSION (what/when to plant next), not true
crop-family ROTATION (deliberately avoiding replanting the same plant
family to break pest/disease and nutrient-depletion cycles) — real
rotation science needs a plant-family taxonomy this project doesn't
have anywhere in species_profiles. Suggesting "replant the same
species" here is a real, useful, compatibility-proven default, not a
rotation recommendation — conflating the two would be exactly the kind
of overclaimed sophistication this project's honesty discipline
refuses to ship. If plant-family data is ever added to
species_profiles, real rotation logic becomes a real, separate future
step from this one.
"""

import logging
import sqlite3
from datetime import datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.succession_planner")


class SuccessionPlanner(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def get_succession_suggestions(self, days_ahead: int = 14, cell_id: int = None) -> list[dict]:
        """Active plantings whose expected_harvest_date is within
        days_ahead (or already past — flagged overdue, not hidden),
        each with a real proposal: replant the same species (a
        known-compatible default — it was already thriving there), plus
        any OTHER species that would genuinely fit this cell's shared
        water chemistry once this planting is gone. Proposal only —
        never plants or converts anything on its own, same
        propose-then-a-human-acts pattern as
        propose_experiments_for_underperformance()."""
        self.db.row_factory = sqlite3.Row
        q = (
            "SELECT bp.*, sp.common_name FROM bed_plantings bp "
            "JOIN species_profiles sp ON sp.id = bp.species_id "
            "WHERE bp.status = 'active' AND bp.expected_harvest_date IS NOT NULL "
            "AND bp.expected_harvest_date <= datetime('now', ?)"
        )
        params = [f"+{days_ahead} days"]
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params.append(cell_id)
        plantings = [dict(r) for r in self.db.execute(q, params).fetchall()]

        now = datetime.utcnow().isoformat(sep=" ")
        suggestions = []
        for planting in plantings:
            already_planned = self.db.execute(
                "SELECT COUNT(*) FROM bed_plantings WHERE grow_bed_name = ? AND status = 'planned'",
                (planting["grow_bed_name"],),
            ).fetchone()[0] > 0

            candidates = self._compatible_species_for_cell(planting["cell_id"], exclude_planting_id=planting["id"])

            suggestions.append({
                "planting_id": planting["id"],
                "grow_bed_name": planting["grow_bed_name"],
                "cell_id": planting["cell_id"],
                "current_species": planting["common_name"],
                "expected_harvest_date": planting["expected_harvest_date"],
                "overdue": planting["expected_harvest_date"] < now,
                "already_has_next_planned": already_planned,
                "replant_same_species": planting["common_name"],
                "other_compatible_species": candidates["species"],
                "compatibility_note": candidates["note"],
            })
        return suggestions

    def _compatible_species_for_cell(self, cell_id: int, exclude_planting_id: int) -> dict:
        """What else could share this cell's water once exclude_planting_id
        is gone — same overlapping-range logic BedPlantingManager.
        _check_cell_compatibility() already uses for a live warning,
        reused here to PROPOSE candidates instead of just flagging a
        conflict."""
        others = self.db.execute(
            "SELECT sp.ph_min, sp.ph_max, sp.temp_water_min, sp.temp_water_max FROM bed_plantings bp "
            "JOIN species_profiles sp ON sp.id = bp.species_id "
            "WHERE bp.cell_id = ? AND bp.status = 'active' AND bp.id != ? AND sp.organism_type = 'plant'",
            (cell_id, exclude_planting_id),
        ).fetchall()

        if not others:
            rows = self.db.execute(
                "SELECT common_name FROM species_profiles WHERE organism_type = 'plant' ORDER BY common_name"
            ).fetchall()
            return {
                "species": [r[0] for r in rows],
                "note": "no other active planting would remain in this cell — any known plant species is compatible",
            }

        ph_bounds = [(r[0], r[1]) for r in others if r[0] is not None and r[1] is not None]
        temp_bounds = [(r[2], r[3]) for r in others if r[2] is not None and r[3] is not None]

        q = "SELECT common_name, ph_min, ph_max, temp_water_min, temp_water_max FROM species_profiles WHERE organism_type = 'plant'"
        candidates = []
        for row in self.db.execute(q).fetchall():
            name, ph_min, ph_max, temp_min, temp_max = row
            ok = True
            if ph_bounds and ph_min is not None and ph_max is not None:
                overlap_min = max([b[0] for b in ph_bounds] + [ph_min])
                overlap_max = min([b[1] for b in ph_bounds] + [ph_max])
                if overlap_min > overlap_max:
                    ok = False
            if ok and temp_bounds and temp_min is not None and temp_max is not None:
                overlap_min = max([b[0] for b in temp_bounds] + [temp_min])
                overlap_max = min([b[1] for b in temp_bounds] + [temp_max])
                if overlap_min > overlap_max:
                    ok = False
            if ok:
                candidates.append(name)

        return {
            "species": candidates,
            "note": (
                f"must overlap the pH/water-temp range of the {len(others)} other active "
                "planting(s) remaining in this cell's shared water"
            ),
        }

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="succession_planner",
            display_name="Succession Planning",
            purpose=(
                "Proactively suggests what to plant next in a bed as its current planting nears "
                "harvest, instead of the bed just becoming empty with no forward-looking "
                "suggestion. Reuses the real pH/water-temp compatibility check already enforced "
                "elsewhere so any suggested species genuinely fits the cell's shared water."
            ),
            data_produced=["succession suggestions — what to plant next, per bed nearing harvest"],
            actions_possible=[
                "list active plantings nearing (or past) their expected harvest date",
                "suggest replanting the same species (a proven-compatible default)",
                "suggest other species genuinely compatible with the cell's remaining shared water",
            ],
            limits_and_safety=(
                "Read/suggest only — never plants, converts, or approves anything on its own; a "
                "human acts on a suggestion via the existing plan()/convert_to_active() path. "
                "Deliberately NOT true crop-family rotation science (avoiding the same plant "
                "family to break pest/nutrient cycles) — species_profiles has no plant-family "
                "taxonomy to base that on; conflating the two would be overclaimed sophistication "
                "this project doesn't actually have."
            ),
            example_questions=["What should I plant next in Bed A1?", "Any beds coming up for harvest soon?"],
            verification_evidence=["scenarios.py::scenario_succession_planning"],
        )

    def describe_hardware_requirements(self) -> list:
        return []
