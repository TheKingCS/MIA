"""
MIA Homestead — Pest / Disease Observation Log and Knowledge Base
v0.1

Nothing anywhere in this system logs or reasons about plant pests,
disease symptoms, or fish illness — a real gap alongside the water-
chemistry/plant-centric focus everything else has. Same two-part shape
as core/species_registry.py: a knowledge base (real, common symptoms
and guidance per organism type/species, seeded from real horticultural/
aquaculture knowledge) plus a log of real observations against it.

Deliberately NOT built as an automatic closed-loop refinement the way
core/species_registry.py's refine_from_experiment() works — a species'
pH/EC range is a clean number an experiment result can confirm or
extend; "was this symptom description accurate" is fuzzy, textual, and
doesn't have the same clean confirm/extend signal. Refining knowledge
entries here stays a manual add_knowledge()/human-edited action, not
an automated one — an honest scope decision, not an oversight.

Camera-based visual detection is a real, much bigger stretch goal (ties
into the AI HAT/NPU hardware docs/OFFLINE_ASSISTANT_PLAN.md already
flags as unproven) — not this version. This is the manual log + lookup
half only.
"""

import logging
import sqlite3

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.pest_disease")

# Real, commonly-documented aquaponics/aquarium pest and disease
# knowledge — same "real horticultural data, not fabricated" discipline
# core/species_registry.py's BASELINE_SPECIES already applies.
BASELINE_KNOWLEDGE = [
    {
        "organism_type": "plant", "name": "Aphids",
        "symptoms": "Small (1-3mm) soft-bodied insects clustered on new growth, leaf undersides, "
                    "and stems; sticky honeydew residue; curling or yellowing leaves; sometimes "
                    "visible ants tending them.",
        "guidance": "Introduce ladybugs or lacewings (natural predators), spray with insecticidal "
                    "soap or diluted neem oil, isolate heavily affected plants, and check nearby "
                    "plants — aphids spread fast.",
    },
    {
        "organism_type": "plant", "name": "Powdery Mildew",
        "symptoms": "White or gray powdery coating on leaf surfaces and stems, usually starting on "
                    "older/lower leaves; common in humid conditions with poor air circulation.",
        "guidance": "Improve air circulation (spacing, fans), remove and discard affected leaves "
                    "(don't compost them), avoid wetting foliage when watering, and reduce "
                    "humidity around the canopy if possible.",
    },
    {
        "organism_type": "plant", "name": "Root Rot",
        "symptoms": "Wilting despite adequate water/nutrients, roots that are brown/black and "
                    "mushy instead of white and firm, foul smell from the root zone, stunted growth.",
        "guidance": "Check dissolved oxygen and flow to the root zone (root rot is usually an "
                    "oxygen/flow problem, not a watering one, in an aquaponics system), remove "
                    "affected plants before it spreads, check water temperature isn't "
                    "consistently too warm.",
    },
    {
        "organism_type": "fish", "name": "Ich (White Spot Disease)",
        "symptoms": "Small white spots (like grains of salt) across the body and fins; fish "
                    "rubbing/flashing against surfaces; clamped fins; lethargy.",
        "guidance": "Gradually raise water temperature (accelerates the parasite's life cycle, "
                    "making it easier to treat), confirm water quality is otherwise good, "
                    "consider a proven ich treatment if severe — check compatibility with the "
                    "biofilter and plants first.",
    },
    {
        "organism_type": "fish", "name": "Fin Rot",
        "symptoms": "Fins appear frayed, ragged, or are visibly disintegrating, sometimes with "
                    "discolored (white/red) edges; often progresses from the tips inward.",
        "guidance": "Usually stress- or water-quality-driven — check pH/ammonia/nitrite "
                    "immediately (see core/biofilter_model.py), isolate the affected fish if "
                    "a bacterial infection is suspected to prevent spread.",
    },
    {
        "organism_type": "fish", "name": "Columnaris",
        "symptoms": "White or gray patches on the skin, often around the mouth ('cotton mouth') "
                    "or dorsal fin; can progress rapidly (hours to days).",
        "guidance": "Often fatal quickly if untreated — isolate affected fish immediately and "
                    "check water quality right away; this is one of the few fish conditions "
                    "where speed of response matters most.",
    },
]


