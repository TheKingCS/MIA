"""
MIA Homestead — MCU Transport Manager
v0.1

Orchestrates drivers/mcu_serial.py's protocol primitives — real gap
found live 2026-09-02 (docs/DAY_ONE_READINESS.md, item #2), confirmed
by grep: core/device_registry.py already built real pair_confirm
payloads but nothing ever sent one, and main.py's execute_command()
was explicitly a "v0.1 stand-in for real MCU dispatch," logging only.

Three real jobs:
1. Scans for and pairs new devices, closing
   docs/DEVICE_SETUP_GUIDE.md's own promise — "the system checks for
   it on its own within a few seconds... within about a minute" —
   which nothing actually implemented before this (announce_device()
   was "manual test call today").
2. Sends heartbeats to every paired link and dispatches real actuator
   commands over the right one, falling back to main.py's existing
   simulated-log behavior when no real MCU is paired for that
   actuator yet (which is every actuator, today — zero real hardware
   exists in this environment; that's the correct, honest state, not
   a bug).
3. Reacts to a paired MCU's own reported fallback_active state —
   SAFETY_SPEC.md's "safety MCU failed to hear from Pi" critical
   example, made real instead of theoretical.

Always safely does nothing when there's no serial hardware present
(list_available_ports() returns [], no links ever open) — same
"honestly does nothing when there's nothing to do" discipline as
config/location.yaml's weather gate or config/mia_home_sync.yaml's
destination gate. Real hardware only needs to prove the physical link
works; the protocol/pairing/dispatch/fallback logic here is already
scenario-proven against a fake in-memory port.

Deliberately NOT a MiaHomesteadModule — same "no sensor reading to go
stale" reasoning core/irrigation.py's and core/mia_home_sync.py's own
docstrings already give for the identical choice. A periodic check
called from main.py's loop instead.
"""

import logging
from datetime import datetime, timedelta

from contracts.capability import Describable
from contracts.mia_homestead_contract import raise_alert

logger = logging.getLogger("mia_homestead.mcu_transport")

DEFAULT_SCAN_INTERVAL_SECONDS = 60  # matches DEVICE_SETUP_GUIDE.md's own "within about a minute" promise


