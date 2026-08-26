"""
MIA Homestead — Species Registry
v0.1

The "what does this organism actually want" reference. Seeded with
baseline horticultural/aquaculture data on first run; individual values
get refined by the experiment system as real evidence accumulates
(source flips from 'baseline' to 'experiment_derived' when that
happens, so you can always tell a textbook number from an earned one).

This is knowledge, not control — a cell's actual live target comes from
target_overrides (see experiment_manager.py), not directly from here.
This table informs what a good target IS; it doesn't enforce it.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.species_registry")

# Baseline values are commonly-cited aquaponics/hydroponics ranges —
# treat as a reasonable starting point, not gospel. Real conditions
# (your specific system, water source, climate) will differ.
BASELINE_SPECIES = [
    {
        "common_name": "Lettuce", "organism_type": "plant",
        "scientific_name": "Lactuca sativa",
        "ph_min": 6.0, "ph_max": 7.0, "ec_min": 700, "ec_max": 1400,
        "temp_water_min": 60, "temp_water_max": 75,
        "temp_air_min": 60, "temp_air_max": 75,
        "days_to_maturity": 45,
        "notes": "Forgiving, fast-growing — good first crop for validating the control loop.",
    },
    {
        "common_name": "Basil", "organism_type": "plant",
        "scientific_name": "Ocimum basilicum",
        "ph_min": 5.5, "ph_max": 6.5, "ec_min": 1000, "ec_max": 1600,
        "temp_water_min": 65, "temp_water_max": 80,
        "temp_air_min": 70, "temp_air_max": 85,
        "days_to_maturity": 60,
        "notes": "Wants slightly more acidic/higher EC than lettuce — a real example of "
                 "why two species with meaningfully different needs shouldn't share one cell.",
    },
    {
        "common_name": "Tilapia", "organism_type": "fish",
        "scientific_name": "Oreochromis niloticus",
        "ph_min": 6.5, "ph_max": 8.5, "ec_min": None, "ec_max": None,
        "temp_water_min": 75, "temp_water_max": 85,
        "temp_air_min": None, "temp_air_max": None,
        "days_to_maturity": 240,  # to harvest size, not "maturity" in the reproductive sense
        "notes": "Wide tolerance, hardy — the reason it's a common first fish for aquaponics. "
                 "Water temp matters more than pH for tilapia specifically.",
    },
]


class SpeciesRegistry(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn
        self._seed_if_empty()

    def _seed_if_empty(self):
        count = self.db.execute("SELECT COUNT(*) FROM species_profiles").fetchone()[0]
        if count > 0:
            return
        for s in BASELINE_SPECIES:
            self.db.execute(
                """
                INSERT INTO species_profiles
                (common_name, organism_type, scientific_name, ph_min, ph_max,
                 ec_min, ec_max, temp_water_min, temp_water_max,
                 temp_air_min, temp_air_max, days_to_maturity, notes, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'baseline')
                """,
                (s["common_name"], s["organism_type"], s["scientific_name"],
                 s["ph_min"], s["ph_max"], s["ec_min"], s["ec_max"],
                 s["temp_water_min"], s["temp_water_max"],
                 s["temp_air_min"], s["temp_air_max"], s["days_to_maturity"], s["notes"]),
            )
        self.db.commit()
        logger.info("Seeded %d baseline species profiles", len(BASELINE_SPECIES))

    def get_profile(self, species_id: int) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM species_profiles WHERE id = ?", (species_id,)).fetchone()
        return dict(row) if row else None

    def find_by_name(self, common_name: str) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute(
            "SELECT * FROM species_profiles WHERE common_name LIKE ?", (f"%{common_name}%",)
        ).fetchone()
        return dict(row) if row else None

    def list_all(self) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute("SELECT * FROM species_profiles").fetchall()]

    def add_species(self, common_name: str, organism_type: str, **kwargs) -> int:
        cur = self.db.execute(
            "INSERT INTO species_profiles (common_name, organism_type, scientific_name, "
            "ph_min, ph_max, ec_min, ec_max, temp_water_min, temp_water_max, "
            "temp_air_min, temp_air_max, days_to_maturity, notes, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'baseline')",
            (common_name, organism_type, kwargs.get("scientific_name"),
             kwargs.get("ph_min"), kwargs.get("ph_max"),
             kwargs.get("ec_min"), kwargs.get("ec_max"),
             kwargs.get("temp_water_min"), kwargs.get("temp_water_max"),
             kwargs.get("temp_air_min"), kwargs.get("temp_air_max"),
             kwargs.get("days_to_maturity"), kwargs.get("notes")),
        )
        self.db.commit()
        return cur.lastrowid

    def refine_from_experiment(self, species_id: int, param_name: str, new_value: float) -> None:
        """Called when a completed experiment produces strong enough
        evidence to update the species knowledge base itself, not just
        one cell's target. Flips source to 'experiment_derived' so it's
        always clear this number was earned, not looked up."""
        column = {"ph_min": "ph_min", "ph_max": "ph_max",
                  "ec_min": "ec_min", "ec_max": "ec_max"}.get(param_name)
        if not column:
            return
        self.db.execute(
            f"UPDATE species_profiles SET {column} = ?, source = 'experiment_derived', "
            f"updated_at = datetime('now') WHERE id = ?",
            (new_value, species_id),
        )
        self.db.commit()
        logger.info("Species %s %s updated to %.2f from experiment evidence", species_id, param_name, new_value)

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="species_registry",
            display_name="Species Knowledge Base",
            purpose=(
                "Tracks ideal pH/EC/temperature ranges per plant and fish species, "
                "seeded from baseline horticultural data and refined over time as "
                "experiments produce real evidence."
            ),
            data_produced=["species profiles with ideal ranges, sourced as baseline or experiment-derived"],
            actions_possible=["add a new species profile", "refine an existing one from experiment evidence"],
            limits_and_safety=(
                "Baseline values are commonly-cited ranges, not guaranteed correct for your "
                "specific system — treat as a starting point. Never directly controls dosing; "
                "informs target_overrides, which is what the control loop actually reads."
            ),
            example_questions=["What pH does lettuce want?", "What's the ideal range for tilapia?"],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure knowledge base, no hardware of its own