class PestDisease(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn
        self._seed_if_empty()

    def _seed_if_empty(self):
        count = self.db.execute("SELECT COUNT(*) FROM pest_disease_knowledge").fetchone()[0]
        if count > 0:
            return
        for k in BASELINE_KNOWLEDGE:
            self.db.execute(
                "INSERT INTO pest_disease_knowledge (organism_type, name, symptoms, guidance, source) "
                "VALUES (?, ?, ?, ?, 'baseline')",
                (k["organism_type"], k["name"], k["symptoms"], k["guidance"]),
            )
        self.db.commit()
        logger.info("Seeded %d baseline pest/disease knowledge entries", len(BASELINE_KNOWLEDGE))

    # ---------- Knowledge base ----------

    def add_knowledge(self, organism_type: str, name: str, symptoms: str,
                       guidance: str = None, species_id: int = None) -> int:
        cur = self.db.execute(
            "INSERT INTO pest_disease_knowledge (organism_type, species_id, name, symptoms, "
            "guidance, source) VALUES (?, ?, ?, ?, ?, 'human_added')",
            (organism_type, species_id, name, symptoms, guidance),
        )
        self.db.commit()
        return cur.lastrowid

    def find_knowledge_by_name(self, name: str) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute(
            "SELECT * FROM pest_disease_knowledge WHERE name LIKE ?", (f"%{name}%",)
        ).fetchone()
        return dict(row) if row else None

    def list_knowledge(self, organism_type: str = None) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        query = "SELECT * FROM pest_disease_knowledge"
        params = ()
        if organism_type:
            query += " WHERE organism_type = ?"
            params = (organism_type,)
        return [dict(r) for r in self.db.execute(query, params).fetchall()]

    # ---------- Observations ----------

    def record_observation(self, cell_id: int, description: str, category: str = "other",
                            species_id: int = None, knowledge_id: int = None,
                            severity: str = None, action_taken: str = None, notes: str = None) -> int:
        if category not in ("pest", "disease", "other"):
            raise ValueError("category must be 'pest', 'disease', or 'other'")
        cur = self.db.execute(
            "INSERT INTO pest_disease_observations (cell_id, species_id, knowledge_id, category, "
            "description, severity, action_taken, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (cell_id, species_id, knowledge_id, category, description, severity, action_taken, notes),
        )
        self.db.commit()
        logger.info("Pest/disease observation logged for cell %s: %s", cell_id, description)
        return cur.lastrowid

    def get_observation_history(self, cell_id: int, days: int = 30) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM pest_disease_observations WHERE cell_id = ? "
            "AND timestamp >= datetime('now', ?) ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return [dict(r) for r in rows]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="pest_disease",
            display_name="Pest / Disease Observation Log and Knowledge Base",
            purpose=(
                "Tracks plant pest/disease and fish illness observations against a real, seeded "
                "knowledge base of common symptoms and guidance — a gap nothing else in this "
                "system covers."
            ),
            data_produced=["pest/disease knowledge entries", "observation history per cell"],
            actions_possible=[
                "look up known pest/disease symptoms and guidance by name or organism type",
                "add a new knowledge entry", "log a real observation for a cell",
                "get observation history for a cell",
            ],
            limits_and_safety=(
                "Purely a logging/knowledge-lookup layer — never touches dosing, actuators, or "
                "any control-loop decision. Knowledge entries are added manually (add_knowledge, "
                "same pattern as species_registry.add_species), never automatically refined from "
                "observations — unlike a species' numeric pH/EC range, 'was this symptom "
                "description accurate' doesn't have a clean confirm/extend signal, so this stays "
                "a deliberate human action, not an automated one. Camera-based visual detection "
                "is a real, much larger future step, not this version — this is the manual log + "
                "lookup half only."
            ),
            example_questions=[
                "What does powdery mildew look like?",
                "Log an observation: white spots on the tilapia",
                "Has anything been logged for Cell A recently?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_pest_disease_tracking — confirmed baseline knowledge "
                "seeds with 6 real entries (3 plant, 3 fish) and no duplicate seeding on a "
                "second construction; confirmed find_knowledge_by_name() and add_knowledge() "
                "work correctly; confirmed an observation can log linked to a known knowledge "
                "entry OR as a novel unlinked observation, and both retrieve correctly via "
                "get_observation_history().",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure logging/knowledge-lookup layer, no hardware of its own
