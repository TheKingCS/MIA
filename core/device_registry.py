"""
MIA Homestead — Device Registry
v0.1

Every physical MCU role (watering, fertilizer dosing, pH dosing, etc)
has a human-readable YAML file under config/devices/roles/ that IS the
setup instructions — port to plug into, where to mount it, what it
controls. This is deliberately not code: adding or changing a role
means editing a YAML file, not touching Python.

The pairing flow (real version, once MCU firmware exists):
1. MCU boots, sends an "announce" message over the Pi<->MCU link with
   its own hardware_id and (if pre-flashed) a requested_role label.
2. If requested_role matches a known role and that role isn't already
   claimed by a different device, auto-pair — no human needed.
3. If the role is missing, unknown, or already claimed by another
   device, it sits in the unpaired queue until a human (or the
   assistant, on a human's behalf) resolves it with pair_device().

This file's `announce_device()` is the entry point either way — it's
called the same way whether the trigger is real firmware sending a
message or main.py polling a pairing table. See MCU_PROTOCOL.md for the
wire-level "announce" message this maps to.
"""

import logging
import sqlite3
from pathlib import Path

import yaml

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.device_registry")

ROLES_DIR = Path(__file__).parent.parent / "config" / "devices" / "roles"


class DeviceRegistry(Describable):
    def __init__(self, db_conn: sqlite3.Connection, notifier=None):
        self.db = db_conn
        self.notifier = notifier
        self.roles = self._load_roles()

    def _load_roles(self) -> dict:
        roles = {}
        for path in ROLES_DIR.glob("*.yaml"):
            data = yaml.safe_load(path.read_text())
            roles[data["role"]] = data
        return roles

    def list_roles(self) -> list[dict]:
        return [
            {"role": r["role"], "display_name": r["display_name"], "description": r["description"]}
            for r in self.roles.values()
        ]

    def get_setup_instructions(self, role: str) -> str:
        r = self.roles.get(role)
        if not r:
            available = ", ".join(self.roles.keys())
            return f"No role called '{role}'. Available roles: {available}"
        return (
            f"=== {r['display_name']} ===\n"
            f"{r['description'].strip()}\n\n"
            f"{r['setup_instructions'].strip()}"
        )

    # ---------- Announce / pairing ----------

    def announce_device(self, hardware_id: str, requested_role: str = None) -> dict:
        """Called when a device shows up (real handshake later, manual
        test call today). Auto-pairs if the requested role is known and
        unclaimed; otherwise queues it for human resolution."""
        existing = self.db.execute(
            "SELECT id, role, status FROM device_registrations WHERE hardware_id = ?",
            (hardware_id,),
        ).fetchone()

        if existing:
            self.db.execute(
                "UPDATE device_registrations SET last_seen = datetime('now') WHERE hardware_id = ?",
                (hardware_id,),
            )
            self.db.commit()
            return {"hardware_id": hardware_id, "status": existing[2], "role": existing[1]}

        if requested_role and requested_role in self.roles:
            role_claimed = self.db.execute(
                "SELECT id FROM device_registrations WHERE role = ? AND status = 'paired'",
                (requested_role,),
            ).fetchone()
            if not role_claimed:
                return self._pair(hardware_id, requested_role)

        # Unknown role, missing role, or role already claimed by another
        # device — needs a human to sort out.
        self.db.execute(
            "INSERT INTO device_registrations (hardware_id, role, status) VALUES (?, ?, 'needs_attention')",
            (hardware_id, requested_role),
        )
        self.db.commit()
        logger.warning(
            "New device %s needs attention (requested_role=%s) — check unpaired devices",
            hardware_id, requested_role,
        )
        if self.notifier:
            self.notifier.dispatch(
                "warning",
                f"New device plugged in (id: {hardware_id[:8]}...) needs a role assigned. "
                f"Requested: {requested_role or 'none specified'}.",
                source="device_registry",
            )
        return {"hardware_id": hardware_id, "status": "needs_attention", "role": requested_role}

    def pair_device(self, hardware_id: str, role: str, cell_id: int = None) -> dict:
        """Manual/assistant-driven pairing — for a device already sitting
        in needs_attention, or forcing a specific role assignment."""
        if role not in self.roles:
            raise ValueError(f"Unknown role '{role}'. Available: {list(self.roles.keys())}")
        existing = self.db.execute(
            "SELECT id FROM device_registrations WHERE hardware_id = ?", (hardware_id,)
        ).fetchone()
        if existing:
            return self._pair(hardware_id, role, cell_id, update=True)
        return self._pair(hardware_id, role, cell_id, update=False)

    def _pair(self, hardware_id: str, role: str, cell_id: int = None, update: bool = False) -> dict:
        role_def = self.roles[role]
        target_cell = cell_id if cell_id is not None else role_def.get("default_cell_id")

        if update:
            self.db.execute(
                "UPDATE device_registrations SET role = ?, cell_id = ?, status = 'paired', "
                "paired_at = datetime('now'), last_seen = datetime('now') WHERE hardware_id = ?",
                (role, target_cell, hardware_id),
            )
        else:
            self.db.execute(
                "INSERT INTO device_registrations (hardware_id, role, cell_id, status, paired_at) "
                "VALUES (?, ?, ?, 'paired', datetime('now'))",
                (hardware_id, role, target_cell),
            )
        self.db.commit()

        self._ensure_actuators_exist(role_def, target_cell)

        logger.info("Paired device %s as role '%s' (cell %s)", hardware_id, role, target_cell)
        if self.notifier:
            self.notifier.dispatch(
                "info",
                f"Device {hardware_id[:8]}... paired as {role_def['display_name']}",
                source="device_registry",
            )
        return {"hardware_id": hardware_id, "status": "paired", "role": role, "cell_id": target_cell}

    def _ensure_actuators_exist(self, role_def: dict, cell_id: int) -> None:
        """Once a device is paired, make sure the actuators it's supposed
        to control actually exist in the DB — so the control modules
        have something to command the moment the MCU is live."""
        for control in role_def.get("controls", []):
            existing = self.db.execute(
                "SELECT id FROM actuators WHERE cell_id = ? AND name = ?",
                (cell_id, control["actuator_name"]),
            ).fetchone()
            if not existing:
                self.db.execute(
                    "INSERT INTO actuators (cell_id, type, name, safe_default_state) VALUES (?, ?, ?, ?)",
                    (cell_id, control["actuator_type"], control["actuator_name"], control["safe_default_state"]),
                )
        self.db.commit()

    def list_unpaired(self) -> list[dict]:
        rows = self.db.execute(
            "SELECT hardware_id, role, first_seen FROM device_registrations WHERE status = 'needs_attention'"
        ).fetchall()
        return [{"hardware_id": r[0], "requested_role": r[1], "first_seen": r[2]} for r in rows]

    def list_paired(self) -> list[dict]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute(
            "SELECT * FROM device_registrations WHERE status = 'paired'"
        ).fetchall()
        return [dict(r) for r in rows]

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="device_registry",
            display_name="Device Registry (Plug-and-Play MCUs)",
            purpose=(
                "Recognizes and pairs physical MCU controllers by role "
                "(watering, fertilizer dosing, pH dosing, etc), driven by "
                "human-readable config files rather than code. Auto-pairs "
                "when a device announces a known, unclaimed role; queues "
                "anything ambiguous for a human to resolve."
            ),
            data_produced=["paired device list", "unpaired/needs-attention device list"],
            actions_possible=[
                "pair a device to a role", "give plain-language setup instructions for a role",
                "auto-create the actuators a newly paired device controls",
            ],
            limits_and_safety=(
                "Never auto-pairs an ambiguous or role-conflicting device — "
                "always defers to a human. Pairing doesn't grant a device "
                "any control authority beyond what the safety MCU/dosing "
                "limits already allow."
            ),
            example_questions=[
                "How do I set up the watering MCU?",
                "Is there a device waiting to be paired?",
                "What's plugged in right now?",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        # Aggregate the MCUs implied by every defined role — this is the
        # one service where hardware needs are defined by config files
        # rather than hardcoded, so pull from the loaded roles directly.
        return [
            HardwareRequirement(
                item=f"MCU ({r['display_name']})", category="mcu", quantity=1,
                purpose=f"Controls: {', '.join(c['actuator_name'] for c in r.get('controls', []))}",
                est_unit_cost=20.0,
                notes=f"Port: {r.get('port_label', '?')}. ~$20 for an Adafruit ESP32 board — verify "
                      f"current price before ordering, see docs/HARDWARE_BOM_CURRENT.md. "
                      f"See config/devices/roles/{role_id}.yaml",
            )
            for role_id, r in self.roles.items()
        ]
