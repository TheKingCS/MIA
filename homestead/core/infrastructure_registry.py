"""
MIA Homestead — Infrastructure Registry
v0.1

The physical-layer knowledge base: what's wired to what, why, and how
water actually flows through a cell. Wiring detail lives directly in
config/devices/roles/*.yaml (each control entry has relay_channel +
wiring_rationale) — this class just reads it back out, queryable by
actuator name. Plumbing lives in config/infrastructure/plumbing.yaml,
synced into plumbing_map on load.

This is what makes diagnostics specific instead of generic — "check
the sensor" vs "the pH sensor is wired through the pH Dosing MCU
(PORT 2, relay channel 1), mounted next to the pH-up/pH-down bottles;
that pump shares this line's plumbing with the sump return leg."
"""

import logging
import sqlite3
from pathlib import Path

import yaml

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.infrastructure_registry")

ROLES_DIR = Path(__file__).parent.parent / "config" / "devices" / "roles"
PLUMBING_PATH = Path(__file__).parent.parent / "config" / "infrastructure" / "plumbing.yaml"


class InfrastructureRegistry(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn
        self.roles = self._load_roles()
        self.plumbing = self._load_plumbing()
        self._sync_plumbing_to_db()

    def _load_roles(self) -> dict:
        roles = {}
        for path in ROLES_DIR.glob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            roles[data["role"]] = data
        return roles

    def _load_plumbing(self) -> dict:
        if not PLUMBING_PATH.exists():
            return {"cells": []}
        return yaml.safe_load(PLUMBING_PATH.read_text())

    def _sync_plumbing_to_db(self) -> None:
        for cell in self.plumbing.get("cells", []):
            for seg in cell.get("segments", []):
                self.db.execute(
                    """
                    INSERT INTO plumbing_map
                    (cell_id, segment_name, from_component, to_component,
                     pipe_diameter_in, flow_direction, driven_by_actuator, rationale, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(cell_id, segment_name) DO UPDATE SET
                        from_component = excluded.from_component,
                        to_component = excluded.to_component,
                        pipe_diameter_in = excluded.pipe_diameter_in,
                        flow_direction = excluded.flow_direction,
                        driven_by_actuator = excluded.driven_by_actuator,
                        rationale = excluded.rationale,
                        notes = excluded.notes
                    """,
                    (cell["cell_id"], seg["name"], seg["from_component"], seg["to_component"],
                     seg.get("pipe_diameter_in"), seg.get("flow_direction"),
                     seg.get("driven_by_actuator"), seg.get("rationale"), seg.get("notes")),
                )
        self.db.commit()

    # ---------- Wiring queries ----------

    @staticmethod
    def _normalize_actuator_name(name: str) -> str:
        """Case/punctuation-insensitive comparison key so 'pH-up pump',
        'ph up pump', and the internal 'ph_up_pump' all resolve to the
        same actuator. Real gap found via live-model testing
        (docs/OFFLINE_ASSISTANT_PLAN.md step 5): a model correctly
        grounded on this method's own (wrongly null) result and honestly
        reported 'not wired' — it wasn't fabricating, the exact-match
        lookup was just silently failing on a natural-language-formatted
        name a human or assistant would naturally produce."""
        import re
        return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    def get_wiring_for_actuator(self, actuator_name: str) -> dict | None:
        """Finds which MCU role, port, relay channel, and WHY that
        actuator is wired the way it is."""
        target = self._normalize_actuator_name(actuator_name)
        for role_id, role in self.roles.items():
            for control in role.get("controls", []):
                if self._normalize_actuator_name(control["actuator_name"]) == target:
                    return {
                        "role_id": role_id,
                        "role_display_name": role["display_name"],
                        "port_label": role.get("port_label"),
                        "mount_location": role.get("mount_location"),
                        "relay_channel": control.get("relay_channel"),
                        "wiring_rationale": control.get("wiring_rationale"),
                    }
        return None

    def get_all_wiring(self) -> list[dict]:
        results = []
        for role_id, role in self.roles.items():
            for control in role.get("controls", []):
                results.append({
                    "actuator_name": control["actuator_name"],
                    "role_id": role_id,
                    "port_label": role.get("port_label"),
                    "relay_channel": control.get("relay_channel"),
                    "wiring_rationale": control.get("wiring_rationale"),
                })
        return results

    # ---------- Plumbing queries ----------

    def get_plumbing_for_cell(self, cell_id: int) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        return [dict(r) for r in self.db.execute(
            "SELECT * FROM plumbing_map WHERE cell_id = ?", (cell_id,)
        ).fetchall()]

    def get_plumbing_for_actuator(self, actuator_name: str) -> list[dict]:
        """Which physical pipe segments does this actuator actually drive?
        Filters in Python (not SQL) so the same normalized-name matching
        as get_wiring_for_actuator() applies here too — table size in this
        project is small enough (per-cell plumbing segments) that this
        costs nothing real."""
        target = self._normalize_actuator_name(actuator_name)
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute("SELECT * FROM plumbing_map").fetchall()
        return [
            dict(r) for r in rows
            if self._normalize_actuator_name(r["driven_by_actuator"] or "") == target
        ]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="infrastructure_registry",
            display_name="Infrastructure Registry (Wiring & Plumbing)",
            purpose=(
                "Knows the physical wiring (which relay channel, which MCU, why) and "
                "plumbing (which pipe segment, what size, why routed that way) for every "
                "actuator in the system. Source of truth is human-authored config files, "
                "not inferred — this reflects the actual build, kept current by editing "
                "config/devices/roles/*.yaml and config/infrastructure/plumbing.yaml."
            ),
            data_produced=["wiring map (actuator -> MCU/port/relay channel + rationale)",
                            "plumbing map (pipe segments, sizes, flow direction + rationale)"],
            actions_possible=["look up wiring for a specific actuator",
                               "look up plumbing segments for a cell or actuator"],
            limits_and_safety=(
                "Read-only knowledge — never alters wiring or plumbing itself, only reports "
                "what the config files say is true. Accuracy depends entirely on those files "
                "being kept up to date when the physical build changes."
            ),
            example_questions=[
                "How is the pH-up pump wired?",
                "What's the plumbing between the tank and the grow bed?",
                "Why is that pipe 3/4 inch instead of 1 inch?",
            ],
            verification_evidence=[
                "Live manual test 2026-08-26: confirmed wiring/plumbing queries return correct, "
                "specific data (relay channel, port, mount location, pipe segments) for a real "
                "actuator and cell",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure knowledge layer, no hardware of its own
