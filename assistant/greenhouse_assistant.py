"""
MIA Homestead — Greenhouse Assistant
v0.1

The conversational layer: lets Zac ask the greenhouse natural-language
questions and get answers grounded in real data via tool use. This is
NOT a control interface — it cannot bypass dosing limits or the safety
layer. It reads state and explains it; the module_registry + safety MCU
own all actual actuation.

Requires: anthropic python SDK (`pip install anthropic --break-system-packages`)
and ANTHROPIC_API_KEY set in environment.
"""

import json
import logging
import sqlite3
from pathlib import Path

import anthropic

from core.capability_registry import CapabilityRegistry
from core.hardware_registry import HardwareRegistry

logger = logging.getLogger("mia_homestead.assistant")

MODEL = "claude-sonnet-5"

PERSONALITY_PATH = Path(__file__).parent / "PERSONALITY.md"


TOOLS = [
    {
        "name": "get_current_status",
        "description": (
            "Get the latest sensor readings (pH, EC, temp, DO, water "
            "level, etc) for a given cell, or all cells if none specified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_open_alerts",
        "description": "Get all unresolved alerts, optionally filtered by minimum severity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                },
            },
        },
    },
    {
        "name": "get_dosing_history",
        "description": "Get recent dosing events for a cell, within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_yield_summary",
        "description": "Get harvest/yield events for a cell within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_power_status",
        "description": "Get the latest power telemetry — solar/battery/generator watts and battery SOC.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_inventory_status",
        "description": "Get current stock levels for all tracked inventory items (sensors, chemicals, spare parts).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_low_stock_items",
        "description": "Get inventory items at or below their reorder threshold.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_open_maintenance_tasks",
        "description": "Get open/in-progress maintenance tasks, optionally filtered by priority.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
        },
    },
    {
        "name": "create_maintenance_task",
        "description": (
            "Create a maintenance task — e.g. 'swap the MCU', 'fix a leak in Cell A', "
            "'order a replacement pH probe'. Use this whenever the user asks you to "
            "log, assign, or track a repair/replacement/inspection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "task_type": {"type": "string", "enum": ["repair", "replacement", "calibration", "inspection", "other"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                "description": {"type": "string"},
                "assigned_to": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO date, optional"},
            },
            "required": ["title", "task_type"],
        },
    },
    {
        "name": "get_revenue_summary",
        "description": "Get revenue transactions within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "get_to_order_list",
        "description": "Get items awaiting approve/deny decision in the reorder queue — things the system flagged as low stock.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_order",
        "description": "Approve a pending order in the to-order queue by its order_id.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "deny_order",
        "description": "Deny/dismiss a pending order in the to-order queue by its order_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_system_capabilities",
        "description": (
            "Get full detail on what a specific part of the system can do — "
            "actions it can take, limits, safety behavior. Use this whenever "
            "you're unsure what a module is capable of, or the user asks "
            "'what can you do' / 'can you handle X'. Omit module_id to get "
            "everything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
        },
    },
    {
        "name": "get_self_change_history",
        "description": (
            "Get the real history of how your own capabilities/hardware needs have "
            "changed as the underlying code was developed. Use when asked 'how have "
            "you changed', 'what's new about you', or similar self-development questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_active_help_requests",
        "description": "Get any active 'help requested' beacon triggers — critical issues where a human presence was detected near the greenhouse.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "acknowledge_help_request",
        "description": "Acknowledge an active help request so the beacon stops nudging — use when the user says they're on it / helping now.",
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "integer"}},
            "required": ["request_id"],
        },
    },
    {
        "name": "get_unpaired_devices",
        "description": "Get devices that are plugged in but haven't been assigned a role yet.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_device_setup_instructions",
        "description": "Get plain-language setup instructions for a device role (e.g. 'watering_mcu') — what to plug in, which port, where to mount it.",
        "input_schema": {
            "type": "object",
            "properties": {"role": {"type": "string"}},
            "required": ["role"],
        },
    },
    {
        "name": "pair_device",
        "description": "Assign a role to a device by its hardware_id — use when the user tells you what a newly plugged-in device is for.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hardware_id": {"type": "string"},
                "role": {"type": "string"},
            },
            "required": ["hardware_id", "role"],
        },
    },
    {
        "name": "get_wiring_info",
        "description": "Get how a specific actuator is wired — which MCU, port, relay channel, and why.",
        "input_schema": {
            "type": "object",
            "properties": {"actuator_name": {"type": "string"}},
            "required": ["actuator_name"],
        },
    },
    {
        "name": "get_plumbing_info",
        "description": "Get plumbing segments for a cell or a specific actuator, including pipe sizes and why routed that way.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "actuator_name": {"type": "string"},
            },
        },
    },
    {
        "name": "diagnose_alert",
        "description": "Get a specific, wiring-aware diagnosis for an alert — which physical component to check, not generic troubleshooting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "integer"},
                "create_task": {"type": "boolean", "default": False},
            },
            "required": ["alert_id"],
        },
    },
    {
        "name": "get_expected_vs_actual_yield",
        "description": "Compare expected vs actual yield for a specific planting.",
        "input_schema": {
            "type": "object",
            "properties": {"planting_id": {"type": "integer"}},
            "required": ["planting_id"],
        },
    },
    {
        "name": "get_water_usage",
        "description": "Get water usage history for a cell, with the reason behind each use.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_dosing_rationale",
        "description": "Get recent dosing events for a cell WITH the reasoning behind each dose, not just the amount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_bed_plantings",
        "description": "Get what's currently planted in each bed, optionally filtered by cell.",
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
        },
    },
    {
        "name": "record_planting",
        "description": "Record a new planting in a grow bed — use when the user tells you what they planted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "grow_bed_name": {"type": "string"},
                "cell_id": {"type": "integer"},
                "species_name": {"type": "string", "description": "e.g. 'lettuce', 'tilapia'"},
                "variety": {"type": "string"},
            },
            "required": ["grow_bed_name", "cell_id", "species_name"],
        },
    },
    {
        "name": "mark_planting_harvested",
        "description": "Mark a planting as harvested — use when the user says they harvested something.",
        "input_schema": {
            "type": "object",
            "properties": {"planting_id": {"type": "integer"}},
            "required": ["planting_id"],
        },
    },
    {
        "name": "mark_planting_failed",
        "description": "Mark a planting as failed — use when the user says a crop died or didn't make it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "planting_id": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["planting_id"],
        },
    },
    {
        "name": "record_water_usage",
        "description": "Log water usage with a reason — use when the user tells you they watered something, or to record a manual watering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "amount_gallons": {"type": "number"},
                "reason": {"type": "string"},
                "grow_bed_name": {"type": "string"},
            },
            "required": ["cell_id", "amount_gallons", "reason"],
        },
    },
    {
        "name": "add_species",
        "description": "Add a new species to the knowledge base — use when the user wants to track a plant or fish species that isn't already known.",
        "input_schema": {
            "type": "object",
            "properties": {
                "common_name": {"type": "string"},
                "organism_type": {"type": "string", "enum": ["plant", "fish"]},
                "scientific_name": {"type": "string"},
                "ph_min": {"type": "number"}, "ph_max": {"type": "number"},
                "ec_min": {"type": "number"}, "ec_max": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["common_name", "organism_type"],
        },
    },
    {
        "name": "update_maintenance_task_status",
        "description": "Change a maintenance task's status — use when the user says a repair is done, in progress, or should be cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["open", "in_progress", "done", "cancelled"]},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "assign_maintenance_task",
        "description": "Assign a maintenance task to someone — use when the user tells you who should handle a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "assigned_to": {"type": "string"},
            },
            "required": ["task_id", "assigned_to"],
        },
    },
    {
        "name": "deny_parameter_change",
        "description": "Deny a suggested permanent target change from a completed experiment.",
        "input_schema": {
            "type": "object",
            "properties": {"proposal_id": {"type": "integer"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "complete_experiment_now",
        "description": "End a running experiment early and get its result summary — use when the user wants to stop an experiment before its planned end date.",
        "input_schema": {
            "type": "object",
            "properties": {"experiment_id": {"type": "integer"}},
            "required": ["experiment_id"],
        },
    },
    {
        "name": "get_deadmans_switch_status",
        "description": "Check how long it's been since a human checked in, and whether the dead-man's-switch has escalated.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_species_profile",
        "description": "Get the ideal pH/EC/temperature range for a species by name.",
        "input_schema": {
            "type": "object",
            "properties": {"species_name": {"type": "string"}},
            "required": ["species_name"],
        },
    },
    {
        "name": "list_species",
        "description": "List all species in the knowledge base.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "propose_experiment",
        "description": (
            "Propose a controlled experiment — changing one target variable on a cell for a "
            "duration to see if it improves yield. Use when the user wants to test/tune conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "hypothesis": {"type": "string"},
                "variable_changed": {"type": "string", "enum": ["ph_target_min", "ph_target_max", "ec_target_min", "ec_target_max"]},
                "baseline_value": {"type": "number"},
                "test_value": {"type": "number"},
                "duration_days": {"type": "integer", "default": 14},
            },
            "required": ["cell_id", "hypothesis", "variable_changed", "baseline_value", "test_value"],
        },
    },
    {
        "name": "start_experiment",
        "description": "Start a proposed experiment — this actually changes the cell's live dosing target. Only call after explicit user approval.",
        "input_schema": {
            "type": "object",
            "properties": {"experiment_id": {"type": "integer"}},
            "required": ["experiment_id"],
        },
    },
    {
        "name": "get_active_experiments",
        "description": "Get experiments currently proposed or running.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pending_parameter_changes",
        "description": "Get evidence-based target changes awaiting approval from completed experiments.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_parameter_change",
        "description": "Approve a suggested permanent target change from a completed experiment.",
        "input_schema": {
            "type": "object",
            "properties": {"proposal_id": {"type": "integer"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "create_config_snapshot",
        "description": "Create a backup snapshot of current configuration before making a change.",
        "input_schema": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["label"],
        },
    },
    {
        "name": "list_config_snapshots",
        "description": "List available configuration backup snapshots.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "restore_config_snapshot",
        "description": "Restore configuration from a snapshot — reverts config files and control parameters, not history. Use only after explicit user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {"snapshot_id": {"type": "integer"}},
            "required": ["snapshot_id"],
        },
    },
    {
        "name": "get_verification_coverage",
        "description": "Get how many capabilities are actually proven vs just described — an honest maturity check.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_automated_actions",
        "description": "Get recent automated actions with their rationale (load-shedding, beacon triggers, etc) — the 'why did you do that' log for non-dosing actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "days": {"type": "integer", "default": 7},
            },
        },
    },
    {
        "name": "get_greenhouse_report",
        "description": "Get a compiled state-of-the-greenhouse report — yields, dosing, alerts, pending approvals, maintenance, experiments — instead of asking several separate questions.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 7}},
        },
    },
    {
        "name": "get_consumable_forecast",
        "description": "Get a projection of when an inventory item will hit its reorder threshold based on real consumption rate.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "integer"}},
            "required": ["item_id"],
        },
    },
    {
        "name": "record_human_checkin",
        "description": "Record that a human has checked in/interacted with the system — resets the dead-man's-switch escalation. Call this naturally whenever the user is actively conversing.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_hardware_needs_list",
        "description": "Get the running hardware shopping list — every physical component every module/service has declared it needs, aggregated with estimated cost.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_last_human_checkin",
        "description": "Get when a human last acknowledged an alert or viewed the dashboard.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


class GreenhouseAssistant:
    def __init__(self, db_path: str, api_key: str | None = None):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.client = anthropic.Anthropic(api_key=api_key)
        self.personality = PERSONALITY_PATH.read_text()
        self.history: list[dict] = []

    # ---------- Public interface ----------

    def ask(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})

        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=self._system_prompt(),
                tools=TOOLS,
                messages=self.history,
            )

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content
                    if block.type == "text"
                )
                self.history.append({"role": "assistant", "content": response.content})
                return final_text

            # Handle tool calls, feed results back, loop again
            self.history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = self._dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
            self.history.append({"role": "user", "content": tool_results})

    # ---------- System prompt ----------

    def _system_prompt(self) -> str:
        live_capabilities = CapabilityRegistry.render_compact(self.db)
        return (
            "You are the conversational voice of a homestead greenhouse "
            "aquaponics system called MIA Homestead. You answer questions "
            "about your own state using the tools provided — every factual "
            "claim must come from a tool call, never from assumption or "
            "prior turns if fresher data might exist. Follow this "
            "personality and behavior spec exactly:\n\n" + self.personality +
            "\n\n---\n\n"
            "The following is a LIVE, auto-generated list of every module "
            "currently registered in this system — it was built directly "
            "from the code at startup, not written by hand, so it's always "
            "current even as modules get added later. Use this to know what "
            "exists; call get_system_capabilities for full detail (actions "
            "possible, limits, safety behavior) on anything specific:\n\n" +
            live_capabilities
        )

    # ---------- Tool dispatch ----------

    def _dispatch_tool(self, name: str, tool_input: dict) -> dict:
        try:
            handler = getattr(self, f"_tool_{name}")
            return handler(**tool_input)
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return {"error": str(e)}

    def _tool_get_current_status(self, cell_id: int | None = None) -> dict:
        query = """
            SELECT s.cell_id, s.type, sr.value, sr.timestamp, sr.is_stale
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id)
        """
        params = ()
        if cell_id is not None:
            query += " AND s.cell_id = ?"
            params = (cell_id,)
        rows = self.db.execute(query, params).fetchall()
        return {"readings": [dict(r) for r in rows]}

    def _tool_get_open_alerts(self, min_severity: str | None = None) -> dict:
        order = {"info": 0, "warning": 1, "critical": 2}
        query = "SELECT * FROM alerts WHERE resolved = 0 ORDER BY timestamp DESC LIMIT 20"
        rows = [dict(r) for r in self.db.execute(query).fetchall()]
        if min_severity:
            rows = [r for r in rows if order.get(r["severity"], 0) >= order[min_severity]]
        return {"alerts": rows}

    def _tool_get_dosing_history(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            """
            SELECT * FROM dosing_events
            WHERE cell_id = ? AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"dosing_events": [dict(r) for r in rows]}

    def _tool_get_yield_summary(self, cell_id: int, days: int = 30) -> dict:
        rows = self.db.execute(
            """
            SELECT * FROM yield_events
            WHERE cell_id = ? AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"yield_events": [dict(r) for r in rows]}

    def _tool_get_power_status(self) -> dict:
        row = self.db.execute(
            "SELECT * FROM power_telemetry ORDER BY timestamp DESC LIMIT 5"
        ).fetchall()
        return {"recent_power_telemetry": [dict(r) for r in row]}

    def _tool_get_last_human_checkin(self) -> dict:
        row = self.db.execute(
            "SELECT * FROM human_checkins ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return {"last_checkin": dict(row) if row else None}

    def _tool_get_system_capabilities(self, module_id: str | None = None) -> dict:
        return {"capabilities": CapabilityRegistry.render_full(self.db, module_id=module_id)}

    def _tool_get_self_change_history(self, module_id: str | None = None, limit: int = 20) -> dict:
        return {"changes": CapabilityRegistry.get_change_history(self.db, module_id=module_id, limit=limit)}

    def _tool_create_config_snapshot(self, label: str, reason: str | None = None) -> dict:
        from core.backup_manager import BackupManager
        mgr = BackupManager(self.db)
        snapshot_id = mgr.create_snapshot(label, reason=reason)
        return {"snapshot_id": snapshot_id, "label": label}

    def _tool_list_config_snapshots(self) -> dict:
        rows = self.db.execute(
            "SELECT id, label, reason, created_at, is_auto_pre_update FROM config_snapshots ORDER BY created_at DESC"
        ).fetchall()
        return {"snapshots": [dict(r) for r in rows]}

    def _tool_restore_config_snapshot(self, snapshot_id: int) -> dict:
        from core.backup_manager import BackupManager
        mgr = BackupManager(self.db)
        return mgr.restore_snapshot(snapshot_id)

    def _tool_get_verification_coverage(self) -> dict:
        return CapabilityRegistry.get_verification_coverage(self.db)

    def _tool_get_recent_automated_actions(self, module_id: str | None = None, days: int = 7) -> dict:
        from core.action_log import get_recent_actions
        return {"actions": get_recent_actions(self.db, module_id=module_id, days=days)}

    def _tool_get_greenhouse_report(self, days: int = 7) -> dict:
        from core.report_generator import ReportGenerator
        gen = ReportGenerator(self.db)
        return {"report": gen.generate_report(days=days)}

    def _tool_get_consumable_forecast(self, item_id: int) -> dict:
        from core.inventory import InventoryManager
        inv = InventoryManager(self.db)
        forecast = inv.forecast_depletion(item_id)
        return {"forecast": forecast}

    def _tool_record_human_checkin(self) -> dict:
        from core.deadmans_switch import DeadMansSwitchMonitor
        mgr = DeadMansSwitchMonitor(self.db)
        mgr.record_checkin(method="assistant_conversation")
        return {"checked_in": True}

    def _tool_get_hardware_needs_list(self) -> dict:
        return {
            "bom_summary": HardwareRegistry.render_bom(self.db, group_by_module=False),
            "items": HardwareRegistry.get_all(self.db),
        }

    def _tool_get_wiring_info(self, actuator_name: str) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        infra = InfrastructureRegistry(self.db)
        wiring = infra.get_wiring_for_actuator(actuator_name)
        return {"wiring": wiring}

    def _tool_get_plumbing_info(self, cell_id: int | None = None, actuator_name: str | None = None) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        infra = InfrastructureRegistry(self.db)
        if actuator_name:
            return {"plumbing": infra.get_plumbing_for_actuator(actuator_name)}
        if cell_id is not None:
            return {"plumbing": infra.get_plumbing_for_cell(cell_id)}
        return {"error": "provide cell_id or actuator_name"}

    def _tool_diagnose_alert(self, alert_id: int, create_task: bool = False) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        from core.diagnostics import DiagnosticEngine
        from core.maintenance import MaintenanceManager
        infra = InfrastructureRegistry(self.db)
        maintenance = MaintenanceManager(self.db)
        engine = DiagnosticEngine(self.db, infra, maintenance=maintenance)
        return engine.diagnose_alert(alert_id, create_task=create_task)

    def _tool_get_expected_vs_actual_yield(self, planting_id: int) -> dict:
        from core.species_registry import SpeciesRegistry
        from core.bed_planting import BedPlantingManager
        species = SpeciesRegistry(self.db)
        bp = BedPlantingManager(self.db, species)
        return bp.get_expected_vs_actual(planting_id)

    def _tool_get_water_usage(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            "SELECT * FROM water_usage_events WHERE cell_id = ? AND timestamp >= datetime('now', ?) "
            "ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"water_usage": [dict(r) for r in rows]}

    def _tool_get_dosing_rationale(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            "SELECT dose_type, timestamp, reading_before, rationale, triggered_by FROM dosing_events "
            "WHERE cell_id = ? AND timestamp >= datetime('now', ?) ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"dosing_events": [dict(r) for r in rows]}

    def _tool_get_bed_plantings(self, cell_id: int | None = None) -> dict:
        q = """
            SELECT bp.*, sp.common_name, sp.ph_min, sp.ph_max, sp.ec_min, sp.ec_max
            FROM bed_plantings bp JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status = 'active'
        """
        params = ()
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params = (cell_id,)
        rows = self.db.execute(q, params).fetchall()
        return {"plantings": [dict(r) for r in rows]}

    def _tool_record_planting(self, grow_bed_name: str, cell_id: int, species_name: str, variety: str | None = None) -> dict:
        species_row = self.db.execute(
            "SELECT id FROM species_profiles WHERE common_name LIKE ?", (f"%{species_name}%",)
        ).fetchone()
        if not species_row:
            return {"error": f"No species profile found matching '{species_name}'. Use list_species to see options."}
        species_id = species_row[0]
        cur = self.db.execute(
            "INSERT INTO bed_plantings (grow_bed_name, cell_id, species_id, variety) VALUES (?, ?, ?, ?)",
            (grow_bed_name, cell_id, species_id, variety),
        )
        self.db.commit()
        return {"planting_id": cur.lastrowid, "grow_bed_name": grow_bed_name, "species": species_name}

    def _tool_mark_planting_harvested(self, planting_id: int) -> dict:
        self.db.execute("UPDATE bed_plantings SET status = 'harvested' WHERE id = ?", (planting_id,))
        self.db.commit()
        return {"planting_id": planting_id, "status": "harvested"}

    def _tool_mark_planting_failed(self, planting_id: int, notes: str | None = None) -> dict:
        self.db.execute("UPDATE bed_plantings SET status = 'failed', notes = ? WHERE id = ?", (notes, planting_id))
        self.db.commit()
        return {"planting_id": planting_id, "status": "failed"}

    def _tool_record_water_usage(self, cell_id: int, amount_gallons: float, reason: str,
                                   grow_bed_name: str | None = None) -> dict:
        cur = self.db.execute(
            "INSERT INTO water_usage_events (cell_id, grow_bed_name, amount_gallons, reason, triggered_by) "
            "VALUES (?, ?, ?, ?, 'manual_override')",
            (cell_id, grow_bed_name, amount_gallons, reason),
        )
        self.db.commit()
        return {"event_id": cur.lastrowid, "amount_gallons": amount_gallons, "reason": reason}

    def _tool_add_species(self, common_name: str, organism_type: str, scientific_name: str | None = None,
                            ph_min: float | None = None, ph_max: float | None = None,
                            ec_min: float | None = None, ec_max: float | None = None,
                            notes: str | None = None) -> dict:
        cur = self.db.execute(
            "INSERT INTO species_profiles (common_name, organism_type, scientific_name, "
            "ph_min, ph_max, ec_min, ec_max, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'baseline')",
            (common_name, organism_type, scientific_name, ph_min, ph_max, ec_min, ec_max, notes),
        )
        self.db.commit()
        return {"species_id": cur.lastrowid, "common_name": common_name}

    def _tool_update_maintenance_task_status(self, task_id: int, status: str) -> dict:
        completed_at = "datetime('now')" if status == "done" else "NULL"
        self.db.execute(
            f"UPDATE maintenance_tasks SET status = ?, completed_at = {completed_at} WHERE id = ?",
            (status, task_id),
        )
        self.db.commit()
        return {"task_id": task_id, "status": status}

    def _tool_assign_maintenance_task(self, task_id: int, assigned_to: str) -> dict:
        self.db.execute("UPDATE maintenance_tasks SET assigned_to = ? WHERE id = ?", (assigned_to, task_id))
        self.db.commit()
        return {"task_id": task_id, "assigned_to": assigned_to}

    def _tool_deny_parameter_change(self, proposal_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.deny_parameter_change(proposal_id)
        return {"proposal_id": proposal_id, "status": "denied"}

    def _tool_complete_experiment_now(self, experiment_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        return mgr.complete_experiment(experiment_id)

    def _tool_get_deadmans_switch_status(self) -> dict:
        from core.deadmans_switch import DeadMansSwitchMonitor
        mgr = DeadMansSwitchMonitor(self.db)
        return mgr.get_status()

    def _tool_get_species_profile(self, species_name: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM species_profiles WHERE common_name LIKE ?", (f"%{species_name}%",)
        ).fetchone()
        return {"profile": dict(row) if row else None}

    def _tool_list_species(self) -> dict:
        rows = self.db.execute("SELECT common_name, organism_type, ph_min, ph_max, ec_min, ec_max FROM species_profiles").fetchall()
        return {"species": [dict(r) for r in rows]}

    def _tool_propose_experiment(self, cell_id: int, hypothesis: str, variable_changed: str,
                                   baseline_value: float, test_value: float, duration_days: int = 14) -> dict:
        from datetime import datetime, timedelta
        planned_end = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        cur = self.db.execute(
            "INSERT INTO experiments (cell_id, hypothesis, variable_changed, baseline_value, "
            "test_value, planned_end_date, created_by) VALUES (?, ?, ?, ?, ?, ?, 'assistant')",
            (cell_id, hypothesis, variable_changed, baseline_value, test_value, planned_end),
        )
        self.db.commit()
        return {"experiment_id": cur.lastrowid, "status": "proposed", "planned_end_date": planned_end}

    def _tool_start_experiment(self, experiment_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.start_experiment(experiment_id)
        return {"experiment_id": experiment_id, "status": "running"}

    def _tool_get_active_experiments(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM experiments WHERE status IN ('proposed', 'approved', 'running')"
        ).fetchall()
        return {"experiments": [dict(r) for r in rows]}

    def _tool_get_pending_parameter_changes(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM parameter_change_proposals WHERE status = 'proposed'"
        ).fetchall()
        return {"proposals": [dict(r) for r in rows]}

    def _tool_approve_parameter_change(self, proposal_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.approve_parameter_change(proposal_id)
        return {"proposal_id": proposal_id, "status": "approved"}

    def _tool_get_active_help_requests(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM help_requests WHERE resolved = 0 ORDER BY created_at DESC"
        ).fetchall()
        return {"help_requests": [dict(r) for r in rows]}

    def _tool_acknowledge_help_request(self, request_id: int) -> dict:
        self.db.execute(
            "UPDATE help_requests SET acknowledged = 1, acknowledged_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        self.db.commit()
        return {"request_id": request_id, "acknowledged": True}

    def _tool_get_unpaired_devices(self) -> dict:
        rows = self.db.execute(
            "SELECT hardware_id, role, first_seen FROM device_registrations WHERE status = 'needs_attention'"
        ).fetchall()
        return {"unpaired_devices": [dict(r) for r in rows]}

    def _tool_get_device_setup_instructions(self, role: str) -> dict:
        from core.device_registry import DeviceRegistry
        registry = DeviceRegistry(self.db)
        return {"instructions": registry.get_setup_instructions(role)}

    def _tool_pair_device(self, hardware_id: str, role: str) -> dict:
        from core.device_registry import DeviceRegistry
        registry = DeviceRegistry(self.db)
        return registry.pair_device(hardware_id, role)

    def _tool_get_to_order_list(self) -> dict:
        rows = self.db.execute(
            """
            SELECT io.id AS order_id, ii.name, ii.category, io.quantity, ii.unit,
                   io.cost, io.notes, ii.supplier
            FROM inventory_orders io
            JOIN inventory_items ii ON ii.id = io.item_id
            WHERE io.status = 'proposed'
            ORDER BY io.ordered_at ASC
            """
        ).fetchall()
        return {"pending_orders": [dict(r) for r in rows]}

    def _tool_approve_order(self, order_id: int) -> dict:
        self.db.execute(
            "UPDATE inventory_orders SET status = 'approved' WHERE id = ? AND status = 'proposed'",
            (order_id,),
        )
        self.db.commit()
        return {"order_id": order_id, "status": "approved"}

    def _tool_deny_order(self, order_id: int, reason: str | None = None) -> dict:
        notes_suffix = f" | denied: {reason}" if reason else " | denied"
        self.db.execute(
            "UPDATE inventory_orders SET status = 'denied', "
            "notes = COALESCE(notes, '') || ? WHERE id = ? AND status = 'proposed'",
            (notes_suffix, order_id),
        )
        self.db.commit()
        return {"order_id": order_id, "status": "denied"}

    def _tool_get_inventory_status(self) -> dict:
        rows = self.db.execute(
            "SELECT name, category, quantity_on_hand, unit, reorder_threshold FROM inventory_items"
        ).fetchall()
        return {"inventory": [dict(r) for r in rows]}

    def _tool_get_low_stock_items(self) -> dict:
        rows = self.db.execute(
            "SELECT name, category, quantity_on_hand, reorder_threshold, unit, supplier "
            "FROM inventory_items WHERE quantity_on_hand <= reorder_threshold"
        ).fetchall()
        return {"low_stock": [dict(r) for r in rows]}

    def _tool_get_open_maintenance_tasks(self, priority: str | None = None) -> dict:
        q = "SELECT * FROM maintenance_tasks WHERE status IN ('open', 'in_progress')"
        params = ()
        if priority:
            q += " AND priority = ?"
            params = (priority,)
        rows = self.db.execute(q, params).fetchall()
        return {"tasks": [dict(r) for r in rows]}

    def _tool_create_maintenance_task(
        self, title: str, task_type: str, priority: str = "medium",
        description: str | None = None, assigned_to: str | None = None,
        due_date: str | None = None,
    ) -> dict:
        cur = self.db.execute(
            """
            INSERT INTO maintenance_tasks
            (title, description, task_type, priority, assigned_to, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'assistant')
            """,
            (title, description, task_type, priority, assigned_to, due_date),
        )
        self.db.commit()
        return {"created_task_id": cur.lastrowid, "title": title, "priority": priority}

    def _tool_get_revenue_summary(self, days: int = 30) -> dict:
        rows = self.db.execute(
            "SELECT * FROM revenue_transactions WHERE timestamp >= datetime('now', ?) "
            "ORDER BY timestamp DESC",
            (f"-{days} days",),
        ).fetchall()
        total = sum(r["total_amount"] for r in rows) if rows else 0
        return {"transactions": [dict(r) for r in rows], "total": total}


if __name__ == "__main__":
    import os
    assistant = GreenhouseAssistant(
        db_path="mia_homestead.db",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    print("MIA Homestead assistant ready. Ctrl+C to exit.")
    while True:
        try:
            q = input("\nyou: ")
            print(f"\ngreenhouse: {assistant.ask(q)}")
        except KeyboardInterrupt:
            break
