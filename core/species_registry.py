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
    {
        "common_name": "Kale", "organism_type": "plant",
        "scientific_name": "Brassica oleracea",
        "ph_min": 5.5, "ph_max": 6.5, "ec_min": 1250, "ec_max": 1600,
        "temp_water_min": 60, "temp_water_max": 75,
        "temp_air_min": 55, "temp_air_max": 75,
        "days_to_maturity": 60,
        "notes": "Cool-season leafy green, similar water/EC range to lettuce but tolerates "
                 "cooler air better — a reasonable companion crop in the same cell.",
    },
    {
        "common_name": "Spinach", "organism_type": "plant",
        "scientific_name": "Spinacia oleracea",
        "ph_min": 6.0, "ph_max": 7.0, "ec_min": 1800, "ec_max": 2300,
        "temp_water_min": 50, "temp_water_max": 68,
        "temp_air_min": 50, "temp_air_max": 70,
        "days_to_maturity": 45,
        "notes": "A heavier feeder than lettuce (higher EC) and genuinely cold-tolerant — "
                 "the narrowest warm-end temp tolerance of the plants here, worth flagging "
                 "before pairing with a warm-water fish tank's ambient heat.",
    },
    {
        "common_name": "Swiss Chard", "organism_type": "plant",
        "scientific_name": "Beta vulgaris subsp. vulgaris",
        "ph_min": 6.0, "ph_max": 6.5, "ec_min": 1800, "ec_max": 2300,
        "temp_water_min": 60, "temp_water_max": 75,
        "temp_air_min": 60, "temp_air_max": 75,
        "days_to_maturity": 55,
        "notes": "Similar profile to spinach but more heat-tolerant — a reasonable "
                 "warm-season substitute where spinach's air-temp ceiling is a problem.",
    },
    {
        "common_name": "Strawberry", "organism_type": "plant",
        "scientific_name": "Fragaria x ananassa",
        "ph_min": 5.5, "ph_max": 6.5, "ec_min": 1300, "ec_max": 1800,
        "temp_water_min": 60, "temp_water_max": 75,
        "temp_air_min": 60, "temp_air_max": 80,
        "days_to_maturity": 100,  # to first harvest, not full-season yield — a perennial
        "notes": "Perennial, not an annual harvest-once crop like the leafy greens above — "
                 "days_to_maturity here means first harvest, worth stating explicitly since "
                 "it reads misleadingly next to the others otherwise.",
    },
    {
        "common_name": "Cucumber", "organism_type": "plant",
        "scientific_name": "Cucumis sativus",
        "ph_min": 5.5, "ph_max": 6.0, "ec_min": 1700, "ec_max": 2500,
        "temp_water_min": 70, "temp_water_max": 80,
        "temp_air_min": 70, "temp_air_max": 85,
        "days_to_maturity": 60,
        "notes": "Warm-season, heaviest EC demand of the plants seeded here. Real case this "
                 "seeding pass found: Cucumber (pH 5.5-6.0) and Spinach (pH 6.0-7.0) share a "
                 "single point of pH overlap at 6.0, so the old pH-only compatibility check "
                 "would have passed them as compatible — but their water temps (70-80F vs "
                 "50-68F) don't overlap AT ALL. Fixed core/bed_planting.py's "
                 "_check_cell_compatibility() to also check temp_water overlap, not just pH, "
                 "over exactly this pair.",
    },
    {
        "common_name": "Channel Catfish", "organism_type": "fish",
        "scientific_name": "Ictalurus punctatus",
        "ph_min": 6.5, "ph_max": 8.5, "ec_min": None, "ec_max": None,
        "temp_water_min": 75, "temp_water_max": 85,
        "temp_air_min": None, "temp_air_max": None,
        "days_to_maturity": 300,
        "notes": "Similar warm-water/wide-pH tolerance to tilapia and a common alternative "
                 "where tilapia farming is regulated or restricted — check local rules before "
                 "assuming either is legal to stock.",
    },
    {
        "common_name": "Rainbow Trout", "organism_type": "fish",
        "scientific_name": "Oncorhynchus mykiss",
        "ph_min": 6.5, "ph_max": 8.0, "ec_min": None, "ec_max": None,
        "temp_water_min": 50, "temp_water_max": 65,
        "temp_air_min": None, "temp_air_max": None,
        "days_to_maturity": 365,
        "notes": "Cold-water fish — a genuine contrast to tilapia/catfish's warm-water "
                 "range. NOT checked by core/bed_planting.py's cell-compatibility warning, "
                 "though — that check only ever sees bed_plantings (grow-bed PLANTS); fish "
                 "are tracked via tanks.species, a free-text field with no species_profiles "
                 "link at all right now. This fish's real value here is as documented data, "
                 "not as an automatically-checked one — see Spinach/Cucumber below for the "
                 "actual compatibility-check gap this seeding pass found and fixed.",
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

    def refine_from_experiment(self, species_id: int, param_name: str, new_value: float,
                                evidence_note: str = None) -> bool:
        """Called when a completed AND human-approved experiment produces
        real evidence about a species, not just one cell's target
        (core/experiment_manager.py's approve_parameter_change()) —
        this is what makes the species knowledge base itself improve
        from confirmed results, benefiting every future cell/planting of
        that species, not just the one cell the experiment ran on.

        Self-gating, deliberately: only ever EXTENDS the known-good range
        (a lower value than the current _min, or a higher value than the
        current _max), never narrows it. A single before/after comparison
        moving a value further INTO the already-documented range doesn't
        teach anything new about the species — it's just fixing one
        cell's config drift toward what's already known, and blindly
        overwriting on every call would let one N=1 result silently
        narrow a range that took several observations to establish.
        Returns True if it actually updated something, False if the new
        value didn't extend the range (nothing changed).

        Flips source to 'experiment_derived' so it's always clear this
        number was earned, not looked up, and appends evidence_note to
        notes for a human-readable trail of which experiment/cell/result
        justified the change."""
        column = {"ph_min": "ph_min", "ph_max": "ph_max",
                  "ec_min": "ec_min", "ec_max": "ec_max"}.get(param_name)
        if not column:
            return False

        row = self.db.execute(
            f"SELECT {column}, notes FROM species_profiles WHERE id = ?", (species_id,)
        ).fetchone()
        if not row:
            return False
        current_value, current_notes = row

        is_min = param_name.endswith("_min")
        extends_range = (
            current_value is None
            or (is_min and new_value < current_value)
            or (not is_min and new_value > current_value)
        )
        if not extends_range:
            logger.debug(
                "Species %s %s=%.2f did not extend current range (%.2f) — not updated",
                species_id, param_name, new_value, current_value if current_value is not None else float("nan"),
            )
            return False

        new_notes = current_notes or ""
        if evidence_note:
            new_notes = f"{new_notes}\n{evidence_note}".strip()

        self.db.execute(
            f"UPDATE species_profiles SET {column} = ?, source = 'experiment_derived', "
            f"notes = ?, updated_at = datetime('now') WHERE id = ?",
            (new_value, new_notes, species_id),
        )
        self.db.commit()
        logger.info("Species %s %s updated to %.2f from experiment evidence", species_id, param_name, new_value)
        return True

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
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed baseline seeding produces 3 correct "
                "species profiles (lettuce, basil, tilapia) with real horticultural ranges",
                "Correction 2026-08-31: refine_from_experiment() itself had NO real verification "
                "evidence despite being named in actions_possible since it was written — the "
                "entry above only ever proved baseline seeding. It also existed unwired (never "
                "called from anywhere) until this date. Real evidence now: "
                "scenarios.py::scenario_closed_loop_species_learning confirms a genuinely "
                "range-extending value updates ec_max and flips source to 'experiment_derived', "
                "and confirms the self-gating gate correctly REFUSES a value that doesn't extend "
                "the range (returns False, no update) — the never-narrow guarantee this method's "
                "own docstring promises.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure knowledge base, no hardware of its own