class McuTransportManager(Describable):
    def __init__(self, db_conn, device_registry, notifier=None,
                 scan_interval_seconds: int = DEFAULT_SCAN_INTERVAL_SECONDS):
        self.db = db_conn
        self.device_registry = device_registry
        self.notifier = notifier
        self.scan_interval_seconds = scan_interval_seconds
        self._links: dict[str, object] = {}       # hardware_id -> MCULink, paired devices only
        self._actuator_to_hardware_id: dict[int, str] = {}
        self._last_fallback_state: dict[str, bool] = {}  # hardware_id -> last known fallback_active

    # ---------- Pairing / discovery ----------

    def scan_for_new_devices(self, ports: list[str] | None = None, open_port_fn=None) -> list[dict]:
        """Called every main.py cycle — cheap, self-paced (a date
        check most cycles; only actually opens/listens on ports once
        scan_interval_seconds has genuinely elapsed, same is_due()
        pattern core/mia_home_sync.py already established).

        ports/open_port_fn: real hardware entry points
        (drivers.mcu_serial.list_available_ports/open_port) by
        default — overridable so this whole method is testable
        end-to-end against a fake in-memory link, same
        dependency-injection precedent as
        core.module_registry.ModuleRegistry's force_read_fn and
        core.deploy_manager.DeployManager's repo_path."""
        if not self._scan_due():
            return []
        self._record_scan_attempt()

        from drivers.mcu_serial import list_available_ports, open_port
        if ports is None:
            ports = list_available_ports()
        if open_port_fn is None:
            open_port_fn = open_port

        newly_paired = []
        already_linked_paths = {getattr(link.port, "port", None) for link in self._links.values()}
        for device_path in ports:
            if device_path in already_linked_paths:
                continue  # already an open, paired link on this port — don't re-probe it
            link = open_port_fn(device_path)
            if link is None:
                continue
            result = self.device_registry.listen_for_announce(link)
            if result is not None and result.get("status") == "paired":
                link.hardware_id = result["hardware_id"]
                self._links[result["hardware_id"]] = link
                self._rebuild_actuator_map()
                newly_paired.append(result)
            else:
                link.close()  # nothing paired on this port this pass — don't hold it open
        return newly_paired

    def _scan_due(self) -> bool:
        row = self.db.execute(
            "SELECT last_seen FROM system_heartbeat WHERE component = 'mcu_transport_scan' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return True
        elapsed = datetime.utcnow() - datetime.fromisoformat(row[0])
        return elapsed >= timedelta(seconds=self.scan_interval_seconds)

    def _record_scan_attempt(self) -> None:
        self.db.execute(
            "INSERT INTO system_heartbeat (component, last_seen) VALUES ('mcu_transport_scan', datetime('now'))"
        )
        self.db.commit()

    def _rebuild_actuator_map(self) -> None:
        """Real DB ids, rebuilt from the live device_registrations +
        actuators tables every time a device pairs — never assumed or
        cached stale, same discipline build_pair_confirm_payload()
        itself already uses for the ids it hands out."""
        self._actuator_to_hardware_id = {}
        for device in self.device_registry.list_paired():
            if device["hardware_id"] not in self._links:
                continue  # paired in the DB, but no open link this process has (e.g. from a prior run)
            try:
                payload = self.device_registry.build_pair_confirm_payload(device["role"], device["cell_id"])
            except ValueError:
                continue
            for control in payload["controls"]:
                self._actuator_to_hardware_id[control["actuator_id"]] = device["hardware_id"]

    # ---------- Heartbeats / command dispatch ----------

    def send_heartbeats(self) -> None:
        """Called every main.py cycle. Every paired link needs a real
        heartbeat regularly or MCU_PROTOCOL.md's own MCU-side fallback
        timeout engages — this is what keeps that from happening
        during genuinely healthy operation with nothing to command."""
        for link in self._links.values():
            link.send_heartbeat()

    def dispatch_command(self, cmd) -> bool:
        """Called from main.py's execute_command() for every proposed
        ActuatorCommand. Returns True if it was actually sent over a
        real MCU link (caller should NOT also log the old simulated
        line for this command); False if no real MCU is paired for
        this actuator yet, so the caller's existing simulated-log
        fallback applies — unchanged behavior for every actuator in
        this environment today."""
        hardware_id = self._actuator_to_hardware_id.get(cmd.actuator_id)
        if hardware_id is None:
            return False
        link = self._links.get(hardware_id)
        if link is None:
            return False
        duration_ms = int(cmd.duration_seconds * 1000) if cmd.duration_seconds else None
        return link.send_command(cmd.actuator_id, cmd.action, duration_ms=duration_ms)

    # ---------- Status / fallback detection ----------

    def poll_status(self) -> list[dict]:
        """Called every main.py cycle. Reads any pending ack/status
        messages from every open paired link — real, not theoretical,
        version of SAFETY_SPEC.md's 'safety MCU failed to hear from
        Pi' critical example: a status message reporting
        fallback_active:true raises a real CRITICAL alert (via
        raise_alert()'s existing dedup — one row, occurrence_count
        bumping, not a new row every poll). No bespoke resolve logic
        needed: once the MCU reports fallback_active:false again, this
        simply stops re-raising, and alert_manager's existing stale
        sweep auto-resolves it, same as everywhere else in this
        project. Returns every status/ack message actually read this
        call, for the caller to log if it wants."""
        messages = []
        for hardware_id, link in self._links.items():
            msg = link.read_message()
            if msg is None:
                continue
            messages.append(msg)
            self.db.execute(
                "UPDATE device_registrations SET last_seen = datetime('now') WHERE hardware_id = ?",
                (hardware_id,),
            )
            self.db.commit()
            if msg.get("type") == "status":
                self._handle_status(hardware_id, msg)
        return messages

    def _handle_status(self, hardware_id: str, msg: dict) -> None:
        fallback_active = bool(msg.get("fallback_active"))
        if fallback_active:
            raise_alert(
                self.db, "mcu_transport", "critical",
                f"mcu_transport: MCU {hardware_id[:8]}... reports fallback_active — "
                f"it stopped hearing from the Pi and has fallen back to hard-coded safe "
                f"defaults (SAFETY_SPEC.md: aeration/circulation on, dosing off)",
                self.notifier,
            )
        self._last_fallback_state[hardware_id] = fallback_active

    def get_status(self) -> dict:
        """Read-only — for conversational status checks. Never scans/
        sends anything itself, same 'a question shouldn't have a side
        effect' discipline as DeadMansSwitchMonitor.get_status().

        Deliberately reads DB-persisted facts (device_registrations,
        the mcu_transport_scan heartbeat), not just this instance's
        own in-memory _links — main.py and the assistant are separate
        processes (same reasoning main.py's own comment gives for why
        force_read_fn is None there), so an assistant-constructed
        instance would otherwise always report zero open links even
        while main.py's real, long-running instance has real ones —
        misleading, not just incomplete."""
        paired_devices = self.device_registry.list_paired()
        scan_row = self.db.execute(
            "SELECT last_seen FROM system_heartbeat WHERE component = 'mcu_transport_scan' "
            "ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "paired_device_count": len(paired_devices),
            "paired_devices": [
                {"hardware_id": d["hardware_id"], "role": d["role"], "cell_id": d["cell_id"],
                 "last_seen": d["last_seen"]}
                for d in paired_devices
            ],
            "last_scan_attempt": scan_row[0] if scan_row else None,
            "links_open_in_this_process": len(self._links),  # this instance's own in-process links only
        }

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="mcu_transport",
            display_name="MCU Transport",
            purpose=(
                "Real serial transport between the Pi and paired Safety MCUs (docs/MCU_PROTOCOL.md) — "
                "scans for and pairs new devices, sends heartbeats, dispatches real actuator commands "
                "over the correct MCU's link, and reacts to a paired MCU reporting it has fallen back "
                "to hard-coded safe defaults."
            ),
            data_produced=["which MCUs are currently paired and linked", "each link's last reported fallback state"],
            actions_possible=[
                "scan available serial ports for a new device and pair it",
                "send a real actuator command over an MCU's link",
                "detect and alert on a real fallback_active report",
            ],
            limits_and_safety=(
                "Always safely does nothing when no serial hardware is present — list_available_ports() "
                "returns [] with zero devices plugged in, exactly today's real environment, and every "
                "actuator command falls back to main.py's existing simulated-log behavior. A real "
                "fallback_active report raises a real, deduplicated CRITICAL alert rather than silently "
                "logging — matches SAFETY_SPEC.md's own critical-severity example for this exact "
                "condition."
            ),
            example_questions=["Is any MCU paired and connected right now?", "Has any MCU fallen back to safe mode?"],
            verification_evidence=[
                "scenarios.py::scenario_mcu_transport_pairs_over_a_real_link — confirmed a real "
                "announce message on a fake link results in a real pairing and a real pair_confirm "
                "sent back",
                "scenarios.py::scenario_mcu_transport_dispatches_real_command — confirmed a command "
                "for a paired actuator is sent over its real link, and an unpaired actuator correctly "
                "falls back (returns False) for the caller's existing simulated path",
                "scenarios.py::scenario_mcu_transport_fallback_raises_critical — confirmed a real "
                "fallback_active:true status message raises a real, deduplicated CRITICAL alert",
                "scenarios.py::scenario_mcu_transport_scan_paces_by_interval — confirmed scan pacing "
                "is real and enforced, same pattern as core/mia_home_sync.py's is_due()",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # the MCU itself is already priced under each device role's own hardware requirement
